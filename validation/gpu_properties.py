"""Checks on a GPU's extracted properties.

For now only the rule every type shares: inferred values need a reason. Range
checks like the CPU's can be added once they're agreed.
"""

from __future__ import annotations

from extraction.schema import GpuComponent
from validation.flags import Flag
from validation.properties import inferred_without_reason


def check_gpu_properties(component: GpuComponent) -> list[Flag]:
    return inferred_without_reason(component.gpu)
