# Commercial Catalog — project context

Import vendor hardware quotes (bare metal servers first) into a structured,
searchable database, replacing manual spreadsheets. Full product brief:
`docs/00-purpose.md`.

Phase 1 success criteria: a user can upload a vendor quote, review the
AI-extracted information, approve it, and search previously imported hardware.

## Architecture

```
pasted text ─┐
PDF ─────────┤──► ingestion (adapters) ──► normalized Markdown ──► LLM extraction ──► 1..N quote drafts
Excel / CSV ─┘                                                                         │
                                                       review UI ◄── Postgres ◄────────┘ (on approve)
```

- **Ingestion** (built, in `ingestion/`): one adapter per input type, each
  returning normalized Markdown. Pure `content -> content`; provenance
  (including `original_sha256` for dedup and re-runs) is added in `dispatch.py`.
- **Extraction** (next): reads `NormalizedDoc.markdown`, calls the model,
  returns 1..N structured quote drafts.
- **Storage**: Postgres. Planned schema: vendors → quotes → line_items →
  config_components, with a normalized `components` catalog everything points at.
- **Review UI**: shows raw vendor text mapped to canonical catalog components
  with a match state (matched / low confidence / unmatched); human approves.

## Decisions already made

- **One input → N drafts.** A single paste or PDF often holds several quotes.
  Adapters emit ONE document; the fan-out happens in extraction.
- **Scanned (image-only) PDFs are out of MVP scope.** Detect, add a warning,
  skip. No OCR yet.
- **Faithful over clever.** Adapters don't strip email signatures or quoted
  replies, and don't map spreadsheet columns. Messy content passes through and
  the model sorts it out, so new vendor layouts never require adapter changes.
- **Keep three layers per input:** the original, the normalized Markdown, and
  the extracted draft, so extraction can be re-run without re-uploading.
- **DOCX** is listed as an input in the product brief but not built yet.
  Likely candidate for the next adapter.
- Bundled quotes price the whole server, not each part. How to attribute
  component-level cost for "historical pricing" is still an open question.

## Stack and environment

- Python 3.11+, FastAPI (planned), Postgres (planned), pytest.
- Development happens on a MacBook: code in PyCharm, Claude Code in iTerm.
  The virtualenv is `venv/` in the project root; activate it before running
  anything (and before starting `claude`, so its commands use it).
- Model: Qwen3.8 27B, quantized to IQ3_S (GGUF), served on a separate server
  with two NVIDIA T4 GPUs via an OpenAI-compatible HTTP endpoint (llama.cpp).
- **Never hard-code the model location.** Read the base URL from config/env
  (`.env`, which is gitignored). In dev it points at the server over the LAN;
  in production the whole backend runs on that server and points at localhost.
- IQ3_S is an aggressive quant. For extraction, use constrained decoding
  (llama.cpp GBNF grammar / JSON-schema-enforced output) to guarantee valid
  JSON. If quality is still poor, a higher-bit quant (e.g. Q4_K_M) is the fallback.

## Next step: extraction

- Define the quote draft schema with **Pydantic** (not SQLAlchemy yet), so
  extraction stays decoupled from the database while the schema is moving.
- Client that sends `doc.markdown` + schema to the model endpoint and returns
  a list of validated drafts (supports N quotes per input).
- Test against `fixtures/paste_two_quotes.txt`, which contains two quotes and
  should produce two drafts.

## Commands

```bash
source venv/bin/activate
pip install -r requirements-dev.txt
python make_fixtures.py   # regenerate the binary fixtures (xlsx, pdf)
python demo.py            # print normalized Markdown for each fixture
pytest -q                 # run the tests (keep them passing)
```

## Conventions

- Adapters stay pure and deterministic; anything needing the network or the
  model lives outside `ingestion/`.
- Add a test for each new adapter or behavior; tests build their own inputs in
  memory rather than relying on `fixtures/`.
