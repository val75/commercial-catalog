"""Fixes applied to the model's drafts in code, because instructions alone didn't hold.

- CPUs: the model may identify a CPU (manufacturer, family, model), but its
  specifications come only from the quote. The specs it supplied from its own
  knowledge were wrong on both model servers, so they're dropped (decided
  2026-11-13, 01-cpu.md rule 5).
- Quotes: the email-date flag is kept only on an email with a quote date, and
  the file-name flag only with a quote number.
- Quotes: a draft with nothing in it is dropped. The model once added an
  all-null quote after a spreadsheet's real one.
- Quotes: a revision the document doesn't contain is dropped, with a review
  flag. The model numbered quotes "1" in an email that gives no revision.
- Vendor product IDs: in a spreadsheet with a plain "Product ID" column and a
  named one ("ACME Product ID"), the named column is the vendor product ID
  (decision log D-001, D-005). The model kept taking the plain one, whatever
  the instructions said, so its value is swapped for the same row's named one.
- Vendor product IDs: in a PDF list "CODE(x4)MPN ...", CODE is the vendor's.
  When the model gave the MPN but no vendor product ID, CODE is taken.
- Network adapters: the crypto variant is kept only as written, never inferred
  (05-network-adapter.md rule 20).
- Network adapters: "IB/EN", "EN/IB" or VPI written on the adapter's own part
  means "Ethernet and InfiniBand". The model read "NDR400G IB/EN" as
  "InfiniBand NDR", taking the speed's name for the technology.
- Network adapters: a model that repeats the MPN is cleared. The model copied
  NVIDIA's SKU into both; the variant designation (the OPN) is left for the
  reviewer. Drives keep theirs: a drive's model and MPN are often one code.
- Power supplies: a model that repeats the MPN is cleared too, so the code is
  kept once (06-power-supply.md 3.4). An inferred AC input phase or input
  connector is dropped: those come only from the quote, and later from
  manufacturer documentation (sections 3.7 and 3.10, approved 2026-11-19).
- Chassis (on the quote item): the model often left it empty (2026-11-19), so
  what the item's own line states plainly is read in code when the model gave
  nothing: a rack height such as "2U" or "(1U)", and a code labelled
  "CHASSIS ..." as the model. Identity and the rest are left to the model and
  the reviewer (docs/review-fixes.md). A chassis with nothing in it is dropped.
- Chassis: a model that repeats the MPN is cleared, as for power supplies
  (07-chassis.md 3.4). Inferred dimensions, drive bays, expansion slots, power
  supply bays and cooling are dropped: section 5.1 has them filled from
  manufacturer documentation, and the model's memory isn't that.
- Drives: an MPN found only inside the vendor's code ("HDS-XYZ-<MPN>"), never on
  its own, is marked inferred and flagged as possibly shortened (03-storage.md
  decision). The model marked such MPNs as stated. A model equal to it goes too.
- Drives: a connector named as the form factor, such as U.2, moves to the
  connector, with a review flag, because the quote then doesn't state the form
  factor (03-storage.md keeps the two apart).
"""

from __future__ import annotations

import re

from extraction.schema import (
    Basis,
    ChassisProperties,
    ItemChassis,
    CpuComponent,
    CpuProperties,
    NicComponent,
    NicProperties,
    Property,
    PsuComponent,
    PsuProperties,
    QuoteDraft,
    StorageComponent,
)

CPU_IDENTITY = {"manufacturer", "product_family", "model"}
# Taken from the quote only; manufacturer documentation fills them later (06-power-supply.md 3.7, 3.10).
PSU_ONLY_AS_WRITTEN = ("ac_input_phase", "input_connector")
# Taken from the quote only; manufacturer documentation fills them later (07-chassis.md 5.1).
CHASSIS_ONLY_AS_WRITTEN = ("dimensions", "drive_bays", "expansion_slots", "psu_bays", "cooling")
# "2U DP RACK SERVER", "(1U)"; not inside a code such as SYS-2U-X400.
_RACK_HEIGHT = re.compile(r"(?<![A-Za-z0-9-])(\d{1,2}U)(?![A-Za-z0-9-])")
# "CHASSIS CX-210": a code with a digit after the label.
_CHASSIS_CODE = re.compile(r"\bCHASSIS[:\s]+([A-Za-z0-9][A-Za-z0-9-]*\d[A-Za-z0-9-]*)", re.IGNORECASE)

# Quote flags the instructions ask for in these exact words (a test checks).
EMAIL_DATE_FLAG = "The quote date is the email's sent date."
FILE_NAME_FLAG = "The quote number is from the file name."
MPN_IN_VENDOR_CODE_FLAG = "The MPN is taken from the vendor's code and may be shortened."

# What separates one code from the next in quote text and Markdown tables.
_TOKEN_SEPARATORS = re.compile(r"[\s|,;()]+")

# Lines at the start of a line, as an email client writes them: "From:" with "Sent:" or "Date:".
_EMAIL_FROM = re.compile(r"^\s*From:", re.MULTILINE)
_EMAIL_SENT = re.compile(r"^\s*(Sent|Date):", re.MULTILINE)

# A spreadsheet column such as "ACME Product ID": a name in front of "Product ID".
_NAMED_PRODUCT_ID = re.compile(r"^\S.*\sProduct ID$")
CONNECTORS = {"U.2", "U.3"}  # M.2 is left alone: it names a form factor too.

# A part in a PDF list: "NIC-CX7-1P-NDR(x4)900-..." starts with the vendor's code and the count.
_PART_START = re.compile(r"(?<![A-Za-z0-9-])([A-Za-z0-9][A-Za-z0-9-]*)\(x\s*\d+\)")
_PART_END = re.compile(r"\||\n\s*\n")  # the end of a table cell, or a blank line

BOTH_TECHNOLOGIES = "Ethernet and InfiniBand"
_BOTH_TECHNOLOGIES_WRITTEN = re.compile(r"(?<![A-Za-z0-9])(IB/EN|EN/IB|VPI)(?![A-Za-z0-9])", re.IGNORECASE)


def clean_drafts(drafts: list[QuoteDraft], document: str | None = None) -> list[QuoteDraft]:
    """Cleaned copies of the drafts. The originals are left unchanged.

    With the document's text, a revision it doesn't contain is dropped too.
    """
    cleaned = [draft.model_copy(deep=True) for draft in drafts if draft != QuoteDraft()]
    for draft in cleaned:
        if document is not None:
            _drop_revision_not_in(document, draft)
        _drop_flags_that_dont_fit(draft, document)
        vendor_ids = _vendor_ids_by_plain_product_id(document) if document is not None else {}
        for item in draft.items:
            _read_the_chassis_from_the_items_line(item)
            if item.chassis is not None:
                _use_the_vendor_named_product_id(item.chassis, vendor_ids)
                if document is not None:
                    _take_the_vendor_code_in_front_of_the_count(item.chassis, document)
                _clear_a_model_that_repeats_the_mpn(item.chassis)
                _drop_inferred(item.chassis, CHASSIS_ONLY_AS_WRITTEN)
            for component in item.components:
                properties = getattr(component, component.component_type, None)
                _use_the_vendor_named_product_id(properties, vendor_ids)
                if document is not None:
                    _take_the_vendor_code_in_front_of_the_count(properties, document)
                if isinstance(component, CpuComponent):
                    _drop_inferred_cpu_specs(component.cpu)
                elif isinstance(component, NicComponent):
                    if component.nic.crypto is not None and component.nic.crypto.basis == Basis.INFERRED:
                        component.nic.crypto = None
                    if document is not None:
                        _read_ib_en_as_both_technologies(component.nic, document)
                    _clear_a_model_that_repeats_the_mpn(component.nic)
                elif isinstance(component, PsuComponent):
                    _clear_a_model_that_repeats_the_mpn(component.psu)
                    _drop_inferred(component.psu, PSU_ONLY_AS_WRITTEN)
                elif isinstance(component, StorageComponent):
                    _move_connector_out_of_form_factor(component)
                    if document is not None:
                        _mark_mpn_from_vendor_code(component, document)
    return cleaned


def _drop_revision_not_in(document: str, draft: QuoteDraft) -> None:
    # Written on its own, not inside another word or number: "1" doesn't count as
    # written in "(1U)" or "12".
    revision = draft.revision
    if revision is None:
        return
    written_alone = rf"(?<![A-Za-z0-9]){re.escape(revision.strip())}(?![A-Za-z0-9])"
    if not re.search(written_alone, document, flags=re.IGNORECASE):
        draft.revision = None
        draft.review_flags.append(f'The revision "{revision}" isn\'t written in the document, so it was left out.')


def _vendor_ids_by_plain_product_id(document: str) -> dict[str, str]:
    """For each table with a plain "Product ID" column and a named one ("ACME Product
    ID"), each row's plain value mapped to its named value."""
    mapping: dict[str, str] = {}
    header: list[str] | None = None
    plain = named = None
    for line in document.splitlines():
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            header = None
            continue
        cells = [cell.strip() for cell in line[1:-1].split("|")]
        if all(set(cell) <= set("-: ") for cell in cells):
            continue  # the header's separator row
        if header is None:
            header = cells
            plain = header.index("Product ID") if "Product ID" in header else None
            named = next((i for i, cell in enumerate(header) if i != plain and _NAMED_PRODUCT_ID.match(cell)), None)
            continue
        if plain is not None and named is not None and len(cells) == len(header):
            if cells[plain] and cells[named] and cells[plain] != cells[named]:
                mapping[cells[plain]] = cells[named]
    return mapping


def _use_the_vendor_named_product_id(properties, vendor_ids: dict[str, str]) -> None:
    product_id = getattr(properties, "vendor_product_id", None)
    if product_id is not None and product_id.value in vendor_ids:
        properties.vendor_product_id = product_id.model_copy(update={"value": vendor_ids[product_id.value]})


def _take_the_vendor_code_in_front_of_the_count(properties, document: str) -> None:
    # "NIC-CX7-1P-NDR(x4)900-9X000-0000-ST0 ...": the vendor's code, the count, the MPN.
    fields = type(properties).model_fields if properties is not None else {}
    if "vendor_product_id" not in fields or "mpn" not in fields:
        return
    if properties.vendor_product_id is not None or properties.mpn is None:
        return
    pattern = rf"(?<![A-Za-z0-9-])([A-Za-z0-9][A-Za-z0-9-]*)\(x\s*\d+\)\s*{re.escape(properties.mpn.value.strip())}"
    found = re.search(pattern, document)
    if found:
        properties.vendor_product_id = properties.mpn.model_copy(
            update={"value": found.group(1), "basis": Basis.STATED, "reason": None}
        )


def _part_texts(document: str) -> list[str]:
    """The document's text cut into one piece per part, as far as it can be told.

    A part that starts "CODE(xN)" runs to the next such start, the end of its
    table cell or a blank line, across line breaks: PDF text wraps a part's
    description. Every line without such a start, such as a spreadsheet row,
    is a piece of its own.
    """
    pieces = []
    starts = [found.start(1) for found in _PART_START.finditer(document)]
    for start, stop in zip(starts, starts[1:] + [len(document)]):
        end = _PART_END.search(document, start, stop)
        pieces.append(document[start : end.start() if end else stop])
    pieces += [line for line in document.splitlines() if not _PART_START.search(line)]
    return pieces


def _read_ib_en_as_both_technologies(adapter: NicProperties, document: str) -> None:
    # "IB/EN" (or VPI) is an adapter that runs Ethernet and InfiniBand, but the model
    # read "NDR400G IB/EN" as "InfiniBand NDR" on both the PDF and the spreadsheet.
    if adapter.network_technology is not None and adapter.network_technology.value == BOTH_TECHNOLOGIES:
        return
    codes = [value.value for value in (adapter.vendor_product_id, adapter.mpn) if value is not None]
    wording = [adapter.port_speed_gbps.as_written] if adapter.port_speed_gbps and adapter.port_speed_gbps.as_written else []
    pieces = _part_texts(document)
    for anchors in (codes, wording):  # the port wording only when no code finds the part
        matched = [piece for piece in pieces if any(_contains_ignoring_spaces(piece, anchor) for anchor in anchors)]
        if matched:
            break
    for piece in matched:
        written = _BOTH_TECHNOLOGIES_WRITTEN.search(piece)
        if written:
            adapter.network_technology = Property[str](
                value=BOTH_TECHNOLOGIES, basis=Basis.STATED, reason=f"The document says {written.group(0)}."
            )
            return


def _read_the_chassis_from_the_items_line(item) -> None:
    chassis = item.chassis if item.chassis is not None else ItemChassis()
    heights = set(_RACK_HEIGHT.findall(item.description))
    if chassis.rack_height is None and len(heights) == 1:
        [height] = heights
        chassis.rack_height = Property[str](value=height, basis=Basis.STATED)
    codes = {code for code in _CHASSIS_CODE.findall(item.description) if not _RACK_HEIGHT.fullmatch(code)}
    if chassis.model is None and len(codes) == 1:
        [code] = codes
        chassis.model = Property[str](value=code, basis=Basis.STATED)
    item.chassis = None if chassis == ItemChassis() else chassis


def _drop_inferred(part, names: tuple[str, ...]) -> None:
    for name in names:
        value = getattr(part, name)
        if value is not None and value.basis == Basis.INFERRED:
            setattr(part, name, None)


def _clear_a_model_that_repeats_the_mpn(part: NicProperties | PsuProperties | ChassisProperties) -> None:
    # Adapters: NVIDIA cards carry a SKU (the 900-... code quotes write) and an order
    # number, the OPN (MCX...). The model put the SKU in both fields; the OPN is the
    # model, and the quote doesn't give it, so the reviewer fills it in.
    # Power supplies and chassis: one code in both fields is kept once, as the MPN
    # (06-power-supply.md 3.4, 07-chassis.md 3.4).
    if part.model is None or part.mpn is None:
        return
    if _without_spaces(part.model.value) == _without_spaces(part.mpn.value):
        part.model = None


def _without_spaces(text: str) -> str:
    return re.sub(r"\s+", "", text).upper()


def _contains_ignoring_spaces(text: str, anchor: str) -> bool:
    wanted = _without_spaces(anchor)
    return bool(wanted) and wanted in _without_spaces(text)


def _drop_flags_that_dont_fit(draft: QuoteDraft, document: str | None) -> None:
    # The model added these on documents they don't describe: the email-date flag
    # on a PDF and on a spreadsheet, the file-name flag with no quote number.
    is_email = document is None or bool(_EMAIL_FROM.search(document) and _EMAIL_SENT.search(document))
    wrong = set()
    if draft.quote_number is None:
        wrong.add(FILE_NAME_FLAG)
    if draft.quote_date is None or not is_email:
        wrong.add(EMAIL_DATE_FLAG)
    draft.review_flags = [flag for flag in draft.review_flags if flag not in wrong]


def _drop_inferred_cpu_specs(cpu: CpuProperties) -> None:
    for name in CpuProperties.model_fields.keys() - CPU_IDENTITY:
        value = getattr(cpu, name)
        if value is not None and value.basis == "inferred":
            setattr(cpu, name, None)


def _mark_mpn_from_vendor_code(drive: StorageComponent, document: str) -> None:
    mpn = drive.storage.mpn
    if mpn is None:
        return
    tokens = [token.strip(".:") for token in _TOKEN_SEPARATORS.split(document)]
    wanted = mpn.value.strip().upper()
    if any(token.upper() == wanted for token in tokens):
        return  # written on its own somewhere: the quote states it
    codes = [token for token in tokens if wanted in token.upper()]
    if not codes:
        return
    reason = f"Taken from inside the vendor's code {codes[0]}."
    for name in ("mpn", "model"):
        value = getattr(drive.storage, name)
        if value is not None and value.value.strip().upper() == wanted:
            setattr(drive.storage, name, value.model_copy(update={"basis": Basis.INFERRED, "reason": reason}))
    if not any("shortened" in flag for flag in drive.review_flags):
        drive.review_flags.append(MPN_IN_VENDOR_CODE_FLAG)


def _move_connector_out_of_form_factor(drive: StorageComponent) -> None:
    form_factor = drive.storage.form_factor
    if form_factor is None or form_factor.value.strip().upper() not in CONNECTORS:
        return
    if drive.storage.connector is None:
        drive.storage.connector = form_factor.model_copy(update={"value": form_factor.value.strip().upper()})
    drive.storage.form_factor = None
    drive.review_flags.append(
        f"{form_factor.value.strip().upper()} is a connector, not a form factor. The quote doesn't state the form factor."
    )
