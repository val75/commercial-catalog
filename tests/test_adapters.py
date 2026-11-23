from __future__ import annotations

import io
import os

import pytest
from openpyxl import Workbook
from reportlab.pdfgen import canvas

from ingestion import SourceType, ingest_file, ingest_text


def test_text_fixes_mojibake_and_keeps_content():
    raw = "Quote #: DF-Q-88214\r\nOption A â€” Dell R660\r\n\r\n\r\nUnit price: $14,280   "
    doc = ingest_text(raw)
    assert doc.source_type is SourceType.PASTED_TEXT
    assert "\u2014" in doc.markdown          # em dash repaired
    assert "\r" not in doc.markdown          # line endings normalized
    assert "\n\n\n" not in doc.markdown      # blank-line runs collapsed
    assert "DF-Q-88214" in doc.markdown      # content preserved
    assert "original_sha256" in doc.meta


def test_text_preserves_both_quotes_for_downstream_fanout():
    raw = "Quote #: A-1\n...\nQuote #: A-2\n..."
    doc = ingest_text(raw)
    # The adapter emits ONE doc; the two quotes remain intact for the extractor.
    assert "A-1" in doc.markdown and "A-2" in doc.markdown


def test_empty_text_warns():
    doc = ingest_text("   \n  \n")
    assert doc.is_empty
    assert any("empty" in w.lower() for w in doc.warnings)


def _xlsx_bytes() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Vendor Quote  —  title row"])   # messy title row above the header
    ws.append([])
    ws.append(["Line", "Description", "Qty", "Unit Price"])
    ws.append([1, "Xeon Gold 6438N 32C", 2, 1650])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_xlsx_renders_markdown_table_faithfully():
    doc = ingest_file(_xlsx_bytes(), "quote.xlsx")
    assert doc.source_type is SourceType.EXCEL
    assert "## Sheet: Sheet" in doc.markdown
    assert "| Line | Description | Qty | Unit Price |" in doc.markdown
    assert "Xeon Gold 6438N 32C" in doc.markdown
    assert "title row" in doc.markdown          # faithful: nothing dropped


def test_csv_sniffs_delimiter():
    data = b"Line;Description;Qty\n1;Xeon Gold 6438N;2\n"
    doc = ingest_file(data, "bom.csv")
    assert doc.source_type is SourceType.CSV
    assert doc.meta["delimiter"] == ";"
    assert "| Line | Description | Qty |" in doc.markdown


def _text_pdf_bytes() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, "Quote SMC-2026-4471")
    c.drawString(72, 700, "AS-1115CS-TNR EPYC 9354P 32C")
    c.showPage()
    c.save()
    return buf.getvalue()


def test_pdf_extracts_text():
    doc = ingest_file(_text_pdf_bytes(), "quote.pdf")
    assert doc.source_type is SourceType.PDF
    assert "SMC-2026-4471" in doc.markdown
    assert doc.meta["page_count"] == 1


def test_blank_pdf_warns_manual_handling():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()  # a page with no text and no image
    c.save()
    doc = ingest_file(buf.getvalue(), "blank.pdf")
    assert doc.is_empty
    assert any("scanned" in w.lower() or "manual" in w.lower() for w in doc.warnings)


def test_unsupported_extension_raises():
    with pytest.raises(ValueError):
        ingest_file(b"whatever", "notes.docx")
