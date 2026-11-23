"""Sends a normalized document to the model and returns validated quote drafts.

The model runs behind an OpenAI-compatible endpoint (llama.cpp), and its address
comes from config, never from code. Output is constrained to the draft schema.

Quotes can be confidential, and error messages end up in terminals and logs, so
errors here describe what went wrong without repeating any quote content.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from extraction.cleanup import clean_drafts
from extraction.schema import ExtractionResult, QuoteDraft, drop_empty_properties, extraction_json_schema

BASE_URL_SETTING = "MODEL_BASE_URL"
API_KEY_SETTING = "MODEL_API_KEY"
MODEL_NAME_SETTING = "MODEL_NAME"
DEFAULT_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_TIMEOUT_SECONDS = 600.0

SYSTEM_PROMPT = """\
You extract vendor hardware quotes from a document into JSON.

Write compact JSON on a single line, with no indentation, line breaks or spaces between tokens.

- A document can hold several quotes. Output one entry in "quotes" for each, and an empty list if there are none.
- A table of hardware lines with quantities, such as a spreadsheet export, is a quote even when it has no quote number, date, vendor or header. Output it, with null for what it doesn't state.
- In a flat table where a server or chassis line is followed by part lines, such as CPUs, memory, drives and GPUs, the part lines are that server's components, even though each has its own row and no price.
- Only record what the document states. Use null for anything it doesn't state, and never calculate a value. Infer only where the rules below allow it.
- Copy "raw_text" and "description" exactly as the vendor wrote them.
- The document may start with its file name, which often contains the quote number. If the document itself doesn't state a quote number, take it from the file name and add the quote "review_flags" entry "The quote number is from the file name."
- Set "revision" only when the document gives the quote a revision or version, such as "Rev 2", and use null otherwise. Never number a quote yourself.
- Give dates as YYYY-MM-DD. If a date is ambiguous, use null.
- If the only date is when an email was sent, use it as "quote_date" and add the quote "review_flags" entry "The quote date is the email's sent date."
- One priced line is one item. The parts and services listed under it are its components.
- A line's parts can continue on the next page, after the page header and column headings repeat. They still belong to the same item: a part line with no price of its own, such as "CODE(x16)...", is never an item.
- Subtotal, discount, tax and total lines aren't items: they go in the quote's "subtotal", "discount", "tax" and "total".
- If the same content appears more than once, such as a page repeated as a table, record it only once.
- Set "quantity_basis" to "per_unit" when a component's quantity is for one server, "order_total" when it covers the whole order, and "unknown" when the document doesn't make that clear.
- To tell them apart, compare the counts under a line with the line's own quantity. If something every server has exactly once, such as the chassis or base system, a warranty or an assembly fee, has the same count as the line (a line of 4 servers with a chassis "(x4)"), the counts under that line cover the whole order: use "order_total" for all of them. "2x CPU" under a line of 8 servers is "per_unit".
- Record only CPU, memory, GPU, storage, network adapter ("nic") and power supply ("psu") components. Leave out everything else, such as DPUs, network ports built into the motherboard, cables, warranties, support, licenses and fees.
- Infer a part's properties only from that part's own manufacturer, model or part number, never from the server or chassis it's installed in.
- Every property must be answered: give its value, or null if it's unknown. Don't leave a component's properties empty when the document states them.
- A "review_flags" entry is one short sentence for the person reviewing the quote, such as "Several modules match this description." Never think aloud in it; put values in their properties instead.
- A part's "note" holds context the document gives about that part which none of its properties holds, as written, such as "BOSS boot". Leave it null otherwise. Never put specifications or the whole line in it.
- For a CPU, fill only the properties in "cpu". Give each one as {"value", "basis"}: "stated" when the document says it, or "inferred" with a short "reason". Only the manufacturer, product family and model may be inferred, from the rest of the line: the code name Turin means the manufacturer is AMD. Take every other CPU property from the document, or give null. Never supply cores, threads, clock, cache, TDP or code name from your own knowledge.
- Use GHz for the base clock, MB of total L3 cache for the cache, W for the TDP, and whole numbers for cores and threads.
- Prefer the manufacturer's exact model designation, such as 9654, over the vendor's own codes and shorthand.
- A tier word belongs to the model, not the family: "Intel Xeon Gold 6438N" is product family "Xeon" and model "Gold 6438N".
- Add a "review_flags" entry when more than one CPU model could match, or when the document contradicts itself, and don't pick a value in that case.
- For memory, fill only the properties in "memory", in the same {"value", "basis"} form as for a CPU. Infer only from the manufacturer, model or MPN, or from a standard every module of that type follows, such as 1.1 V for DDR5, and give the "reason".
- "mpn" and "model" are the memory manufacturer's codes, never the vendor's. "vendor_product_id" is the vendor's own code for the line. A spreadsheet's "Product ID" column may hold a manufacturer's code: check it, and use it as the MPN or model only if it is one.
- "capacity_gb" is one module's capacity. If the document gives only the total memory and not the number of modules, leave "capacity_gb" null and add a review flag.
- The data rate is in MT/s: "DDR5-6400" is 6400. Decode speed-class names too: "PC5-51200R" is DDR5, 6400 MT/s (51200 / 8) and RDIMM ("R" is registered), and "PC4-25600" is DDR4 at 3200 MT/s. These count as stated.
- Fill "operating_frequency_mhz" only when the document gives a clock frequency separate from the data rate. Never work it out from the data rate. A figure in MHz that matches the speed grade, such as "DDR4 3200MHz", is the data rate mislabeled: record it as the data rate.
- "2Rx4" is rank 2 and DRAM organization x4. "(24Gb)" is a DRAM chip density of 24.
- Give "module_height" exactly as written, such as "LP", and put its meaning, such as "Low Profile", in "meaning" if you know it.
- Add a "review_flags" entry when more than one module could match, or when the document contradicts itself.
- For a GPU, fill only the properties in "gpu", in the same {"value", "basis"} form as for a CPU. When the manufacturer and model identify the GPU precisely, infer the missing specifications from your own knowledge, such as architecture, chip, core counts, interface, cooling and power, and give the "reason".
- "manufacturer" is the GPU chip's maker, such as NVIDIA. "board_manufacturer" is the card's maker when it's named, such as an OEM for an OEM-branded card. "mpn" is the card maker's own part number, never the vendor's code, which goes in "vendor_product_id".
- Keep "model" as quoted, such as "H100 SXM 80GB". "memory_capacity_gb" is the memory of one GPU, not of all of them.
- Use GB, GB/s, bits, MHz and W. When you convert a number from another unit, such as "1.6 TB/s" to 1600 GB/s, put the quote's wording in "as_written". Don't mix decimal and binary units.
- Give "processing_cores" with the manufacturer's own term in "terminology", such as "CUDA cores" or "Stream processors".
- For "power_w", say in "kind" whether it's the maximum board power, a configured power limit or typical power, and leave "kind" null if the document doesn't make it clear.
- "interface" is text, such as "PCIe 5.0 x16" or "SXM5". If you complete it from your own knowledge, such as adding x16 to a stated "PCIe 5", mark it "inferred" and say in the "reason" which part the document states.
- Fill the NVLink properties only when the document states them, or the exact model establishes them reliably.
- Add a "review_flags" entry when more than one GPU could match, when a value depends on a card variant or power configuration the model name doesn't settle, or when the document contradicts itself.
- A DPU, such as BlueField, isn't a GPU or a network adapter, even if the vendor's code starts with "GPU": leave it out.
- For a drive, fill only the properties in "storage", in the same {"value", "basis"} form as for a CPU. When the manufacturer and model identify the drive precisely, infer the missing specifications from your own knowledge and give the "reason", except flash technology, which you record only if the document or the manufacturer states it.
- Each storage line is its own group of identical drives. Never combine lines.
- "mpn" and "model" are the drive manufacturer's codes, never the vendor's. If a vendor's code contains one, such as a manufacturer's part number after the vendor's prefix, give it exactly as written, mark it "inferred", and add a review flag that it may be shortened.
- Keep form factor (such as 2.5-inch or E1.S), connector (such as U.2 or U.3) and interface (such as NVMe PCIe 4.0 x4) apart. A 2.5-inch drive can be NVMe, SAS or SATA.
- "capacity" is one drive's capacity, with the unit as written: GB or TB. Don't convert between them.
- Give "endurance" in the manufacturer's own metric, such as 1 DWPD or 7000 TBW, and never convert DWPD to TBW or back.
- "power_w" is one figure. Say in "kind" whether it's maximum, typical or average, and leave "kind" null if the document doesn't say.
- "encryption" is the drive's own hardware encryption as written, such as "SED", "TCG Opal 2.0" or "Non-SED". Leave it null when the encryption comes from the host or software.
- Add a "review_flags" entry when more than one drive could match, when a value depends on the variant, or when the document contradicts itself.
- For a network adapter, fill only the properties in "nic", in the same {"value", "basis"} form as for a CPU. When the manufacturer and model identify the adapter precisely, infer the missing specifications from your own knowledge and give the "reason". Never infer "crypto": record it only as written, such as "NoCrypto".
- "mpn" and "model" are the adapter manufacturer's codes, never the vendor's, which goes in "vendor_product_id". "product_family" is the line, such as ConnectX-7; "model" is the specific variant within it, such as E810-XXVDA2.
- "adapter_type" is the category: NIC, SmartNIC, HCA or CNA. "network_technology" is the standard, such as Ethernet or InfiniBand NDR; "IB/EN" or VPI means "Ethernet and InfiniBand".
- "port_count" is the physical ports and "port_speed_gbps" the maximum speed of one port, in Gb/s, never the total: "2x25GbE" is 2 ports at 25, "1xNDR400G" is 1 port at 400. For several speeds, such as "10/25GbE", give the highest and put the quote's wording in "as_written".
- Keep the port connector (such as SFP28, QSFP56, OSFP or RJ45), the host interface (such as PCIe 5.0 x16; "Gen5x16" is PCIe 5.0 x16, which counts as stated) and the form factor (such as PCIe low-profile or OCP 3.0 SFF) apart. OCP 3.0 is a form factor, never a host interface.
- Fill "rdma_support" with the protocol, such as RoCEv2, only when the document states it or the exact model establishes it, not just because the adapter is Ethernet or InfiniBand.
- Add a "review_flags" entry when more than one adapter could match, when a value depends on a variant the model name doesn't settle, or when the document contradicts itself.
- Record a power supply only when the document lists it as its own part. Never add one because a server or chassis comes with power supplies.
- For a power supply, fill only the properties in "psu", in the same {"value", "basis"} form as for a CPU. When the manufacturer and model or MPN identify the power supply precisely, infer the missing specifications from your own knowledge and give the "reason", except "ac_input_phase" and "input_connector", which you record only as written.
- "mpn" and "model" are the power supply manufacturer's codes, never the vendor's, which goes in "vendor_product_id". "manufacturer" is the power supply's own maker, never the server's brand.
- "rated_output_w" is one power supply's rated output in W, never the total: "2x 1100W" is 1100. If the rating depends on the input voltage, give the highest, put the quote's wording in "as_written", and add a review flag.
- Give "efficiency_certification" exactly as written, such as "Titanium" or "80 PLUS Platinum": never add or drop words. Never derive it from an efficiency percentage.
- "hot_swap" is true when the document says hot-plug or hot-swap, false only when it says the power supply isn't, and null otherwise, unless the exact model establishes it.
- "power_supply_type" is AC or DC, only when the document states it or the exact model establishes it, never from the wattage or voltage alone.
- Redundancy, such as "redundant" or "1+1", isn't a power supply property: put it in the power supply's "note" as written.
- Add a "review_flags" entry when more than one power supply could match, or when the document contradicts itself.
- An item's "chassis" is the enclosure of the server it quotes. Fill it from the item's own line or the server's base system or chassis line, such as "CODE(x4)1U RACK SERVER, BOARD ..., CHASSIS ...". Use null for an item that isn't a server.
- For a chassis, fill only the properties in "chassis", in the same {"value", "basis"} form as for a CPU. Infer only the identity, chassis type, form factor and rack height, from the exact model or the line itself, such as "Rackmount" for a 2U server, and give the "reason". Record dimensions, drive bays, expansion slots, power supply bays and cooling only as written.
- A chassis's properties are what it supports, never the parts installed in it: "drive_bays" counts bays, not drives, and "psu_bays" counts positions, not power supplies.
- "model" is the chassis's own designation when the document names one, such as "CHASSIS CSE-X400". If it gives only the server's or base system's model, use that and add the review flag "This is the server's model, not the chassis's own." "manufacturer" is the chassis's maker, only when the document names it or the exact model establishes it.
"""


class ExtractionError(Exception):
    """Extraction failed. The message never contains quote content."""


@dataclass(frozen=True)
class ModelSettings:
    base_url: str
    api_key: str | None = None  # sent as a bearer token when the server needs one
    model: str | None = None  # the server's model name, when it wants one in the request


def load_settings(env_file: Path | str = DEFAULT_ENV_FILE) -> ModelSettings:
    """Each setting comes from the environment, otherwise from the .env file."""
    from_file = _read_env_file(Path(env_file))

    def setting(name: str) -> str | None:
        return os.environ.get(name) or from_file.get(name) or None

    base_url = setting(BASE_URL_SETTING)
    if not base_url:
        raise ExtractionError(f"{BASE_URL_SETTING} isn't set. Add it to .env (see .env.example).")
    return ModelSettings(base_url, setting(API_KEY_SETTING), setting(MODEL_NAME_SETTING))


def load_base_url(env_file: Path | str = DEFAULT_ENV_FILE) -> str:
    """The model's address: from the environment, otherwise from the .env file."""
    return load_settings(env_file).base_url


def extract_quotes(
    markdown: str,
    base_url: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    *,
    api_key: str | None = None,
    model: str | None = None,
    settings: ModelSettings | None = None,
    source_name: str | None = None,
) -> list[QuoteDraft]:
    """Propose 1..N quote drafts from one normalized document.

    With no base_url, the address, key and model name all come from load_settings().
    source_name is the original file name (NormalizedDoc.source_name). Vendors put
    the quote number in it, and a spreadsheet export may not have one inside.
    """
    if settings is None:
        settings = ModelSettings(base_url, api_key, model) if base_url else load_settings()
    document = f"File name: {source_name}\n\n{markdown}" if source_name else markdown
    reply = _post_chat_completion(settings, _request_body(document, settings.model), timeout)
    return clean_drafts(_parse_reply(reply).quotes, document=document)


def _request_body(markdown: str, model: str | None = None) -> dict:
    body = {"model": model} if model else {}
    return body | {
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": markdown},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "extraction_result", "schema": extraction_json_schema()},
        },
    }


def _post_chat_completion(settings: ModelSettings, body: dict, timeout: float) -> dict:
    base_url = settings.base_url
    headers = {"Content-Type": "application/json"}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise ExtractionError(
                f"The model server returned HTTP {error.code}: it needs an API key, or rejected the one in {API_KEY_SETTING}."
            ) from None
        raise ExtractionError(f"The model server returned HTTP {error.code}.") from None
    except (OSError, ValueError) as error:
        if isinstance(error, json.JSONDecodeError):
            raise ExtractionError("The model server's response wasn't JSON.") from None
        raise ExtractionError(f"Could not reach the model server at {base_url}: {type(error).__name__}.") from None


def _parse_reply(reply: dict) -> ExtractionResult:
    try:
        choice = reply["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise ExtractionError("The model server's response didn't have the expected shape.") from None

    if choice.get("finish_reason") == "length":
        raise ExtractionError("The model's output was cut off at the token limit, so the draft is incomplete.")

    try:
        return ExtractionResult.model_validate(drop_empty_properties(_require_json(content)))
    except ValidationError as error:
        problems = [
            f"{'.'.join(str(part) for part in problem['loc'])} ({problem['type']})"
            for problem in error.errors(include_input=False, include_context=False, include_url=False)
        ]
        raise ExtractionError(f"The model's output doesn't match the draft schema: {'; '.join(problems)}.") from None


def _require_json(content: str) -> Any:
    try:
        return json.loads(content)
    except (TypeError, ValueError):
        raise ExtractionError("The model's output wasn't valid JSON.") from None


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    settings = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        settings[key.strip()] = value.strip().strip("\"'")
    return settings
