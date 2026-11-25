"""Why an import failed, in plain words for the queue's failed-imports section."""

from __future__ import annotations

from dataclasses import dataclass

from extraction.client import ExtractionError


@dataclass(frozen=True)
class Failure:
    reason: str
    hint: str | None
    retryable: bool


EMPTY_PDF = Failure("A scanned image with no text. Scanned PDFs aren't supported yet.", None, False)
EMPTY_DOCUMENT = Failure("The document has no text to read.", None, False)
NO_QUOTES = Failure(
    "The model found no quote in this document.", "Check that this is a quote. Retrying reads it again.", True
)
UNREACHABLE = Failure(
    "The model server didn't answer.",
    "Usually the server is busy or offline. Retrying sends the same document again.",
    True,
)
CUT_OFF = Failure("The model's reply was cut off before the end.", "Very long documents can do this. Retrying may work.", True)
UNEXPECTED = Failure("Something went wrong while reading the quote.", "Download the log for details.", True)


def describe_failure(error: Exception) -> Failure:
    if not isinstance(error, ExtractionError):
        return UNEXPECTED
    message = str(error)
    if message.startswith("Could not reach"):
        return UNREACHABLE
    if "cut off at the token limit" in message:
        return CUT_OFF
    return Failure(message, "Retrying sends the same document again.", True)
