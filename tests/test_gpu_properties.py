from __future__ import annotations

import pytest

from extraction.schema import GpuComponent
from validation.gpu_properties import check_gpu_properties
from validation.properties import PropertyIssue


def _gpu(**properties) -> GpuComponent:
    return GpuComponent.model_validate({"component_type": "gpu", "gpu": properties})


def _flagged(gpu: GpuComponent) -> list[tuple[PropertyIssue, str]]:
    return [(flag.issue, flag.property) for flag in check_gpu_properties(gpu)]


def test_inferred_gpu_values_with_reasons_have_no_flags():
    gpu = _gpu(
        model={"value": "H100 SXM 80GB", "basis": "stated"},
        architecture={"value": "Hopper", "basis": "inferred", "reason": "H100 is a Hopper GPU"},
        processing_cores={"value": 16896, "terminology": "CUDA cores", "basis": "inferred", "reason": "H100 SXM spec"},
    )
    assert check_gpu_properties(gpu) == []


@pytest.mark.parametrize(
    "prop, value",
    [
        ("architecture", {"value": "Hopper", "basis": "inferred"}),
        ("processing_cores", {"value": 16896, "terminology": "CUDA cores", "basis": "inferred", "reason": " "}),
        ("power_w", {"value": 700, "kind": "max_board_power", "basis": "inferred"}),
        ("memory_bandwidth_gbs", {"value": 3350, "as_written": "3.35 TB/s", "basis": "inferred", "reason": ""}),
    ],
)
def test_an_inferred_gpu_value_without_a_reason_is_flagged(prop, value):
    assert _flagged(_gpu(**{prop: value})) == [(PropertyIssue.INFERRED_WITHOUT_REASON, prop)]
