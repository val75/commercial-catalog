"""What the reviewer does to one quote: decide, approve, reject, undo. Nothing here commits."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from review.apply import apply_decisions
from review.decisions import decision_key, validate_decision
from storage.tables import ApprovedQuote, Draft, Review

NEEDS_REVIEW, APPROVED, REJECTED = "needs_review", "approved", "rejected"


class NotReviewable(Exception):
    """The quote was approved or rejected already, or this undo isn't allowed."""


def record_decision(session: Session, draft_id: int, decision: dict, *, by: str) -> dict:
    """Store one decision, replacing an earlier one on the same thing. Returns it with who and when."""
    review, draft = _open(session, draft_id)
    stored = validate_decision(draft.draft, draft.checks, decision) | {"by": by, "at": _now().isoformat()}
    review.decisions = {**review.decisions, decision_key(stored): stored}
    session.flush()
    return stored


def withdraw_decision(session: Session, draft_id: int, key: str) -> None:
    review, _ = _open(session, draft_id)
    if key in review.decisions:
        review.decisions = {k: v for k, v in review.decisions.items() if k != key}
        session.flush()


def approve(session: Session, draft_id: int, *, by: str) -> int:
    """Store the quote with the decisions applied. Raises QuoteNotReady while a question is open."""
    review, draft = _open(session, draft_id)
    quote = apply_decisions(draft.draft, draft.checks, review.decisions)
    approved = ApprovedQuote(
        draft_id=draft_id,
        vendor_name=quote.get("vendor_name"),
        quote_number=quote.get("quote_number"),
        currency=quote.get("currency"),
        quote_date=date.fromisoformat(quote["quote_date"]) if quote.get("quote_date") else None,
        total=Decimal(str(quote["total"])) if quote.get("total") is not None else None,
        quote=quote,
        approved_by=by,
    )
    session.add(approved)
    _decide(review, APPROVED, by)
    session.flush()
    return approved.id


def reject(session: Session, draft_id: int, reason: str, *, by: str) -> None:
    review, _ = _open(session, draft_id)
    if not (reason or "").strip():
        raise ValueError("Say why the quote is rejected.")
    review.reject_reason = reason.strip()
    _decide(review, REJECTED, by)
    session.flush()


def undo_approval(session: Session, draft_id: int) -> None:
    """Put the most recent approval back in the queue, with its decisions as they were."""
    review = _locked(session, draft_id)
    latest = session.scalars(
        select(ApprovedQuote).order_by(ApprovedQuote.approved_at.desc(), ApprovedQuote.id.desc()).limit(1)
    ).first()
    if review.status != APPROVED or latest is None or latest.draft_id != draft_id:
        raise NotReviewable("Only the most recent approval can be undone.")
    session.delete(latest)
    review.status = NEEDS_REVIEW
    review.decided_by = review.decided_at = None
    session.flush()


def _open(session: Session, draft_id: int) -> tuple[Review, Draft]:
    review = _locked(session, draft_id)
    if review.status != NEEDS_REVIEW:
        raise NotReviewable(f"This quote was {review.status} already.")
    return review, session.get(Draft, draft_id)


def _locked(session: Session, draft_id: int) -> Review:
    """The review, locked and read fresh, so overlapping requests on one quote take turns.

    Without the lock, two decisions recorded at once would each write back the decisions
    they read, and one would be lost.
    """
    review = session.get(Review, draft_id, with_for_update=True, populate_existing=True)
    if review is None:
        raise LookupError(f"There's no quote {draft_id}.")
    return review


def _decide(review: Review, status: str, by: str) -> None:
    review.status = status
    review.decided_by = by
    review.decided_at = _now()


def _now() -> datetime:
    return datetime.now(timezone.utc)
