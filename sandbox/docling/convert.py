"""Convert PDFs to Markdown with docling, next to the current pdfplumber adapter.

    sandbox/docling/.venv/bin/python sandbox/docling/convert.py fixtures/supermicro_quote.pdf
    sandbox/docling/.venv/bin/python sandbox/docling/convert.py a.pdf b.pdf --fast --ocr

For each input PDF it writes, into sandbox/docling/out/ (gitignored):
    <name>.docling.md      docling's Markdown export
    <name>.docling.json    docling's full document model (layout, tables, provenance)
    <name>.pdfplumber.md   what ingestion/adapters/pdf.py produces today

Then compare, e.g.:  diff sandbox/docling/out/<name>.pdfplumber.md sandbox/docling/out/<name>.docling.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"


def build_converter(ocr: bool, fast: bool, device: str):
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.document_converter import DocumentConverter, PdfFormatOption

    try:
        from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    except ImportError:  # older docling 2.x
        from docling.datamodel.pipeline_options import AcceleratorDevice, AcceleratorOptions

    opts = PdfPipelineOptions()
    # Scanned PDFs are out of MVP scope, so OCR is off unless asked for.
    opts.do_ocr = ocr
    opts.do_table_structure = True
    opts.table_structure_options.mode = TableFormerMode.FAST if fast else TableFormerMode.ACCURATE
    # Fill table cells with the PDF's own text rather than predicted text.
    opts.table_structure_options.do_cell_matching = True
    # auto picks MPS on Apple Silicon, CUDA on a GPU box, else CPU.
    opts.accelerator_options = AcceleratorOptions(device=AcceleratorDevice(device))

    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )


def pdfplumber_markdown(path: Path) -> str:
    sys.path.insert(0, str(ROOT))
    from ingestion import ingest_file

    doc = ingest_file(path.read_bytes(), path.name)
    header = "".join(f"<!-- warning: {w} -->\n" for w in doc.warnings)
    return header + doc.markdown


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("pdfs", nargs="+", type=Path)
    ap.add_argument("--ocr", action="store_true", help="enable OCR (off by default)")
    ap.add_argument("--fast", action="store_true", help="FAST table model instead of ACCURATE")
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "mps", "cuda"])
    ap.add_argument("--no-compare", action="store_true", help="skip the pdfplumber output")
    args = ap.parse_args()

    OUT.mkdir(exist_ok=True)

    t0 = time.perf_counter()
    converter = build_converter(args.ocr, args.fast, args.device)
    print(f"converter ready in {time.perf_counter() - t0:.1f}s")

    for pdf in args.pdfs:
        if not pdf.is_file():
            print(f"skip {pdf}: not a file")
            continue

        t0 = time.perf_counter()
        result = converter.convert(pdf)
        elapsed = time.perf_counter() - t0
        doc = result.document

        (OUT / f"{pdf.stem}.docling.md").write_text(doc.export_to_markdown(), encoding="utf-8")
        (OUT / f"{pdf.stem}.docling.json").write_text(
            json.dumps(doc.export_to_dict(), indent=2), encoding="utf-8"
        )
        print(
            f"{pdf.name}: {result.status.name} in {elapsed:.1f}s, "
            f"{len(doc.pages)} page(s), {len(doc.tables)} table(s)"
        )
        for err in result.errors:
            print(f"   error: {err}")

        if not args.no_compare:
            (OUT / f"{pdf.stem}.pdfplumber.md").write_text(
                pdfplumber_markdown(pdf), encoding="utf-8"
            )

    print(f"output in {OUT}")


if __name__ == "__main__":
    main()
