"""Generate the binary fixtures (xlsx, pdf) so everything is reproducible.

Run once:  python make_fixtures.py
"""

from __future__ import annotations

import os

from openpyxl import Workbook
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

HERE = os.path.dirname(__file__)
FIX = os.path.join(HERE, "fixtures")


def make_xlsx() -> None:
    """A Dell BOM with a title row and a blank row ABOVE the real header — the
    common messy shape that trips up rigid column mapping."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Quote"
    ws.append(["Dell Technologies  —  Quote Q-88214  (valid 30 days)"])
    ws.append([])
    ws.append(["Line", "SKU", "Description", "Qty", "Unit Price (USD)"])
    ws.append([1, "210-BFTL", "PowerEdge R660 1U server chassis", 8, 4200])
    ws.append([2, "338-CJXP", "Intel Xeon Gold 6438N 32C 2.0GHz", 16, 1650])
    ws.append([3, "370-AEVR", "32GB DDR5-4800 RDIMM", 128, 190])
    ws.append([4, "400-BQOO", "3.84TB NVMe U.2 Gen4 SSD", 48, 720])
    ws.append([5, "540-BCOP", "Broadcom 57508 2x25GbE OCP", 8, 410])
    ws.append([6, "450-AKMP", "1100W Titanium hot-plug PSU", 16, 260])
    wb.save(os.path.join(FIX, "dell_bom.xlsx"))


def make_pdf() -> None:
    """A small text-based (not scanned) Supermicro quote with a header block and
    a line-item table drawn as text."""
    path = os.path.join(FIX, "supermicro_quote.pdf")
    c = canvas.Canvas(path, pagesize=LETTER)
    width, height = LETTER
    y = height - inch

    c.setFont("Helvetica-Bold", 14)
    c.drawString(inch, y, "Supermicro Reseller — Server Quotation")
    y -= 22
    c.setFont("Helvetica", 10)
    for line in [
        "Quote #: SMC-2026-4471          Date: 2026-07-30",
        "Vendor: Supermicro (via Approved Reseller)     Currency: USD",
        "Valid until: 2026-08-15",
    ]:
        c.drawString(inch, y, line)
        y -= 14

    y -= 10
    c.setFont("Helvetica-Bold", 10)
    cols = [inch, inch + 3.6 * inch, inch + 4.3 * inch, inch + 5.2 * inch]
    for x, head in zip(cols, ["Description", "Qty", "Unit Price", "Line Total"]):
        c.drawString(x, y, head)
    y -= 4
    c.line(inch, y, width - inch, y)
    y -= 16

    c.setFont("Helvetica", 10)
    c.drawString(cols[0], y, "AS-1115CS-TNR bare metal server")
    c.drawString(cols[1], y, "12")
    c.drawString(cols[2], y, "$11,950")
    c.drawString(cols[3], y, "$143,400")
    y -= 14
    for spec in [
        "1x AMD EPYC 9354P 32-core",
        "384GB DDR5 (12x 32GB)",
        "4x 7.68TB Gen5 NVMe",
        "dual 10GbE onboard, 2x 860W PSU",
    ]:
        c.drawString(cols[0] + 12, y, spec)
        y -= 13

    c.showPage()
    c.save()


if __name__ == "__main__":
    os.makedirs(FIX, exist_ok=True)
    make_xlsx()
    make_pdf()
    print("Wrote fixtures to", FIX)
