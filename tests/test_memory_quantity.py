from __future__ import annotations

import pytest

from extraction.schema import QuoteItem
from validation.quantity import Issue, modules_per_server


def _memory_line(quantity=None, basis="unknown", **properties) -> dict:
    memory = {name: {"value": value, "basis": "stated"} for name, value in properties.items()}
    return {"component_type": "memory", "quantity": quantity, "quantity_basis": basis, "memory": memory}


def _server(*components, servers=4) -> QuoteItem:
    return QuoteItem.model_validate({"description": "Example Server", "quantity": servers, "components": list(components)})


def _issues(check) -> list[Issue]:
    return [flag.issue for flag in check.flags]


def test_a_whole_order_count_of_modules_is_divided_by_the_number_of_servers():
    check = modules_per_server(_server(_memory_line(quantity=96, basis="order_total", capacity_gb=96), servers=4))
    assert (check.per_server, check.calculated, check.flags) == (24, True, [])


@pytest.mark.parametrize("per_server", [3, 12, 24, 48])
def test_any_whole_count_of_modules_per_server_passes(per_server):
    # No list of usual counts for memory yet.
    check = modules_per_server(_server(_memory_line(quantity=per_server, basis="per_unit")))
    assert (check.per_server, check.flags) == (per_server, [])


def test_an_item_without_a_memory_line_has_nothing_to_check():
    cpu = {"component_type": "cpu", "quantity": 2, "quantity_basis": "per_unit"}
    assert modules_per_server(_server(cpu)) is None


def test_cpu_lines_are_not_counted_as_memory():
    cpu = {"component_type": "cpu", "quantity": 2, "quantity_basis": "per_unit"}
    check = modules_per_server(_server(cpu, _memory_line(quantity=16, basis="per_unit")))
    assert (check.per_server, check.flags) == (16, [])


def test_an_unknown_basis_is_asked():
    check = modules_per_server(_server(_memory_line(quantity=96, basis="unknown")))
    assert check.per_server is None
    assert _issues(check) == [Issue.UNKNOWN_BASIS]


def test_a_memory_line_without_a_module_count_is_asked():
    # Covers a quote that gives only total memory, such as "512GB DDR5 RDIMM".
    check = modules_per_server(_server(_memory_line(quantity=None, basis="per_unit")))
    assert check.per_server is None
    assert _issues(check) == [Issue.NO_QUANTITY]


def test_modules_that_do_not_split_evenly_are_flagged():
    check = modules_per_server(_server(_memory_line(quantity=90, basis="order_total"), servers=4))
    assert _issues(check) == [Issue.UNEVEN_SPLIT]


def test_the_same_module_on_several_lines_is_asked_rather_than_added_up():
    check = modules_per_server(
        _server(
            _memory_line(quantity=8, basis="per_unit", capacity_gb=64),
            _memory_line(quantity=8, basis="per_unit", capacity_gb=64),
        )
    )
    assert check.per_server is None
    assert _issues(check) == [Issue.SEVERAL_LINES]


@pytest.mark.parametrize(
    "first, second",
    [
        ({"capacity_gb": 64}, {"capacity_gb": 32}),
        ({"mpn": "MPN-A"}, {"mpn": "MPN-B"}),
        ({"vendor_product_id": "VND-1"}, {"vendor_product_id": "VND-2"}),
    ],
    ids=["capacity", "mpn", "vendor product id"],
)
def test_different_modules_in_one_server_are_flagged(first, second):
    check = modules_per_server(
        _server(_memory_line(quantity=8, basis="per_unit", **first), _memory_line(quantity=8, basis="per_unit", **second))
    )
    assert check.per_server is None
    assert _issues(check) == [Issue.MIXED_MODELS]


def test_lines_that_differ_only_where_one_says_nothing_are_asked_about_not_called_mixed():
    check = modules_per_server(
        _server(
            _memory_line(quantity=8, basis="per_unit", capacity_gb=64, mpn="MPN-A"),
            _memory_line(quantity=8, basis="per_unit", capacity_gb=64),
        )
    )
    assert _issues(check) == [Issue.SEVERAL_LINES]
