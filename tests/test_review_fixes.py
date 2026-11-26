"""Behaviour pinned after the whole-branch review: concurrency, removals, older drafts, guessed sizes."""

from __future__ import annotations

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from pipeline import review_draft
from review.actions import record_decision
from review.apply import apply_decisions
from review.checks_json import checks_to_json
from review.decisions import decision_key, validate_decision
from review.imports import import_file, import_text, remove_import
from review.paths import get_at
from review.summary import badges
from storage.config import StorageConfigError, load_test_database_url
from storage.originals import OriginalStore
from storage.tables import Document, Import, Review
from tests.quote_builders import cpu, drive, example_quote, inferred, item, quote, stored_draft
from tests.test_review_imports import _blank_pdf

CORES = "items/0/components/0/cpu/physical_cores"
THREADS = "items/0/components/0/cpu/threads"


@pytest.fixture
def committed(db_engine):
    """Sessions that really commit, for behaviour the rolled-back db fixture can't show. Cleans up after."""
    sessions: list[Session] = []

    def open_session() -> Session:
        session = Session(db_engine)
        sessions.append(session)
        return session

    yield open_session
    for session in sessions:
        session.close()
    with Session(db_engine) as cleanup:
        cleanup.execute(delete(Document))
        cleanup.commit()


def test_two_overlapping_decisions_are_both_kept(committed):
    setup = committed()
    draft_id = stored_draft(setup, example_quote())
    setup.commit()

    first, second = committed(), committed()
    held = second.get(Review, draft_id)  # the second request has read the quote before the first one commits
    assert held.decisions == {}
    record_decision(first, draft_id, {"kind": "use_guess", "path": CORES}, by="reviewer")
    first.commit()
    record_decision(second, draft_id, {"kind": "use_guess", "path": THREADS}, by="reviewer")
    second.commit()

    fresh = committed()
    assert set(fresh.get(Review, draft_id).decisions) == {f"property:{CORES}", f"property:{THREADS}"}


def test_a_removal_closed_without_a_commit_keeps_the_original(db, tmp_path):
    store = OriginalStore(tmp_path / "originals")
    import_id = import_file(db, store, _blank_pdf(), "Scan-1.pdf")
    path = db.get(Document, db.get(Import, import_id).document_id).original_path
    remove_import(db, store, import_id)
    db.close()  # abandoned: no commit

    import_text(db, store, "Quote Q-7: 1 x Example Server")
    db.commit()
    assert (store.root / path).exists()


def test_a_removal_in_a_rolled_back_savepoint_keeps_the_original(db, tmp_path):
    store = OriginalStore(tmp_path / "originals")
    import_id = import_file(db, store, _blank_pdf(), "Scan-1.pdf")
    path = db.get(Document, db.get(Import, import_id).document_id).original_path
    savepoint = db.begin_nested()
    remove_import(db, store, import_id)
    savepoint.rollback()
    db.commit()
    assert db.get(Import, import_id) is not None
    assert (store.root / path).exists()


def test_a_draft_stored_under_an_older_schema_can_still_be_corrected():
    draft_model = quote(item(cpu(2, physical_cores=inferred(32))))
    draft, checks = draft_model.model_dump(mode="json"), checks_to_json(review_draft(draft_model))
    draft["items"][0]["components"][0]["field_from_an_older_schema"] = "kept"
    decision = validate_decision(draft, checks, {"kind": "set_value", "path": CORES, "value": "28"})
    assert decision["value"] == 28
    with pytest.raises(ValueError):
        validate_decision(draft, checks, {"kind": "set_value", "path": CORES, "value": "many"})


def test_a_used_guessed_size_still_gets_the_standard_size():
    guessed = drive(3.8)
    guessed["storage"]["capacity"] |= {"basis": "inferred", "reason": "From the part code"}
    draft_model = quote(item(cpu(2), guessed))
    draft, checks = draft_model.model_dump(mode="json"), checks_to_json(review_draft(draft_model))
    path = "items/0/components/1/storage/capacity"
    use = {"kind": "use_guess", "path": path}
    decisions = {decision_key(use): validate_decision(draft, checks, use)}

    capacity = get_at(apply_decisions(draft, checks, decisions), path)
    assert (capacity["value"], capacity["source"]) == (3.84, "standard_size")
    assert badges(draft, checks, decisions).changes == 1


def test_the_test_database_must_not_be_the_real_one(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/commercial_catalog")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+psycopg://localhost/commercial_catalog")
    with pytest.raises(StorageConfigError, match="TEST_DATABASE_URL"):
        load_test_database_url(tmp_path / "missing.env")
