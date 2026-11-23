from __future__ import annotations

from extraction.schema import QuoteItem
from validation.quantity import Issue, nics_per_server


def _nic_line(quantity=None, basis="unknown", **properties) -> dict:
    nic = {name: {"value": value, "basis": "stated"} for name, value in properties.items()}
    return {"component_type": "nic", "quantity": quantity, "quantity_basis": basis, "nic": nic}


def _server(*components, servers=4) -> QuoteItem:
    return QuoteItem.model_validate({"description": "Example Server", "quantity": servers, "components": list(components)})


def test_a_whole_order_count_of_adapters_is_divided_by_the_number_of_servers():
    check = nics_per_server(_server(_nic_line(quantity=16, basis="order_total"), servers=4))
    assert (check.per_server, check.calculated, check.flags) == (4, True, [])


def test_a_per_server_count_is_kept():
    check = nics_per_server(_server(_nic_line(quantity=2, basis="per_unit")))
    assert (check.per_server, check.flags) == (2, [])


def test_an_unknown_basis_is_asked():
    check = nics_per_server(_server(_nic_line(quantity=16)))
    assert Issue.UNKNOWN_BASIS in [flag.issue for flag in check.flags]


def test_an_item_without_an_adapter_has_nothing_to_check():
    fan = {"component_type": "fan", "raw_text": "4x Example 60mm fan"}
    assert nics_per_server(_server(fan)) is None
