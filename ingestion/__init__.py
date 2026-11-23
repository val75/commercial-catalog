"""Commercial Catalog — ingestion layer.

Turns any supported input into one normalized Markdown document. Extraction
(the next step) reads that document and produces 1..N quote drafts.
"""

from .dispatch import ingest_file, ingest_text
from .models import AdapterOut, NormalizedDoc, SourceType

__all__ = [
    "ingest_text",
    "ingest_file",
    "NormalizedDoc",
    "SourceType",
    "AdapterOut",
]
