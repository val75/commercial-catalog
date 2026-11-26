"""The review queue (board D) and one quote's details (board A), read from storage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from review.decisions import open_questions
from review.summary import Badges, badges, what_was_quoted
from storage.tables import Document, Draft, Import, Review


@dataclass(frozen=True)
class QueueEntry:
    draft_id: int
    document_id: int
    vendor_name: str | None
    quote_number: str | None
    received_at: datetime
    source_name: str
    source_type: str
    description: str
    price_per_server: Decimal | None
    total: Decimal | None
    currency: str | None
    badges: Badges


@dataclass(frozen=True)
class QueueGroup:
    """A file or paste that held several listed quotes: one main row, its quotes underneath."""

    document_id: int
    source_name: str
    source_type: str
    received_at: datetime
    entries: list[QueueEntry]


@dataclass(frozen=True)
class FailedImport:
    import_id: int
    source_name: str
    received_at: datetime
    reason: str | None
    hint: str | None
    retryable: bool


@dataclass(frozen=True)
class ProcessingImport:
    """Waiting for the model or being read: "Reading the quote…"."""

    import_id: int
    source_name: str
    received_at: datetime


@dataclass(frozen=True)
class QueueView:
    failed: list[FailedImport]
    processing: list[ProcessingImport]
    rows: list[QueueEntry | QueueGroup]
    all_count: int  # quotes waiting for review
    ready_count: int  # of those, quotes with no open question


@dataclass(frozen=True)
class QuoteDetail:
    draft_id: int
    status: str
    document: Document
    draft: dict
    checks: dict
    decisions: dict
    badges: Badges
    open_questions: list[str]


def list_queue(session: Session, view: Literal["all", "ready", "rejected"] = "all") -> QueueView:
    if view not in ("all", "ready", "rejected"):
        raise ValueError(f"Unknown queue view {view!r}.")
    waiting = _entries(session, "needs_review")
    ready = [entry for entry in waiting if entry.badges.ready]
    if view == "all":
        shown = waiting
    elif view == "ready":
        shown = ready
    else:
        shown = _entries(session, "rejected")
    return QueueView(
        failed=_failed(session),
        processing=_processing(session),
        rows=_grouped(shown),
        all_count=len(waiting),
        ready_count=len(ready),
    )


def get_quote(session: Session, draft_id: int) -> QuoteDetail:
    found = session.execute(
        select(Review, Draft, Document)
        .join(Draft, Draft.id == Review.draft_id)
        .join(Document, Document.id == Draft.document_id)
        .where(Review.draft_id == draft_id)
    ).first()
    if found is None:
        raise LookupError(f"There's no quote {draft_id}.")
    review, draft, document = found
    return QuoteDetail(
        draft_id=draft.id,
        status=review.status,
        document=document,
        draft=draft.draft,
        checks=draft.checks,
        decisions=review.decisions,
        badges=badges(draft.draft, draft.checks, review.decisions),
        open_questions=open_questions(draft.checks, review.decisions),
    )


def _entries(session: Session, status: str) -> list[QueueEntry]:
    rows = session.execute(
        select(Review, Draft, Document)
        .join(Draft, Draft.id == Review.draft_id)
        .join(Document, Document.id == Draft.document_id)
        .where(Review.status == status)
        .order_by(Document.received_at, Document.id, Draft.position)
    ).all()
    return [_entry(review, draft, document) for review, draft, document in rows]


def _entry(review: Review, draft: Draft, document: Document) -> QueueEntry:
    quote = draft.draft
    items = quote.get("items") or []
    return QueueEntry(
        draft_id=draft.id,
        document_id=document.id,
        vendor_name=quote.get("vendor_name"),
        quote_number=quote.get("quote_number"),
        received_at=document.received_at,
        source_name=document.source_name,
        source_type=document.source_type,
        description=what_was_quoted(quote, draft.checks, review.decisions),
        price_per_server=_money(items[0].get("unit_price")) if len(items) == 1 else None,
        total=_money(quote.get("total")),
        currency=quote.get("currency"),
        badges=badges(quote, draft.checks, review.decisions),
    )


def _grouped(entries: list[QueueEntry]) -> list[QueueEntry | QueueGroup]:
    by_document: dict[int, list[QueueEntry]] = {}
    for entry in entries:
        by_document.setdefault(entry.document_id, []).append(entry)
    rows: list[QueueEntry | QueueGroup] = []
    for document_entries in by_document.values():
        if len(document_entries) == 1:
            rows.append(document_entries[0])
        else:
            first = document_entries[0]
            rows.append(QueueGroup(first.document_id, first.source_name, first.source_type, first.received_at,
                                   document_entries))
    return rows


def _failed(session: Session) -> list[FailedImport]:
    rows = _imports(session, ("failed",))
    return [
        FailedImport(record.id, document.source_name, document.received_at, record.failure_reason,
                     record.failure_hint, record.retryable)
        for record, document in rows
    ]


def _processing(session: Session) -> list[ProcessingImport]:
    return [
        ProcessingImport(record.id, document.source_name, document.received_at)
        for record, document in _imports(session, ("waiting", "processing"))
    ]


def _imports(session: Session, statuses: tuple[str, ...]):
    return session.execute(
        select(Import, Document)
        .join(Document, Document.id == Import.document_id)
        .where(Import.status.in_(statuses))
        .order_by(Document.received_at, Document.id)
    ).all()


def _money(value) -> Decimal | None:
    return None if value is None else Decimal(str(value))
