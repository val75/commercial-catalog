"""The pipeline's checks for one quote, as JSON to store beside its draft.

Lines that share one QuantityCheck (two RAID controller lines, one question) share
one count id, so the question is asked, and answered, once.
"""

from __future__ import annotations

from typing import Any

from pipeline import QuoteReview
from validation.flags import Flag
from validation.quantity import QuantityCheck
from validation.ssd_capacity import CapacityCheck


def checks_to_json(review: QuoteReview) -> dict[str, Any]:
    counts: dict[str, dict] = {}
    ids: list[tuple[QuantityCheck, str]] = []  # by identity: equal checks on different lines stay separate

    def count_id(check: QuantityCheck | None) -> str | None:
        if check is None:
            return None
        for known, known_id in ids:
            if known is check:
                return known_id
        new_id = f"c{len(ids)}"
        ids.append((check, new_id))
        counts[new_id] = {
            "per_server": check.per_server,
            "calculated": check.calculated,
            "explanation": check.explanation,
            "flags": [_flag(flag) for flag in check.flags],
        }
        return new_id

    items = [
        {
            "flags": [_flag(flag) for flag in item.flags],
            "components": [
                {
                    "count": count_id(component.quantity),
                    "capacity": _capacity(component.capacity),
                    "flags": [_flag(flag) for flag in component.flags],
                }
                for component in item.components
            ],
        }
        for item in review.items
    ]
    return {"counts": counts, "items": items}


def _flag(flag: Flag) -> dict[str, Any]:
    return {
        "kind": type(flag.issue).__name__,
        "issue": flag.issue.value,
        "message": flag.message,
        "property": flag.property,
    }


def _capacity(check: CapacityCheck | None) -> dict[str, Any] | None:
    if check is None:
        return None
    return {
        "value": check.value,
        "unit": check.unit,
        "automatic": check.automatic,
        "explanation": check.explanation,
        "flags": [_flag(flag) for flag in check.flags],
    }
