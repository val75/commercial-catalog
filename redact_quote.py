"""Make a redacted copy of a confidential quote, safe to share for development.

Run this yourself, in a separate terminal rather than through Claude Code:

    python redact_quote.py private/your-quote.pdf

It reads the names to remove from private/names.txt and writes the result to
private/quote.redacted.md. Read that file, then copy it to redacted/ if it's
clean. Only the Markdown body is written, never the filename, hash or PDF
metadata.

If a listed name still appears after redaction, nothing is written to the output
file. A copy goes to private/quote.redacted.needs-review.md and the lines are
reported. Add the missing spelling to names.txt and run again, or if the match
is a false alarm, rerun with --allow-line N for each line you've checked.

Terminal messages stay free of names and filenames, so they're safe to share.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from ingestion import ingest_file

ROOT = Path(__file__).resolve().parent
DEFAULT_NAMES = ROOT / "private" / "names.txt"
DEFAULT_OUTPUT = ROOT / "private" / "quote.redacted.md"

EMAIL = "[EMAIL]"
URL = "[URL]"
PHONE = "[PHONE]"

_PLACEHOLDER = re.compile(r"[A-Z][A-Z0-9_]*")
_MIN_NAME_LENGTH = 2

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

_URL_END = r"[^\s|)\]>]"
_URL_RE = re.compile(
    rf"\bhttps?://{_URL_END}+"
    rf"|\bwww\.{_URL_END}+"
    r"|\b(?:[a-z0-9-]+\.)+"
    r"(?:com|net|org|io|co|biz|info|ai|uk|de|fr|es|it|nl|be|ch|at|se|no|dk|fi|ie|pl|ro|eu|ca|au|jp|in)\b"
    rf"(?:/{_URL_END}*)?",
    re.IGNORECASE,
)

_PHONE_LABEL_RE = re.compile(
    r"(\b(?:tel|telephone|phone|mobile|cell|fax)\b\.?:?[ \t]*)\+?\(?\d[\d \t().-]{5,}\d",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(
    r"(?<![\w.-])\+\d[\d \t().-]{7,}\d(?![\w-])"
    # The digit-and-space guards keep a list of numbers from looking like a phone number.
    r"|(?<![\w.$,-])(?<!\d )\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?![\w-])(?! \d)"
)


@dataclass
class RedactionResult:
    text: str
    counts: dict[str, int]


@dataclass(frozen=True)
class Leftover:
    placeholder: str
    line: int


def _fold(text: str) -> str:
    """Lowercase letters and digits only, with accents removed."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed.casefold() if ch.isalnum())


def parse_names(text: str) -> dict[str, list[str]]:
    """Parse the names file. Errors give line numbers, never the line's content."""
    names: dict[str, list[str]] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        placeholder, separator, name = line.partition("=")
        placeholder, name = placeholder.strip(), name.strip()
        if not separator or not _PLACEHOLDER.fullmatch(placeholder):
            raise ValueError(f"names file line {number}: expected PLACEHOLDER = name, with PLACEHOLDER in capitals")
        if len(_fold(name)) < _MIN_NAME_LENGTH:
            raise ValueError(f"names file line {number}: the name is too short to match safely")
        names.setdefault(placeholder, []).append(name)
    if not names:
        raise ValueError("names file has no names in it yet")
    return names


def _name_pattern(name: str) -> str:
    words = re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", name))
    body = r"[\W_]+".join(re.escape(word) for word in words)
    return rf"(?<![^\W_]){body}(?![^\W_])"


def redact(text: str, names: dict[str, list[str]]) -> RedactionResult:
    counts = {placeholder: 0 for placeholder in names}
    counts.update({EMAIL: 0, URL: 0, PHONE: 0})

    # Contact details go first: an email address often contains a company name.
    text = unicodedata.normalize("NFKC", text)
    text, counts[EMAIL] = _EMAIL_RE.subn(EMAIL, text)
    text, counts[URL] = _URL_RE.subn(URL, text)
    text, labelled = _PHONE_LABEL_RE.subn(lambda m: m.group(1) + PHONE, text)
    text, unlabelled = _PHONE_RE.subn(PHONE, text)
    counts[PHONE] = labelled + unlabelled

    # One combined pass, longest first, so a placeholder is never rewritten and
    # a long name is never partly replaced by a shorter one.
    pairs = [(name, placeholder) for placeholder, spellings in names.items() for name in spellings]
    if pairs:
        pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
        groups = "|".join(f"(?P<n{i}>{_name_pattern(name)})" for i, (name, _) in enumerate(pairs))

        def replace(match: re.Match[str]) -> str:
            placeholder = pairs[int(match.lastgroup[1:])][1]
            counts[placeholder] += 1
            return placeholder

        text = re.sub(groups, replace, text, flags=re.IGNORECASE)

    return RedactionResult(text=text, counts=counts)


def find_leftovers(text: str, names: dict[str, list[str]]) -> list[Leftover]:
    """Search for each name while ignoring spaces, punctuation, case and accents.

    Placeholders become a separator, so they can't match a name themselves or
    join the text on either side of them into a false match.
    """
    markers = [*names, EMAIL, URL, PHONE]
    masked = re.sub("|".join(re.escape(marker) for marker in markers), "\0", text)

    folded: list[str] = []
    lines: list[int] = []
    for number, line in enumerate(masked.split("\n"), start=1):
        for char in line:
            piece = "\0" if char == "\0" else _fold(char)
            folded.append(piece)
            lines.extend([number] * len(piece))
    haystack = "".join(folded)

    found: set[Leftover] = set()
    for placeholder, spellings in names.items():
        for name in spellings:
            key = _fold(name)
            start = haystack.find(key)
            while start != -1:
                found.add(Leftover(placeholder, lines[start]))
                start = haystack.find(key, start + 1)
    return sorted(found, key=lambda item: (item.line, item.placeholder))


def _review_path(output_path: Path) -> Path:
    return output_path.with_suffix(".needs-review" + output_path.suffix)


def run(
    quote_path: Path,
    names_path: Path,
    output_path: Path,
    allowed_lines: set[int] | None = None,
) -> int:
    review_path = _review_path(output_path)
    # A stale file from an earlier run must never be mistaken for this result.
    output_path.unlink(missing_ok=True)
    review_path.unlink(missing_ok=True)

    try:
        names = parse_names(names_path.read_text(encoding="utf-8"))
    except OSError:
        print("Stopped: could not read the names file.", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Stopped: {exc}.", file=sys.stderr)
        return 1

    try:
        data = quote_path.read_bytes()
    except OSError:
        print("Stopped: could not read the quote file.", file=sys.stderr)
        return 1

    # The adapters get a neutral filename, because the real one may be private.
    # Exception text isn't printed, since it can include names or file contents.
    try:
        doc = ingest_file(data, f"quote{quote_path.suffix}")
    except ValueError:
        print("Stopped: this file type isn't supported. Use .pdf, .xlsx, .xlsm, .csv or .tsv.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Stopped: could not process the quote ({type(exc).__name__}).", file=sys.stderr)
        return 1

    if doc.is_empty:
        print(
            "Stopped: no text was found in the quote. Scanned PDFs aren't supported yet.",
            file=sys.stderr,
        )
        return 1

    result = redact(doc.markdown, names)

    print("Replacements:")
    for label, count in result.counts.items():
        note = "  (not found: check the spelling if you expected it)" if count == 0 and label in names else ""
        print(f"  {label}: {count}{note}")

    allowed = allowed_lines or set()
    leftovers = [item for item in find_leftovers(result.text, names) if item.line not in allowed]
    if leftovers:
        review_path.write_text(result.text, encoding="utf-8")
        print("\nStopped: a listed name may still be present. Don't share this copy.", file=sys.stderr)
        for item in leftovers:
            print(f"  line {item.line}: possible {item.placeholder}", file=sys.stderr)
        print(
            f"\nCheck those lines in {review_path}\n"
            "Add any missing spelling to the names file and run again. If a line is a false\n"
            "alarm, run again with --allow-line and that line number.",
            file=sys.stderr,
        )
        return 1

    output_path.write_text(result.text, encoding="utf-8")

    if doc.warnings:
        print(f"\nThe quote had {len(doc.warnings)} ingestion warning(s):")
        for warning in doc.warnings:
            cleaned = redact(warning, names).text
            hidden = bool(find_leftovers(cleaned, names))
            print(f"  {'(hidden: may contain a listed name)' if hidden else cleaned}")

    print(
        f"\nWrote {output_path}\n"
        "This check only covers the names you listed. Before sharing, read the file for\n"
        "addresses, contact people, signatures, quote number prefixes, and product lines\n"
        "or part numbers that identify the company. If it's clean, copy it to redacted/."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Make a redacted copy of a confidential quote.")
    parser.add_argument("quote", type=Path, help="path to the quote (.pdf, .xlsx, .xlsm, .csv or .tsv)")
    parser.add_argument(
        "--allow-line",
        type=int,
        action="append",
        default=[],
        metavar="N",
        help="skip the leftover check on line N, after you've confirmed it's a false alarm",
    )
    args = parser.parse_args()
    return run(args.quote, DEFAULT_NAMES, DEFAULT_OUTPUT, set(args.allow_line))


if __name__ == "__main__":
    sys.exit(main())
