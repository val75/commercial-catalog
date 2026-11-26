from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from review.actions import NotReviewable, approve, record_decision, reject, undo_approval, withdraw_decision
from review.apply import QuoteNotReady
from storage.tables import ApprovedQuote, Review
from tests.quote_builders import cpu, item, quote, stored_draft

CORES = "items/0/components/0/cpu/physical_cores"
NIC_ANSWER = {"kind": "answer", "count": "c4", "per_server": 1}  # the example quote's network adapter question


def _review(db, draft_id) -> Review:
    return db.get(Review, draft_id)


def _approved_count(db) -> int:
    return db.scalar(select(func.count()).select_from(ApprovedQuote))


def test_a_decision_is_stored_with_who_and_when(db):
    draft_id = stored_draft(db)
    stored = record_decision(db, draft_id, NIC_ANSWER, by="reviewer")
    assert stored["by"] == "reviewer"
    datetime.fromisoformat(stored["at"])
    assert _review(db, draft_id).decisions == {"answer:c4": stored}


def test_a_later_decision_on_the_same_property_replaces_the_first(db):
    draft_id = stored_draft(db)
    record_decision(db, draft_id, {"kind": "use_guess", "path": CORES}, by="reviewer")
    record_decision(db, draft_id, {"kind": "set_value", "path": CORES, "value": 28}, by="reviewer")
    decisions = _review(db, draft_id).decisions
    assert list(decisions) == [f"property:{CORES}"]
    assert decisions[f"property:{CORES}"]["value"] == 28


def test_withdrawing_a_decision_removes_it(db):
    draft_id = stored_draft(db)
    record_decision(db, draft_id, NIC_ANSWER, by="reviewer")
    withdraw_decision(db, draft_id, "answer:c4")
    withdraw_decision(db, draft_id, "answer:c9")  # unknown: nothing happens
    assert _review(db, draft_id).decisions == {}


def test_a_refused_decision_stores_nothing(db):
    draft_id = stored_draft(db)
    with pytest.raises(ValueError):
        record_decision(db, draft_id, {"kind": "answer", "count": "c4", "per_server": 0}, by="reviewer")
    assert _review(db, draft_id).decisions == {}


def test_approve_stores_the_applied_quote_and_its_columns(db):
    draft_id = stored_draft(db)
    record_decision(db, draft_id, NIC_ANSWER, by="reviewer")
    approved = db.get(ApprovedQuote, approve(db, draft_id, by="reviewer"))
    assert (approved.quote_number, approved.vendor_name, approved.currency) == ("Q-48210", "Example Systems", "USD")
    assert approved.total == Decimal("98000")
    assert approved.approved_by == "reviewer"
    assert [c["quantity_per_server"] for c in approved.quote["items"][0]["components"]] == [2, 16, 2, 2, 1]
    assert approved.quote["items"][0]["components"][0]["cpu"]["physical_cores"] is None  # unused guess
    review = _review(db, draft_id)
    assert (review.status, review.decided_by) == ("approved", "reviewer")
    assert review.decided_at is not None


def test_approve_with_an_open_question_changes_nothing(db):
    draft_id = stored_draft(db)
    with pytest.raises(QuoteNotReady):
        approve(db, draft_id, by="reviewer")
    assert _review(db, draft_id).status == "needs_review"
    assert _approved_count(db) == 0


def test_reject_needs_a_reason(db):
    draft_id = stored_draft(db)
    with pytest.raises(ValueError):
        reject(db, draft_id, "   ", by="reviewer")
    assert _review(db, draft_id).status == "needs_review"


def test_reject_keeps_the_quote_and_the_reason(db):
    draft_id = stored_draft(db)
    reject(db, draft_id, "Duplicate of an older quote", by="reviewer")
    review = _review(db, draft_id)
    assert (review.status, review.reject_reason, review.decided_by) == ("rejected", "Duplicate of an older quote", "reviewer")


def test_approving_twice_or_after_rejecting_is_refused(db):
    ready = stored_draft(db, quote(item(cpu(2))))
    approve(db, ready, by="reviewer")
    with pytest.raises(NotReviewable):
        approve(db, ready, by="reviewer")
    with pytest.raises(NotReviewable):
        record_decision(db, ready, {"kind": "set_value", "path": "items/0/components/0/cpu/model", "value": "X"}, by="r")

    rejected = stored_draft(db, quote(item(cpu(2))))
    reject(db, rejected, "Not a server quote", by="reviewer")
    with pytest.raises(NotReviewable):
        approve(db, rejected, by="reviewer")
    with pytest.raises(NotReviewable):
        reject(db, rejected, "Again", by="reviewer")
    assert _approved_count(db) == 1


def test_undo_reopens_the_latest_approval_with_its_decisions(db):
    draft_id = stored_draft(db)
    record_decision(db, draft_id, NIC_ANSWER, by="reviewer")
    approve(db, draft_id, by="reviewer")
    undo_approval(db, draft_id)
    review = _review(db, draft_id)
    assert (review.status, review.decided_by, review.decided_at) == ("needs_review", None, None)
    assert list(review.decisions) == ["answer:c4"]
    assert _approved_count(db) == 0


def test_undo_refuses_an_older_approval(db):
    older, newer = stored_draft(db, quote(item(cpu(2)))), stored_draft(db, quote(item(cpu(2))))
    approve(db, older, by="reviewer")
    approve(db, newer, by="reviewer")
    with pytest.raises(NotReviewable):
        undo_approval(db, older)
    undo_approval(db, newer)
    assert _review(db, newer).status == "needs_review"


def test_undo_refuses_a_quote_that_is_not_approved(db):
    with pytest.raises(NotReviewable):
        undo_approval(db, stored_draft(db))
