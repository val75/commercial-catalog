"""The SSD size rule: on full server quotes, rounded SSD sizes become the enterprise standard size."""

from __future__ import annotations

import pytest

from extraction.schema import QuoteItem, StorageComponent
from validation.ssd_capacity import CapacityIssue, is_full_server, standard_ssd_capacity


def _drive(value, unit="TB", storage_type="SSD") -> StorageComponent:
    storage = {"capacity": {"value": value, "unit": unit, "basis": "stated"}}
    if storage_type is not None:
        storage["storage_type"] = {"value": storage_type, "basis": "stated"}
    return StorageComponent.model_validate({"component_type": "storage", "storage": storage})


# --- applied automatically --------------------------------------------------------


@pytest.mark.parametrize("written, standard", [(1.9, 1.92), (3.8, 3.84), (7.6, 7.68), (15, 15.36)])
def test_rounded_enterprise_sizes_become_the_standard_size(written, standard):
    check = standard_ssd_capacity(_drive(written), full_server=True)
    assert (check.value, check.unit, check.automatic, check.flags) == (standard, "TB", True, [])


def test_the_change_says_what_the_quote_wrote():
    check = standard_ssd_capacity(_drive(3.8), full_server=True)
    assert "3.8" in check.explanation and "3.84" in check.explanation


# --- suggested, and the user decides ---------------------------------------------


@pytest.mark.parametrize("written, suggested", [(2, 1.92), (4, 3.84), (8, 7.68)])
def test_consumer_sizes_are_suggested_as_the_standard_size_and_asked(written, suggested):
    check = standard_ssd_capacity(_drive(written), full_server=True)
    assert (check.value, check.automatic) == (suggested, False)
    assert [flag.issue for flag in check.flags] == [CapacityIssue.CONSUMER_SIZE_ON_A_SERVER]
    assert check.flags[0].message


# --- left alone -------------------------------------------------------------------


@pytest.mark.parametrize("value, unit", [(3.84, "TB"), (960, "GB"), (1.6, "TB"), (30.72, "TB")])
def test_other_sizes_are_left_alone(value, unit):
    assert standard_ssd_capacity(_drive(value, unit), full_server=True) is None


def test_a_size_written_in_gb_is_left_alone():
    assert standard_ssd_capacity(_drive(3800, "GB"), full_server=True) is None


def test_the_rule_only_applies_to_full_server_quotes():
    assert standard_ssd_capacity(_drive(3.8), full_server=False) is None


@pytest.mark.parametrize("storage_type", ["HDD", None])
def test_the_rule_only_applies_to_ssds(storage_type):
    assert standard_ssd_capacity(_drive(3.8, storage_type=storage_type), full_server=True) is None


def test_a_drive_without_a_capacity_is_left_alone():
    drive = StorageComponent.model_validate({"component_type": "storage"})
    assert standard_ssd_capacity(drive, full_server=True) is None


# --- what counts as a full server quote -----------------------------------------


def _item(*components) -> QuoteItem:
    return QuoteItem.model_validate({"description": "Example", "components": list(components)})


def test_an_item_with_a_cpu_is_a_full_server():
    assert is_full_server(_item({"component_type": "cpu"}, {"component_type": "storage"}))


def test_an_item_with_a_chassis_is_a_full_server():
    item = QuoteItem.model_validate({"description": "Example 2U server", "chassis": {"rack_height": {"value": "2U", "basis": "stated"}}})
    assert is_full_server(item)


def test_an_item_with_only_drives_is_not_a_full_server():
    assert not is_full_server(_item({"component_type": "storage"}, {"component_type": "storage"}))
