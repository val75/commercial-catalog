"""Checks that apply to the properties of every component type with a spec file."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from extraction.schema import Basis
from validation.flags import Flag


class PropertyIssue(str, Enum):
    INFERRED_WITHOUT_REASON = "inferred_without_reason"
    THREADS_DONT_MATCH_CORES = "threads_dont_match_cores"
    CLOCK_OUT_OF_RANGE = "clock_out_of_range"
    NOT_ABOVE_ZERO = "not_above_zero"
    MAX_POWER_UNAVAILABLE = "max_power_unavailable"
    POWER_KIND_UNKNOWN = "power_kind_unknown"


def inferred_without_reason(properties: BaseModel) -> list[Flag]:
    """Inferred values must say what they were worked out from (00-overview.md, section 4)."""
    flags = []
    for name, prop in properties:
        if prop is not None and prop.basis is Basis.INFERRED and not (prop.reason or "").strip():
            flags.append(
                Flag(
                    PropertyIssue.INFERRED_WITHOUT_REASON,
                    f"The {name.replace('_', ' ')} was inferred, but the model didn't say from what.",
                    name,
                )
            )
    return flags
