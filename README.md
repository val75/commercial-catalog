# Commercial Catalog — ingestion layer (MVP)

Turns any supported input into **one normalized Markdown document**. That's the
whole job. The next step (extraction) reads the Markdown and produces one or more
quote drafts — so "one input → N quotes" is handled *there*, not here.

```
pasted text ─┐
PDF ─────────┤──►  normalized Markdown  ──►  (LLM extraction → 1..N drafts)
Excel / CSV ─┘
```

## Public API

```python
from ingestion import ingest_text, ingest_file

doc = ingest_text(pasted_string)              # email / SMS / chat
doc = ingest_file(file_bytes, "quote.pdf")    # .pdf, .xlsx/.xlsm, .csv/.tsv

doc.markdown       # what the extractor consumes
doc.source_type    # pasted_text | pdf | excel | csv
doc.warnings       # e.g. skipped scanned page, empty sheet
doc.meta           # page_count / sheet_names / original_sha256 / ...
```

## What each adapter does

- **text** — fixes encoding (mojibake) and whitespace, keeps everything else
  verbatim. No signature/quote stripping — the model ignores boilerplate better
  than a regex does.
- **pdf** — extracts text + tables from text-based PDFs. Scanned (image-only)
  pages are **flagged and skipped** (OCR is deliberately out of MVP scope).
- **spreadsheet** — renders each sheet / CSV as a Markdown table, faithfully.
  No column mapping, so a new vendor layout never means code changes.

## Design decisions baked in

- One common representation (Markdown) → a single extraction path to maintain.
- Adapters are pure `content -> content`; provenance (incl. a SHA-256 of the
  original, for dedup and re-runs) is attached by `dispatch`.
- Faithful over clever: messy title rows, odd columns, and boilerplate pass
  through intact for the extractor to sort out.

## Run it

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
python make_fixtures.py   # builds the binary sample files
python demo.py            # ingests each fixture, prints the Markdown
pytest -q                 # runs the test suite
```

## Layout

```
ingestion/
  models.py                 NormalizedDoc, AdapterOut, SourceType
  dispatch.py               ingest_text / ingest_file (+ provenance)
  adapters/
    text.py  pdf.py  spreadsheet.py
fixtures/                   sample inputs (one paste has TWO quotes)
tests/                      pytest suite
demo.py  make_fixtures.py
requirements.txt  requirements-dev.txt  pyproject.toml
```

## Not in this step (next up)

Extraction: feed `doc.markdown` + the target schema to the model, get 1..N
structured drafts back. Then persistence (Postgres) and the review UI.
