from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from review.actions import approve, reject
from review.queue import FailedImport, ProcessingImport, QueueEntry, QueueGroup, get_quote, list_queue
from storage.tables import Import
from tests.quote_builders import cpu, example_quote, item, quote, stored_document, stored_draft

DAY = datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc)


def ready_quote(number: str = "Q-2"):
    return quote(item(cpu(2), unit_price=14200, extended_price=56800), quote_number=number, total=56800)


def test_the_queue_is_oldest_first(db):
    newer = stored_draft(db, ready_quote("Q-NEW"), received_at=DAY + timedelta(days=2))
    older = stored_draft(db, example_quote(), received_at=DAY)
    rows = list_queue(db).rows
    assert [row.draft_id for row in rows] == [older, newer]
    first = rows[0]
    assert (first.vendor_name, first.quote_number, first.source_name) == ("Example Systems", "Q-48210", "Q-1.pdf")
    assert first.description.startswith("4 × Example SR-650 2U")
    assert (first.price_per_server, first.total, first.currency) == (Decimal("24500"), Decimal("98000"), "USD")
    assert first.badges.questions == 1


def test_two_quotes_from_one_file_are_a_group(db):
    document = stored_document(db, source_name="SC-2207-08.pdf")
    first = stored_draft(db, ready_quote("SC-2207"), document=document, position=0)
    second = stored_draft(db, ready_quote("SC-2208"), document=document, position=1)
    (group,) = list_queue(db).rows
    assert isinstance(group, QueueGroup)
    assert (group.document_id, group.source_name) == (document.id, "SC-2207-08.pdf")
    assert [entry.draft_id for entry in group.entries] == [first, second]


def test_a_group_with_one_quote_left_is_a_plain_row(db):
    document = stored_document(db)
    first = stored_draft(db, ready_quote("SC-2207"), document=document, position=0)
    second = stored_draft(db, ready_quote("SC-2208"), document=document, position=1)
    approve(db, first, by="reviewer")
    (row,) = list_queue(db).rows
    assert isinstance(row, QueueEntry)
    assert row.draft_id == second


def test_ready_shows_only_quotes_without_open_questions(db):
    stored_draft(db, example_quote(), received_at=DAY)
    ready = stored_draft(db, ready_quote(), received_at=DAY + timedelta(days=1))
    view = list_queue(db, "ready")
    assert [row.draft_id for row in view.rows] == [ready]
    assert (view.all_count, view.ready_count) == (2, 1)


def test_approved_quotes_leave_the_queue_and_rejected_ones_have_their_own_view(db):
    approved = stored_draft(db, ready_quote("Q-A"))
    rejected = stored_draft(db, ready_quote("Q-R"))
    waiting = stored_draft(db, ready_quote("Q-W"))
    approve(db, approved, by="reviewer")
    reject(db, rejected, "Wrong vendor", by="reviewer")
    assert [row.draft_id for row in list_queue(db).rows] == [waiting]
    assert [row.draft_id for row in list_queue(db, "rejected").rows] == [rejected]


def test_failed_and_processing_imports_are_always_listed(db):
    failed_document = stored_document(db, source_name="DH-0931.pdf")
    reading_document = stored_document(db, source_name="Q-48402.xlsx")
    waiting_document = stored_document(db, source_name="pasted-text")
    db.add_all([
        Import(document_id=failed_document.id, status="failed", failure_reason="The model server didn't answer.",
               failure_hint="Usually the server is busy or offline.", retryable=True, log=""),
        Import(document_id=reading_document.id, status="processing", log=""),
        Import(document_id=waiting_document.id, status="waiting", log=""),
        Import(document_id=stored_document(db).id, status="done", log=""),
    ])
    db.flush()
    for view in ("all", "ready", "rejected"):
        queue = list_queue(db, view)
        assert [(f.source_name, f.reason, f.hint, f.retryable) for f in queue.failed] == [
            ("DH-0931.pdf", "The model server didn't answer.", "Usually the server is busy or offline.", True)
        ]
        assert all(isinstance(f, FailedImport) for f in queue.failed)
        assert [p.source_name for p in queue.processing] == ["Q-48402.xlsx", "pasted-text"]
        assert all(isinstance(p, ProcessingImport) for p in queue.processing)


def test_counts_are_quotes_not_rows(db):
    document = stored_document(db)
    stored_draft(db, ready_quote("SC-2207"), document=document, position=0)
    stored_draft(db, ready_quote("SC-2208"), document=document, position=1)
    stored_draft(db, example_quote())
    view = list_queue(db)
    assert len(view.rows) == 2
    assert (view.all_count, view.ready_count) == (3, 2)


def test_a_quote_with_several_items_has_no_price_per_server(db):
    draft_id = stored_draft(db, quote(item(cpu(2), unit_price=100), item(cpu(1), unit_price=50), total=250))
    (row,) = list_queue(db).rows
    assert (row.draft_id, row.price_per_server, row.total) == (draft_id, None, Decimal("250"))


def test_a_draft_with_no_items_still_gets_a_row(db):
    draft_id = stored_draft(db, quote())
    (row,) = list_queue(db).rows
    assert (row.draft_id, row.description, row.badges.ready) == (draft_id, "", True)


def test_get_quote_returns_the_document_draft_and_decisions(db):
    draft_id = stored_draft(db, example_quote(), source_name="Q-48210.pdf")
    detail = get_quote(db, draft_id)
    assert (detail.draft_id, detail.status, detail.document.source_name) == (draft_id, "needs_review", "Q-48210.pdf")
    assert detail.draft["quote_number"] == "Q-48210"
    assert "counts" in detail.checks
    assert detail.decisions == {}
    assert detail.open_questions == ["c4"]
    assert detail.badges.questions == 1


def test_get_quote_on_a_missing_id_raises(db):
    with pytest.raises(LookupError):
        get_quote(db, 999_999)
