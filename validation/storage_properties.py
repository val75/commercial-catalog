"""Checks on a drive's extracted properties.

The rule every type shares (inferred values need a reason), plus the power rule
of 03-storage.md (rule 8): the spec wants the maximum, so a typical or average
figure is kept as it is, labeled, and the maximum flagged as unavailable.
"""

from __future__ import annotations

from extraction.schema import StorageComponent
from validation.flags import Flag
from validation.properties import PropertyIssue, inferred_without_reason


def check_storage_properties(component: StorageComponent) -> list[Flag]:
    drive = component.storage
    flags = inferred_without_reason(drive)

    power = drive.power_w
    if power is not None and power.kind in ("typical", "average"):
        flags.append(
            Flag(
                PropertyIssue.MAX_POWER_UNAVAILABLE,
                f"The quote gives {power.kind} power ({power.value:g} W), not the maximum. The maximum isn't available.",
                "power_w",
            )
        )
    elif power is not None and power.kind is None:
        flags.append(
            Flag(
                PropertyIssue.POWER_KIND_UNKNOWN,
                f"It isn't clear whether {power.value:g} W is the maximum, typical or average power.",
                "power_w",
            )
        )
    return flags
