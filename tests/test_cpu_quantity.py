from __future__ import annotations

import pytest

from extraction.schema import QuoteItem
from validation.quantity import Issue, cpus_per_server


def _cpu_line(quantity=None, basis="unknown", model="9654") -> dict:
    line = {"component_type": "cpu", "quantity": quantity, "quantity_basis": basis}
    if model is not None:
        line["cpu"] = {"model": {"value": model, "basis": "stated"}}
    return line


def _server(*components, servers=4) -> QuoteItem:
    return QuoteItem.model_validate({"description": "Example Server", "quantity": servers, "components": list(components)})


def _issues(check) -> list[Issue]:
    return [flag.issue for flag in check.flags]


# --- counts the step can work out on its own ------------------------------------


def test_a_whole_order_count_is_divided_by_the_number_of_servers():
    check = cpus_per_server(_server(_cpu_line(quantity=8, basis="order_total"), servers=4))
    assert (check.per_server, check.calculated, check.flags) == (2, True, [])


def test_a_per_server_count_is_taken_as_written():
    check = cpus_per_server(_server(_cpu_line(quantity=2, basis="per_unit"), servers=8))
    assert (check.per_server, check.calculated, check.flags) == (2, False, [])


def test_a_per_server_count_does_not_need_the_number_of_servers():
    check = cpus_per_server(_server(_cpu_line(quantity=1, basis="per_unit"), servers=None))
    assert (check.per_server, check.flags) == (1, [])


def test_an_item_without_a_cpu_line_has_nothing_to_check():
    memory = {"component_type": "memory", "quantity": 16, "quantity_basis": "per_unit"}
    nic = {"component_type": "fan", "raw_text": "4x Example 60mm fan"}
    assert cpus_per_server(_server(memory, nic)) is None


# --- answers the user has to give (no count is proposed) -------------------------


def test_an_unknown_basis_is_always_asked_even_when_only_one_reading_makes_sense():
    # 3 across 4 servers can't be a whole-order count, but the user still decides.
    check = cpus_per_server(_server(_cpu_line(quantity=3, basis="unknown"), servers=4))
    assert check.per_server is None
    assert _issues(check) == [Issue.UNKNOWN_BASIS]


def test_a_cpu_line_without_a_quantity_is_asked_rather_than_assumed_to_be_one():
    check = cpus_per_server(_server(_cpu_line(quantity=None, basis="per_unit")))
    assert check.per_server is None
    assert _issues(check) == [Issue.NO_QUANTITY]


def test_a_whole_order_count_without_a_server_count_cannot_be_divided():
    check = cpus_per_server(_server(_cpu_line(quantity=8, basis="order_total"), servers=None))
    assert check.per_server is None
    assert _issues(check) == [Issue.NO_SERVER_COUNT]


@pytest.mark.parametrize("servers", [0, -2])
def test_a_server_count_below_one_cannot_be_divided_by(servers):
    check = cpus_per_server(_server(_cpu_line(quantity=8, basis="order_total"), servers=servers))
    assert check.per_server is None
    assert _issues(check) == [Issue.NO_SERVER_COUNT]


def test_a_count_that_does_not_split_evenly_across_the_servers_is_flagged():
    check = cpus_per_server(_server(_cpu_line(quantity=9, basis="order_total"), servers=4))
    assert check.per_server is None
    assert _issues(check) == [Issue.UNEVEN_SPLIT]


@pytest.mark.parametrize("quantity", [0, -2])
def test_a_quantity_below_one_is_flagged(quantity):
    check = cpus_per_server(_server(_cpu_line(quantity=quantity, basis="per_unit")))
    assert check.per_server is None
    assert _issues(check) == [Issue.NOT_A_COUNT]


def test_the_same_cpu_on_several_lines_is_asked_rather_than_added_up():
    check = cpus_per_server(
        _server(_cpu_line(quantity=1, basis="per_unit"), _cpu_line(quantity=1, basis="per_unit"), servers=4)
    )
    assert check.per_server is None
    assert _issues(check) == [Issue.SEVERAL_LINES]


def test_different_cpu_models_in_one_server_are_flagged():
    check = cpus_per_server(
        _server(
            _cpu_line(quantity=1, basis="per_unit", model="9654"),
            _cpu_line(quantity=1, basis="per_unit", model="9554"),
        )
    )
    assert check.per_server is None
    assert _issues(check) == [Issue.MIXED_MODELS]


def test_cpu_lines_whose_model_is_unknown_are_asked_about_not_called_mixed():
    check = cpus_per_server(_server(_cpu_line(quantity=1, model="9654"), _cpu_line(quantity=1, model=None)))
    assert _issues(check) == [Issue.SEVERAL_LINES]


# --- plausible counts: 1, 2, 4 or 8 per server -----------------------------------


@pytest.mark.parametrize("per_server", [1, 2, 4, 8])
def test_usual_counts_per_server_pass(per_server):
    check = cpus_per_server(_server(_cpu_line(quantity=per_server * 4, basis="order_total"), servers=4))
    assert (check.per_server, check.flags) == (per_server, [])


@pytest.mark.parametrize("per_server", [3, 5, 6, 16])
def test_unusual_counts_per_server_are_proposed_but_flagged(per_server):
    check = cpus_per_server(_server(_cpu_line(quantity=per_server, basis="per_unit")))
    assert check.per_server == per_server
    assert _issues(check) == [Issue.UNUSUAL_COUNT]


def test_an_unusual_count_after_dividing_is_still_marked_as_calculated():
    check = cpus_per_server(_server(_cpu_line(quantity=12, basis="order_total"), servers=4))
    assert (check.per_server, check.calculated) == (3, True)
    assert _issues(check) == [Issue.UNUSUAL_COUNT]


# --- what review shows -----------------------------------------------------------


def test_a_calculated_count_explains_how_it_was_worked_out():
    check = cpus_per_server(_server(_cpu_line(quantity=8, basis="order_total"), servers=4))
    assert "8" in check.explanation and "4" in check.explanation


def test_every_flag_has_a_message_for_the_user():
    check = cpus_per_server(_server(_cpu_line(quantity=3, basis="unknown"), servers=4))
    assert all(flag.message for flag in check.flags)
