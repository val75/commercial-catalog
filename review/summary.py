"""What the queue shows about one quote: its badges and a one-line summary of what was quoted."""

from __future__ import annotations

from dataclasses import dataclass

from review.apply import overrides_standard_size
from review.decisions import open_questions
from review.paths import inferred_paths


@dataclass(frozen=True)
class Badges:
    questions: int  # open questions: approval waits for these
    guesses: int  # inferred values the reviewer hasn't used or replaced
    changes: int  # standard SSD sizes that will be applied
    ready: bool  # no question open


def badges(draft: dict, checks: dict, decisions: dict) -> Badges:
    questions = len(open_questions(checks, decisions))
    guesses = sum(1 for path in inferred_paths(draft) if f"property:{path}" not in decisions)
    changes = 0
    for i, item in enumerate(checks.get("items", [])):
        for j, component in enumerate(item["components"]):
            capacity = component["capacity"]
            path = f"items/{i}/components/{j}/storage/capacity"
            if capacity and capacity["automatic"] and not overrides_standard_size(decisions, path):
                changes += 1
    return Badges(questions=questions, guesses=guesses, changes=changes, ready=questions == 0)


def what_was_quoted(draft: dict, checks: dict, decisions: dict) -> str:
    """Such as "4 × Example SR-650 2U · 2 × Xeon Gold 6530 · 2 × L40S 48 GB · 1 TB DDR5". Items joined with "; "."""
    items = draft.get("items") or []
    item_checks = checks.get("items", [])
    return "; ".join(
        _item_summary(item, item_checks[i]["components"] if i < len(item_checks) else [], checks, decisions)
        for i, item in enumerate(items)
    )


def _item_summary(item: dict, component_checks: list[dict], checks: dict, decisions: dict) -> str:
    name = " ".join(part for part in (item.get("manufacturer"), item.get("model")) if part)
    if not name:
        name = (item.get("description") or "")[:40]
    parts = [f"{_number(item.get('quantity'))} × {name}"]

    lines = item.get("components") or []
    per_server = [
        _per_server(component_checks[j]["count"] if j < len(component_checks) else None, checks, decisions)
        for j in range(len(lines))
    ]

    for line, count in zip(lines, per_server):
        if line.get("component_type") == "cpu" and (model := _value(line["cpu"], "model")):
            parts.append(f"{_number(count)} × {model}")

    gpus = [(line, count) for line, count in zip(lines, per_server) if line.get("component_type") == "gpu"]
    for line, count in gpus:
        model = _value(line["gpu"], "model")
        if model:
            memory = _value(line["gpu"], "memory_capacity_gb")
            parts.append(f"{_number(count)} × {model}" + (f" {memory:g} GB" if memory is not None else ""))
    if not gpus and item.get("chassis"):
        parts.append("no GPU")

    memory = _memory(
        [(line["memory"], count) for line, count in zip(lines, per_server) if line.get("component_type") == "memory"]
    )
    if memory:
        parts.append(memory)
    return " · ".join(parts)


def _memory(lines: list[tuple[dict, int | None]]) -> str | None:
    sized = [(_value(properties, "capacity_gb"), count, properties) for properties, count in lines]
    sized = [(capacity, count, properties) for capacity, count, properties in sized if capacity is not None]
    if not sized:
        return None
    types = list(dict.fromkeys(t for _, _, p in sized if (t := _value(p, "memory_type"))))
    suffix = f" {'/'.join(types)}" if types else ""
    if any(count is None for _, count, _ in sized):
        # Module counts not settled yet: show the module size instead of a total.
        sizes = " + ".join(f"{_number(count)} × {capacity:g} GB" for capacity, count, _ in sized)
        return sizes + suffix
    total = sum(capacity * count for capacity, count, _ in sized)
    if total % 1024 == 0:
        return f"{total // 1024:,} TB{suffix}"
    return f"{total:,} GB{suffix}"


def _per_server(count_id: str | None, checks: dict, decisions: dict) -> int | None:
    if count_id is None:
        return None
    per_server = checks["counts"][count_id]["per_server"]
    if per_server is None and (answer := decisions.get(f"answer:{count_id}")):
        per_server = answer["per_server"]
    return per_server


def _value(properties: dict | None, name: str):
    prop = (properties or {}).get(name)
    return prop["value"] if isinstance(prop, dict) else None


def _number(value: int | None) -> str:
    return "?" if value is None else str(value)
