from __future__ import annotations

import json

import pytest

from extraction.client import ExtractionError, ModelSettings
from extraction.schema import Basis, QuoteDraft
from pipeline import process_file, process_text, review_draft
from tests.test_extraction_client import FakeModelServer, _reply
from validation.properties import PropertyIssue
from validation.quantity import Issue


@pytest.fixture
def server():
    fake = FakeModelServer()
    yield fake
    fake.close()


def _answer(server: FakeModelServer, *quotes: dict) -> ModelSettings:
    server.body = json.dumps(_reply(json.dumps({"quotes": list(quotes)})))
    return ModelSettings(server.base_url)


def _stated(value) -> dict:
    return {"value": value, "basis": "stated"}


def _cpu(quantity=2, basis="per_unit", **properties) -> dict:
    return {
        "component_type": "cpu",
        "quantity": quantity,
        "quantity_basis": basis,
        "cpu": {"model": _stated("Xeon Silver 4510"), **properties},
    }


def _drive(capacity_tb: float, quantity=4, basis="per_unit") -> dict:
    return {
        "component_type": "storage",
        "quantity": quantity,
        "quantity_basis": basis,
        "storage": {
            "storage_type": _stated("SSD"),
            "capacity": {"value": capacity_tb, "unit": "TB", "basis": "stated"},
        },
    }


def _draft(*components, servers=4, **item) -> QuoteDraft:
    return QuoteDraft.model_validate(
        {
            "quote_number": "Q-1",
            "items": [{"description": "Example Server", "quantity": servers, "components": list(components), **item}],
        }
    )


# --- running the stages ----------------------------------------------------------


def test_pasted_text_goes_through_extraction_with_its_source_name(server):
    settings = _answer(server, {"quote_number": "Q-1"}, {"quote_number": "Q-2"})
    result = process_text("Quote Q-1 ... Quote Q-2", source_name="email.txt", settings=settings)
    assert [quote.draft.quote_number for quote in result.quotes] == ["Q-1", "Q-2"]
    assert server.requests[0]["json"]["messages"][-1]["content"].startswith("File name: email.txt")
    assert result.document.source_name == "email.txt"


def test_a_file_is_ingested_by_its_type_first(server):
    settings = _answer(server, {"quote_number": "Q-9"})
    result = process_file(b"Item,Qty\nExample Server,2\n", "Q-9.csv", settings=settings)
    assert result.document.source_type.value == "csv"
    assert "| Example Server |" in server.requests[0]["json"]["messages"][-1]["content"]
    assert [quote.draft.quote_number for quote in result.quotes] == ["Q-9"]


def test_an_empty_document_stops_before_the_model(server):
    result = process_text("   \n ", settings=ModelSettings(server.base_url))
    assert (result.quotes, server.requests) == ([], [])


def test_an_extraction_failure_stops_the_pipeline(server):
    server.status = 500
    with pytest.raises(ExtractionError):
        process_text("Quote Q-1", settings=ModelSettings(server.base_url))


# --- the checks, attached where review shows them ---------------------------------


def test_each_component_gets_its_count_per_server():
    review = review_draft(_draft(_cpu(quantity=8, basis="order_total"), servers=4))
    [component] = review.items[0].components
    assert (component.quantity.per_server, component.quantity.calculated) == (2, True)


def test_two_lines_of_one_kind_both_carry_the_question():
    review = review_draft(_draft(_cpu(), _cpu(model=_stated("Xeon Gold 6530"))))
    first, second = review.items[0].components
    assert first.quantity is second.quantity
    assert first.quantity.flags[0].issue is Issue.MIXED_MODELS


def test_each_drive_group_gets_its_own_count():
    review = review_draft(_draft(_drive(3.84, quantity=2), _drive(7.68, quantity=8)))
    assert [component.quantity.per_server for component in review.items[0].components] == [2, 8]


def test_a_rounded_ssd_size_on_a_server_is_proposed_not_applied():
    draft = _draft(_cpu(), _drive(3.8))
    review = review_draft(draft)
    drive = review.items[0].components[1]
    assert (drive.capacity.value, drive.capacity.automatic) == (3.84, True)
    assert draft.items[0].components[1].storage.capacity.value == 3.8


def test_property_checks_are_on_their_component():
    cpu = _cpu(threads=_stated(48), physical_cores=_stated(16))
    review = review_draft(_draft(cpu))
    [flag] = review.items[0].components[0].flags
    assert (flag.issue, flag.property) == (PropertyIssue.THREADS_DONT_MATCH_CORES, "threads")


@pytest.mark.parametrize(
    ("component_type", "properties"),
    [("nic", "nic"), ("dpu", "dpu"), ("psu", "psu"), ("raid_controller", "raid_controller")],
)
def test_every_specified_type_needs_a_reason_for_an_inferred_value(component_type, properties):
    line = {"component_type": component_type, "quantity": 1, "quantity_basis": "per_unit"}
    line[properties] = {"manufacturer": {"value": "Examplecorp", "basis": "inferred"}}
    review = review_draft(_draft(line))
    [flag] = review.items[0].components[0].flags
    assert (flag.issue, flag.property) == (PropertyIssue.INFERRED_WITHOUT_REASON, "manufacturer")


def test_the_chassis_needs_a_reason_for_an_inferred_value_too():
    chassis = {"rack_height": {"value": "2U", "basis": "inferred"}, "note": "Rails included", "review_flags": ["x"]}
    review = review_draft(_draft(chassis=chassis))
    [flag] = review.items[0].flags
    assert (flag.issue, flag.property) == (PropertyIssue.INFERRED_WITHOUT_REASON, "rack_height")


def test_a_part_without_a_spec_file_has_nothing_to_check():
    fan = {"component_type": "fan", "raw_text": "4x Example 60mm fan"}
    [component] = review_draft(_draft(fan)).items[0].components
    assert (component.quantity, component.capacity, component.flags) == (None, None, [])


def test_the_draft_is_kept_as_the_model_and_cleanup_left_it():
    draft = _draft(_cpu(quantity=8, basis="order_total"))
    before = draft.model_dump()
    review = review_draft(draft)
    assert review.draft is draft and draft.model_dump() == before
    assert draft.items[0].components[0].cpu.model.basis is Basis.STATED
