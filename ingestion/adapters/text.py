"""Pasted-text adapter.

Pasted text is the easiest input technically (it's already text) and the messiest
semantically: forwarded email threads, signatures, disclaimers, quoted replies,
and encoding gremlins from copying out of Outlook or a phone.

Design choice: normalize gently, do NOT try to strip signatures/quoted replies
with rules. Anything you strip you might need. The extraction model is good at
ignoring boilerplate; a regex is not. So we only fix encoding and whitespace and
otherwise keep the text verbatim.
"""

from __future__ import annotations

import re
import unicodedata

from ..models import AdapterOut

try:  # optional; much better mojibake repair if installed
    import ftfy
except ImportError:  # pragma: no cover
    ftfy = None

# The handful of cp1252-decoded-as-utf8 sequences that show up constantly in
# pasted email. Used only as a fallback when ftfy isn't available.
_MOJIBAKE = {
    "\u00e2\u20ac\u2122": "\u2019",  # ’
    "\u00e2\u20ac\u02dc": "\u2018",  # ‘
    "\u00e2\u20ac\u0153": "\u201c",  # “
    "\u00e2\u20ac\u009d": "\u201d",  # ”
    "\u00e2\u20ac\u201d": "\u2014",  # —
    "\u00e2\u20ac\u201c": "\u2013",  # –
    "\u00e2\u20ac\u00a6": "\u2026",  # …
    "\u00c2\u00a0": " ",             # non-breaking space artifact
}


def _fix_encoding(s: str) -> str:
    if ftfy is not None:
        return ftfy.fix_text(s)
    for bad, good in _MOJIBAKE.items():
        s = s.replace(bad, good)
    return s


def to_markdown(raw: str) -> AdapterOut:
    warnings: list[str] = []
    if not raw:
        return AdapterOut("", ["Pasted text was empty."])

    s = _fix_encoding(raw)
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")

    # trim trailing whitespace per line; collapse runs of blank lines to one gap
    s = "\n".join(line.rstrip() for line in s.split("\n"))
    s = re.sub(r"\n{3,}", "\n\n", s).strip("\n")

    if not s.strip():
        warnings.append("Pasted text was empty after normalization.")

    return AdapterOut(markdown=s, warnings=warnings, meta={"char_count": len(s)})
