"""Runs the real, redacted quote through the model, when it's here and asked for:

    RUN_MODEL_TESTS=1 python -m pytest tests/test_extraction_redacted.py -q

redacted/ is gitignored, so this skips in any shared copy of the repo. The
assertions check structure only, never the quote's values, so nothing from the
quote ends up in the repo.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from extraction.client import extract_quotes

PDF = Path(__file__).parent.parent / "redacted" / "quote-pdf.md"

pytestmark = [
    pytest.mark.skipif(not os.environ.get("RUN_MODEL_TESTS"), reason="set RUN_MODEL_TESTS=1 to use the model"),
    pytest.mark.skipif(not PDF.is_file(), reason="the redacted quote isn't here"),
]


def test_parts_continued_on_the_next_page_stay_with_their_server():
    # The network adapter is on page 2. The model once made it an item of its
    # own and lost the drives and GPU at the end of page 1.
    [draft] = extract_quotes(PDF.read_text(encoding="utf-8"), source_name=PDF.name)
    [item] = draft.items
    assert item.chassis is not None
    assert sorted(component.component_type for component in item.components) == [
        "cpu",
        "gpu",
        "memory",
        "nic",
        "storage",
        "storage",
    ]
