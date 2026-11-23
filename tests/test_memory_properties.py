from __future__ import annotations

import pytest

from extraction.schema import MemoryComponent
from validation.memory_properties import check_memory_properties
from validation.properties import PropertyIssue


def _memory(**properties) -> MemoryComponent:
    return MemoryComponent.model_validate({"component_type": "memory", "memory": properties})


def test_inferred_memory_values_with_reasons_have_no_flags():
    memory = _memory(
        manufacturer={"value": "Example Maker", "basis": "inferred", "reason": "reseller listing"},
        voltage_v={"value": 1.1, "basis": "inferred", "reason": "DDR5 standard"},
        capacity_gb={"value": 96, "basis": "stated"},
    )
    assert check_memory_properties(memory) == []


@pytest.mark.parametrize("reason", [None, "", "  "])
def test_an_inferred_memory_value_without_a_reason_is_flagged(reason):
    flags = check_memory_properties(_memory(cas_latency={"value": 52, "basis": "inferred", "reason": reason}))
    assert [(flag.issue, flag.property) for flag in flags] == [(PropertyIssue.INFERRED_WITHOUT_REASON, "cas_latency")]
    assert flags[0].message


def test_an_inferred_module_height_without_a_reason_is_flagged_too():
    flags = check_memory_properties(_memory(module_height={"value": "LP", "meaning": "Low Profile", "basis": "inferred"}))
    assert [(flag.issue, flag.property) for flag in flags] == [(PropertyIssue.INFERRED_WITHOUT_REASON, "module_height")]
