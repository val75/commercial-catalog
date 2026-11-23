from __future__ import annotations

import pytest

from extraction.schema import StorageComponent
from validation.properties import PropertyIssue
from validation.storage_properties import check_storage_properties


def _drive(**properties) -> StorageComponent:
    return StorageComponent.model_validate({"component_type": "storage", "storage": properties})


def _flagged(drive: StorageComponent) -> list[tuple[PropertyIssue, str]]:
    return [(flag.issue, flag.property) for flag in check_storage_properties(drive)]


def test_a_stated_maximum_power_has_no_flags():
    assert check_storage_properties(_drive(power_w={"value": 25, "kind": "maximum", "basis": "stated"})) == []


@pytest.mark.parametrize("kind", ["typical", "average"])
def test_a_typical_or_average_power_flags_the_maximum_as_unavailable(kind):
    # 03-storage.md, rule 8.
    drive = _drive(power_w={"value": 12, "kind": kind, "basis": "stated"})
    assert _flagged(drive) == [(PropertyIssue.MAX_POWER_UNAVAILABLE, "power_w")]


def test_a_power_figure_of_unknown_kind_is_flagged():
    drive = _drive(power_w={"value": 12, "kind": None, "basis": "stated"})
    assert _flagged(drive) == [(PropertyIssue.POWER_KIND_UNKNOWN, "power_w")]


@pytest.mark.parametrize(
    "prop, value",
    [
        ("mpn", {"value": "EXAMPLE123", "basis": "inferred"}),
        ("capacity", {"value": 3.84, "unit": "TB", "basis": "inferred", "reason": " "}),
        ("endurance", {"value": 1, "metric": "DWPD", "basis": "inferred"}),
    ],
)
def test_an_inferred_storage_value_without_a_reason_is_flagged(prop, value):
    assert _flagged(_drive(**{prop: value})) == [(PropertyIssue.INFERRED_WITHOUT_REASON, prop)]


def test_every_flag_has_a_message():
    flags = check_storage_properties(_drive(power_w={"value": 12, "kind": "typical", "basis": "inferred"}))
    assert len(flags) == 2
    assert all(flag.message for flag in flags)
