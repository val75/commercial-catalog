"""The reviewer's decisions on a draft: what each kind may say, and which questions are still open.

    answer         {count, per_server}       a count the checks couldn't settle
    use_guess      {path}                    keep an inferred value as it is
    set_value      {path, value, basis}      type a value, for a guess or to correct any property
    keep_original  {path}                    refuse the standard SSD size for one drive

Decisions are stored by key, so a later one on the same thing replaces the earlier:
use_guess and set_value on one property share "property:<path>".
"""

from __future__ import annotations

import copy
import re
from typing import Any

from pydantic import ValidationError

from extraction.schema import QuoteDraft
from review.paths import get_at, inferred_paths, property_paths, set_at

_CAPACITY_PATH = re.compile(r"items/(\d+)/components/(\d+)/storage/capacity")
_BASES = ("stated", "inferred")


def decision_key(decision: dict) -> str:
    kind = decision.get("kind")
    if kind == "answer":
        return f"answer:{decision['count']}"
    if kind in ("use_guess", "set_value"):
        return f"property:{decision['path']}"
    if kind == "keep_original":
        return f"keep_original:{decision['path']}"
    raise ValueError(f"Unknown decision kind {kind!r}.")


def validate_decision(draft: dict, checks: dict, decision: dict) -> dict:
    """The decision with only its own fields, checked against this draft and its checks. Raises ValueError."""
    kind = decision.get("kind")
    if kind == "answer":
        return _answer(checks, decision)
    if kind == "use_guess":
        path = _path(decision)
        if path not in inferred_paths(draft):
            raise ValueError(f"{path} isn't a guessed value in this draft.")
        return {"kind": kind, "path": path}
    if kind == "set_value":
        return _set_value(draft, decision)
    if kind == "keep_original":
        path = _path(decision)
        if not _automatic_capacity(checks, path):
            raise ValueError(f"{path} has no standard size change to refuse.")
        return {"kind": kind, "path": path}
    raise ValueError(f"Unknown decision kind {kind!r}.")


def open_questions(checks: dict, decisions: dict) -> list[str]:
    """Count ids the checks couldn't settle and the reviewer hasn't answered, in id order."""
    unsettled = [cid for cid, count in checks.get("counts", {}).items() if count["per_server"] is None]
    return sorted((cid for cid in unsettled if f"answer:{cid}" not in decisions), key=lambda cid: int(cid[1:]))


def _answer(checks: dict, decision: dict) -> dict:
    count = decision.get("count")
    known = checks.get("counts", {}).get(count)
    if known is None:
        raise ValueError(f"There's no count {count!r} in this draft's checks.")
    if known["per_server"] is not None:
        raise ValueError(f"Count {count} is already settled ({known['per_server']} per server).")
    per_server = decision.get("per_server")
    if isinstance(per_server, bool) or not isinstance(per_server, int) or per_server < 1:
        raise ValueError("The number per server must be a whole number of at least 1.")
    return {"kind": "answer", "count": count, "per_server": per_server}


def _set_value(draft: dict, decision: dict) -> dict:
    path = _path(decision)
    if path not in property_paths(draft):
        raise ValueError(f"{path} isn't a property in this draft.")
    value = decision.get("value")
    if value is not None and (isinstance(value, (list, dict)) or not isinstance(value, (str, int, float, bool))):
        raise ValueError("A value must be text, a number, true or false, or nothing.")
    basis = decision.get("basis", "stated")
    if basis not in _BASES:
        raise ValueError(f"The basis must be stated or inferred, not {basis!r}.")
    if value is None:
        return {"kind": "set_value", "path": path, "value": None, "basis": basis}

    # Check the value against the draft schema, which also turns "28" into 28 for a count.
    trial = copy.deepcopy(draft)
    set_at(trial, path, {**get_at(trial, path), "value": value, "basis": basis, "reason": None})
    try:
        checked = QuoteDraft.model_validate(trial).model_dump(mode="json")
    except ValidationError:
        raise ValueError(f"{value!r} isn't a valid value for {path.rsplit('/', 1)[-1].replace('_', ' ')}.") from None
    return {"kind": "set_value", "path": path, "value": get_at(checked, path)["value"], "basis": basis}


def _path(decision: dict) -> str:
    path = decision.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError("The decision needs the path of a property.")
    return path


def _automatic_capacity(checks: dict, path: str) -> bool:
    match = _CAPACITY_PATH.fullmatch(path)
    if not match:
        return False
    i, j = int(match[1]), int(match[2])
    try:
        capacity = checks["items"][i]["components"][j]["capacity"]
    except (IndexError, KeyError):
        return False
    return bool(capacity and capacity["automatic"])
