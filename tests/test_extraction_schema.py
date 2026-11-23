from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from extraction.schema import (
    NicComponent,
    NicProperties,
    ChassisProperties,
    ItemChassis,
    PsuComponent,
    PsuProperties,
    Basis,
    ComponentType,
    CpuComponent,
    ExtractionResult,
    GenericComponent,
    GpuComponent,
    MemoryComponent,
    StorageComponent,
    QuantityBasis,
    QuoteDraft,
    QuoteItem,
    extraction_json_schema,
)


def _component(**overrides) -> dict:
    return {"component_type": "fan", "raw_text": "4x Example 60mm hot-swap fan", **overrides}


def _cpu(**overrides) -> dict:
    return {"component_type": "cpu", **overrides}


def _memory(**overrides) -> dict:
    return {"component_type": "memory", **overrides}


def _gpu(**overrides) -> dict:
    return {"component_type": "gpu", **overrides}


def _storage(**overrides) -> dict:
    return {"component_type": "storage", **overrides}


def _parse_component(data: dict):
    """Parse one component the way extraction does: inside a quote item."""
    return QuoteItem.model_validate(_item(components=[data])).components[0]


def _item(**overrides) -> dict:
    return {"description": "Example Server 1U", **overrides}


# --- the shapes vendors actually send ------------------------------------------


def test_one_input_can_hold_several_quotes():
    result = ExtractionResult.model_validate(
        {"quotes": [{"quote_number": "Q-1", "items": [_item()]}, {"quote_number": "Q-2", "items": [_item()]}]}
    )
    assert [draft.quote_number for draft in result.quotes] == ["Q-1", "Q-2"]


def test_bundled_server_has_a_price_on_the_item_and_none_on_its_parts():
    item = QuoteItem.model_validate(
        _item(
            quantity=8,
            unit_price=14280.0,
            extended_price=114240.0,
            components=[_component(quantity=2, quantity_basis="per_unit")],
        )
    )
    assert item.unit_price == Decimal("14280")
    assert item.components[0].unit_price is None
    assert item.components[0].quantity_basis is QuantityBasis.PER_UNIT


def test_itemized_bom_has_prices_on_the_parts_and_none_on_the_item():
    item = QuoteItem.model_validate(
        _item(
            quantity=4,
            components=[_component(quantity=8, quantity_basis="order_total", unit_price=1180.0, extended_price=9440.0)],
        )
    )
    assert item.unit_price is None
    assert item.components[0].extended_price == Decimal("9440")
    assert item.components[0].quantity_basis is QuantityBasis.ORDER_TOTAL


def test_services_and_fees_sit_alongside_hardware_in_the_same_list():
    item = QuoteItem.model_validate(
        _item(
            components=[
                _component(component_type="fan"),
                _component(component_type="warranty"),
                _component(component_type="support"),
                _component(component_type="service"),
                _component(component_type="license"),
                _component(component_type="cable"),
            ]
        )
    )
    assert ComponentType.WARRANTY in {component.component_type for component in item.components}


def test_line_numbers_are_not_extracted():
    assert "line_number" not in QuoteItem.model_fields


def test_quote_keeps_its_identity_and_totals():
    draft = QuoteDraft.model_validate(
        {
            "quote_number": "Q-1",
            "vendor_name": "Example Reseller",
            "currency": "USD",
            "quote_date": "2026-07-29",
            "subtotal": 100.5,
            "discount": 0.5,
            "tax": 6.0,
            "total": 106.0,
        }
    )
    assert draft.quote_date == date(2026, 7, 29)
    assert draft.total == Decimal("106")


@pytest.mark.parametrize(
    "field",
    ["issued_to", "contact_name", "expiry_date", "payment_terms", "incoterms", "ship_via"],
)
def test_details_the_catalog_does_not_need_are_not_extracted(field):
    assert field not in QuoteDraft.model_fields
    assert field not in extraction_json_schema()["$defs"]["QuoteDraft"]["properties"]


# --- faithful capture: the schema proposes, later stages judge ------------------


def test_money_keeps_its_exact_decimal_value():
    assert QuoteItem.model_validate(_item(unit_price=282293.15)).unit_price == Decimal("282293.15")


def test_implausible_values_are_kept_for_the_validation_stage_to_flag():
    # Stage 5 turns these into review issues. Rejecting them here would lose the draft.
    item = QuoteItem.model_validate(_item(quantity=0, unit_price=-1.0))
    assert item.quantity == 0
    assert item.unit_price == Decimal("-1")


def test_a_draft_with_almost_nothing_found_is_still_valid():
    draft = QuoteDraft.model_validate({})
    assert draft.quote_number is None
    assert draft.items == []


@pytest.mark.parametrize(
    "data",
    [_component(), _cpu(), _memory(), _gpu(), _storage()],
    ids=["generic", "cpu", "memory", "gpu", "storage"],
)
def test_quantity_basis_defaults_to_unknown(data):
    assert _parse_component(data).quantity_basis is QuantityBasis.UNKNOWN


def test_specs_hold_whatever_the_vendor_stated():
    component = _parse_component(_component(specs={"size": "60mm", "hot_swap": "yes"}))
    assert component.specs["size"] == "60mm"


def test_each_line_gets_the_shape_of_its_type():
    item = QuoteItem.model_validate(_item(components=[_cpu(), _memory(), _gpu(), _storage(), _component()]))
    assert [type(component) for component in item.components] == [
        CpuComponent,
        MemoryComponent,
        GpuComponent,
        StorageComponent,
        GenericComponent,
    ]


# --- CPUs: docs/03-component-library/01-cpu.md -----------------------------------


def test_cpu_properties_hold_values_in_the_specs_units():
    cpu = _parse_component(
        _cpu(
            cpu={
                "model": {"value": "9654", "basis": "stated"},
                "code_name": {"value": "Genoa", "basis": "stated"},
                "physical_cores": {"value": 96, "basis": "stated"},
                "threads": {"value": 192, "basis": "stated"},
                "base_clock_ghz": {"value": 2.4, "basis": "stated"},
                "cache_mb": {"value": 384, "basis": "stated"},
                "tdp_w": {"value": 360, "basis": "stated"},
            }
        )
    ).cpu
    assert (cpu.physical_cores.value, cpu.threads.value) == (96, 192)
    assert (cpu.base_clock_ghz.value, cpu.cache_mb.value, cpu.tdp_w.value) == (2.4, 384, 360)
    assert (cpu.model.value, cpu.code_name.value) == ("9654", "Genoa")


def test_an_inferred_cpu_value_is_marked_and_keeps_its_reason():
    cpu = _parse_component(
        _cpu(cpu={"manufacturer": {"value": "AMD", "basis": "inferred", "reason": "Genoa is an AMD code name"}})
    ).cpu
    assert cpu.manufacturer.basis is Basis.INFERRED
    assert cpu.manufacturer.reason == "Genoa is an AMD code name"


def test_a_cpu_known_only_by_its_code_name_is_still_valid():
    # Rules 2 and 11: partial identification is kept, not discarded.
    cpu = _parse_component(_cpu(cpu={"code_name": {"value": "Genoa", "basis": "stated"}})).cpu
    assert cpu.code_name.value == "Genoa"
    assert cpu.model is None


def test_a_cpu_line_keeps_what_review_and_the_quantity_step_need():
    cpu = _parse_component(
        _cpu(
            quantity=16,
            quantity_basis="order_total",
            unit_price=4250.0,
            review_flags=["The quote says 32 cores, but the 9654 has 96."],
        )
    )
    assert (cpu.quantity, cpu.quantity_basis) == (16, QuantityBasis.ORDER_TOTAL)
    assert cpu.unit_price == Decimal("4250")
    assert cpu.review_flags == ["The quote says 32 cores, but the 9654 has 96."]


@pytest.mark.parametrize("basis", ["guessed", "unknown", ""])
def test_a_cpu_value_is_either_stated_or_inferred(basis):
    with pytest.raises(ValidationError):
        _parse_component(_cpu(cpu={"model": {"value": "9654", "basis": basis}}))


def test_cpu_core_and_thread_counts_are_whole_numbers():
    with pytest.raises(ValidationError):
        _parse_component(_cpu(cpu={"physical_cores": {"value": 96.5, "basis": "stated"}}))


@pytest.mark.parametrize(
    "extra",
    [
        {"raw_text": "2x Example CPU"},
        {"part_number": "VND-CPU-001"},
        {"manufacturer_part_number": "100-000000999"},
        {"specs": {"socket": "SP5"}},
        {"extended_price": 8500.0},
        {"cpu": {"socket": {"value": "SP5", "basis": "stated"}}},
    ],
    ids=["original text", "vendor code", "manufacturer part number", "free specs", "line total", "socket"],
)
def test_a_cpu_line_refuses_anything_the_cpu_spec_does_not_list(extra):
    with pytest.raises(ValidationError):
        _parse_component(_cpu(**extra))


# --- memory: docs/03-component-library/02-memory.md -------------------------------


def _stated(value) -> dict:
    return {"value": value, "basis": "stated"}


def test_memory_properties_hold_values_in_the_specs_units():
    memory = _parse_component(
        _memory(
            memory={
                "manufacturer": _stated("Samsung"),
                "product_family": _stated("DDR5 Server Memory"),
                "model": _stated("M321R8GA0BB0-CQK"),
                "mpn": _stated("M321R8GA0BB0-CQK"),
                "vendor_product_id": _stated("VND-MEM-064"),
                "memory_type": _stated("DDR5"),
                "form_factor": _stated("RDIMM"),
                "capacity_gb": _stated(64),
                "data_rate_mts": _stated(4800),
                "operating_frequency_mhz": _stated(2400),
                "ecc": _stated(True),
                "rank": _stated(2),
                "dram_organization": _stated("x4"),
                "dram_density_gb": _stated(16),
                "voltage_v": _stated(1.1),
                "cas_latency": _stated(40),
            }
        )
    ).memory
    assert (memory.capacity_gb.value, memory.data_rate_mts.value, memory.operating_frequency_mhz.value) == (
        64,
        4800,
        2400,
    )
    assert (memory.rank.value, memory.dram_organization.value, memory.dram_density_gb.value) == (2, "x4", 16)
    assert (memory.ecc.value, memory.voltage_v.value, memory.cas_latency.value) == (True, 1.1, 40)
    assert (memory.mpn.value, memory.vendor_product_id.value) == ("M321R8GA0BB0-CQK", "VND-MEM-064")


def test_module_height_keeps_the_quotes_wording_and_its_meaning_separately():
    # Rule 7: the original designation stays; the interpretation sits beside it.
    height = _parse_component(
        _memory(memory={"module_height": {"value": "LP", "meaning": "Low Profile", "basis": "stated"}})
    ).memory.module_height
    assert (height.value, height.meaning) == ("LP", "Low Profile")


def test_module_height_meaning_is_optional_when_unknown():
    height = _parse_component(_memory(memory={"module_height": _stated("XLP")})).memory.module_height
    assert (height.value, height.meaning) == ("XLP", None)


def test_an_inferred_memory_value_is_marked_and_keeps_its_reason():
    voltage = _parse_component(
        _memory(memory={"voltage_v": {"value": 1.1, "basis": "inferred", "reason": "DDR5 standard"}})
    ).memory.voltage_v
    assert (voltage.basis, voltage.reason) == (Basis.INFERRED, "DDR5 standard")


def test_memory_known_only_by_its_capacity_is_still_valid():
    # Rule 11: partial identification is kept.
    memory = _parse_component(_memory(memory={"capacity_gb": _stated(64)})).memory
    assert memory.capacity_gb.value == 64
    assert memory.manufacturer is None


@pytest.mark.parametrize("organization", ["4", "X4", "x5", "4-bit"])
def test_dram_organization_uses_the_standard_notation_only(organization):
    with pytest.raises(ValidationError):
        _parse_component(_memory(memory={"dram_organization": _stated(organization)}))


def test_ecc_is_a_yes_or_no():
    with pytest.raises(ValidationError):
        _parse_component(_memory(memory={"ecc": _stated("maybe")}))


@pytest.mark.parametrize("prop", ["capacity_gb", "data_rate_mts", "rank", "dram_density_gb", "cas_latency"])
def test_memory_counts_and_sizes_are_whole_numbers(prop):
    with pytest.raises(ValidationError):
        _parse_component(_memory(memory={prop: _stated(64.5)}))


def test_a_memory_line_keeps_what_review_and_the_quantity_step_need():
    memory = _parse_component(
        _memory(quantity=96, quantity_basis="order_total", unit_price=410.0, review_flags=["Only a total is given."])
    )
    assert (memory.quantity, memory.quantity_basis) == (96, QuantityBasis.ORDER_TOTAL)
    assert memory.unit_price == Decimal("410")
    assert memory.review_flags == ["Only a total is given."]


@pytest.mark.parametrize(
    "extra",
    [
        {"raw_text": "16x Example 64GB DDR5 RDIMM"},
        {"part_number": "VND-MEM-064"},
        {"specs": {"speed": "PC5-38400"}},
        {"extended_price": 6560.0},
        {"memory": {"speed_grade": _stated("PC5-38400R")}},
    ],
    ids=["original text", "part number", "free specs", "line total", "unlisted property"],
)
def test_a_memory_line_refuses_anything_the_memory_spec_does_not_list(extra):
    with pytest.raises(ValidationError):
        _parse_component(_memory(**extra))


# --- GPUs: docs/03-component-library/04-gpu.md -------------------------------------


def test_gpu_properties_hold_values_in_the_specs_units():
    gpu = _parse_component(
        _gpu(
            gpu={
                "manufacturer": _stated("NVIDIA"),
                "product_family": _stated("Data Center GPU"),
                "model": _stated("H100 SXM 80GB"),
                "mpn": _stated("900-21010-0000-000"),
                "vendor_product_id": _stated("VND-GPU-H100"),
                "architecture": _stated("Hopper"),
                "gpu_chip": _stated("GH100"),
                "memory_capacity_gb": _stated(80),
                "memory_type": _stated("HBM3"),
                "memory_bandwidth_gbs": _stated(2000),
                "memory_interface_bits": _stated(5120),
                "processing_cores": {"value": 16896, "terminology": "CUDA cores", "basis": "stated"},
                "tensor_cores": _stated(528),
                "base_clock_mhz": _stated(1095),
                "boost_clock_mhz": _stated(1980),
                "interface": _stated("SXM5"),
                "form_factor": _stated("SXM"),
                "cooling": _stated("Passive"),
                "power_w": {"value": 700, "kind": "max_board_power", "basis": "stated"},
                "power_connector": _stated("16-pin"),
                "nvlink_support": _stated(True),
                "nvlink_bandwidth_gbs": _stated(900),
            }
        )
    ).gpu
    assert (gpu.memory_capacity_gb.value, gpu.memory_bandwidth_gbs.value, gpu.memory_interface_bits.value) == (
        80,
        2000,
        5120,
    )
    assert (gpu.processing_cores.value, gpu.processing_cores.terminology) == (16896, "CUDA cores")
    assert (gpu.base_clock_mhz.value, gpu.boost_clock_mhz.value) == (1095, 1980)
    assert (gpu.power_w.value, gpu.power_w.kind) == (700, "max_board_power")
    assert (gpu.interface.value, gpu.nvlink_support.value, gpu.nvlink_bandwidth_gbs.value) == ("SXM5", True, 900)
    assert (gpu.mpn.value, gpu.vendor_product_id.value) == ("900-21010-0000-000", "VND-GPU-H100")


def test_the_gpu_chip_maker_and_the_card_maker_are_kept_apart():
    # Rule 3: an NVIDIA GPU can come on an OEM-branded card with the OEM's own part number.
    gpu = _parse_component(
        _gpu(
            gpu={
                "manufacturer": _stated("NVIDIA"),
                "board_manufacturer": _stated("Example OEM"),
                "mpn": _stated("OEM-PN-1234"),
            }
        )
    ).gpu
    assert (gpu.manufacturer.value, gpu.board_manufacturer.value, gpu.mpn.value) == (
        "NVIDIA",
        "Example OEM",
        "OEM-PN-1234",
    )


def test_a_converted_gpu_number_keeps_the_quotes_wording():
    # Rule 16: "1.6 TB/s" becomes 1600 GB/s, and the original stays.
    bandwidth = _parse_component(
        _gpu(gpu={"memory_bandwidth_gbs": {"value": 1600, "as_written": "1.6 TB/s", "basis": "stated"}})
    ).gpu.memory_bandwidth_gbs
    assert (bandwidth.value, bandwidth.as_written) == (1600, "1.6 TB/s")


@pytest.mark.parametrize("kind", ["max_board_power", "power_limit", "typical"])
def test_gpu_power_says_which_figure_it_is(kind):
    power = _parse_component(_gpu(gpu={"power_w": {"value": 600, "kind": kind, "basis": "stated"}})).gpu.power_w
    assert power.kind == kind


def test_gpu_power_refuses_a_kind_the_spec_does_not_name():
    with pytest.raises(ValidationError):
        _parse_component(_gpu(gpu={"power_w": {"value": 600, "kind": "peak", "basis": "stated"}}))


def test_processing_cores_must_name_the_manufacturers_term():
    # Rule 6: CUDA cores and stream processors aren't comparable, so the term stays.
    with pytest.raises(ValidationError):
        _parse_component(_gpu(gpu={"processing_cores": _stated(16896)}))


@pytest.mark.parametrize("prop", ["memory_interface_bits", "tensor_cores"])
def test_gpu_counts_are_whole_numbers(prop):
    with pytest.raises(ValidationError):
        _parse_component(_gpu(gpu={prop: _stated(528.5)}))


def test_a_gpu_known_only_by_its_model_is_still_valid():
    # Rule 14: partial identification is kept.
    gpu = _parse_component(_gpu(gpu={"model": _stated("H100")})).gpu
    assert gpu.model.value == "H100"
    assert gpu.memory_capacity_gb is None


def test_a_gpu_line_keeps_what_review_and_the_quantity_step_need():
    gpu = _parse_component(
        _gpu(quantity=32, quantity_basis="order_total", unit_price=25000.0, review_flags=["Bandwidth varies by variant."])
    )
    assert (gpu.quantity, gpu.quantity_basis) == (32, QuantityBasis.ORDER_TOTAL)
    assert gpu.unit_price == Decimal("25000")
    assert gpu.review_flags == ["Bandwidth varies by variant."]


@pytest.mark.parametrize(
    "extra",
    [
        {"raw_text": "8x Example GPU"},
        {"part_number": "VND-GPU-H100"},
        {"specs": {"rt_cores": "188"}},
        {"extended_price": 200000.0},
        {"gpu": {"rt_cores": _stated(188)}},
    ],
    ids=["original text", "part number", "free specs", "line total", "unlisted property"],
)
def test_a_gpu_line_refuses_anything_the_gpu_spec_does_not_list(extra):
    with pytest.raises(ValidationError):
        _parse_component(_gpu(**extra))


# --- storage: docs/03-component-library/03-storage.md -------------------------------


def test_storage_properties_hold_values_in_the_specs_units():
    drive = _parse_component(
        _storage(
            storage={
                "manufacturer": _stated("Samsung"),
                "product_family": _stated("PM9A3"),
                "model": _stated("MZQL23T8HCLS-00A07"),
                "mpn": _stated("MZQL23T8HCLS-00A07"),
                "storage_type": _stated("SSD"),
                "form_factor": _stated("2.5-inch"),
                "connector": _stated("U.2"),
                "interface": _stated("NVMe PCIe 4.0 x4"),
                "capacity": {"value": 3.84, "unit": "TB", "basis": "stated"},
                "flash_technology": _stated("TLC"),
                "endurance": {"value": 1, "metric": "DWPD", "basis": "stated"},
                "power_w": {"value": 15, "kind": "maximum", "basis": "stated"},
                "encryption": _stated("SED, TCG Opal 2.0"),
            }
        )
    ).storage
    assert (drive.capacity.value, drive.capacity.unit) == (3.84, "TB")
    assert (drive.endurance.value, drive.endurance.metric) == (1, "DWPD")
    assert (drive.power_w.value, drive.power_w.kind) == (15, "maximum")
    assert (drive.connector.value, drive.form_factor.value, drive.interface.value) == ("U.2", "2.5-inch", "NVMe PCIe 4.0 x4")
    assert (drive.mpn.value, drive.encryption.value) == ("MZQL23T8HCLS-00A07", "SED, TCG Opal 2.0")


@pytest.mark.parametrize("unit", ["GB", "TB"])
def test_capacity_keeps_the_unit_as_written(unit):
    capacity = _parse_component(
        _storage(storage={"capacity": {"value": 960, "unit": unit, "basis": "stated"}})
    ).storage.capacity
    assert capacity.unit == unit


@pytest.mark.parametrize("unit", ["TiB", "GiB", "MB", ""])
def test_capacity_refuses_other_units(unit):
    # Rule 19: no mixing of decimal and binary conventions.
    with pytest.raises(ValidationError):
        _parse_component(_storage(storage={"capacity": {"value": 960, "unit": unit, "basis": "stated"}}))


def test_a_capacity_changed_by_a_rule_keeps_the_quotes_wording():
    capacity = _parse_component(
        _storage(storage={"capacity": {"value": 3.84, "unit": "TB", "as_written": "3.8TB", "basis": "stated"}})
    ).storage.capacity
    assert (capacity.value, capacity.as_written) == (3.84, "3.8TB")


@pytest.mark.parametrize("metric", ["DWPD", "TBW", "PBW"])
def test_endurance_keeps_the_manufacturers_metric(metric):
    # Rule 10: DWPD and TBW aren't converted into each other.
    endurance = _parse_component(
        _storage(storage={"endurance": {"value": 7000, "metric": metric, "basis": "stated"}})
    ).storage.endurance
    assert (endurance.value, endurance.metric) == (7000, metric)


def test_endurance_must_name_its_metric():
    with pytest.raises(ValidationError):
        _parse_component(_storage(storage={"endurance": _stated(1)}))


@pytest.mark.parametrize("kind", ["maximum", "typical", "average", None])
def test_storage_power_is_one_number_labeled_with_what_it_is(kind):
    power = _parse_component(_storage(storage={"power_w": {"value": 12, "kind": kind, "basis": "stated"}})).storage.power_w
    assert (power.value, power.kind) == (12, kind)


def test_storage_power_refuses_a_kind_the_spec_does_not_name():
    with pytest.raises(ValidationError):
        _parse_component(_storage(storage={"power_w": {"value": 12, "kind": "peak", "basis": "stated"}}))


def test_a_drive_known_only_by_its_capacity_is_still_valid():
    # Rule 17: partial identification is kept.
    drive = _parse_component(_storage(storage={"capacity": {"value": 960, "unit": "GB", "basis": "stated"}})).storage
    assert drive.capacity.value == 960
    assert drive.manufacturer is None


def test_a_storage_line_keeps_what_review_and_the_quantity_step_need():
    drive = _parse_component(
        _storage(quantity=16, quantity_basis="order_total", unit_price=250.0, review_flags=["MPN may be shortened."])
    )
    assert (drive.quantity, drive.quantity_basis) == (16, QuantityBasis.ORDER_TOTAL)
    assert drive.unit_price == Decimal("250")
    assert drive.review_flags == ["MPN may be shortened."]


@pytest.mark.parametrize(
    "extra",
    [
        {"raw_text": "16x Example 3.84TB NVMe SSD"},
        {"part_number": "VND-SSD-384"},
        {"specs": {"height": "15mm"}},
        {"extended_price": 4000.0},
        {"storage": {"vendor_product_id": _stated("VND-SSD-384")}},
        {"storage": {"warranty": _stated("5 years")}},
        {"storage": {"height_mm": _stated(15)}},
    ],
    ids=["original text", "part number", "free specs", "line total", "vendor product id", "warranty", "height"],
)
def test_a_storage_line_refuses_anything_the_storage_spec_does_not_list(extra):
    with pytest.raises(ValidationError):
        _parse_component(_storage(**extra))


# --- things the schema must refuse ----------------------------------------------


def test_component_requires_the_vendors_original_text():
    with pytest.raises(ValidationError):
        GenericComponent.model_validate({"component_type": "fan"})


def test_item_requires_the_vendors_original_description():
    with pytest.raises(ValidationError):
        QuoteItem.model_validate({"quantity": 1})


def test_unknown_component_type_is_refused_and_other_is_the_escape_hatch():
    with pytest.raises(ValidationError):
        _parse_component(_component(component_type="flux_capacitor"))
    assert _parse_component(_component(component_type="other")).component_type == ComponentType.OTHER


@pytest.mark.parametrize("component_type", ["cpu", "memory", "gpu", "storage"])
def test_a_type_with_its_own_shape_cannot_use_the_generic_one(component_type):
    # Otherwise the model could skip the listed properties and write free text instead.
    with pytest.raises(ValidationError):
        _parse_component({"component_type": component_type, "raw_text": "Example part", "specs": {"size": "64"}})


@pytest.mark.parametrize(
    "model, data",
    [
        (ExtractionResult, {"quotes": [], "surprise": 1}),
        (QuoteDraft, {"surprise": 1}),
        (QuoteItem, _item(surprise=1)),
        (GenericComponent, _component(surprise=1)),
        (CpuComponent, _cpu(surprise=1)),
        (MemoryComponent, _memory(surprise=1)),
        (GpuComponent, _gpu(surprise=1)),
        (StorageComponent, _storage(surprise=1)),
    ],
)
def test_unexpected_fields_are_refused(model, data):
    with pytest.raises(ValidationError):
        model.model_validate(data)


# --- the JSON schema sent to llama.cpp for constrained decoding -----------------


def _walk(node):
    yield node
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def test_json_schema_top_level_is_a_list_of_quotes():
    schema = extraction_json_schema()
    assert schema["required"] == ["quotes"]
    assert schema["properties"]["quotes"]["type"] == "array"


def test_json_schema_has_no_regex_patterns():
    # llama.cpp's grammar converter can't handle lookaheads, which Pydantic's
    # default Decimal schema uses.
    assert not [node for node in _walk(extraction_json_schema()) if isinstance(node, dict) and "pattern" in node]


def test_json_schema_describes_money_as_a_plain_number():
    price = extraction_json_schema()["$defs"]["QuoteItem"]["properties"]["unit_price"]
    assert {"type": "number"} in price["anyOf"]


def test_json_schema_forbids_extra_properties_on_every_object():
    defs = extraction_json_schema()["$defs"]
    assert all(defs[name]["additionalProperties"] is False for name in defs if "properties" in defs[name])
    shapes = {"QuoteDraft", "QuoteItem"}
    for kind in ("Cpu", "Memory", "Gpu", "Storage"):
        shapes |= {f"{kind}Component", f"{kind}Properties"}
    assert shapes <= defs.keys()


def test_json_schema_offers_only_the_types_that_have_a_spec_file():
    # Only CPU, memory, GPU, storage, network adapters, power supplies and chassis have reviewed spec files, so the model
    # extracts nothing else. A free-form "specs" on a network card once ran away
    # into "other_other_other_notes": "None" until the token limit.
    defs = extraction_json_schema()["$defs"]
    choices = defs["QuoteItem"]["properties"]["components"]["items"]["anyOf"]
    assert sorted(choice["$ref"] for choice in choices) == [
        "#/$defs/CpuComponent",
        "#/$defs/GpuComponent",
        "#/$defs/MemoryComponent",
        "#/$defs/NicComponent",
        "#/$defs/PsuComponent",
        "#/$defs/StorageComponent",
    ]
    assert "GenericComponent" not in defs
    assert not [node for node in _walk(extraction_json_schema()) if isinstance(node, dict) and "specs" in node]


def test_the_generic_shape_still_refuses_a_specified_type():
    # Kept in the drafts for the types still to come, but never for a specified type.
    with pytest.raises(ValidationError):
        GenericComponent.model_validate({"component_type": "cpu", "raw_text": "2x CPU"})


def test_json_schema_makes_the_model_answer_every_property():
    # With optional properties, the grammar lets the model close an object at
    # once, and the real model did: "cpu": {}. Required-but-nullable keys make it
    # fill each property or write null.
    defs = extraction_json_schema()["$defs"]
    for name, definition in defs.items():
        if "properties" in definition:
            assert sorted(definition.get("required", [])) == sorted(definition["properties"]), name


# --- network adapters (05-network-adapter.md) -----------------------------------------------


def _nic(**overrides) -> dict:
    return {"component_type": "nic", **overrides}


def test_a_network_adapter_has_exactly_the_properties_its_spec_lists():
    # 05-network-adapter.md, with the changes approved on 2026-11-16: Vendor
    # Product ID and Crypto added, maximum power dropped.
    assert list(NicProperties.model_fields) == [
        "manufacturer",
        "product_family",
        "model",
        "mpn",
        "vendor_product_id",
        "adapter_type",
        "network_technology",
        "port_count",
        "port_speed_gbps",
        "port_connector",
        "host_interface",
        "form_factor",
        "rdma_support",
        "crypto",
    ]


def test_a_network_adapter_line_gets_its_own_shape():
    adapter = _parse_component(
        _nic(
            nic={
                "manufacturer": {"value": "Example", "basis": "stated"},
                "port_count": {"value": 2, "basis": "stated"},
                "port_speed_gbps": {"value": 25, "as_written": "10/25GbE", "basis": "stated"},
                "crypto": {"value": "NoCrypto", "basis": "stated"},
            },
            quantity=4,
            quantity_basis="order_total",
        )
    )
    assert isinstance(adapter, NicComponent)
    assert (adapter.nic.port_count.value, adapter.nic.port_speed_gbps.value) == (2, 25)
    assert adapter.nic.port_speed_gbps.as_written == "10/25GbE"
    assert (adapter.quantity, adapter.quantity_basis) == (4, QuantityBasis.ORDER_TOTAL)


def test_a_network_adapter_is_no_longer_a_generic_line():
    with pytest.raises(ValidationError):
        GenericComponent.model_validate({"component_type": "nic", "raw_text": "2x Example 25GbE NIC"})


@pytest.mark.parametrize("data", [_cpu(), _memory(), _gpu(), _storage(), _nic(), {"component_type": "psu"}])
def test_a_part_can_carry_a_note_from_the_quote(data):
    # Context no property holds, such as "BOSS boot" (00-overview.md, section 6).
    assert _parse_component({**data, "note": "BOSS boot"}).note == "BOSS boot"
    assert _parse_component(data).note is None


def test_a_quote_can_carry_review_flags():
    draft = QuoteDraft.model_validate({"quote_number": "Q-1", "review_flags": ["The date is the email's sent date."]})
    assert draft.review_flags == ["The date is the email's sent date."]
    assert QuoteDraft.model_validate({"quote_number": "Q-1"}).review_flags == []


def test_json_schema_puts_a_quotes_flags_before_its_items():
    # The model writes properties in schema order. With the flags after the items,
    # it ended the whole output after flagging the first quote and dropped the second.
    order = list(extraction_json_schema()["$defs"]["QuoteDraft"]["properties"])
    assert order.index("review_flags") < order.index("items")


def test_json_schema_lets_the_model_leave_a_property_value_empty():
    # With required properties the model opens each one as an object. If "value"
    # can't be null, it fills it anyway: on the lab box it wrote "Unknown" 34 times
    # and guessed "typical" specs for parts the quote doesn't name.
    property_shapes = {
        name: definition
        for name, definition in extraction_json_schema()["$defs"].items()
        if {"value", "basis"} <= definition.get("properties", {}).keys()
    }
    assert {"Property_str_", "Capacity", "Endurance"} <= property_shapes.keys()
    for name, definition in property_shapes.items():
        assert {"type": "null"} in definition["properties"]["value"].get("anyOf", []), name


def _psu(**overrides) -> dict:
    return {"component_type": "psu", **overrides}


def test_a_power_supply_has_exactly_the_properties_its_spec_lists():
    # 06-power-supply.md, with Vendor Product ID added (approved 2026-11-19).
    assert list(PsuProperties.model_fields) == [
        "manufacturer",
        "product_family",
        "model",
        "mpn",
        "vendor_product_id",
        "rated_output_w",
        "power_supply_type",
        "ac_input_phase",
        "input_voltage",
        "input_frequency",
        "input_connector",
        "efficiency_certification",
        "form_factor",
        "hot_swap",
    ]


def test_a_power_supply_line_gets_its_own_shape():
    psu = _parse_component(
        _psu(
            psu={
                "rated_output_w": {"value": 1100, "as_written": "1100W", "basis": "stated"},
                "efficiency_certification": {"value": "Titanium", "basis": "stated"},
                "hot_swap": {"value": True, "basis": "stated"},
            },
            quantity=16,
            quantity_basis="order_total",
            note="redundant",
        )
    )
    assert isinstance(psu, PsuComponent)
    assert (psu.psu.rated_output_w.value, psu.psu.efficiency_certification.value, psu.psu.hot_swap.value) == (
        1100,
        "Titanium",
        True,
    )
    assert (psu.quantity, psu.quantity_basis, psu.note) == (16, QuantityBasis.ORDER_TOTAL, "redundant")


def test_a_power_supply_is_no_longer_a_generic_line():
    with pytest.raises(ValidationError):
        GenericComponent.model_validate({"component_type": "psu", "raw_text": "2x Example 1100W PSU"})


def test_a_power_supply_refuses_redundancy_as_a_property():
    # Redundancy belongs to the System Library configuration (06-power-supply.md section 6).
    with pytest.raises(ValidationError):
        _parse_component(_psu(psu={"redundancy": {"value": "1+1", "basis": "stated"}}))


def test_json_schema_offers_the_power_supply_shape():
    choices = extraction_json_schema()["$defs"]["QuoteItem"]["properties"]["components"]["items"]["anyOf"]
    assert "#/$defs/PsuComponent" in [choice["$ref"] for choice in choices]


def test_the_drafts_themselves_stay_forgiving_about_missing_properties():
    cpu = _parse_component(_cpu(cpu={"code_name": {"value": "Genoa", "basis": "stated"}}))
    assert cpu.cpu.model is None


def test_json_schema_is_plain_json():
    assert json.loads(json.dumps(extraction_json_schema()))


# --- chassis (07-chassis.md) ----------------------------------------------------------------


def test_a_chassis_has_exactly_the_properties_its_spec_lists():
    # 07-chassis.md section 2, with Vendor Product ID added as for the other parts.
    assert list(ChassisProperties.model_fields) == [
        "manufacturer",
        "product_family",
        "model",
        "mpn",
        "vendor_product_id",
        "chassis_type",
        "form_factor",
        "rack_height",
        "dimensions",
        "drive_bays",
        "expansion_slots",
        "psu_bays",
        "cooling",
    ]


def _item_with_chassis(chassis: dict) -> QuoteItem:
    return QuoteItem.model_validate({"description": "Example 2U server", "quantity": 2, "chassis": chassis})


def test_a_quote_item_carries_its_servers_chassis():
    item = _item_with_chassis(
        {
            "model": {"value": "CX-210", "basis": "stated"},
            "rack_height": {"value": "2U", "basis": "stated"},
            "dimensions": {"value": "437 x 89 x 647 mm", "as_written": "17.2 x 3.5 x 25.5 in", "basis": "stated"},
            "review_flags": ["This is the server's model, not the chassis's own."],
        }
    )
    assert isinstance(item.chassis, ItemChassis)
    assert (item.chassis.model.value, item.chassis.rack_height.value) == ("CX-210", "2U")
    assert item.chassis.dimensions.as_written == "17.2 x 3.5 x 25.5 in"
    assert item.chassis.review_flags == ["This is the server's model, not the chassis's own."]


def test_an_item_without_a_chassis_is_allowed():
    assert QuoteItem.model_validate({"description": "4x Example 1.92TB SSD"}).chassis is None


def test_a_chassis_isnt_a_component():
    # It sits on the item: as a component made from the item's own line, the model began
    # a new item at the next priced row (2026-11-19).
    with pytest.raises(ValidationError):
        GenericComponent.model_validate({"component_type": "chassis", "raw_text": "Example 2U chassis"})
    choices = extraction_json_schema()["$defs"]["QuoteItem"]["properties"]["components"]["items"]["anyOf"]
    assert not [choice for choice in choices if "Chassis" in choice["$ref"]]


def test_a_chassis_refuses_the_drives_installed_as_a_property():
    # Installed parts belong to the System Library configuration (07-chassis.md section 6).
    with pytest.raises(ValidationError):
        _item_with_chassis({"drives_installed": {"value": 8, "basis": "stated"}})


def test_json_schema_puts_an_items_chassis_before_its_components():
    # The model writes in schema order, so it fills the chassis from the item's own line first.
    order = list(extraction_json_schema()["$defs"]["QuoteItem"]["properties"])
    assert order.index("chassis") < order.index("components")
