"""Dispatch: choose the adapter, attach provenance, return a NormalizedDoc.

This is the single entry point the rest of the app (and later the FastAPI intake
endpoints) calls. Two public functions:

    ingest_text(raw)            -> for copy-pasted email / SMS / chat
    ingest_file(data, filename) -> for uploaded PDF / Excel / CSV

Both return a NormalizedDoc. We record a SHA-256 of the *original* input so the
same paste/file isn't imported twice and so extraction can be re-run later from
stored originals without a re-upload.
"""

from __future__ import annotations

import hashlib
import os

from .adapters import pdf as pdf_adapter
from .adapters import spreadsheet as spreadsheet_adapter
from .adapters import text as text_adapter
from .models import NormalizedDoc, SourceType

_PDF_EXT = {".pdf"}
_SHEET_EXT = {".xlsx", ".xlsm", ".xls", ".csv", ".tsv"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ingest_text(raw: str, source_name: str = "pasted-text") -> NormalizedDoc:
    out = text_adapter.to_markdown(raw)
    meta = {**out.meta, "original_sha256": _sha256((raw or "").encode("utf-8"))}
    return NormalizedDoc(
        source_type=SourceType.PASTED_TEXT,
        source_name=source_name,
        markdown=out.markdown,
        warnings=out.warnings,
        meta=meta,
    )


def ingest_file(data: bytes, filename: str) -> NormalizedDoc:
    ext = os.path.splitext(filename)[1].lower()

    if ext in _PDF_EXT:
        out = pdf_adapter.to_markdown(data)
        source_type = SourceType.PDF
    elif ext in _SHEET_EXT:
        out = spreadsheet_adapter.to_markdown(data, filename)
        source_type = SourceType.CSV if ext in (".csv", ".tsv") else SourceType.EXCEL
    else:
        raise ValueError(
            f"Unsupported file type {ext or '(none)'!r} for {filename!r}. "
            "MVP supports .pdf, .xlsx/.xlsm, and .csv/.tsv."
        )

    meta = {**out.meta, "original_sha256": _sha256(data)}
    return NormalizedDoc(
        source_type=source_type,
        source_name=filename,
        markdown=out.markdown,
        warnings=out.warnings,
        meta=meta,
    )
