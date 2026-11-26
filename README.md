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

## The pipeline: upload to drafts in one call

`pipeline/` runs the stages in order: ingestion, then extraction (the model,
then cleanup), then the deterministic checks in `validation/`.

```python
from pipeline import process_text, process_file

result = process_file(file_bytes, "Q-1234.pdf")   # or process_text(pasted_string)

result.document                # the NormalizedDoc above, with warnings and provenance
for quote in result.quotes:    # one input can hold several quotes
    quote.draft                # the draft, as extraction and cleanup left it
    for item in quote.items:
        item.flags             # chassis problems
        for c in item.components:
            c.quantity         # parts per server, or the question to ask
            c.capacity         # drives only: the standard SSD size proposed
            c.flags            # problems with this part's properties
```

- **Checks only propose.** The draft is never changed: a count per server, a
  standard SSD size and every flag sit beside it, so review can show what the
  quote said next to what the checks suggest.
- **Each check sits where review shows it**: on its component line, or on the
  item for the chassis. Several lines of one kind (a RAID controller and an HBA,
  say) share one question rather than being added up.
- **Failures stop at their stage.** An unsupported file type raises
  `ValueError`, a model problem raises `ExtractionError`. An empty document,
  such as a PDF with only scanned pages, returns no quotes without calling the
  model; its warnings say why.
- The model's address comes from `MODEL_BASE_URL` in the environment or `.env`
  (see `.env.example`), or from a `settings=ModelSettings(...)` argument.

## Review storage

`storage/` keeps everything the review queue needs in PostgreSQL, and `review/`
holds the logic on top of it: imports, decisions, approval and the queue listing.
The draft, its checks, the reviewer's decisions and each approved quote are JSONB.

Settings, from the environment or `.env` (see `.env.example`):

- `DATABASE_URL`, such as `postgresql+psycopg://localhost/commercial_catalog`
- `TEST_DATABASE_URL`: a separate database that the tests wipe on every run.
  Without it, the database tests skip.
- `ORIGINALS_DIR`: the folder that keeps each uploaded original, named by its SHA-256

Set up once, then after each new migration:

```bash
createdb commercial_catalog
createdb commercial_catalog_test
alembic upgrade head      # creates or updates the tables in DATABASE_URL
```

```python
from review import imports, actions, queue

import_id = imports.import_file(session, store, file_bytes, "Q-1234.pdf")  # stored, waiting
imports.claim_next_import(session)       # one document at a time
imports.run_import(session, import_id)   # drafts and reviews, or a plain failure reason
queue.list_queue(session)                # failed, reading, and the quotes to review
actions.record_decision(session, draft_id, {"kind": "use_guess", "path": "..."}, by="me")
actions.approve(session, draft_id, by="me")
```

- **Nothing in `review/` commits.** The caller owns the transaction. An
  original removed with a failed import is deleted only after the commit.
- **A guess reaches an approved quote only if the reviewer used it or typed a
  value.** Approval is refused while a question is open.
- **Decisions are kept apart from the draft**, so Undo restores them and
  extraction can be re-run.

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
extraction/                 draft schema, model client, cleanup
validation/                 quantity, property and SSD-size checks
pipeline/                   process_text / process_file: all of the above in order
storage/                    Postgres tables, Alembic migrations, the originals folder
review/                     imports, decisions, approve / reject / undo, the queue
fixtures/                   sample inputs (one paste has TWO quotes)
tests/                      pytest suite
demo.py  make_fixtures.py
requirements.txt  requirements-dev.txt  pyproject.toml  alembic.ini
```

## Not in this step (next up)

The server API (FastAPI) on top of `review/`, then the review screens (React).
