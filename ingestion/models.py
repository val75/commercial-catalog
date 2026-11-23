"""Shared types for the ingestion layer.

The ingestion layer has exactly one job: turn any supported input into a single
normalized Markdown document. It does NOT decide how many quotes are inside that
document — that fan-out (one input -> N drafts) happens later, in the extraction
step, which is free to read one normalized doc and emit several quote drafts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SourceType(str, Enum):
    PASTED_TEXT = "pasted_text"
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"


@dataclass
class AdapterOut:
    """What a format adapter returns: content only, no provenance.

    Provenance (source type, original hash, filename) is attached by the
    dispatch layer so adapters stay pure content -> content functions.
    """

    markdown: str
    warnings: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


@dataclass
class NormalizedDoc:
    """The single common representation every input converges to.

    `markdown` is what the extraction step consumes. `warnings` surface things a
    human may want to know (a skipped scanned page, an empty sheet). `meta`
    carries light provenance/structure (page count, sheet names, original hash).
    """

    source_type: SourceType
    source_name: str
    markdown: str
    warnings: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.markdown.strip()
