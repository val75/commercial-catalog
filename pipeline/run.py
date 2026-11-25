"""One call from an upload to drafts ready for review (docs/05-ingestion-pipeline.md, stages 3-5).

    process_text(raw)            -> for copy-pasted email / SMS / chat
    process_file(data, filename) -> for uploaded PDF / Excel / CSV

Each runs ingestion, then extraction (the model, then cleanup), then the
deterministic checks in validation/. The checks only propose: a count per
server, a standard SSD size and every flag sit beside the draft, which stays as
extraction left it, so review can show what the quote said next to what the
checks suggest.

A failure stops the pipeline at its stage (an unsupported file type, an
unreachable model). An empty document, such as a scanned PDF whose pages were
all skipped, stops before the model: there's nothing to extract, and the
document's warnings say why.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from extraction.client import ModelSettings, extract_quotes
from extraction.schema import (
    Component,
    CpuComponent,
    DpuComponent,
    GpuComponent,
    MemoryComponent,
    NicComponent,
    PsuComponent,
    QuoteDraft,
    QuoteItem,
    RaidControllerComponent,
    StorageComponent,
)
from ingestion import ingest_file, ingest_text
from ingestion.models import NormalizedDoc
from validation import quantity
from validation.cpu_properties import check_cpu_properties
from validation.flags import Flag
from validation.gpu_properties import check_gpu_properties
from validation.memory_properties import check_memory_properties
from validation.properties import inferred_without_reason
from validation.quantity import QuantityCheck
from validation.ssd_capacity import CapacityCheck, is_full_server, standard_ssd_capacity
from validation.storage_properties import check_storage_properties


@dataclass(frozen=True)
class ComponentReview:
    """One component line and what the checks propose for it."""

    component: Component
    # Identical parts per server. Several lines of one kind share one check, the question about them.
    quantity: QuantityCheck | None = None
    # Storage only: the standard SSD size (decision D-002).
    capacity: CapacityCheck | None = None
    flags: list[Flag] = field(default_factory=list)


@dataclass(frozen=True)
class ItemReview:
    item: QuoteItem
    components: list[ComponentReview]
    # About the chassis, which sits on the item.
    flags: list[Flag] = field(default_factory=list)


@dataclass(frozen=True)
class QuoteReview:
    draft: QuoteDraft
    items: list[ItemReview]


@dataclass(frozen=True)
class PipelineResult:
    """The document (with its warnings and provenance) and each quote found in it."""

    document: NormalizedDoc
    quotes: list[QuoteReview]


def process_text(raw: str, source_name: str = "pasted-text", *, settings: ModelSettings | None = None) -> PipelineResult:
    return process_document(ingest_text(raw, source_name), settings=settings)


def process_file(data: bytes, filename: str, *, settings: ModelSettings | None = None) -> PipelineResult:
    return process_document(ingest_file(data, filename), settings=settings)


def process_document(document: NormalizedDoc, *, settings: ModelSettings | None = None) -> PipelineResult:
    """Extraction and checks for a document already ingested, such as one stored for review."""
    if document.is_empty:
        return PipelineResult(document, [])
    drafts = extract_quotes(document.markdown, settings=settings, source_name=document.source_name)
    return PipelineResult(document, [review_draft(draft) for draft in drafts])


def review_draft(draft: QuoteDraft) -> QuoteReview:
    """Every deterministic check on one draft, without changing it."""
    return QuoteReview(draft, [_review_item(item) for item in draft.items])


# The kinds counted per server, and each kind's property checks. Storage is
# counted per drive group instead (validation/quantity.py).
_KINDS = {
    CpuComponent: quantity.CPU,
    MemoryComponent: quantity.MEMORY,
    GpuComponent: quantity.GPU,
    NicComponent: quantity.NIC,
    DpuComponent: quantity.DPU,
    PsuComponent: quantity.PSU,
    RaidControllerComponent: quantity.RAID_CONTROLLER,
}
_PROPERTY_CHECKS = {
    CpuComponent: check_cpu_properties,
    MemoryComponent: check_memory_properties,
    GpuComponent: check_gpu_properties,
    StorageComponent: check_storage_properties,
    # No checks of their own yet: only the rule every type shares.
    NicComponent: lambda line: inferred_without_reason(line.nic),
    DpuComponent: lambda line: inferred_without_reason(line.dpu),
    PsuComponent: lambda line: inferred_without_reason(line.psu),
    RaidControllerComponent: lambda line: inferred_without_reason(line.raid_controller),
}


def _review_item(item: QuoteItem) -> ItemReview:
    counts = {kind: quantity.quantity_installed(item, _KINDS[kind]) for kind in _KINDS}
    drive_counts = iter(quantity.storage_per_server(item))
    full_server = is_full_server(item)

    components = []
    for line in item.components:
        kind = type(line)
        if kind is StorageComponent:
            count, capacity = next(drive_counts), standard_ssd_capacity(line, full_server)
        else:
            count, capacity = counts.get(kind), None
        check = _PROPERTY_CHECKS.get(kind)
        components.append(ComponentReview(line, count, capacity, check(line) if check else []))

    chassis_flags = inferred_without_reason(item.chassis) if item.chassis is not None else []
    return ItemReview(item, components, chassis_flags)
