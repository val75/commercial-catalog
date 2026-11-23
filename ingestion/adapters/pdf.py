"""PDF adapter (text-based PDFs only for the MVP).

Two kinds of PDF exist in the wild:
  * text-based  -> real text you can extract (most vendor quotes). Handled here.
  * scanned     -> image-only, no text layer. Out of scope for the MVP: we detect
                   these pages, add a warning, and skip them rather than OCR.

We pull both prose and tables, because quotes are table-heavy, and render tables
as Markdown so the extractor sees rows and columns explicitly.
"""

from __future__ import annotations

import io

import pdfplumber

from ..models import AdapterOut


def _cell(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("\n", " ").strip()


def _rows_to_markdown_table(rows: list[list]) -> str:
    """Render a grid as a Markdown table. First non-empty row becomes the header.

    Deliberately faithful, not clever: we don't try to guess which row is the
    'real' header. The extraction model handles irregular shapes fine.
    """
    grid = [[_cell(c) for c in row] for row in rows]
    grid = [r for r in grid if any(c for c in r)]
    if not grid:
        return ""

    width = max(len(r) for r in grid)
    grid = [r + [""] * (width - len(r)) for r in grid]

    def fmt(r: list[str]) -> str:
        return "| " + " | ".join(c.replace("|", "\\|") for c in r) + " |"

    header, *body = grid
    out = [fmt(header), "| " + " | ".join(["---"] * width) + " |"]
    out += [fmt(r) for r in body]
    return "\n".join(out)


def to_markdown(data: bytes) -> AdapterOut:
    warnings: list[str] = []
    meta: dict = {}
    parts: list[str] = []
    scanned_pages: list[int] = []

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        meta["page_count"] = len(pdf.pages)
        multipage = len(pdf.pages) > 1

        for i, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            tables = page.extract_tables() or []

            if not text and not tables:
                # No text layer. If the page carries an image, it's a scan we
                # can't read without OCR -> flag and skip. Otherwise it's blank.
                if page.images:
                    scanned_pages.append(i)
                continue

            segment: list[str] = []
            if multipage:
                segment.append(f"### Page {i}")
            if text:
                segment.append(text)
            for table in tables:
                md = _rows_to_markdown_table(table)
                if md:
                    segment.append(md)
            parts.append("\n\n".join(segment))

    if scanned_pages:
        meta["scanned_pages"] = scanned_pages
        warnings.append(
            f"Skipped {len(scanned_pages)} scanned/image-only page(s) {scanned_pages}: "
            "OCR is out of scope for the MVP. Flag this quote for manual entry."
        )

    markdown = "\n\n".join(parts).strip()
    if not markdown:
        warnings.append(
            "No extractable text found. The PDF is likely fully scanned; "
            "route it to manual handling."
        )

    return AdapterOut(markdown=markdown, warnings=warnings, meta=meta)
