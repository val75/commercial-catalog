"""Works out "Quantity installed": identical parts per server, for CPUs, memory, GPUs, drives, network adapters,
DPUs, power supplies and RAID controllers.

The component spec files store counts per server, but quotes state them either
per server ("2x CPU") or across the whole order ("(x8)" under 4 servers). The
model reports what's written and what it counts; this step does the arithmetic,
so a quantized model never has to.

Anything it can't settle is a flag for the user, never a guess. As agreed:
an unknown basis is always asked, a missing quantity is asked rather than taken
as 1, and the same part on several lines is asked rather than added up. CPUs are
also checked against the usual counts per server; memory and GPUs aren't, until
a list of valid counts is agreed. The chassis isn't counted: each item has one, on the item itself.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from extraction.schema import (
    CpuComponent,
    DpuComponent,
    GpuComponent,
    MemoryComponent,
    NicComponent,
    PsuComponent,
    QuantityBasis,
    QuoteItem,
    RaidControllerComponent,
    StorageComponent,
)
from validation.flags import Flag

USUAL_CPUS_PER_SERVER = (1, 2, 4, 8)


class Issue(str, Enum):
    NO_QUANTITY = "no_quantity"
    UNKNOWN_BASIS = "unknown_basis"
    NO_SERVER_COUNT = "no_server_count"
    UNEVEN_SPLIT = "uneven_split"
    NOT_A_COUNT = "not_a_count"
    UNUSUAL_COUNT = "unusual_count"
    SEVERAL_LINES = "several_lines"
    MIXED_MODELS = "mixed_models"


@dataclass(frozen=True)
class QuantityCheck:
    """The proposed count for review. With any flag, the user has to confirm or answer."""

    per_server: int | None
    calculated: bool = False
    explanation: str | None = None
    flags: list[Flag] = field(default_factory=list)


@dataclass(frozen=True)
class _Kind:
    component: type
    one: str
    many: str
    # The values that tell two parts apart, such as model or capacity.
    identity: Callable[[Any], dict[str, Any]]
    usual_counts: tuple[int, ...] | None = None


def _values(properties, names: tuple[str, ...]) -> dict[str, Any]:
    found = {name: getattr(properties, name) for name in names}
    return {name: prop.value for name, prop in found.items() if prop is not None}


CPU = _Kind(
    CpuComponent,
    "CPU",
    "CPUs",
    identity=lambda line: _values(line.cpu, ("model",)),
    usual_counts=USUAL_CPUS_PER_SERVER,
)
MEMORY = _Kind(
    MemoryComponent,
    "module",
    "modules",
    identity=lambda line: _values(line.memory, ("mpn", "model", "vendor_product_id", "capacity_gb")),
)
GPU = _Kind(
    GpuComponent,
    "GPU",
    "GPUs",
    identity=lambda line: _values(line.gpu, ("mpn", "model", "vendor_product_id", "memory_capacity_gb")),
)


NIC = _Kind(
    NicComponent,
    "network adapter",
    "network adapters",
    identity=lambda line: _values(line.nic, ("mpn", "model", "vendor_product_id", "port_speed_gbps")),
)


PSU = _Kind(
    PsuComponent,
    "power supply",
    "power supplies",
    identity=lambda line: _values(line.psu, ("mpn", "model", "vendor_product_id", "rated_output_w")),
)


DPU = _Kind(
    DpuComponent,
    "DPU",
    "DPUs",
    # The crypto variant too: crypto-enabled and disabled cards are different parts.
    identity=lambda line: _values(line.dpu, ("mpn", "model", "vendor_product_id", "crypto")),
)


def dpus_per_server(item: QuoteItem) -> QuantityCheck | None:
    """The DPUs per server for one quote item, or None if it has no DPU line."""
    return quantity_installed(item, DPU)


RAID_CONTROLLER = _Kind(
    RaidControllerComponent,
    "RAID controller",
    "RAID controllers",
    # The type too: a RAID controller and an HBA in one server are two roles, never added up.
    identity=lambda line: _values(line.raid_controller, ("mpn", "model", "vendor_product_id", "controller_type")),
)


def raid_controllers_per_server(item: QuoteItem) -> QuantityCheck | None:
    """The RAID controllers, HBAs and tri-mode cards per server for one quote item, or None if it has none."""
    return quantity_installed(item, RAID_CONTROLLER)


def psus_per_server(item: QuoteItem) -> QuantityCheck | None:
    """The power supplies per server for one quote item, or None if it has no power supply line."""
    return quantity_installed(item, PSU)


def nics_per_server(item: QuoteItem) -> QuantityCheck | None:
    """The network adapters per server for one quote item, or None if it has no adapter line."""
    return quantity_installed(item, NIC)


def cpus_per_server(item: QuoteItem) -> QuantityCheck | None:
    """The CPUs per server for one quote item, or None if it has no CPU line."""
    return quantity_installed(item, CPU)


def modules_per_server(item: QuoteItem) -> QuantityCheck | None:
    """The memory modules per server for one quote item, or None if it has no memory line."""
    return quantity_installed(item, MEMORY)


def gpus_per_server(item: QuoteItem) -> QuantityCheck | None:
    """The GPUs per server for one quote item, or None if it has no GPU line."""
    return quantity_installed(item, GPU)


STORAGE = _Kind(StorageComponent, "drive", "drives", identity=lambda line: {})


def storage_per_server(item: QuoteItem) -> list[QuantityCheck]:
    """The drives per server for each storage group, in order.

    Unlike CPUs, several storage lines are normal: each is an independent group
    (03-storage.md, section 3), so they're never flagged as mixed or added up.
    """
    return [
        _one_line(line, STORAGE, servers=item.quantity)
        for line in item.components
        if isinstance(line, StorageComponent)
    ]


def quantity_installed(item: QuoteItem, kind: _Kind) -> QuantityCheck | None:
    lines = [component for component in item.components if isinstance(component, kind.component)]
    if not lines:
        return None
    if len(lines) > 1:
        return _several_lines(lines, kind)
    return _one_line(lines[0], kind, servers=item.quantity)


def _several_lines(lines: list, kind: _Kind) -> QuantityCheck:
    identities = [kind.identity(line) for line in lines]
    for name in dict.fromkeys(key for identity in identities for key in identity):
        values = {identity[name] for identity in identities if name in identity}
        if len(values) > 1:
            listed = ", ".join(sorted(str(value) for value in values))
            return _ask(
                Issue.MIXED_MODELS,
                f"This server lists different {kind.many} ({name.replace('_', ' ')}: {listed}). "
                f"A server normally can't mix them.",
            )
    return _ask(
        Issue.SEVERAL_LINES,
        f"This server has {len(lines)} {kind.one} lines. Are they the same {kind.one}, "
        f"and should their counts be added up?",
    )


def _one_line(line, kind: _Kind, servers: int | None) -> QuantityCheck:
    quantity = line.quantity
    if quantity is None:
        return _ask(Issue.NO_QUANTITY, f"The quote doesn't say how many {kind.many}. How many are in each server?")
    if quantity < 1:
        return _ask(Issue.NOT_A_COUNT, f"The {kind.one} quantity reads as {quantity}, which isn't a count.")

    if line.quantity_basis is QuantityBasis.UNKNOWN:
        across = f" across all {servers} servers" if servers else " across the whole order"
        return _ask(
            Issue.UNKNOWN_BASIS,
            f"The quote says {quantity} {kind.many}. Is that {quantity} per server, or {quantity}{across}?",
        )

    if line.quantity_basis is QuantityBasis.PER_UNIT:
        return _checked(quantity, kind, calculated=False, explanation=f"As written: {quantity} per server")

    if servers is None or servers < 1:
        return _ask(
            Issue.NO_SERVER_COUNT,
            f"The quote says {quantity} {kind.many} for the whole order, but not how many servers, "
            f"so they can't be divided.",
        )
    if quantity % servers:
        return _ask(
            Issue.UNEVEN_SPLIT,
            f"{quantity} {kind.many} don't divide evenly across {servers} servers. How many are in each server?",
        )
    return _checked(
        quantity // servers,
        kind,
        calculated=True,
        explanation=f"Calculated: {quantity} {kind.many} across {servers} servers",
    )


def _checked(per_server: int, kind: _Kind, calculated: bool, explanation: str) -> QuantityCheck:
    flags = []
    if kind.usual_counts is not None and per_server not in kind.usual_counts:
        usual = ", ".join(str(count) for count in kind.usual_counts)
        flags.append(
            Flag(Issue.UNUSUAL_COUNT, f"{per_server} {kind.many} per server is unusual (expected {usual}). Is it right?")
        )
    return QuantityCheck(per_server=per_server, calculated=calculated, explanation=explanation, flags=flags)


def _ask(issue: Issue, message: str) -> QuantityCheck:
    return QuantityCheck(per_server=None, flags=[Flag(issue, message)])
