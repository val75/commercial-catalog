"""Imports: an upload stored, then read by the pipeline one document at a time.

An upload is ingested straight away (so an unsupported type or a duplicate is
refused at once), and its original, Markdown and provenance are stored. The model
runs later, from the stored Markdown, through claim_next_import and run_import, so
a retry never needs the upload again.

Nothing here commits. An original removed with remove_import is deleted from the
folder only after the caller's commit, so a rolled-back removal never loses it.
"""

from __future__ import annotations

import traceback
from pathlib import Path

from sqlalchemy import event, select, update
from sqlalchemy.orm import Session

from extraction.client import ModelSettings
from ingestion import ingest_file, ingest_text
from ingestion.models import NormalizedDoc, SourceType
from pipeline import process_document
from review.checks_json import checks_to_json
from review.failures import EMPTY_DOCUMENT, EMPTY_PDF, NO_QUOTES, Failure, describe_failure
from storage.originals import OriginalStore
from storage.tables import Document, Draft, Import, Review

WAITING, PROCESSING, DONE, FAILED = "waiting", "processing", "done", "failed"


class DuplicateDocument(Exception):
    """This exact file or text was imported already."""

    def __init__(self, document_id: int):
        super().__init__(f"This document was imported already (document {document_id}).")
        self.document_id = document_id


def import_file(session: Session, store: OriginalStore, data: bytes, filename: str) -> int:
    """Store an uploaded file and queue it. Raises ValueError for an unsupported type."""
    document = ingest_file(data, filename)
    return _store(session, store, document, data, Path(filename).suffix.lower())


def import_text(session: Session, store: OriginalStore, text: str) -> int:
    """Store pasted text and queue it. The original is kept as a .txt file."""
    document = ingest_text(text)
    return _store(session, store, document, (text or "").encode("utf-8"), ".txt")


def _store(session: Session, store: OriginalStore, document: NormalizedDoc, data: bytes, suffix: str) -> int:
    sha256 = document.meta["original_sha256"]
    existing = session.scalar(select(Document.id).where(Document.sha256 == sha256))
    if existing is not None:
        raise DuplicateDocument(existing)

    row = Document(
        sha256=sha256,
        source_type=document.source_type.value,
        source_name=document.source_name,
        original_path=store.save(data, sha256, suffix),
        markdown=document.markdown,
        warnings=list(document.warnings),
        meta=dict(document.meta),
    )
    session.add(row)
    session.flush()

    record = Import(document_id=row.id, status=WAITING, log="")
    if document.is_empty:
        _fail(record, EMPTY_PDF if document.source_type is SourceType.PDF else EMPTY_DOCUMENT)
        record.log = "\n".join(document.warnings)
    session.add(record)
    session.flush()
    return record.id


def claim_next_import(session: Session) -> int | None:
    """Take the oldest waiting import and mark it processing. None when nothing waits."""
    record = session.scalars(
        select(Import).where(Import.status == WAITING).order_by(Import.id).limit(1).with_for_update(skip_locked=True)
    ).first()
    if record is None:
        return None
    record.status = PROCESSING
    session.flush()
    return record.id


def run_import(session: Session, import_id: int, *, settings: ModelSettings | None = None) -> None:
    """Read one stored document with the pipeline. Never raises for a pipeline failure: the import records it."""
    record = session.get(Import, import_id)
    document = session.get(Document, record.document_id)
    try:
        result = process_document(_normalized(document), settings=settings)
        drafts = [(quote.draft.model_dump(mode="json"), checks_to_json(quote)) for quote in result.quotes]
    except Exception as error:  # every failure becomes a reason on the queue, never a lost import
        _fail(record, describe_failure(error))
        record.log = "".join(traceback.format_exception(error))
        session.flush()
        return

    if not drafts:
        _fail(record, NO_QUOTES)
        record.log = "The model returned no quotes."
        session.flush()
        return

    for position, (draft, checks) in enumerate(drafts):
        row = Draft(document_id=document.id, position=position, draft=draft, checks=checks)
        session.add(row)
        session.flush()
        session.add(Review(draft_id=row.id, status="needs_review", decisions={}))
    record.status = DONE
    record.log = f"Found {len(drafts)} quote{'s' if len(drafts) != 1 else ''}."
    session.flush()


def retry_import(session: Session, import_id: int) -> None:
    """Put a failed import back in line. Only failures a retry can fix."""
    record = _get(session, import_id)
    if record.status != FAILED or not record.retryable:
        raise ValueError("Only a failed import that can be retried goes back in line.")
    record.status = WAITING
    record.failure_reason = record.failure_hint = None
    record.retryable = False
    session.flush()


def remove_import(session: Session, store: OriginalStore, import_id: int) -> None:
    """Delete a failed import, its document and (after the commit) its original, so it can be uploaded again."""
    record = _get(session, import_id)
    if record.status != FAILED:
        raise ValueError("Only a failed import can be removed.")
    document = session.get(Document, record.document_id)
    _delete_after_commit(session, store, document.original_path)
    session.delete(record)
    session.flush()  # the import first: deleting the document would cascade to it in the database
    session.delete(document)
    session.flush()


def requeue_interrupted(session: Session) -> int:
    """At start-up: imports left processing by a stopped server go back to waiting. Returns how many."""
    result = session.execute(update(Import).where(Import.status == PROCESSING).values(status=WAITING))
    return result.rowcount


def _normalized(document: Document) -> NormalizedDoc:
    return NormalizedDoc(
        source_type=SourceType(document.source_type),
        source_name=document.source_name,
        markdown=document.markdown,
        warnings=list(document.warnings),
        meta=dict(document.meta),
    )


def _fail(record: Import, failure: Failure) -> None:
    record.status = FAILED
    record.failure_reason = failure.reason
    record.failure_hint = failure.hint
    record.retryable = failure.retryable


def _get(session: Session, import_id: int) -> Import:
    record = session.get(Import, import_id)
    if record is None:
        raise LookupError(f"There's no import {import_id}.")
    return record


_PENDING = "originals_to_delete"


def _delete_after_commit(session: Session, store: OriginalStore, path: str) -> None:
    """Delete the original once the removal is really committed, never when it's rolled back or abandoned.

    Each pending delete remembers the transaction it was asked in. Rolling back that
    transaction, or any around it, drops it; so does the session's transaction ending
    without a commit (a close). Only a commit of the whole session transaction deletes.
    """
    if _PENDING not in session.info:
        session.info[_PENDING] = []

        @event.listens_for(session, "after_commit")
        def _delete(committed: Session) -> None:
            pending, committed.info[_PENDING] = committed.info[_PENDING], []
            for _, pending_store, pending_path in pending:
                pending_store.delete(pending_path)

        @event.listens_for(session, "after_soft_rollback")
        def _drop_rolled_back(rolled_back: Session, previous_transaction) -> None:
            rolled_back.info[_PENDING] = [
                entry for entry in rolled_back.info[_PENDING] if not _inside(entry[0], previous_transaction)
            ]

        @event.listens_for(session, "after_transaction_end")
        def _drop_abandoned(ended: Session, transaction) -> None:
            if transaction.parent is None:  # after_commit has run already if this was a commit
                ended.info[_PENDING] = []

    transaction = session.get_nested_transaction() or session.get_transaction()
    session.info[_PENDING].append((transaction, store, path))


def _inside(transaction, outer) -> bool:
    while transaction is not None:
        if transaction is outer:
            return True
        transaction = transaction.parent
    return False
