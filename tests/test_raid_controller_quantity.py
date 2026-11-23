from __future__ import annotations

from extraction.schema import QuoteItem
from validation.quantity import Issue, raid_controllers_per_server


def _controller_line(quantity=None, basis="unknown", **properties) -> dict:
    controller = {name: {"value": value, "basis": "stated"} for name, value in properties.items()}
    return {"component_type": "raid_controller", "quantity": quantity, "quantity_basis": basis, "raid_controller": controller}


def _server(*components, servers=4) -> QuoteItem:
    return QuoteItem.model_validate({"description": "Example Server", "quantity": servers, "components": list(components)})


def test_a_whole_order_count_of_controllers_is_divided_by_the_number_of_servers():
    # "RC-16I-TM(x4)" under a line of 4 servers.
    check = raid_controllers_per_server(_server(_controller_line(quantity=4, basis="order_total"), servers=4))
    assert (check.per_server, check.calculated, check.flags) == (1, True, [])


def test_a_per_server_count_is_kept():
    check = raid_controllers_per_server(_server(_controller_line(quantity=2, basis="per_unit")))
    assert (check.per_server, check.flags) == (2, [])


def test_an_unknown_basis_is_asked():
    check = raid_controllers_per_server(_server(_controller_line(quantity=4)))
    assert Issue.UNKNOWN_BASIS in [flag.issue for flag in check.flags]


def test_a_raid_controller_and_an_hba_are_asked_not_added():
    # Two roles in one server (08-raid-controller.md section 5): the configuration records each.
    check = raid_controllers_per_server(
        _server(
            _controller_line(quantity=1, basis="per_unit", model="RC-9500-8i", controller_type="Hardware RAID"),
            _controller_line(quantity=1, basis="per_unit", model="HB-9500-16i", controller_type="HBA"),
        )
    )
    assert check.per_server is None and check.flags


def test_an_item_without_a_controller_has_nothing_to_check():
    fan = {"component_type": "fan", "raw_text": "4x Example 60mm fan"}
    assert raid_controllers_per_server(_server(fan)) is None
