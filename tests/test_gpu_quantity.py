from __future__ import annotations

import pytest

from extraction.schema import QuoteItem
from validation.quantity import Issue, gpus_per_server


def _gpu_line(quantity=None, basis="unknown", **properties) -> dict:
    gpu = {name: {"value": value, "basis": "stated"} for name, value in properties.items()}
    return {"component_type": "gpu", "quantity": quantity, "quantity_basis": basis, "gpu": gpu}


def _server(*components, servers=4) -> QuoteItem:
    return QuoteItem.model_validate({"description": "Example Server", "quantity": servers, "components": list(components)})


def _issues(check) -> list[Issue]:
    return [flag.issue for flag in check.flags]


def test_a_whole_order_count_of_gpus_is_divided_by_the_number_of_servers():
    check = gpus_per_server(_server(_gpu_line(quantity=32, basis="order_total"), servers=4))
    assert (check.per_server, check.calculated, check.flags) == (8, True, [])


@pytest.mark.parametrize("per_server", [3, 10, 16])
def test_any_whole_count_of_gpus_per_server_passes(per_server):
    # No list of usual counts for GPUs yet.
    check = gpus_per_server(_server(_gpu_line(quantity=per_server, basis="per_unit")))
    assert (check.per_server, check.flags) == (per_server, [])


def test_a_dpu_line_is_not_counted_as_a_gpu():
    dpu = {"component_type": "dpu", "quantity": 4, "dpu": {"model": {"value": "Example DPU 200GbE", "basis": "stated"}}}
    check = gpus_per_server(_server(dpu, _gpu_line(quantity=8, basis="per_unit")))
    assert (check.per_server, check.flags) == (8, [])


def test_an_item_without_a_gpu_line_has_nothing_to_check():
    dpu = {"component_type": "dpu", "quantity": 4, "dpu": {"model": {"value": "Example DPU 200GbE", "basis": "stated"}}}
    assert gpus_per_server(_server(dpu)) is None


def test_an_unknown_basis_is_asked():
    check = gpus_per_server(_server(_gpu_line(quantity=32)))
    assert check.per_server is None
    assert _issues(check) == [Issue.UNKNOWN_BASIS]


@pytest.mark.parametrize(
    "first, second",
    [
        ({"model": "H100 SXM 80GB"}, {"model": "H200 SXM 141GB"}),
        ({"memory_capacity_gb": 80}, {"memory_capacity_gb": 94}),
    ],
    ids=["model", "memory capacity"],
)
def test_different_gpus_in_one_server_are_flagged(first, second):
    check = gpus_per_server(
        _server(_gpu_line(quantity=4, basis="per_unit", **first), _gpu_line(quantity=4, basis="per_unit", **second))
    )
    assert _issues(check) == [Issue.MIXED_MODELS]


def test_the_same_gpu_on_several_lines_is_asked_rather_than_added_up():
    check = gpus_per_server(
        _server(
            _gpu_line(quantity=4, basis="per_unit", model="H100 SXM 80GB"),
            _gpu_line(quantity=4, basis="per_unit", model="H100 SXM 80GB"),
        )
    )
    assert _issues(check) == [Issue.SEVERAL_LINES]
