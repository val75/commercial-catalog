"""A draft, its checks and the reviewer's decisions, turned into the quote that's approved.

Every property says where its value came from ("source"): the quote, a guess the
reviewer used, a value the reviewer typed, or the standard SSD size. A guess the
reviewer didn't use never reaches the approved quote.
"""

from __future__ import annotations

import copy

from review.decisions import open_questions
from review.paths import get_at, property_paths, set_at


class QuoteNotReady(Exception):
    """Questions are still open, so the quote can't be approved."""

    def __init__(self, questions: list[str]):
        super().__init__(f"{len(questions)} question{'s' if len(questions) != 1 else ''} still open.")
        self.questions = questions


def apply_decisions(draft: dict, checks: dict, decisions: dict) -> dict:
    questions = open_questions(checks, decisions)
    if questions:
        raise QuoteNotReady(questions)

    result = copy.deepcopy(draft)
    for path in property_paths(result):
        _apply_property(result, path, decisions.get(f"property:{path}"))
    _apply_standard_sizes(result, checks, decisions)
    _apply_counts(result, checks, decisions)
    return result


def _apply_property(result: dict, path: str, decision: dict | None) -> None:
    prop = get_at(result, path)
    if decision is None:
        if prop["basis"] == "inferred":
            set_at(result, path, None)  # an unused guess is left out
        else:
            prop["source"] = "quote"
    elif decision["kind"] == "use_guess":
        prop["source"] = "guess_used"
    elif decision["value"] is None:
        set_at(result, path, None)
    else:
        prop.update(value=decision["value"], basis=decision["basis"], reason=None, source="reviewer")


def _apply_standard_sizes(result: dict, checks: dict, decisions: dict) -> None:
    for i, item in enumerate(checks.get("items", [])):
        for j, component in enumerate(item["components"]):
            capacity = component["capacity"]
            path = f"items/{i}/components/{j}/storage/capacity"
            if not (capacity and capacity["automatic"]):
                continue
            if overrides_standard_size(decisions, path):
                continue
            prop = get_at(result, path)
            if prop is None:  # a guessed size nobody used
                continue
            as_written = prop.get("as_written") or f"{prop['value']:g} {prop['unit']}"
            prop.update(value=capacity["value"], unit=capacity["unit"], as_written=as_written, source="standard_size")


def overrides_standard_size(decisions: dict, path: str) -> bool:
    """The reviewer kept the quote's size or typed one. Ticking a guessed size still gets the standard size."""
    typed = decisions.get(f"property:{path}")
    return f"keep_original:{path}" in decisions or (typed is not None and typed["kind"] == "set_value")


def _apply_counts(result: dict, checks: dict, decisions: dict) -> None:
    counts = checks.get("counts", {})
    for i, item in enumerate(checks.get("items", [])):
        for j, component in enumerate(item["components"]):
            cid = component["count"]
            per_server = None
            if cid is not None:
                per_server = counts[cid]["per_server"]
                if per_server is None:
                    per_server = decisions[f"answer:{cid}"]["per_server"]
            result["items"][i]["components"][j]["quantity_per_server"] = per_server
