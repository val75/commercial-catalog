from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Flag:
    """Something review has to show the user. It never changes a value by itself."""

    issue: Enum
    message: str
    # The property the flag is about, such as "threads", so review can show it there.
    property: str | None = None
