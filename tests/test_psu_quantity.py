from __future__ import annotations

from extraction.schema import QuoteItem
from validation.quantity import Issue, psus_per_server


def _psu_line(quantity=None, basis="unknown", **properties) -> dict:
    psu = {name: {"value": value, "basis": "stated"} for name, value in properties.items()}
    return {"component_type": "psu", "quantity": quantity, "quantity_basis": basis, "psu": psu}


def _server(*components, servers=8) -> QuoteItem:
    return QuoteItem.model_validate({"description": "Example Server", "quantity": servers, "components": list(components)})


def test_a_whole_order_count_of_power_supplies_is_divided_by_the_number_of_servers():
    # A spreadsheet line "1100W Titanium hot-plug PSU" x 16 under 8 chassis.
    check = psus_per_server(_server(_psu_line(quantity=16, basis="order_total"), servers=8))
    assert (check.per_server, check.calculated, check.flags) == (2, True, [])


def test_a_per_server_count_is_kept():
    check = psus_per_server(_server(_psu_line(quantity=2, basis="per_unit")))
    assert (check.per_server, check.flags) == (2, [])


def test_an_unknown_basis_is_asked():
    check = psus_per_server(_server(_psu_line(quantity=16)))
    assert Issue.UNKNOWN_BASIS in [flag.issue for flag in check.flags]


def test_two_lines_of_different_wattage_are_asked_not_added():
    check = psus_per_server(
        _server(
            _psu_line(quantity=1, basis="per_unit", vendor_product_id="PSU-1100"),
            _psu_line(quantity=1, basis="per_unit", vendor_product_id="PSU-2000"),
        )
    )
    assert check.per_server is None and check.flags


def test_an_item_without_a_power_supply_has_nothing_to_check():
    fan = {"component_type": "fan", "raw_text": "4x Example 60mm fan"}
    assert psus_per_server(_server(fan)) is None
