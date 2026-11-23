"""The SSD size rule (decision D-002).

Full server quotes are assumed to carry enterprise SSDs, which come in standard
sizes (1.92, 3.84, 7.68 and 15.36 TB). A rounded size, such as "3.8TB", is
recorded as the standard size automatically. A consumer-style size (2, 4 or
8 TB) only gets the standard size suggested, and the user decides. Any other
size is left alone.

This step only proposes. The quote's wording is kept beside the new value
(03-storage.md, rule 19), and review shows the change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from extraction.schema import CpuComponent, QuoteItem, StorageComponent
from validation.flags import Flag

# Rounded size as written -> the standard size, in TB.
AUTOMATIC = {1.9: 1.92, 3.8: 3.84, 7.6: 7.68, 15.0: 15.36}
SUGGESTED = {2.0: 1.92, 4.0: 3.84, 8.0: 7.68}


class CapacityIssue(str, Enum):
    CONSUMER_SIZE_ON_A_SERVER = "consumer_size_on_a_server"


@dataclass(frozen=True)
class CapacityCheck:
    """The proposed standard size. Automatic changes need no answer; suggestions do."""

    value: float
    unit: str
    automatic: bool
    explanation: str
    flags: list[Flag] = field(default_factory=list)


def is_full_server(item: QuoteItem) -> bool:
    """A quote item for a whole server, rather than loose parts: it has a CPU or a chassis."""
    return item.chassis is not None or any(isinstance(component, CpuComponent) for component in item.components)


def standard_ssd_capacity(drive: StorageComponent, full_server: bool) -> CapacityCheck | None:
    """The standard size for one drive, or None if the rule doesn't apply."""
    capacity, storage_type = drive.storage.capacity, drive.storage.storage_type
    if not full_server or capacity is None or capacity.unit != "TB":
        return None
    if storage_type is None or storage_type.value.strip().upper() != "SSD":
        return None

    written = round(capacity.value, 2)
    if written in AUTOMATIC:
        standard = AUTOMATIC[written]
        return CapacityCheck(
            value=standard,
            unit="TB",
            automatic=True,
            explanation=f"The quote says {written:g} TB; recorded as {standard:g} TB, the enterprise standard size",
        )
    if written in SUGGESTED:
        standard = SUGGESTED[written]
        return CapacityCheck(
            value=standard,
            unit="TB",
            automatic=False,
            explanation=f"The quote says {written:g} TB; the enterprise standard size would be {standard:g} TB",
            flags=[
                Flag(
                    CapacityIssue.CONSUMER_SIZE_ON_A_SERVER,
                    f"{written:g} TB is a consumer drive size. Server SSDs usually come as {standard:g} TB. "
                    f"Record it as {standard:g} TB?",
                    "capacity",
                )
            ],
        )
    return None
