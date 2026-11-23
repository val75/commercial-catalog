from __future__ import annotations

from extraction.schema import QuoteItem
from validation.quantity import Issue, storage_per_server


def _drive(quantity=None, basis="unknown", capacity=None) -> dict:
    storage = {}
    if capacity is not None:
        storage["capacity"] = {"value": capacity[0], "unit": capacity[1], "basis": "stated"}
    return {"component_type": "storage", "quantity": quantity, "quantity_basis": basis, "storage": storage}


def _server(*components, servers=4) -> QuoteItem:
    return QuoteItem.model_validate({"description": "Example Server", "quantity": servers, "components": list(components)})


def test_each_storage_group_gets_its_own_count_per_server():
    # 03-storage.md, section 3: groups are independent and never combined.
    checks = storage_per_server(
        _server(
            _drive(quantity=16, basis="order_total", capacity=(3.84, "TB")),
            _drive(quantity=8, basis="order_total", capacity=(960, "GB")),
            servers=4,
        )
    )
    assert [(check.per_server, check.calculated, check.flags) for check in checks] == [(4, True, []), (2, True, [])]


def test_two_groups_of_the_same_drive_are_not_flagged_or_added_up():
    checks = storage_per_server(
        _server(_drive(quantity=2, basis="per_unit", capacity=(960, "GB")), _drive(quantity=2, basis="per_unit", capacity=(960, "GB")))
    )
    assert [(check.per_server, check.flags) for check in checks] == [(2, []), (2, [])]


def test_each_group_is_checked_on_its_own():
    checks = storage_per_server(_server(_drive(quantity=16, basis="order_total"), _drive(quantity=8, basis="unknown")))
    assert checks[0].per_server == 4
    assert [flag.issue for flag in checks[1].flags] == [Issue.UNKNOWN_BASIS]


def test_any_whole_count_of_drives_per_server_passes():
    checks = storage_per_server(_server(_drive(quantity=36, basis="order_total"), servers=4))
    assert [(check.per_server, check.flags) for check in checks] == [(9, [])]


def test_an_item_without_storage_has_no_groups():
    nic = {"component_type": "fan", "raw_text": "4x Example 60mm fan"}
    assert storage_per_server(_server(nic)) == []
