# Review Storage Implementation Plan (part 1 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Everything the review queue and review screen need below HTTP: Postgres storage for imports,
drafts, decisions and approved quotes, and the review logic (questions, guesses, changes, approve,
reject, undo, the queue listing).

**Architecture:** SQLAlchemy 2.0 tables in Postgres, created by one Alembic migration. Drafts, checks,
decisions and approved snapshots are JSONB. A `review/` package holds plain functions that take a
`Session` and never commit: the caller (the API, in part 2) owns the transaction. Pure logic (checks to
JSON, applying decisions, badges) has no database and is tested on its own.

**Tech Stack:** Python 3.11, SQLAlchemy 2.0, psycopg 3, Alembic, PostgreSQL 14 (Homebrew), pytest.

**Spec:** `docs/superpowers/specs/2026-11-25-review-screen-design.md` (approved 2026-11-25). Parts 2
(FastAPI) and 3 (React screens) get their own plans after this one is built. They cover what this
part leaves out: the endpoints and the background worker, serving originals and PDF page images, the
"page 1" locations on grouped rows, source highlighting, and the screens.

## Global Constraints

- PostgreSQL, not a document database. Drafts, decisions and approved snapshots go in JSONB columns.
- Never hard-code the database location or the model location. `DATABASE_URL`, `TEST_DATABASE_URL`,
  `ORIGINALS_DIR` and `MODEL_BASE_URL` come from the environment, otherwise from `.env`.
- Extraction runs one document at a time.
- `review_draft` never changes a draft. Only applying decisions at approval changes values.
- An inferred value reaches an approved quote only if the reviewer used it or typed a value.
- A quote can't be approved while a question is open.
- Originals are never changed after upload. Keep the original, the normalized Markdown and the draft.
- One user, no login. Every decision still records `by` as a plain string.
- Tests build their own inputs in memory with invented data (the repo is public). Database tests skip
  when `TEST_DATABASE_URL` isn't set, as model tests do without `RUN_MODEL_TESTS=1`.
- Functions in `review/` don't commit.
- Work on branch `review-storage`. Commit at the end of each task.

## Review Focus

- **The model returns no quotes.** The import must not finish silently with nothing in the queue: it
  fails with "The model found no quote in this document." and can be retried. (Task 3)
- **The server stops while an import is processing.** On restart the import goes back to waiting
  instead of staying "processing" forever. (Task 3)
- **A decision about something that doesn't exist** (a path not in the draft, a count id not in the
  checks, `use_guess` on a stated value) is refused with `ValueError` and nothing is stored. (Task 4)
- **Approving twice, approving a rejected quote, or undoing an older approval** is refused. (Task 5)
- **A draft with no items** still gets a queue row: empty description, no badges, ready. (Task 6)

---

## File Structure

| File | Responsibility |
|---|---|
| `storage/config.py` | Read `DATABASE_URL`, `TEST_DATABASE_URL`, `ORIGINALS_DIR` |
| `storage/tables.py` | SQLAlchemy models for the five tables |
| `storage/db.py` | Engine and session factory |
| `storage/originals.py` | The folder of original files, named by SHA-256 |
| `storage/migrations/` + `alembic.ini` | Alembic, one initial migration |
| `review/checks_json.py` | `QuoteReview` checks to JSON, shared counts given ids |
| `review/failures.py` | An exception to a plain-words failure reason |
| `review/imports.py` | Create, claim, run, retry, remove imports |
| `review/paths.py` | Find and change properties in a draft dict by path |
| `review/decisions.py` | Decision validation and open questions |
| `review/apply.py` | Draft + checks + decisions to the approved quote |
| `review/actions.py` | Record and withdraw decisions, approve, reject, undo |
| `review/summary.py` | Badges and the one-line "what was quoted" |
| `review/queue.py` | The queue listing and one quote's details |
| `pipeline/run.py` | Make `_process` public as `process_document` |
| `tests/conftest.py` | The `db` fixture |

---

### Task 1: Tables, migration and the test database

**Files:**
- Modify: `requirements.txt`, `.env.example`, `extraction/client.py` (rename `_read_env_file` to
  `read_env_file`, update its callers)
- Create: `storage/__init__.py`, `storage/config.py`, `storage/tables.py`, `storage/db.py`,
  `alembic.ini`, `storage/migrations/env.py`, `storage/migrations/versions/<rev>_initial_tables.py`,
  `tests/conftest.py`, `tests/test_storage_tables.py`

**Interfaces:**
- Produces:
  - `storage.config.StorageConfigError(Exception)`
  - `storage.config.load_database_url(env_file=DEFAULT_ENV_FILE) -> str` (raises
    `StorageConfigError` naming `DATABASE_URL` when unset)
  - `storage.config.load_test_database_url(env_file=DEFAULT_ENV_FILE) -> str | None`
  - `storage.config.load_originals_dir(env_file=DEFAULT_ENV_FILE) -> Path` (raises when unset)
  - `storage.db.make_engine(url: str) -> Engine`, `storage.db.make_session_factory(engine) -> sessionmaker[Session]`
  - `storage.tables.Base` and models `Document`, `Import`, `Draft`, `Review`, `ApprovedQuote`
  - fixture `db` (a `Session` inside a transaction rolled back after each test)

Tables (integer identity ids, `timestamptz` with `server_default=func.now()`):

| Model | Columns |
|---|---|
| `Document` (`documents`) | `id`, `sha256` text unique, `source_type` text, `source_name` text, `received_at`, `original_path` text, `markdown` text, `warnings` JSONB list, `meta` JSONB dict |
| `Import` (`imports`) | `id`, `document_id` FK unique (cascade delete), `status` text (`waiting`/`processing`/`done`/`failed`), `failure_reason` text null, `failure_hint` text null, `retryable` bool default false, `log` text default `""`, `updated_at` |
| `Draft` (`drafts`) | `id`, `document_id` FK (cascade), `position` int, `draft` JSONB, `checks` JSONB; unique (`document_id`, `position`) |
| `Review` (`reviews`) | `draft_id` FK primary key (cascade), `status` text (`needs_review`/`approved`/`rejected`) default `needs_review`, `decisions` JSONB dict default `{}`, `reject_reason` text null, `decided_by` text null, `decided_at` null |
| `ApprovedQuote` (`approved_quotes`) | `id`, `draft_id` FK unique (cascade), `vendor_name`, `quote_number`, `currency` text null, `quote_date` date null, `total` numeric null, `quote` JSONB, `approved_by` text, `approved_at` |

- [ ] **Step 1: Set up**

Add `sqlalchemy>=2.0`, `psycopg[binary]>=3.1`, `alembic>=1.13` to `requirements.txt`, then
`pip install -r requirements-dev.txt`. Create the databases: `createdb commercial_catalog` and
`createdb commercial_catalog_test`. Add to `.env.example`, with comments:
`DATABASE_URL=postgresql+psycopg://localhost/commercial_catalog`,
`TEST_DATABASE_URL=postgresql+psycopg://localhost/commercial_catalog_test`,
`ORIGINALS_DIR=/path/to/originals`. Put the same three, with real paths, in `.env`. `.env` is the
user's file and is never read by the assistant: give the user the lines to add.

- [ ] **Step 2: Write the failing tests** in `tests/test_storage_tables.py`

```python
def test_database_url_comes_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://example/db")
    assert load_database_url(tmp_path / "missing.env") == "postgresql+psycopg://example/db"

def test_database_url_falls_back_to_the_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    (tmp_path / ".env").write_text("DATABASE_URL=postgresql+psycopg://from-file/db\n")
    assert load_database_url(tmp_path / ".env") == "postgresql+psycopg://from-file/db"

def test_a_missing_database_url_says_which_setting(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(StorageConfigError, match="DATABASE_URL"):
        load_database_url(tmp_path / "missing.env")

def test_the_migration_creates_the_five_tables(db):
    names = set(inspect(db.get_bind()).get_table_names())
    assert {"documents", "imports", "drafts", "reviews", "approved_quotes"} <= names

def test_a_draft_keeps_its_json_exactly(db):
    document = Document(sha256="ab" * 32, source_type="pdf", source_name="Q-1.pdf",
                        original_path="x", markdown="# Q-1", warnings=[], meta={})
    db.add(document); db.flush()
    db.add(Draft(document_id=document.id, position=0, draft={"quote_number": "Q-1", "items": []}, checks={}))
    db.flush()
    assert db.scalars(select(Draft)).one().draft == {"quote_number": "Q-1", "items": []}
```

- [ ] **Step 3: Run them to see them fail**

Run: `pytest tests/test_storage_tables.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'storage'`.

- [ ] **Step 4: Implement** config, tables and db as in Interfaces. `load_*` use
`extraction.client.read_env_file` and the same rule as `load_settings`: environment first, then the
file. Initialise Alembic (`alembic init storage/migrations`), point `env.py` at `Base.metadata` and
`load_database_url()`, then `alembic revision --autogenerate -m "initial tables"` against the dev
database and check the generated file lists the five tables.

- [ ] **Step 5: Write `tests/conftest.py`**

The schema comes from the migration, so the migration itself is what the tests exercise:

```python
@pytest.fixture(scope="session")
def db_engine():
    url = load_test_database_url()
    if not url:
        pytest.skip("TEST_DATABASE_URL isn't set")
    engine = make_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    config = alembic.config.Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    alembic.command.upgrade(config, "head")
    yield engine
    engine.dispose()

@pytest.fixture
def db(db_engine):
    connection = db_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close(); outer.rollback(); connection.close()
```

`env.py` must use `sqlalchemy.url` from the config when it's set, and `load_database_url()` only
otherwise.

- [ ] **Step 6: Run the tests**

Run: `pytest tests/test_storage_tables.py -v`, then `pytest -q`
Expected: 5 passed; the full suite passes (495 + 5 passed, skips unchanged).

- [ ] **Step 7: Commit** `git commit -m "Postgres tables for imports, drafts, reviews and approved quotes"`

---

### Task 2: Checks as JSON

**Files:**
- Create: `review/__init__.py`, `review/checks_json.py`, `tests/test_review_checks_json.py`

**Interfaces:**
- Consumes: `pipeline.review_draft`, `QuoteReview`, `QuantityCheck`, `CapacityCheck`, `Flag`
- Produces: `review.checks_json.checks_to_json(review: QuoteReview) -> dict` with this shape:

```json
{
  "counts": {"c0": {"per_server": null, "calculated": false, "explanation": "...", "flags": [FLAG]}},
  "items": [
    {"flags": [FLAG],
     "components": [{"count": "c0", "capacity": {"value": 3.84, "unit": "TB", "automatic": true,
                     "explanation": "...", "flags": []}, "flags": [FLAG]}]}
  ]
}
```

`FLAG` is `{"kind": "<enum class name>", "issue": "<enum value>", "message": "...", "property": "..." | null}`.
`count` and `capacity` are `null` when the check is `None`. Count ids are `c0`, `c1`, … in the order the
checks are first met. **One id per `QuantityCheck` object** (compare with `is`), so lines that share a
check share an id, and the question is asked once.

- [ ] **Step 1: Write the failing tests** (build drafts with the helpers style of `tests/test_pipeline.py`)

- `test_two_lines_sharing_a_count_share_its_id`: two RAID controller lines that `review_draft` gives one
  shared check → both components have the same `count` id and `counts` has one entry with `per_server` None.
- `test_separate_counts_get_separate_ids`: CPU and memory lines → `c0` and `c1`, each with its `per_server`.
- `test_a_standard_ssd_size_is_kept_as_a_proposal`: one 3.8 TB drive on a full server → `capacity` is
  `{"value": 3.84, "unit": "TB", "automatic": True, ...}`.
- `test_flags_carry_their_kind_issue_and_property`: a CPU with an inferred value and no reason → flag
  `{"kind": "PropertyIssue", "issue": <its value>, "property": "<name>", ...}`.
- `test_the_result_is_plain_json`: `json.loads(json.dumps(result)) == result`.

- [ ] **Step 2: Run to see them fail** — `pytest tests/test_review_checks_json.py -v`, FAIL on import.
- [ ] **Step 3: Implement `checks_to_json`.**
- [ ] **Step 4: Run** — `pytest tests/test_review_checks_json.py -v`: 5 passed.
- [ ] **Step 5: Commit** `git commit -m "Store the pipeline's checks as JSON"`

---

### Task 3: Imports

**Files:**
- Modify: `pipeline/run.py` (rename `_process` to `process_document`, export it from `pipeline/__init__.py`)
- Create: `storage/originals.py`, `review/failures.py`, `review/imports.py`, `tests/test_review_imports.py`

**Interfaces:**
- Consumes: `ingest_file`, `ingest_text`, `NormalizedDoc`, `process_document`, `checks_to_json`, Task 1 models
- Produces:
  - `storage.originals.OriginalStore(root: Path)` with `save(data: bytes, sha256: str, suffix: str) -> str`
    (returns the path stored on the document; the file is `<sha256><suffix>`), `read(path: str) -> bytes`,
    `delete(path: str) -> None`
  - `review.failures.Failure(reason: str, hint: str | None, retryable: bool)` (frozen dataclass)
  - `review.failures.describe_failure(error: Exception) -> Failure`
  - `review.failures.EMPTY_PDF`, `review.failures.EMPTY_DOCUMENT`, `review.failures.NO_QUOTES`: `Failure`
  - `review.imports.DuplicateDocument(Exception)` with `.document_id: int`
  - `review.imports.import_file(session, store, data: bytes, filename: str) -> int` (import id)
  - `review.imports.import_text(session, store, text: str) -> int`
  - `review.imports.claim_next_import(session) -> int | None`
  - `review.imports.run_import(session, import_id: int, *, settings: ModelSettings | None = None) -> None`
  - `review.imports.retry_import(session, import_id: int) -> None`
  - `review.imports.remove_import(session, store, import_id: int) -> None`
  - `review.imports.requeue_interrupted(session) -> int` (how many went back to waiting)

Behaviour:
- `import_file` / `import_text` ingest straight away. An unsupported file type raises the ingestion
  `ValueError` and stores nothing. A SHA-256 already stored raises `DuplicateDocument`. Otherwise:
  save the original (`.txt` for pasted text, the file's own suffix otherwise), add the `Document` and
  an `Import`. An empty document's import is `failed` at once with `EMPTY_PDF` (for a PDF) or
  `EMPTY_DOCUMENT`. Any other import is `waiting`.
- `claim_next_import` takes the oldest `waiting` import with `SELECT … FOR UPDATE SKIP LOCKED`, sets it to
  `processing`, returns its id.
- `run_import` rebuilds the `NormalizedDoc` from the document row, calls `process_document`, and for
  each quote adds a `Draft` (position in document order, `draft` = `model_dump(mode="json")`, `checks`
  = `checks_to_json`) and a `Review`, then sets `done`. No quotes → `failed` with `NO_QUOTES`. An
  exception → `failed` with `describe_failure(error)`; the log gets the exception's type and message.
  Exceptions are never re-raised.
- `retry_import` only on a `failed`, `retryable` import: back to `waiting`, failure fields cleared.
  Otherwise `ValueError`.
- `remove_import` only on a `failed` import: deletes the document (cascade) and its original file, so
  the same file can be uploaded again. Otherwise `ValueError`.

Failure copy (exact):

| Case | reason | hint | retryable |
|---|---|---|---|
| `EMPTY_PDF` | "A scanned image with no text. Scanned PDFs aren't supported yet." | None | False |
| `EMPTY_DOCUMENT` | "The document has no text to read." | None | False |
| `NO_QUOTES` | "The model found no quote in this document." | "Check that this is a quote. Retrying reads it again." | True |
| `ExtractionError` "Could not reach…" | "The model server didn't answer." | "Usually the server is busy or offline. Retrying sends the same document again." | True |
| `ExtractionError` "…cut off at the token limit…" | "The model's reply was cut off before the end." | "Very long documents can do this. Retrying may work." | True |
| `ExtractionError` other | the error's message | "Retrying sends the same document again." | True |
| any other exception | "Something went wrong while reading the quote." | "Download the log for details." | True |

- [ ] **Step 1: Write the failing tests** (the `FakeModelServer` and `_reply` from
  `tests.test_extraction_client`; `OriginalStore(tmp_path)`):

- `test_a_file_is_stored_and_waits`: `import_file` on a small CSV → import `waiting`, document's markdown
  set, `store.read(document.original_path)` equals the bytes.
- `test_pasted_text_is_stored_as_a_txt_original`
- `test_an_unsupported_file_stores_nothing`: `.docx` → `ValueError`, no rows, no file.
- `test_the_same_file_twice_is_a_duplicate`: second call raises `DuplicateDocument` with the first document's id.
- `test_an_empty_pdf_fails_at_once_and_cannot_be_retried`: a PDF with one blank image page (build it with
  reportlab as `tests/test_adapters.py` does) → `failed`, `EMPTY_PDF`, `retryable` False.
- `test_claiming_takes_the_oldest_waiting_import`: two imports → first claim returns the first and marks
  it `processing`; third claim after two returns `None`.
- `test_a_run_stores_one_draft_and_review_per_quote`: fake server answers two quotes → two drafts at
  positions 0 and 1, both reviews `needs_review`, import `done`, `checks` has `counts`.
- `test_no_quotes_is_a_failure_not_an_empty_success` (Review Focus)
- `test_an_unreachable_model_fails_with_a_plain_reason`: settings pointing at a closed port → `failed`,
  reason "The model server didn't answer.", `retryable` True, log contains "ExtractionError".
- `test_retry_puts_a_failed_import_back_in_line`; `test_retry_refuses_an_empty_pdf`.
- `test_removing_a_failed_import_allows_the_file_again`: remove, then `import_file` with the same bytes succeeds.
- `test_interrupted_imports_go_back_to_waiting` (Review Focus): a `processing` import → `requeue_interrupted` returns 1, status `waiting`.

- [ ] **Step 2: Run to see them fail** — `pytest tests/test_review_imports.py -v`
- [ ] **Step 3: Implement** `process_document`, `OriginalStore`, `failures.py`, `imports.py`.
- [ ] **Step 4: Run** — `pytest tests/test_review_imports.py tests/test_pipeline.py -v`, then `pytest -q`: all pass.
- [ ] **Step 5: Commit** `git commit -m "Store imports and run them through the pipeline"`

---

### Task 4: Decisions and applying them

**Files:**
- Create: `review/paths.py`, `review/decisions.py`, `review/apply.py`, `tests/test_review_apply.py`

**Interfaces:**
- Consumes: the draft dict (`QuoteDraft.model_dump(mode="json")`) and the checks dict from Task 2
- Produces:
  - `review.paths.property_paths(draft: dict) -> list[str]`: every property in document order. A
    property is a dict with a `"basis"` key, found under each component's typed properties
    (`cpu`, `memory`, `gpu`, `storage`, `nic`, `dpu`, `psu`, `raid_controller`) and under each item's
    `chassis`. Paths look like `items/0/components/2/cpu/physical_cores` and `items/0/chassis/rack_height`.
  - `review.paths.inferred_paths(draft: dict) -> list[str]`: those with basis `inferred`
  - `review.paths.get_at(data: dict, path: str) -> Any`, `review.paths.set_at(data: dict, path: str, value) -> None`
  - `review.decisions.decision_key(decision: dict) -> str`: `answer:<count id>`, `property:<path>`, `keep_original:<path>`
  - `review.decisions.validate_decision(draft: dict, checks: dict, decision: dict) -> dict`: returns the
    decision normalised, or raises `ValueError`
  - `review.decisions.open_questions(checks: dict, decisions: dict) -> list[str]`: count ids whose
    `per_server` is None and that have no answer, in id order
  - `review.apply.QuoteNotReady(Exception)` with `.questions: list[str]`
  - `review.apply.apply_decisions(draft: dict, checks: dict, decisions: dict) -> dict`

Decision kinds (each also carries `"by"` and `"at"`, added in Task 5):

| kind | fields | valid when |
|---|---|---|
| `answer` | `count`, `per_server` (int ≥ 1) | `count` is in `checks["counts"]` and its `per_server` is None |
| `use_guess` | `path` | `path` is in `inferred_paths(draft)` |
| `set_value` | `path`, `value` (str, int, float, bool or None), `basis` (`stated`/`inferred`, default `stated`) | `path` is in `property_paths(draft)` |
| `keep_original` | `path` (`items/i/components/j/storage/capacity`) | that component's `capacity` check has `automatic` True |

`use_guess` and `set_value` on one path share the key `property:<path>`, so the later one replaces the earlier.

`apply_decisions` returns a deep copy of the draft where:
1. Every property gets `"source"`: `"quote"` when kept as extracted, `"guess_used"` after `use_guess`,
   `"reviewer"` after `set_value` (value and basis replaced, `reason` set to None; a None value removes the
   property), `"standard_size"` for an automatic capacity change.
2. **Every inferred property with no decision is removed** (set to None).
3. Every automatic capacity change is applied (`value` and `unit` from the check, `as_written` kept)
   unless `keep_original` is recorded for it.
4. Every component with a count gets `"quantity_per_server"`: the check's `per_server`, or the answer.
   Components without a count get None.
5. Open questions raise `QuoteNotReady` with their ids.

- [ ] **Step 1: Write the failing tests**

- `test_property_paths_cover_components_and_the_chassis`
- `test_an_unused_guess_is_left_out` (anti-goal): inferred `physical_cores`, no decision → None in the result.
- `test_a_used_guess_is_kept_and_marked`: `use_guess` → value kept, `"source": "guess_used"`.
- `test_a_typed_value_replaces_the_guess`: `set_value` 28 → value 28, basis `stated`, `"source": "reviewer"`.
- `test_a_correction_can_change_a_stated_value_and_its_basis`
- `test_the_standard_ssd_size_is_applied_unless_kept`: 3.8 TB → 3.84 TB with `"source": "standard_size"`;
  with `keep_original` → 3.8 TB, `"source": "quote"`.
- `test_counts_become_quantity_per_server`: calculated count 2; shared question answered 1 → both lines 1.
- `test_an_open_question_blocks`: `QuoteNotReady` with `["c0"]`.
- `test_open_questions_lists_unanswered_counts_only`
- `test_decisions_about_things_that_dont_exist_are_refused` (Review Focus): unknown path, unknown count,
  `use_guess` on a stated value, `answer` with `per_server` 0, `keep_original` on a drive without an
  automatic change → each `ValueError`.
- `test_applying_never_changes_the_draft_it_was_given`

- [ ] **Step 2: Run to see them fail** — `pytest tests/test_review_apply.py -v`
- [ ] **Step 3: Implement** `paths.py`, `decisions.py`, `apply.py`.
- [ ] **Step 4: Run** — `pytest tests/test_review_apply.py -v`: all pass.
- [ ] **Step 5: Commit** `git commit -m "Apply review decisions to a draft"`

---

### Task 5: Review actions

**Files:**
- Create: `review/actions.py`, `tests/test_review_actions.py`

**Interfaces:**
- Consumes: Task 1 models, Task 4 functions
- Produces:
  - `review.actions.record_decision(session, draft_id: int, decision: dict, *, by: str) -> dict` (the stored
    decision, with `by` and an ISO `at`)
  - `review.actions.withdraw_decision(session, draft_id: int, key: str) -> None` (unknown key: no-op)
  - `review.actions.approve(session, draft_id: int, *, by: str) -> int` (the `ApprovedQuote` id)
  - `review.actions.reject(session, draft_id: int, reason: str, *, by: str) -> None`
  - `review.actions.undo_approval(session, draft_id: int) -> None`
  - `review.actions.NotReviewable(Exception)`: raised when the review isn't `needs_review` (record,
    withdraw, approve, reject), or for an undo that isn't allowed

Behaviour:
- `approve` calls `apply_decisions`, lets `QuoteNotReady` through, and stores an `ApprovedQuote` with
  `vendor_name`, `quote_number`, `currency`, `quote_date`, `total` taken from the applied quote, `quote` =
  the applied dict. Review → `approved`, `decided_by`, `decided_at`.
- `reject` needs a reason that isn't blank (`ValueError`). Review → `rejected`, the reason stored.
- `undo_approval` is allowed only on the most recent approval (latest `approved_at`, then highest id):
  deletes its `ApprovedQuote`, review back to `needs_review` with decisions untouched.

- [ ] **Step 1: Write the failing tests** (a `stored_draft(db, draft_dict)` helper in the test file adds a
  `Document`, a `Draft` with `checks_to_json(review_draft(...))`, and a `Review`):

- `test_a_decision_is_stored_with_who_and_when`
- `test_a_later_decision_on_the_same_property_replaces_the_first`
- `test_withdrawing_a_decision_removes_it`
- `test_a_refused_decision_stores_nothing`
- `test_approve_stores_the_applied_quote_and_its_columns`: `quote_number` "Q-1", `total`, `quote` has
  `quantity_per_server`; review `approved`.
- `test_approve_with_an_open_question_changes_nothing`: `QuoteNotReady`, review still `needs_review`, no row.
- `test_reject_needs_a_reason`; `test_reject_keeps_the_quote_and_the_reason`
- `test_approving_twice_or_after_rejecting_is_refused` (Review Focus): `NotReviewable`.
- `test_undo_reopens_the_latest_approval_with_its_decisions`
- `test_undo_refuses_an_older_approval` (Review Focus)

- [ ] **Step 2: Run to see them fail** — `pytest tests/test_review_actions.py -v`
- [ ] **Step 3: Implement `review/actions.py`.**
- [ ] **Step 4: Run** — `pytest tests/test_review_actions.py -v`, then `pytest -q`: all pass.
- [ ] **Step 5: Commit** `git commit -m "Approve, reject and undo reviews"`

---

### Task 6: The queue

**Files:**
- Create: `review/summary.py`, `review/queue.py`, `tests/test_review_summary.py`, `tests/test_review_queue.py`
- Modify: `README.md` (a short "Review storage" section: the settings, `createdb`, `alembic upgrade head`,
  and that `review/` functions don't commit)

**Interfaces:**
- Consumes: Tasks 1–5
- Produces:
  - `review.summary.Badges(questions: int, guesses: int, changes: int, ready: bool)` (frozen dataclass).
    `questions` = open questions; `guesses` = inferred paths with no `property:` decision; `changes` =
    automatic capacity changes not kept original; `ready` = `questions == 0`.
  - `review.summary.badges(draft: dict, checks: dict, decisions: dict) -> Badges`
  - `review.summary.what_was_quoted(draft: dict, checks: dict, decisions: dict) -> str`
  - `review.queue.QueueEntry(draft_id, document_id, vendor_name, quote_number, received_at, source_name,
    source_type, description, price_per_server: Decimal | None, total: Decimal | None, currency, badges)`
  - `review.queue.QueueGroup(document_id, source_name, source_type, received_at, entries: list[QueueEntry])`
  - `review.queue.FailedImport(import_id, source_name, received_at, reason, hint, retryable)`
  - `review.queue.ProcessingImport(import_id, source_name, received_at)`
  - `review.queue.QueueView(failed, processing, rows: list[QueueEntry | QueueGroup], all_count: int, ready_count: int)`
  - `review.queue.list_queue(session, view: Literal["all", "ready", "rejected"] = "all") -> QueueView`
  - `review.queue.QuoteDetail(draft_id, status, document: Document, draft: dict, checks: dict, decisions: dict, badges: Badges, open_questions: list[str])`
  - `review.queue.get_quote(session, draft_id: int) -> QuoteDetail` (`LookupError` when missing)

`what_was_quoted`, per item, items joined with "; " (spec §7, example
`4 × Example SR-650 2U · 2 × Xeon Gold 6530 · 2 × L40S 48 GB · 1 TB DDR5`):
- `"{quantity} × {name}"`, name = manufacturer and model joined with a space, else the description's first 40
  characters; quantity "?" when unknown;
- CPUs: `"{per server} × {model}"`; GPUs: `"{per server} × {model} {memory} GB"`, or `"no GPU"` on a server
  item (one with a chassis) that has none;
- memory: per-server count × module capacity, shown in TB when it's a whole number of TB (1,024 GB = 1 TB),
  else GB, then the memory type: `"1 TB DDR5"`;
- a count that isn't known yet shows `"?"`; a property that's missing is left out.

`list_queue`:
- `all` and `ready` list reviews in `needs_review` (`ready` only those with `badges.ready`); `rejected` lists
  rejected ones. Oldest first: document `received_at`, then document id, then position.
- A document with two or more listed drafts becomes a `QueueGroup`; one listed draft is a plain `QueueEntry`.
- `price_per_server` is the item's unit price when the quote has exactly one item, else None.
- `failed` and `processing` are always filled, whatever the view. Counts are quotes in `needs_review`.

- [ ] **Step 1: Write the failing tests**

`tests/test_review_summary.py` (no database):
- `test_the_example_quote_reads_as_in_the_mockup`: the spec's invented quote → exactly
  `"4 × Example SR-650 2U · 2 × Xeon Gold 6530 · 2 × L40S 48 GB · 1 TB DDR5"` (question answered).
- `test_an_unanswered_count_shows_a_question_mark`
- `test_a_server_without_gpus_says_no_gpu`; `test_memory_under_a_terabyte_is_in_gb` (`"768 GB DDR5"`)
- `test_badges_count_open_questions_undecided_guesses_and_changes`; `test_a_used_guess_is_no_longer_counted`
- `test_a_draft_with_no_items_is_ready_with_an_empty_description` (Review Focus)

`tests/test_review_queue.py` (database):
- `test_the_queue_is_oldest_first`
- `test_two_quotes_from_one_file_are_a_group`; `test_a_group_with_one_quote_left_is_a_plain_row`
- `test_ready_shows_only_quotes_without_open_questions`
- `test_approved_quotes_leave_the_queue_and_rejected_ones_have_their_own_view`
- `test_failed_and_processing_imports_are_always_listed`
- `test_counts_are_quotes_not_rows`
- `test_get_quote_returns_the_document_draft_and_decisions`; `test_get_quote_on_a_missing_id_raises`

- [ ] **Step 2: Run to see them fail** — `pytest tests/test_review_summary.py tests/test_review_queue.py -v`
- [ ] **Step 3: Implement** `summary.py`, `queue.py`; write the README section.
- [ ] **Step 4: Run** — `pytest -q`: everything passes. Then against the dev database:
  `alembic upgrade head` succeeds.
- [ ] **Step 5: Commit** `git commit -m "List the review queue"`
