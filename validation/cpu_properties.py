"""Sanity checks on a CPU's extracted properties.

These catch the usual slips of a quantized model, such as MHz written where GHz
was asked for, and inferred values with no reason (docs/03-component-library/
00-overview.md, section 4). Every problem is a flag; no value is changed.
"""

from __future__ import annotations

from extraction.schema import CpuComponent
from validation.flags import Flag
from validation.properties import PropertyIssue, inferred_without_reason

BASE_CLOCK_GHZ_RANGE = (1.0, 6.0)
_MUST_BE_ABOVE_ZERO = {
    "physical_cores": "core count",
    "threads": "thread count",
    "cache_mb": "cache size",
    "tdp_w": "TDP",
}


def check_cpu_properties(component: CpuComponent) -> list[Flag]:
    cpu = component.cpu
    flags = inferred_without_reason(cpu)

    for name, label in _MUST_BE_ABOVE_ZERO.items():
        prop = getattr(cpu, name)
        if prop is not None and prop.value <= 0:
            flags.append(Flag(PropertyIssue.NOT_ABOVE_ZERO, f"The {label} reads as {prop.value}.", name))

    cores, threads = cpu.physical_cores, cpu.threads
    if cores is not None and threads is not None and cores.value > 0 and threads.value > 0:
        if threads.value not in (cores.value, 2 * cores.value):
            flags.append(
                Flag(
                    PropertyIssue.THREADS_DONT_MATCH_CORES,
                    f"{threads.value} threads for {cores.value} cores: expected {cores.value} or {2 * cores.value}.",
                    "threads",
                )
            )

    clock = cpu.base_clock_ghz
    low, high = BASE_CLOCK_GHZ_RANGE
    if clock is not None and not low <= clock.value <= high:
        flags.append(
            Flag(
                PropertyIssue.CLOCK_OUT_OF_RANGE,
                f"A base clock of {clock.value} GHz is outside {low:g}-{high:g} GHz. Was it given in MHz?",
                "base_clock_ghz",
            )
        )

    return flags
