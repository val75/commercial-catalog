"""Spreadsheet adapter for Excel (.xlsx/.xlsm) and CSV/TSV.

Vendor BOMs look structured but aren't reliably so: every vendor uses different
columns in a different order, often with a title row or notes above the real
header. So we do NOT hard-map columns to fields. We faithfully render each sheet
as a Markdown table and let the extraction model read it. Adding a new vendor
never means touching this adapter.
"""

from __future__ import annotations

import csv
import io
import os

from openpyxl import load_workbook

from ..models import AdapterOut


def _cell(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _grid_to_markdown_table(rows: list[list]) -> str:
    grid = [[_cell(c) for c in row] for row in rows]
    grid = [r for r in grid if any(c for c in r)]  # drop fully-empty rows
    if not grid:
        return ""

    # trim trailing empty columns
    last = max((i for r in grid for i, c in enumerate(r) if c), default=0)
    width = last + 1
    grid = [(r + [""] * width)[:width] for r in grid]

    def fmt(r: list[str]) -> str:
        return "| " + " | ".join(c.replace("|", "\\|") for c in r) + " |"

    header, *body = grid
    out = [fmt(header), "| " + " | ".join(["---"] * width) + " |"]
    out += [fmt(r) for r in body]
    return "\n".join(out)


def _from_xlsx(data: bytes) -> AdapterOut:
    warnings: list[str] = []
    parts: list[str] = []
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        meta = {"sheet_names": list(wb.sheetnames)}
        for ws in wb.worksheets:
            rows = [list(r) for r in ws.iter_rows(values_only=True)]
            table = _grid_to_markdown_table(rows)
            if not table:
                warnings.append(f"Sheet '{ws.title}' had no data; skipped.")
                continue
            parts.append(f"## Sheet: {ws.title}\n\n{table}")
    finally:
        wb.close()

    markdown = "\n\n".join(parts).strip()
    if not markdown:
        warnings.append("Workbook contained no tabular data.")
    return AdapterOut(markdown=markdown, warnings=warnings, meta=meta)


def _from_csv(data: bytes) -> AdapterOut:
    warnings: list[str] = []
    text = data.decode("utf-8-sig", errors="replace")

    sample = text[:4096]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
    except csv.Error:
        delimiter = "\t" if "\t" in sample else ","

    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    table = _grid_to_markdown_table(rows)
    meta = {"delimiter": delimiter, "row_count": len(rows)}
    if not table:
        warnings.append("CSV contained no rows.")
    return AdapterOut(markdown=table, warnings=warnings, meta=meta)


def to_markdown(data: bytes, filename: str) -> AdapterOut:
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        return _from_xlsx(data)
    if ext in (".csv", ".tsv"):
        return _from_csv(data)
    if ext == ".xls":
        return AdapterOut(
            "", [f"Legacy .xls isn't supported in the MVP ({filename}); re-save as .xlsx."]
        )
    # Unknown extension but routed here: best-effort as a workbook.
    return _from_xlsx(data)
