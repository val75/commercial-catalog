from __future__ import annotations

import io
import json
import socket

import pytest
from reportlab.pdfgen import canvas
from sqlalchemy import func, select

from extraction.client import ModelSettings
from review import failures
from review.imports import (
    DuplicateDocument,
    claim_next_import,
    import_file,
    import_text,
    remove_import,
    requeue_interrupted,
    retry_import,
    run_import,
)
from storage.originals import OriginalStore
from storage.tables import Document, Draft, Import, Review
from tests.test_extraction_client import FakeModelServer, _reply

CSV = b"Item,Qty,Price\nExample Server,2,1000\n"


@pytest.fixture
def store(tmp_path):
    return OriginalStore(tmp_path / "originals")


@pytest.fixture
def server():
    fake = FakeModelServer()
    yield fake
    fake.close()


def _answer(server: FakeModelServer, *quotes: dict) -> ModelSettings:
    server.body = json.dumps(_reply(json.dumps({"quotes": list(quotes)})))
    return ModelSettings(server.base_url)


def _blank_pdf() -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _closed_port_url() -> str:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    return f"http://127.0.0.1:{port}/v1"


def _document(db, import_id: int) -> Document:
    return db.get(Document, db.get(Import, import_id).document_id)


def test_a_file_is_stored_and_waits(db, store):
    import_id = import_file(db, store, CSV, "Q-1.csv")
    assert db.get(Import, import_id).status == "waiting"
    document = _document(db, import_id)
    assert "Example Server" in document.markdown
    assert document.source_type == "csv"
    assert store.read(document.original_path) == CSV


def test_pasted_text_is_stored_as_a_txt_original(db, store):
    document = _document(db, import_text(db, store, "Quote Q-2: 1 x Example Server"))
    assert document.original_path.endswith(".txt")
    assert document.source_type == "pasted_text"
    assert store.read(document.original_path) == b"Quote Q-2: 1 x Example Server"


def test_an_unsupported_file_stores_nothing(db, store):
    with pytest.raises(ValueError):
        import_file(db, store, b"whatever", "notes.docx")
    assert db.scalar(select(func.count()).select_from(Document)) == 0
    assert not store.root.exists() or not any(store.root.iterdir())


def test_the_same_file_twice_is_a_duplicate(db, store):
    first = _document(db, import_file(db, store, CSV, "Q-1.csv"))
    with pytest.raises(DuplicateDocument) as raised:
        import_file(db, store, CSV, "copy of Q-1.csv")
    assert raised.value.document_id == first.id


def test_an_empty_pdf_fails_at_once_and_cannot_be_retried(db, store):
    record = db.get(Import, import_file(db, store, _blank_pdf(), "Scan-1.pdf"))
    assert record.status == "failed"
    assert record.failure_reason == failures.EMPTY_PDF.reason
    assert record.failure_reason == "A scanned image with no text. Scanned PDFs aren't supported yet."
    assert record.retryable is False


def test_claiming_takes_the_oldest_waiting_import(db, store):
    first = import_file(db, store, CSV, "Q-1.csv")
    second = import_text(db, store, "Quote Q-2")
    assert claim_next_import(db) == first
    assert db.get(Import, first).status == "processing"
    assert claim_next_import(db) == second
    assert claim_next_import(db) is None


def test_a_run_stores_one_draft_and_review_per_quote(db, store, server):
    settings = _answer(server, {"quote_number": "Q-1"}, {"quote_number": "Q-2"})
    import_id = import_file(db, store, CSV, "Q-1.csv")
    claim_next_import(db)
    run_import(db, import_id, settings=settings)

    assert db.get(Import, import_id).status == "done"
    drafts = db.scalars(select(Draft).order_by(Draft.position)).all()
    assert [(d.position, d.draft["quote_number"]) for d in drafts] == [(0, "Q-1"), (1, "Q-2")]
    assert all("counts" in d.checks for d in drafts)
    assert [db.get(Review, d.id).status for d in drafts] == ["needs_review", "needs_review"]


def test_no_quotes_is_a_failure_not_an_empty_success(db, store, server):
    settings = _answer(server)
    import_id = import_file(db, store, CSV, "Q-1.csv")
    run_import(db, import_id, settings=settings)
    record = db.get(Import, import_id)
    assert record.status == "failed"
    assert record.failure_reason == "The model found no quote in this document."
    assert record.retryable is True
    assert db.scalar(select(func.count()).select_from(Draft)) == 0


def test_an_unreachable_model_fails_with_a_plain_reason(db, store):
    import_id = import_file(db, store, CSV, "Q-1.csv")
    run_import(db, import_id, settings=ModelSettings(_closed_port_url()))
    record = db.get(Import, import_id)
    assert record.status == "failed"
    assert record.failure_reason == "The model server didn't answer."
    assert record.failure_hint == "Usually the server is busy or offline. Retrying sends the same document again."
    assert record.retryable is True
    assert "ExtractionError" in record.log


def test_retry_puts_a_failed_import_back_in_line(db, store):
    import_id = import_file(db, store, CSV, "Q-1.csv")
    run_import(db, import_id, settings=ModelSettings(_closed_port_url()))
    retry_import(db, import_id)
    record = db.get(Import, import_id)
    assert record.status == "waiting"
    assert (record.failure_reason, record.failure_hint, record.retryable) == (None, None, False)
    assert claim_next_import(db) == import_id


def test_retry_refuses_an_empty_pdf(db, store):
    import_id = import_file(db, store, _blank_pdf(), "Scan-1.pdf")
    with pytest.raises(ValueError):
        retry_import(db, import_id)


def test_retry_refuses_an_import_that_did_not_fail(db, store):
    import_id = import_file(db, store, CSV, "Q-1.csv")
    with pytest.raises(ValueError):
        retry_import(db, import_id)


def test_removing_a_failed_import_allows_the_file_again(db, store):
    import_id = import_file(db, store, _blank_pdf(), "Scan-1.pdf")
    path = _document(db, import_id).original_path
    remove_import(db, store, import_id)
    db.commit()
    assert db.get(Import, import_id) is None
    assert not (store.root / path).exists()
    again = import_file(db, store, _blank_pdf(), "Scan-1.pdf")
    assert db.get(Import, again).status == "failed"


def test_removing_keeps_the_original_until_the_commit(db, store):
    import_id = import_file(db, store, _blank_pdf(), "Scan-1.pdf")
    path = _document(db, import_id).original_path
    remove_import(db, store, import_id)
    db.rollback()
    assert (store.root / path).exists()


def test_removing_refuses_an_import_that_did_not_fail(db, store):
    import_id = import_file(db, store, CSV, "Q-1.csv")
    with pytest.raises(ValueError):
        remove_import(db, store, import_id)


def test_interrupted_imports_go_back_to_waiting(db, store):
    import_id = import_file(db, store, CSV, "Q-1.csv")
    claim_next_import(db)
    assert requeue_interrupted(db) == 1
    assert db.get(Import, import_id).status == "waiting"
