"""The fixes applied to the model's output in code, whatever the model did."""

from __future__ import annotations

from extraction.cleanup import EMAIL_DATE_FLAG, FILE_NAME_FLAG, MPN_IN_VENDOR_CODE_FLAG, clean_drafts
from extraction.client import SYSTEM_PROMPT
from extraction.schema import QuoteDraft


def _stated(value):
    return {"value": value, "basis": "stated", "reason": None}


def _inferred(value):
    return {"value": value, "basis": "inferred", "reason": "the model's own knowledge"}


def _draft(*components) -> QuoteDraft:
    return QuoteDraft.model_validate(
        {"quote_number": "Q-1", "items": [{"description": "Example Server 1U", "components": list(components)}]}
    )


def _only_component(draft: QuoteDraft):
    [component] = draft.items[0].components
    return component


# --- CPUs: the model identifies them, but never supplies their specifications ---------------


def test_inferred_cpu_specifications_are_dropped():
    # On both model servers these were wrong: Turin for a Genoa part, 2.4 GHz for 3.25, 225 W for 280.
    draft = _draft(
        {
            "component_type": "cpu",
            "cpu": {
                "model": _stated("9354P"),
                "code_name": _inferred("Turin"),
                "threads": _inferred(64),
                "base_clock_ghz": _inferred(2.4),
                "cache_mb": _inferred(256),
                "tdp_w": _inferred(225),
            },
        }
    )
    cpu = _only_component(clean_drafts([draft])[0]).cpu
    assert (cpu.code_name, cpu.threads, cpu.base_clock_ghz, cpu.cache_mb, cpu.tdp_w) == (None, None, None, None, None)


def test_the_cpus_identity_may_still_be_inferred():
    draft = _draft(
        {
            "component_type": "cpu",
            "cpu": {
                "manufacturer": _inferred("AMD"),
                "product_family": _inferred("EPYC"),
                "model": _inferred("9354P"),
                "code_name": _stated("Genoa"),
            },
        }
    )
    cpu = _only_component(clean_drafts([draft])[0]).cpu
    assert (cpu.manufacturer.value, cpu.product_family.value, cpu.model.value) == ("AMD", "EPYC", "9354P")


def test_stated_cpu_specifications_are_kept():
    draft = _draft({"component_type": "cpu", "cpu": {"base_clock_ghz": _stated(2.0), "physical_cores": _stated(32)}})
    cpu = _only_component(clean_drafts([draft])[0]).cpu
    assert (cpu.base_clock_ghz.value, cpu.physical_cores.value) == (2.0, 32)


def test_other_parts_keep_their_inferred_values():
    draft = _draft({"component_type": "memory", "memory": {"voltage_v": _inferred(1.1)}})
    assert _only_component(clean_drafts([draft])[0]).memory.voltage_v.value == 1.1


# --- network adapters: the crypto variant only as written (05-network-adapter.md rule 20) -----


def test_an_inferred_crypto_variant_is_dropped():
    draft = _draft({"component_type": "nic", "nic": {"crypto": _inferred("Crypto Enabled"), "port_count": _inferred(2)}})
    adapter = _only_component(clean_drafts([draft])[0]).nic
    assert adapter.crypto is None
    assert adapter.port_count.value == 2  # other inferred values stay, marked inferred


def test_a_stated_crypto_variant_is_kept():
    draft = _draft({"component_type": "nic", "nic": {"crypto": _stated("NoCrypto")}})
    assert _only_component(clean_drafts([draft])[0]).nic.crypto.value == "NoCrypto"


def test_a_network_adapters_plain_product_id_is_swapped_too():
    sheet = (
        "| Product ID | ACME Product ID | ACME Mat Descr | Qty |\n| --- | --- | --- | --- |\n"
        "| NIC-25G-004 | NIC-25G-2P | 2x 25GbE SFP28 NIC | 2 |\n"
    )
    draft = _draft({"component_type": "nic", "nic": {"vendor_product_id": _stated("NIC-25G-004")}})
    assert _only_component(clean_drafts([draft], document=sheet)[0]).nic.vendor_product_id.value == "NIC-25G-2P"


BOM = (
    "2 XS-2200-BASE-A, 2U DP RACK SERVER 48,500.00 97,000.00\n"
    "NIC-CX7-1P-NDR(x4)900-9X000-0000-ST0\n1xNDR400G IB/EN OSFP Gen5x16 NoCrypto CX7\n"
)


def test_the_vendor_code_in_front_of_a_count_is_taken_for_its_mpn():
    # In "CODE(x4)MPN ...", CODE is the vendor's; the model recorded the MPN but not it.
    draft = _draft({"component_type": "nic", "nic": {"mpn": _stated("900-9X000-0000-ST0")}})
    adapter = _only_component(clean_drafts([draft], document=BOM)[0]).nic
    assert (adapter.vendor_product_id.value, adapter.vendor_product_id.basis) == ("NIC-CX7-1P-NDR", "stated")


def test_a_vendor_code_the_model_gave_is_kept():
    draft = _draft(
        {"component_type": "nic", "nic": {"mpn": _stated("900-9X000-0000-ST0"), "vendor_product_id": _stated("OTHER")}}
    )
    assert _only_component(clean_drafts([draft], document=BOM)[0]).nic.vendor_product_id.value == "OTHER"


def test_without_that_pattern_no_vendor_code_is_added():
    draft = _draft({"component_type": "nic", "nic": {"mpn": _stated("900-9X000-0000-ST0")}})
    assert _only_component(clean_drafts([draft], document="900-9X000-0000-ST0 1xNDR400G")[0]).nic.vendor_product_id is None


# --- network adapters: "IB/EN" or VPI on the adapter's part is Ethernet and InfiniBand -------


def _technology(document, **nic):
    nic.setdefault("network_technology", _stated("InfiniBand NDR"))
    draft = _draft({"component_type": "nic", "nic": nic})
    return _only_component(clean_drafts([draft], document=document)[0]).nic.network_technology


def test_ib_en_on_the_adapters_part_means_ethernet_and_infiniband():
    # The model read "NDR400G IB/EN" as "InfiniBand NDR" on both the PDF and the spreadsheet.
    technology = _technology(BOM, mpn=_stated("900-9X000-0000-ST0"))
    assert (technology.value, technology.basis, technology.reason) == (
        "Ethernet and InfiniBand",
        "stated",
        "The document says IB/EN.",
    )


def test_an_mpn_broken_across_lines_still_finds_the_part():
    # PDF text breaks the MPN with spaces and line ends: "900-9X000 -0000-\nST0".
    document = "NIC-CX7-1P-NDR(x4)900-9X000 -0000-\nST0 1xNDR400G IB/EN OSFP\nNoCrypto CX7\n"
    assert _technology(document, mpn=_stated("900-9X000-0000-ST0")).value == "Ethernet and InfiniBand"


def test_vpi_in_the_adapters_spreadsheet_row_counts_too():
    sheet = (
        "| ACME Product ID | ACME Mat Descr | Qty |\n| --- | --- | --- |\n"
        "| NIC-VPI-2P | ConnectX-7 VPI 2x200G QSFP112 | 2 |\n"
        "| NIC-25G-2P | 2x 25GbE SFP28 NIC | 2 |\n"
    )
    assert _technology(sheet, vendor_product_id=_stated("NIC-VPI-2P")).value == "Ethernet and InfiniBand"


def test_the_next_parts_ib_en_doesnt_count():
    # A PDF table row can hold several parts on one line.
    document = "| | NIC-25G-2P(x2)E810-XXVDA2 2x25GbE SFP28 NIC-CX7-1P-NDR(x4)900-9X000-0000-ST0 1xNDR400G IB/EN |"
    technology = _technology(document, mpn=_stated("E810-XXVDA2"), network_technology=_stated("Ethernet"))
    assert technology.value == "Ethernet"


def test_another_rows_ib_en_doesnt_count():
    sheet = "| NIC-25G-2P | 2x 25GbE SFP28 NIC | 2 |\n| NIC-VPI-2P | ConnectX-7 IB/EN 2x200G | 2 |\n"
    technology = _technology(sheet, vendor_product_id=_stated("NIC-25G-2P"), network_technology=_stated("Ethernet"))
    assert technology.value == "Ethernet"


def test_the_port_wording_finds_the_part_when_no_code_matches():
    port_speed = {"value": 400.0, "as_written": "1xNDR400G", "basis": "stated", "reason": None}
    assert _technology(BOM, port_speed_gbps=port_speed).value == "Ethernet and InfiniBand"


def test_without_ib_en_the_technology_is_left_alone():
    document = "NIC-IB-1P(x4)900-9X000-0000-ST0 1xNDR400G OSFP Gen5x16\n"
    assert _technology(document, mpn=_stated("900-9X000-0000-ST0")).value == "InfiniBand NDR"


def test_an_adapter_model_equal_to_its_mpn_is_cleared():
    # The model copied NVIDIA's SKU into both; the variant designation (the OPN) isn't in the quote.
    draft = _draft({"component_type": "nic", "nic": {"mpn": _stated("900-9X000-0000-ST0"), "model": _stated("900-9X000-0000-ST0")}})
    adapter = _only_component(clean_drafts([draft])[0]).nic
    assert (adapter.model, adapter.mpn.value) == (None, "900-9X000-0000-ST0")


def test_an_adapter_model_written_differently_from_its_mpn_is_still_the_same_code():
    draft = _draft({"component_type": "nic", "nic": {"mpn": _stated("900-9X000-0000-ST0"), "model": _stated("900-9x000-0000 -ST0")}})
    assert _only_component(clean_drafts([draft])[0]).nic.model is None


def test_a_different_adapter_model_is_kept():
    draft = _draft({"component_type": "nic", "nic": {"mpn": _stated("E810XXVDA2"), "model": _stated("E810-XXVDA2")}})
    assert _only_component(clean_drafts([draft])[0]).nic.model.value == "E810-XXVDA2"


def test_an_adapter_model_without_an_mpn_is_kept():
    draft = _draft({"component_type": "nic", "nic": {"model": _stated("E810-XXVDA2")}})
    assert _only_component(clean_drafts([draft])[0]).nic.model.value == "E810-XXVDA2"


def test_a_drive_model_equal_to_its_mpn_is_kept():
    # For drives the model and MPN are often the same code.
    draft = _draft({"component_type": "storage", "storage": {"mpn": _stated("XQ12T8ABCD7"), "model": _stated("XQ12T8ABCD7")}})
    assert _only_component(clean_drafts([draft])[0]).storage.model.value == "XQ12T8ABCD7"


def test_a_power_supply_model_equal_to_its_mpn_is_cleared():
    # 06-power-supply.md section 3.4: one code in both fields is kept once (approved 2026-11-19).
    draft = _draft({"component_type": "psu", "psu": {"mpn": _stated("PWS-1K28P-SQ"), "model": _stated("PWS-1K28P-SQ")}})
    psu = _only_component(clean_drafts([draft])[0]).psu
    assert (psu.model, psu.mpn.value) == (None, "PWS-1K28P-SQ")


def test_a_power_supplys_inferred_phase_and_connector_are_dropped():
    # Sections 3.7 and 3.10: these come from the quote or, later, from manufacturer documentation.
    draft = _draft(
        {
            "component_type": "psu",
            "psu": {
                "ac_input_phase": _inferred("Single-phase"),
                "input_connector": _inferred("IEC C14"),
                "power_supply_type": _inferred("AC"),
            },
        }
    )
    psu = _only_component(clean_drafts([draft])[0]).psu
    assert (psu.ac_input_phase, psu.input_connector) == (None, None)
    assert psu.power_supply_type.value == "AC"  # other inferred values stay, marked inferred


def test_a_power_supplys_stated_phase_and_connector_are_kept():
    draft = _draft({"component_type": "psu", "psu": {"ac_input_phase": _stated("3-phase"), "input_connector": _stated("IEC C20")}})
    psu = _only_component(clean_drafts([draft])[0]).psu
    assert (psu.ac_input_phase.value, psu.input_connector.value) == ("3-phase", "IEC C20")


def test_a_missing_technology_is_filled_from_ib_en():
    technology = _technology(BOM, mpn=_stated("900-9X000-0000-ST0"), network_technology=None)
    assert technology.value == "Ethernet and InfiniBand"


# --- drives: a connector named as the form factor ------------------------------------------


def _drive(**storage):
    return {"component_type": "storage", "storage": storage}


def test_a_connector_given_as_the_form_factor_moves_to_the_connector():
    drive = _only_component(clean_drafts([_draft(_drive(form_factor=_stated("U.2")))])[0])
    assert drive.storage.form_factor is None
    assert drive.storage.connector.value == "U.2"
    assert drive.review_flags == ["U.2 is a connector, not a form factor. The quote doesn't state the form factor."]


def test_a_connector_given_twice_is_kept_once():
    drive = _only_component(
        clean_drafts([_draft(_drive(form_factor=_stated("u.3"), connector=_stated("U.3")))])[0]
    )
    assert (drive.storage.form_factor, drive.storage.connector.value) == (None, "U.3")
    assert len(drive.review_flags) == 1


def test_a_different_connector_already_recorded_is_not_overwritten():
    drive = _only_component(
        clean_drafts([_draft(_drive(form_factor=_stated("U.2"), connector=_stated("U.3")))])[0]
    )
    assert (drive.storage.form_factor, drive.storage.connector.value) == (None, "U.3")
    assert "U.2" in drive.review_flags[0]


def test_real_form_factors_are_left_alone():
    # M.2 names a form factor as well as a connector.
    for form_factor in ("2.5-inch", "E1.S", "M.2"):
        drive = _only_component(clean_drafts([_draft(_drive(form_factor=_stated(form_factor)))])[0])
        assert drive.storage.form_factor.value == form_factor
        assert drive.review_flags == []


# --- a revision the document doesn't contain --------------------------------------------------


def _quote(revision):
    return QuoteDraft.model_validate({"quote_number": "Q-1", "revision": revision})


def test_a_revision_the_document_doesnt_contain_is_dropped_and_flagged():
    # The model numbered quotes "1" in an email that gives no revision.
    [draft] = clean_drafts([_quote("1")], document="OPTION A: Dell PowerEdge R660 (1U)\nQuote #: DF-Q-88214\nQty: 12")
    assert draft.revision is None
    assert draft.review_flags == ["The revision \"1\" isn't written in the document, so it was left out."]


def test_a_revision_written_in_the_document_is_kept():
    for written, revision in [("Quote Q-1 Rev 2", "2"), ("Revision: B", "b"), ("Q-1-v3", "v3")]:
        [draft] = clean_drafts([_quote(revision)], document=written)
        assert draft.revision == revision
        assert draft.review_flags == []


def test_no_revision_needs_no_check():
    [draft] = clean_drafts([_quote(None)], document="Quote Q-1")
    assert (draft.revision, draft.review_flags) == (None, [])


# --- quote flags that don't fit the draft -----------------------------------------------------------

EMAIL = "From: sales@example.com\nSent: Tuesday, July 29, 2026 4:12 PM\nTo: buyer@example.com\n\nQuote #: Q-1"


def _flagged(**fields):
    return QuoteDraft.model_validate({"review_flags": [EMAIL_DATE_FLAG, FILE_NAME_FLAG], **fields})


def test_the_instructions_ask_for_exactly_these_flags():
    assert EMAIL_DATE_FLAG in SYSTEM_PROMPT and FILE_NAME_FLAG in SYSTEM_PROMPT


def test_the_file_name_flag_needs_a_quote_number():
    # On a spreadsheet whose name has no number, the model flagged a number it didn't give.
    [draft] = clean_drafts([_flagged(quote_date="2026-07-29")], document=EMAIL)
    assert FILE_NAME_FLAG not in draft.review_flags
    [draft] = clean_drafts([_flagged(quote_number="Q-1", quote_date="2026-07-29")], document=EMAIL)
    assert FILE_NAME_FLAG in draft.review_flags


def test_the_email_date_flag_needs_a_date():
    [draft] = clean_drafts([_flagged(quote_number="Q-1")], document=EMAIL)
    assert EMAIL_DATE_FLAG not in draft.review_flags


def test_the_email_date_flag_needs_an_email():
    # It appeared on a PDF and on a spreadsheet export.
    pdf = "Quotation\nDate Page\n08/12/2026 1\nQuotation Number Q-1"
    [draft] = clean_drafts([_flagged(quote_number="Q-1", quote_date="2026-08-12")], document=pdf)
    assert EMAIL_DATE_FLAG not in draft.review_flags


def test_the_email_date_flag_stays_on_an_email_with_a_date():
    [draft] = clean_drafts([_flagged(quote_number="Q-1", quote_date="2026-07-29")], document=EMAIL)
    assert draft.review_flags == [EMAIL_DATE_FLAG, FILE_NAME_FLAG]


def test_without_the_document_the_flags_are_checked_against_the_draft_only():
    [draft] = clean_drafts([_flagged(quote_number="Q-1", quote_date="2026-07-29")])
    assert draft.review_flags == [EMAIL_DATE_FLAG, FILE_NAME_FLAG]


# --- the vendor product ID column in a spreadsheet ------------------------------------------------

SHEET = """\
## Sheet: export

| Item Number | Product ID | ACME Product ID | ACME Mat Descr | Qty |
| --- | --- | --- | --- | --- |
| 40 | MEM-D5-009 | MEM-D5-64G-R2 | 64GB DDR5-5600 2Rx4 ECC RDIMM | 32 |
| 60 | GPU-L40S-002 | GPU-L40S-48G-P | NVIDIA L40S 48GB GDDR6, PCIe 4 | 4 |
"""


def _vendor_ids(document, memory_id, gpu_id):
    draft = _draft(
        {"component_type": "memory", "memory": {"vendor_product_id": _stated(memory_id)}},
        {"component_type": "gpu", "gpu": {"vendor_product_id": _stated(gpu_id)}},
    )
    memory, gpu = clean_drafts([draft], document=document)[0].items[0].components
    return memory.memory.vendor_product_id.value, gpu.gpu.vendor_product_id.value


def test_a_plain_product_id_is_replaced_by_the_vendor_named_columns_value():
    # Three wordings of the instruction didn't stop the model taking the plain column.
    assert _vendor_ids(SHEET, "MEM-D5-009", "GPU-L40S-002") == ("MEM-D5-64G-R2", "GPU-L40S-48G-P")


def test_a_vendor_named_value_is_kept():
    assert _vendor_ids(SHEET, "MEM-D5-64G-R2", "GPU-L40S-48G-P") == ("MEM-D5-64G-R2", "GPU-L40S-48G-P")


def test_a_value_from_elsewhere_is_kept():
    assert _vendor_ids(SHEET, "MEM-OTHER", "GPU-OTHER") == ("MEM-OTHER", "GPU-OTHER")


def test_without_two_product_id_columns_nothing_is_swapped():
    one_column = "| Product ID | Description |\n| --- | --- |\n| MEM-D5-009 | 64GB DDR5 |\n"
    assert _vendor_ids(one_column, "MEM-D5-009", "GPU-L40S-002") == ("MEM-D5-009", "GPU-L40S-002")


# --- a drive MPN found only inside the vendor's code ------------------------------------------------

DRIVE_SHEET = """\
| Item Number | Product ID | ACME Product ID | ACME Mat Descr | Qty |
| --- | --- | --- | --- | --- |
| 50 | SSD-EX-012 | SSD-EXA-XQ12T8ABCD7 | Example X500 1.92TB NVMe PCIe4 U.2 1DWPD | 4 |
"""


def _drive_ids(document, mpn="XQ12T8ABCD7", model="XQ12T8ABCD7", flags=()):
    draft = _draft(
        {
            "component_type": "storage",
            "storage": {"model": _stated(model), "mpn": _stated(mpn)},
            "review_flags": list(flags),
        }
    )
    return _only_component(clean_drafts([draft], document=document)[0])


def test_an_mpn_found_only_inside_the_vendors_code_is_inferred_and_flagged():
    # 03-storage.md decision: offered as written, flagged as possibly shortened.
    drive = _drive_ids(DRIVE_SHEET)
    assert (drive.storage.mpn.value, drive.storage.mpn.basis) == ("XQ12T8ABCD7", "inferred")
    assert "SSD-EXA-XQ12T8ABCD7" in drive.storage.mpn.reason
    assert drive.review_flags == [MPN_IN_VENDOR_CODE_FLAG]


def test_a_model_equal_to_that_mpn_is_treated_the_same():
    drive = _drive_ids(DRIVE_SHEET)
    assert (drive.storage.model.value, drive.storage.model.basis) == ("XQ12T8ABCD7", "inferred")


def test_an_mpn_written_on_its_own_stays_stated():
    document = DRIVE_SHEET + "\nDrive: Example X500, MPN XQ12T8ABCD7\n"
    drive = _drive_ids(document)
    assert (drive.storage.mpn.basis, drive.review_flags) == ("stated", [])


def test_a_different_model_is_left_alone():
    drive = _drive_ids(DRIVE_SHEET, model="X500")
    assert drive.storage.model.basis == "stated"


def test_an_mpn_not_in_the_document_is_left_alone():
    drive = _drive_ids(DRIVE_SHEET, mpn="ZZ999", model="ZZ999")
    assert (drive.storage.mpn.basis, drive.review_flags) == ("stated", [])


def test_the_models_own_shortening_flag_isnt_repeated():
    drive = _drive_ids(DRIVE_SHEET, flags=["The MPN may be shortened."])
    assert drive.review_flags == ["The MPN may be shortened."]


# --- empty drafts ---------------------------------------------------------------------------------


def test_a_draft_with_nothing_in_it_is_dropped():
    # The model once added an all-null quote after a spreadsheet's real one.
    real = QuoteDraft.model_validate({"quote_number": "7700012345"})
    assert clean_drafts([real, QuoteDraft()]) == [real]


def test_a_draft_with_anything_in_it_is_kept():
    for fields in ({"total": 97000}, {"vendor_name": "Example"}, {"items": [{"description": "Example Server 1U"}]}):
        assert len(clean_drafts([QuoteDraft.model_validate(fields)])) == 1


def test_an_item_with_nothing_in_it_is_dropped():
    # After a server with a DPU, the model added an item "," with quantity 1 and no parts,
    # 3 runs of 3 (2026-11-23).
    server = {"description": "Example SR-610 1U server", "quantity": 2, "unit_price": 18900}
    draft = QuoteDraft.model_validate({"quote_number": "Q-1", "items": [server, {"description": ",", "quantity": 1}]})
    [cleaned] = clean_drafts([draft])
    assert [item.description for item in cleaned.items] == ["Example SR-610 1U server"]


def test_an_item_with_any_text_price_code_or_part_is_kept():
    for fields in (
        {"description": "Assembly fee"},
        {"description": ",", "unit_price": 120},
        {"description": ",", "part_number": "FEE-01"},
        {"description": "-", "components": [{"component_type": "cpu"}]},
    ):
        draft = QuoteDraft.model_validate({"quote_number": "Q-1", "items": [fields]})
        assert len(clean_drafts([draft])[0].items) == 1, fields


def test_cleaning_leaves_the_original_drafts_unchanged():
    draft = _draft(_drive(form_factor=_stated("U.2")))
    clean_drafts([draft])
    assert _only_component(draft).storage.form_factor.value == "U.2"


# --- chassis, on the quote item ---------------------------------------------------------------


def _chassis_after_cleanup(chassis: dict):
    draft = QuoteDraft.model_validate(
        {"quote_number": "Q-1", "items": [{"description": "Example Server 2U", "chassis": chassis}]}
    )
    return clean_drafts([draft])[0].items[0].chassis


def test_a_chassis_model_equal_to_its_mpn_is_cleared():
    # 07-chassis.md section 3.4, as for power supplies: one code in both fields is kept once.
    chassis = _chassis_after_cleanup({"mpn": _stated("CSE-X829"), "model": _stated("CSE-X829")})
    assert (chassis.model, chassis.mpn.value) == (None, "CSE-X829")


def test_a_chassiss_inferred_capacities_are_dropped():
    # Section 5.1: these come from the quote or, later, from manufacturer documentation, not the model's memory.
    chassis = _chassis_after_cleanup(
        {
            "dimensions": _inferred("437 x 89 x 647 mm"),
            "drive_bays": _inferred("12 x 3.5-inch front hot-swap"),
            "expansion_slots": _inferred("4 x PCIe 5.0 x16 FHFL"),
            "psu_bays": _inferred("2 x CRPS"),
            "cooling": _inferred("6 x 80 mm hot-swap fans"),
            "chassis_type": _inferred("Rackmount"),
        }
    )
    assert (chassis.dimensions, chassis.drive_bays, chassis.expansion_slots, chassis.psu_bays, chassis.cooling) == (
        None,
        None,
        None,
        None,
        None,
    )
    assert chassis.chassis_type.value == "Rackmount"  # identity and type may be inferred, marked inferred


def test_a_chassiss_stated_capacities_are_kept():
    chassis = _chassis_after_cleanup({"drive_bays": _stated("8 x 2.5-inch"), "psu_bays": _stated("2 x CRPS")})
    assert (chassis.drive_bays.value, chassis.psu_bays.value) == ("8 x 2.5-inch", "2 x CRPS")


def test_a_chassiss_vendor_code_is_taken_from_in_front_of_the_count():
    # The PDF rule for parts applies to the chassis too: "CODE(x4)MPN ..." puts the vendor's code first.
    document = "XS-2200-BASE(x2)CSE-X829 2U RACK SERVER"
    draft = QuoteDraft.model_validate(
        {"quote_number": "Q-1", "items": [{"description": "Example", "chassis": {"mpn": _stated("CSE-X829")}}]}
    )
    chassis = clean_drafts([draft], document)[0].items[0].chassis
    assert chassis.vendor_product_id.value == "XS-2200-BASE"


# --- chassis values read from the item's own line ------------------------------------------------
# The model often left the item's chassis empty (2026-11-19), so what the line states plainly is read in code.


def _item_after_cleanup(description: str, chassis: dict | None = None):
    item = {"description": description, "chassis": chassis}
    draft = QuoteDraft.model_validate({"quote_number": "Q-1", "items": [item]})
    return clean_drafts([draft])[0].items[0]


def test_the_rack_height_is_read_from_the_items_line():
    chassis = _item_after_cleanup("XS-2200-BASE-A, 2U DP RACK SERVER, BASEBOARD XB-22").chassis
    assert (chassis.rack_height.value, chassis.rack_height.basis.value) == ("2U", "stated")


def test_a_rack_height_in_brackets_is_read():
    assert _item_after_cleanup("OPTION A - Example R700 (1U)").chassis.rack_height.value == "1U"


def test_a_code_labelled_chassis_becomes_the_chassis_model():
    chassis = _item_after_cleanup("2U DP RACK SERVER, BASEBOARD XB-22, CHASSIS CX-210").chassis
    assert (chassis.model.value, chassis.model.basis.value) == ("CX-210", "stated")


def test_the_word_chassis_without_a_code_isnt_a_model():
    chassis = _item_after_cleanup("Example R700 1U server chassis").chassis
    assert chassis.model is None and chassis.rack_height.value == "1U"


def test_the_models_own_chassis_values_are_kept():
    chassis = _item_after_cleanup(
        "2U DP RACK SERVER, CHASSIS CX-210", {"model": _stated("CX-210-B"), "rack_height": _inferred("1U")}
    ).chassis
    assert (chassis.model.value, chassis.rack_height.value) == ("CX-210-B", "1U")


def test_two_different_rack_heights_are_left_to_the_reviewer():
    assert _item_after_cleanup("1U or 2U server, to be confirmed").chassis is None


def test_a_code_containing_a_height_isnt_read_as_one():
    assert _item_after_cleanup("SYS-2U-X400 Example server").chassis is None


def test_an_empty_chassis_is_dropped():
    # The model sometimes returned a chassis with every property null.
    assert _item_after_cleanup("4x Example 1.92TB SSD", {}).chassis is None


# --- RAID controllers (08-raid-controller.md) -----------------------------------------------


def _controller_after_cleanup(properties: dict, document: str | None = None):
    draft = _draft({"component_type": "raid_controller", "raid_controller": properties})
    return _only_component(clean_drafts([draft], document=document)[0]).raid_controller


def test_a_raid_controllers_inferred_capabilities_are_dropped():
    # Only identity, controller type and host interface may be inferred (decided 2026-11-23):
    # rules 6, 7 and 10 warn against guessing ports, drive interfaces and RAID levels.
    controller = _controller_after_cleanup(
        {
            "external_ports": _inferred("0"),
            "internal_ports": _inferred("2 x SFF-8654 x8"),
            "supported_drive_interfaces": _inferred("SAS, SATA, NVMe"),
            "max_drive_count": _inferred(240),
            "raid_levels": _inferred("RAID 0, 1, 5, 6, 10, 50, 60"),
            "cache_capacity_gb": {**_inferred(8), "as_written": None},
            "cache_protection": _inferred("CacheVault"),
            "boot_support": _inferred(True),
        }
    )
    assert controller == type(controller)()


def test_a_raid_controllers_inferred_identity_type_and_host_interface_stay():
    controller = _controller_after_cleanup(
        {
            "manufacturer": _inferred("Example"),
            "product_family": _inferred("ExampleRAID"),
            "controller_type": _inferred("Tri-Mode"),
            "host_interface": _inferred("PCIe 4.0 x8"),
        }
    )
    assert [p.value for p in (controller.manufacturer, controller.product_family, controller.controller_type, controller.host_interface)] == [
        "Example",
        "ExampleRAID",
        "Tri-Mode",
        "PCIe 4.0 x8",
    ]


def test_a_raid_controllers_stated_capabilities_are_kept():
    controller = _controller_after_cleanup(
        {"raid_levels": _stated("RAID 0, 1, 10"), "internal_ports": _stated("16 x SAS/SATA"), "boot_support": _stated(True)}
    )
    assert (controller.raid_levels.value, controller.internal_ports.value, controller.boot_support.value) == (
        "RAID 0, 1, 10",
        "16 x SAS/SATA",
        True,
    )


def test_a_raid_controller_model_equal_to_its_mpn_is_cleared():
    # Rule 2: the model, the family and the codes are kept apart.
    controller = _controller_after_cleanup({"mpn": _stated("05-10000-00"), "model": _stated("05-10000-00")})
    assert (controller.model, controller.mpn.value) == (None, "05-10000-00")


def test_a_raid_controllers_vendor_code_in_front_of_the_count_is_taken():
    document = "2 XS-2200-BASE-A, 2U DP RACK SERVER 48,500.00 97,000.00\nRC-16I-TM(x2)05-10000-00 Tri-Mode 16i\n"
    controller = _controller_after_cleanup({"mpn": _stated("05-10000-00")}, document=document)
    assert controller.vendor_product_id.value == "RC-16I-TM"


# --- DPUs (09-dpu.md) -------------------------------------------------------------------------


def _dpu_after_cleanup(properties: dict, document: str | None = None):
    draft = _draft({"component_type": "dpu", "dpu": properties})
    return _only_component(clean_drafts([draft], document=document)[0]).dpu


def test_a_dpus_inferred_compute_memory_and_offloads_are_dropped():
    # Identity and the network side may be inferred (decided 2026-11-23); rules 4, 9 and 11
    # keep the rest to the quote or documentation for the exact model. Crypto never, as for NICs.
    dpu = _dpu_after_cleanup(
        {
            "processor_architecture": _inferred("Arm Cortex-A78"),
            "cpu_cores": _inferred(16),
            "onboard_memory_gb": {**_inferred(32), "as_written": None},
            "hardware_acceleration": _inferred("Crypto, compression"),
            "storage_connectivity": _inferred("NVMe-oF"),
            "crypto": _inferred("Crypto Enable"),
        }
    )
    assert dpu == type(dpu)()


def test_a_dpus_inferred_identity_and_network_side_stay():
    dpu = _dpu_after_cleanup(
        {
            "manufacturer": _inferred("Example"),
            "network_technology": _inferred("Ethernet"),
            "port_connector": _inferred("QSFP112"),
            "host_interface": _inferred("PCIe 5.0 x16"),
            "form_factor": _inferred("PCIe full-height"),
        }
    )
    assert [p.value for p in (dpu.manufacturer, dpu.network_technology, dpu.port_connector, dpu.host_interface, dpu.form_factor)] == [
        "Example",
        "Ethernet",
        "QSFP112",
        "PCIe 5.0 x16",
        "PCIe full-height",
    ]


def test_a_dpus_stated_values_are_kept():
    dpu = _dpu_after_cleanup({"cpu_cores": _stated(16), "crypto": _stated("Crypto Enable")})
    assert (dpu.cpu_cores.value, dpu.crypto.value) == (16, "Crypto Enable")


def test_a_dpu_model_equal_to_its_mpn_is_cleared():
    dpu = _dpu_after_cleanup({"mpn": _stated("900-9D000-0000-AA0"), "model": _stated("900-9D000-0000-AA0")})
    assert (dpu.model, dpu.mpn.value) == (None, "900-9D000-0000-AA0")


def test_a_dpu_written_ib_en_is_both_technologies():
    document = "DPU-DX3-2P(x4)900-9D000-0000-AA0 DX-3 DPU 2x200G IB/EN QSFP112 Crypto Enable\n"
    dpu = _dpu_after_cleanup(
        {"mpn": _stated("900-9D000-0000-AA0"), "network_technology": _stated("InfiniBand")}, document=document
    )
    assert dpu.network_technology.value == "Ethernet and InfiniBand"
    assert dpu.vendor_product_id.value == "DPU-DX3-2P"


def test_a_shortened_crypto_variant_gets_its_written_wording_back():
    # The model gave "Disabled" for "Crypto Disabled" (2026-11-23); the variant is kept as written.
    document = "  - 1x Examplecorp DX-3 D3240 DPU, 2x 200GbE QSFP112, Crypto Disabled\n"
    assert _dpu_after_cleanup({"crypto": _stated("Disabled")}, document=document).crypto.value == "Crypto Disabled"


def test_crypto_wording_across_a_line_break_is_joined():
    document = "DPU-DX3-2P(x4)DX-3 D3220\nDPU 200GbE dual port Crypto\nEnable\n"
    assert _dpu_after_cleanup({"crypto": _stated("Enable")}, document=document).crypto.value == "Crypto Enable"


def test_a_crypto_variant_given_as_written_is_kept():
    document = "DX-3 D3220 Crypto Enable\nNIC 900-9X000 NoCrypto\n"
    assert _dpu_after_cleanup({"crypto": _stated("Crypto Enable")}, document=document).crypto.value == "Crypto Enable"
    draft = _draft({"component_type": "nic", "nic": {"crypto": _stated("NoCrypto")}})
    assert _only_component(clean_drafts([draft], document=document)[0]).nic.crypto.value == "NoCrypto"


def test_without_an_mpn_the_vendor_code_is_found_in_front_of_the_family_and_model():
    # "CODE(x4)<family> <model> ...": no MPN to anchor on, so the part's own designation is used.
    document = "DPU-DX3-2P(x4)DX-3 D3220\nDPU 200GbE dual port Crypto Enable\n"
    dpu = _dpu_after_cleanup({"product_family": _stated("DX-3"), "model": _stated("D3220")}, document=document)
    assert (dpu.vendor_product_id.value, dpu.vendor_product_id.basis) == ("DPU-DX3-2P", "stated")


def test_a_model_found_elsewhere_than_after_the_count_takes_no_code():
    document = "DPU-DX3-2P(x4)900-9D000-0000-AA0 DX-3 D3220 DPU\n"
    dpu = _dpu_after_cleanup({"product_family": _stated("DX-3"), "model": _stated("D3220")}, document=document)
    assert dpu.vendor_product_id is None
