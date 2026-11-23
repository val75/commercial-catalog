"""Runs against the real model server, so it only runs when asked:

    RUN_MODEL_TESTS=1 python -m pytest tests/test_extraction_model.py -q

The fixture is invented. These tests check what the quote states plainly; they
don't pin inferred values, which the model may or may not propose.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from extraction.client import extract_quotes
from extraction.schema import (
    Basis,
    CpuComponent,
    GpuComponent,
    MemoryComponent,
    NicComponent,
    PsuComponent,
    QuantityBasis,
    StorageComponent,
)
from ingestion.dispatch import ingest_text
from validation.quantity import (
    cpus_per_server,
    gpus_per_server,
    modules_per_server,
    nics_per_server,
    psus_per_server,
    storage_per_server,
)

pytestmark = pytest.mark.skipif(not os.environ.get("RUN_MODEL_TESTS"), reason="set RUN_MODEL_TESTS=1 to use the model")

FIXTURES = Path(__file__).parent.parent / "fixtures"


_RESULT: dict = {}


@pytest.fixture(scope="module")
def drafts():
    # One call for the whole module: the lab box takes minutes per extraction.
    # pytest re-runs a module fixture that raised, so a failure is kept too.
    if not _RESULT:
        try:
            doc = ingest_text((FIXTURES / "paste_two_quotes.txt").read_text(encoding="utf-8"))
            _RESULT["drafts"] = {draft.quote_number: draft for draft in extract_quotes(doc.markdown)}
        except Exception as error:
            _RESULT["error"] = error
    if "error" in _RESULT:
        raise _RESULT["error"]
    return _RESULT["drafts"]


# A bill of materials where the counts under the server line are for the whole
# order: the chassis, warranty and fee are (x2), the same as the 2 servers. The
# layout follows a real vendor PDF; the codes, prices and vendor are invented.
_BOM_LINES = """\
2 XS-2200-BASE-A, 2U DP RACK SERVER, BASEBOARD 48,500.00 97,000.00
XB-22, CHASSIS CX-210
XS-2200-BASE(x2)2U DP RACK SERVER,
BASEBOARD XB-22, CHASSIS CX-210
8471.49.9000 / 5A992Z1
WTY-3Y(x2)3 YRS PARTS AND LABOR,
NEXT BUSINESS DAY
CPU-INTL-6530-07(x4)Intel Xeon Gold 6530
32C/64T 2.1G 160MB 270W LGA4677
8542.31.0000 / 5A992C
MEM-D5-64G-R2(x32)64GB DDR5-5600
2Rx4 (16Gb) ECC RDIMM(CQ7700012345)
8473.30.1000 / EAR99
SSD-25N4-1T92-E1-NON-015(x 4)SSD
2.5" NVMe PCIe4 1.92TB 1DWPD TLC,
Non-SED, 15mm(CQ7700012345)
8523.51.1100 / 5A992C
GPU-L40S-48G-P(x4)NVIDIA L40S, 48GB
GDDR6, PCIe 4"""

# Page 2 carries on the same line after the repeated header, as in the real PDF,
# where the model once made the adapter its own item and lost page 1's last parts.
_BOM_PAGE_2_LINES = """\
NIC-CX7-1P-NDR(x4)900-9X000-0000-ST0
1xNDR400G IB/EN OSFP Gen5x16 NoCrypto CX7
8517.62.4300 / 5A992C
ASM-FEE(x2)ASSEMBLY FEE"""

_BOM_HEADER = """\
Quotation
Date Page
03/02/2026 {page}
Quotation Number
7700012345
Expiration Date Currency
04/01/2026 USD
Sold To: Ship To:
CUSTOMER_X CUSTOMER_X
100 EXAMPLE WAY, SPRINGFIELD 100 EXAMPLE WAY, SPRINGFIELD
Reference Customer No. Salesperson Incoterms Ship Via Terms
EX00012 PERSON_X Ex Works GROUND NET 30
Qty. Item Number Description Unit Price PC Extended Price
Ord."""

# The terms an invented vendor prints at the foot of every page.
_BOM_TERMS = (
    "This quotation is provided for reference only and is not an offer for sale. Prices, availability and "
    "lead times may change without notice due to supply, tariffs or other circumstances beyond the vendor's "
    "control. The vendor may revise, reject or cancel this quotation and any related purchase order. This "
    "quotation contains confidential information and must not be shared without the vendor's written consent."
)

ORDER_TOTAL_BOM = f"""\
### Page 1

{_BOM_HEADER.format(page=1)}
{_BOM_LINES}
Comments:
{_BOM_TERMS}
03/02/2026 09:15:00 PST

| Date 03/02/2026 | Page 1 |
| --- | --- |
| Quotation Number 7700012345 |  |
| Expiration Date 04/01/2026 | Currency USD |

| Qty. Ord. | Item Number | Description | Unit Price |  | PC | Extended Price |
| --- | --- | --- | --- | --- | --- | --- |
| {" ".join(_BOM_LINES.splitlines())} |  |  |  |  |  |  |
| Comments: |  |  |  |  |  |  |

### Page 2

{_BOM_HEADER.format(page=2)}
{_BOM_PAGE_2_LINES}
Comments:
Subtotal 97,000.00
Total order 97,000.00
{_BOM_TERMS}
03/02/2026 09:15:00 PST

| Date 03/02/2026 | Page 2 |
| --- | --- |
| Quotation Number 7700012345 |  |
| Expiration Date 04/01/2026 | Currency USD |

| Qty. Ord. | Item Number | Description | Unit Price |  | PC | Extended Price |
| --- | --- | --- | --- | --- | --- | --- |
|  |  | {" ".join(_BOM_PAGE_2_LINES.splitlines())} |  |  |  |  |
| Comments: |  |  |  | Subtotal Total order |  | 97,000.00 97,000.00 |
"""

_BOM_RESULT: dict = {}


@pytest.fixture(scope="module")
def bom_item():
    if not _BOM_RESULT:
        try:
            [draft] = extract_quotes(ORDER_TOTAL_BOM)
            [_BOM_RESULT["item"]] = draft.items
        except Exception as error:
            _BOM_RESULT["error"] = error
    if "error" in _BOM_RESULT:
        raise _BOM_RESULT["error"]
    return _BOM_RESULT["item"]


def test_counts_under_a_line_that_match_its_server_count_are_order_totals(bom_item):
    assert bom_item.quantity == 2
    assert {component.quantity_basis for component in bom_item.components} == {QuantityBasis.ORDER_TOTAL}


def test_order_totals_become_counts_per_server(bom_item):
    assert cpus_per_server(bom_item).per_server == 2
    assert modules_per_server(bom_item).per_server == 16
    assert gpus_per_server(bom_item).per_server == 2
    assert [check.per_server for check in storage_per_server(bom_item)] == [2]
    assert nics_per_server(bom_item).per_server == 2


def test_no_power_supply_is_added_for_a_server_that_comes_with_them(bom_item):
    # The base system includes its power supplies, but the quote doesn't list them as parts.
    assert not [component for component in bom_item.components if isinstance(component, PsuComponent)]


def test_the_base_system_is_the_servers_chassis(bom_item):
    assert _stated(bom_item.chassis.rack_height) == "2U"
    assert "CX-210" in bom_item.chassis.model.value  # the line names the chassis: "CHASSIS CX-210"


def test_the_drives_installed_arent_taken_for_drive_bays(bom_item):
    assert (bom_item.chassis.drive_bays, bom_item.chassis.psu_bays) == (None, None)


def test_a_network_adapters_ports_and_crypto_variant_are_read(bom_item):
    adapter = _only_in(bom_item, NicComponent).nic
    assert (_stated(adapter.port_count), _stated(adapter.port_speed_gbps)) == (1, 400)
    assert _stated(adapter.port_connector) == "OSFP"
    assert _stated(adapter.crypto) == "NoCrypto"
    assert "PCIe 5" in adapter.host_interface.value
    assert adapter.mpn.value == "900-9X000-0000-ST0"
    assert adapter.vendor_product_id.value == "NIC-CX7-1P-NDR"


def test_an_ib_en_adapter_runs_ethernet_and_infiniband(bom_item):
    assert _stated(_only_in(bom_item, NicComponent).nic.network_technology) == "Ethernet and InfiniBand"


# A spreadsheet export of the same kind of quote: one flat row per line, no
# quote number, date or header, and no prices on the part rows. The columns
# follow a real export; the vendor, codes and values are invented.
FLAT_SPREADSHEET = """\
## Sheet: export - 2026-03-02T101500.000

| Item Number | Product ID | ACME Product ID | ACME Mat Descr | Planned EOL Date | Qty | Misc Amt | Item Category | Req. Delivery Date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | XS -2200-001 | XS -2200-BASE | 2U DP RACK SERVER, BASEBOARD XB-22, 8-GPU, CHASSIS CX-210 |  | 2 | 0 | Quotation Item | 03/30/2026 |
| 20 | WTY3Y | WTY3Y | 3 YRS PARTS AND LABOR, NEXT BUSINESS DAY |  | 2 | 0 | Quote Svc Itm Free | 03/30/2026 |
| 30 | CPU-INTL-001 | CPU-INTL-6530-07 | Xeon Gold 6530 32C/64T 2.1G 160MB 270W LGA4677 |  | 4 | 0 | Quotation Item | 03/30/2026 |
| 40 | MEM-D5-009 | MEM-D5-64G-R2 | 64GB DDR5-5600 2Rx4 (16Gb) ECC RDIMM |  | 32 | 0 | Quotation Item | 03/30/2026 |
| 50 | SSD-EX-012 | SSD-EX-1T92-E1 | Example X500 1.92TB NVMe PCIe4 U.2 1DWPD |  | 4 | 0 | Quotation Item | 03/30/2026 |
| 60 | GPU-L40S-002 | GPU-L40S-48G-P | NVIDIA L40S 48GB GDDR6, PCIe 4 |  | 4 | 0 | Quotation Item | 03/30/2026 |
| 70 | NIC-25G-004 | NIC-25G-2P | 2x 25GbE SFP28 NIC |  | 2 | 0 | Quotation Item | 03/30/2026 |
| 80 | ASMFEE | ASMFEE | ASSEMBLY FEE |  | 2 | 0 | Quote Svc Itm Free | 03/30/2026 |
|  |  |  |  |  |  | 97000 |  |  |
"""

SHEET_FILE_NAME = "Quote 7700012345 export.xlsx"  # an invented name; real ones hold the quote number too

_SHEET_RESULT: dict = {}


@pytest.fixture(scope="module")
def sheet_drafts():
    if not _SHEET_RESULT:
        try:
            _SHEET_RESULT["drafts"] = extract_quotes(FLAT_SPREADSHEET, source_name=SHEET_FILE_NAME)
        except Exception as error:
            _SHEET_RESULT["error"] = error
    if "error" in _SHEET_RESULT:
        raise _SHEET_RESULT["error"]
    return _SHEET_RESULT["drafts"]


def test_a_spreadsheet_without_a_quote_header_is_still_a_quote(sheet_drafts):
    assert len(sheet_drafts) == 1


def test_the_vendor_product_id_comes_from_the_vendor_named_column(sheet_drafts):
    # "ACME Product ID", not the plain "Product ID" (decision log D-001, D-005).
    [item] = sheet_drafts[0].items
    memory = _only_in(item, MemoryComponent).memory
    gpu = _only_in(item, GpuComponent).gpu
    assert (memory.vendor_product_id.value, gpu.vendor_product_id.value) == ("MEM-D5-64G-R2", "GPU-L40S-48G-P")
    assert _only_in(item, NicComponent).nic.vendor_product_id.value == "NIC-25G-2P"


def _only_in(item, kind):
    [line] = [component for component in item.components if isinstance(component, kind)]
    return line


def test_the_quote_number_comes_from_the_file_name_when_the_sheet_has_none(sheet_drafts):
    assert sheet_drafts[0].quote_number == "7700012345"
    assert any("file name" in flag for flag in sheet_drafts[0].review_flags)


def test_a_flat_spreadsheets_part_rows_belong_to_its_server_row(sheet_drafts):
    [item] = sheet_drafts[0].items
    assert item.quantity == 2
    kinds = sorted(component.component_type for component in item.components)
    assert kinds == ["cpu", "gpu", "memory", "nic", "storage"]
    assert _stated(item.chassis.rack_height) == "2U"
    assert nics_per_server(item).per_server == 1
    assert cpus_per_server(item).per_server == 2
    assert modules_per_server(item).per_server == 16
    assert gpus_per_server(item).per_server == 2


def _only(draft, kind):
    lines = [component for item in draft.items for component in item.components if isinstance(component, kind)]
    assert len(lines) == 1, f"expected one {kind.__name__}, got {len(lines)}"
    return lines[0]


def _stated(prop):
    assert prop is not None
    assert prop.basis is Basis.STATED
    return prop.value


def test_paste_with_two_quotes_produces_two_drafts(drafts):
    assert set(drafts) == {"DF-Q-88214", "DF-Q-88215"}


def test_intel_cpu_follows_the_naming_rule(drafts):
    line = _only(drafts["DF-Q-88214"], CpuComponent)
    assert (_stated(line.cpu.manufacturer), line.cpu.product_family.value, line.cpu.model.value) == (
        "Intel",
        "Xeon",
        "Gold 6438N",
    )
    assert (_stated(line.cpu.physical_cores), _stated(line.cpu.base_clock_ghz)) == (32, 2.0)
    assert (line.quantity, line.quantity_basis) == (2, QuantityBasis.PER_UNIT)


def test_amd_cpu_is_identified(drafts):
    line = _only(drafts["DF-Q-88215"], CpuComponent)
    assert (line.cpu.manufacturer.value, line.cpu.product_family.value, line.cpu.model.value) == ("AMD", "EPYC", "9354P")
    assert _stated(line.cpu.physical_cores) == 32
    assert line.quantity == 1


@pytest.mark.parametrize("quote, modules", [("DF-Q-88214", 16), ("DF-Q-88215", 12)])
def test_memory_is_recorded_per_module_not_as_the_total(drafts, quote, modules):
    line = _only(drafts[quote], MemoryComponent)
    assert (_stated(line.memory.capacity_gb), _stated(line.memory.memory_type)) == (32, "DDR5")
    assert line.quantity == modules


def test_nothing_is_filled_in_as_unknown(drafts):
    # Before "value" could be null, the model wrote "Unknown" or 0 in its place.
    written = json.dumps([draft.model_dump(mode="json") for draft in drafts.values()])
    assert '"Unknown"' not in written


def test_no_specs_are_guessed_for_a_module_the_quote_doesnt_name(drafts):
    memory = _only(drafts["DF-Q-88214"], MemoryComponent).memory
    assert memory.manufacturer is None and memory.mpn is None
    assert (memory.rank, memory.dram_density_gb, memory.operating_frequency_mhz) == (None, None, None)


def test_only_parts_with_a_spec_file_are_extracted(drafts):
    for draft in drafts.values():
        for item in draft.items:
            for component in item.components:
                assert isinstance(
                    component, (CpuComponent, MemoryComponent, StorageComponent, NicComponent, PsuComponent)
                ), component


@pytest.mark.parametrize("quote, height", [("DF-Q-88214", "1U"), ("DF-Q-88215", "1U")])
def test_a_server_quoted_as_one_model_gets_its_chassis_from_the_line(drafts, quote, height):
    # "Dell PowerEdge R660 (1U)": no separate chassis part, so the chassis comes from the item's line.
    # The flag that its model is the server's (07-chassis.md 3.3) is left to the reviewer: the model
    # added it on one quote and not the other (docs/review-fixes.md).
    [item] = drafts[quote].items
    assert _stated(item.chassis.rack_height) == height


def test_a_power_supply_is_recorded_per_server(drafts):
    psu = _only(drafts["DF-Q-88214"], PsuComponent)
    assert _stated(psu.psu.rated_output_w) == 1100  # one power supply's rating, not 2 x 1100
    assert _stated(psu.psu.efficiency_certification) == "Titanium"  # as written, no "80 PLUS" added
    assert (psu.quantity, psu.quantity_basis) == (2, QuantityBasis.PER_UNIT)


def test_redundancy_goes_in_the_power_supplys_note(drafts):
    # Redundancy belongs to the System Library configuration, which doesn't exist yet (approved 2026-11-19).
    psu = _only(drafts["DF-Q-88215"], PsuComponent)
    assert _stated(psu.psu.rated_output_w) == 860
    assert "redundant" in (psu.note or "").lower()


def test_no_power_supply_specs_are_guessed_from_the_server(drafts):
    # The quote names no power supply model, so nothing identifies it precisely.
    psu = _only(drafts["DF-Q-88214"], PsuComponent).psu
    assert (psu.manufacturer, psu.mpn, psu.ac_input_phase, psu.input_connector) == (None, None, None, None)


def test_a_network_card_is_recorded_with_its_ports(drafts):
    adapter = _only(drafts["DF-Q-88214"], NicComponent)
    assert _stated(adapter.nic.manufacturer) == "Broadcom"
    assert (_stated(adapter.nic.port_count), _stated(adapter.nic.port_speed_gbps)) == (2, 25)
    assert (adapter.quantity, adapter.quantity_basis) == (1, QuantityBasis.PER_UNIT)


def test_network_ports_built_into_the_motherboard_are_left_out(drafts):
    # "Dual 10GbE onboard" belongs to the server's system configuration (05-network-adapter.md rule 22).
    assert not [c for item in drafts["DF-Q-88215"].items for c in item.components if isinstance(c, NicComponent)]


def _storage_lines(draft):
    return [component for item in draft.items for component in item.components if isinstance(component, StorageComponent)]


def test_context_without_a_property_is_kept_as_a_note(drafts):
    [boot] = [line for line in _storage_lines(drafts["DF-Q-88214"]) if line.storage.capacity.value == 480]
    assert "BOSS" in (boot.note or "")


def test_no_revision_is_made_up(drafts):
    # The email gives none. The model once numbered both quotes "1".
    assert [draft.revision for draft in drafts.values()] == [None, None]
    assert not [flag for draft in drafts.values() for flag in draft.review_flags if "revision" in flag]


def test_a_date_taken_from_the_email_header_is_flagged(drafts):
    for draft in drafts.values():
        assert draft.quote_date.isoformat() == "2026-07-29"
        assert any("sent" in flag for flag in draft.review_flags), draft.quote_number


def test_each_storage_group_is_its_own_line(drafts):
    lines = [
        component
        for item in drafts["DF-Q-88214"].items
        for component in item.components
        if isinstance(component, StorageComponent)
    ]
    groups = {(line.storage.capacity.value, line.storage.capacity.unit, line.quantity) for line in lines}
    assert groups == {(480, "GB", 2), (3.84, "TB", 6)}


# A spreadsheet where every count covers the whole order, with a power supply
# line of its own. Invented, in the shape of a server maker's BOM export.
PSU_SHEET = """\
## Sheet: Quote

| Example Servers  —  Quote Q-55120  (valid 30 days) |  |  |  |  |
| --- | --- | --- | --- | --- |
| Line | SKU | Description | Qty | Unit Price (USD) |
| 1 | 210-XXAA | Example R700 1U server chassis | 8 | 4200 |
| 2 | 338-XXBB | Intel Xeon Gold 6438N 32C 2.0GHz | 16 | 1650 |
| 3 | 370-XXCC | 32GB DDR5-4800 RDIMM | 128 | 190 |
| 4 | 450-XXDD | 1100W Titanium hot-plug PSU | 16 | 260 |
"""

_PSU_SHEET_RESULT: dict = {}


@pytest.fixture(scope="module")
def psu_sheet():
    if not _PSU_SHEET_RESULT:
        try:
            [_PSU_SHEET_RESULT["draft"]] = extract_quotes(PSU_SHEET)
        except Exception as error:
            _PSU_SHEET_RESULT["error"] = error
    if "error" in _PSU_SHEET_RESULT:
        raise _PSU_SHEET_RESULT["error"]
    return _PSU_SHEET_RESULT["draft"]


def test_a_priced_chassis_row_is_the_server_and_its_chassis(psu_sheet):
    # Every row has a price. With the chassis as a component made from row 1, the model
    # began a new quote at each later row (2026-11-19).
    [item] = psu_sheet.items
    assert item.quantity == 8
    assert sorted(component.component_type for component in item.components) == ["cpu", "memory", "psu"]
    assert _stated(item.chassis.rack_height) == "1U"


def test_a_whole_order_count_of_power_supplies_becomes_two_per_server(psu_sheet):
    [item] = [item for item in psu_sheet.items if any(isinstance(c, PsuComponent) for c in item.components)]
    assert psus_per_server(item).per_server == 2


def test_a_power_supplys_rating_and_hot_plug_are_read(psu_sheet):
    psu = _only(psu_sheet, PsuComponent)
    assert psu.psu.mpn is None  # the SKU is the vendor's code, not the manufacturer's
    assert _stated(psu.psu.hot_swap) is True
    assert (_stated(psu.psu.rated_output_w), _stated(psu.psu.efficiency_certification)) == (1100, "Titanium")


def test_a_spreadsheets_sku_column_is_the_vendor_product_id(psu_sheet):
    # Failed until the chassis moved onto the item (2026-11-22); then passed 5 runs in a row.
    # See docs/review-fixes.md, 'Vendor codes in a SKU or Part Number column'.
    assert _stated(_only(psu_sheet, PsuComponent).psu.vendor_product_id) == "450-XXDD"
    assert _stated(_only(psu_sheet, MemoryComponent).memory.vendor_product_id) == "370-XXCC"
