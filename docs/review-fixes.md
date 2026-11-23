# Review Fixes

## Purpose

This page lists extraction problems that are left for the reviewer to fix during approval. They aren't fixed by changing the model's instructions.

Each entry describes:

- what the model gets wrong;
- an example (invented, in the shape of a real quote);
- what the code already does about it, if anything;
- what the reviewer has to do;
- what the review screen should offer to make that quick.

The review screen ([06-review-queue.md](06-review-queue.md)) should be built with these in mind. Hermes ([07-hermes.md](07-hermes.md)) learns from review edits, so each correction here is also something it can learn.

---

## Why these are left to the reviewer

The model's instructions are one long prompt, and a small change to one sentence can flip an unrelated decision.

On 2026-11-18 the network technology sentence was reworded (the IB/EN rule moved first, the "InfiniBand NDR" example removed). With the new sentence, the redacted two-page PDF quote came back as two items in 2 of 2 runs: the network adapter on page 2 became a separate item, and the GPU and a drive group from page 1 were lost. With the old sentence it came back as one correct item in 2 of 2 runs. The runs were sent one at a time, so batching on the model server wasn't the cause.

Earlier, three rewordings of the vendor product ID instruction failed, and one of them left every vendor product ID empty.

Each prompt change also needs several model runs to check. So when a mistake is visible to the reviewer, and an automatic fix would mean another prompt change, it goes on this list instead.

Where a check in code is safe and doesn't depend on the model, it's used alongside the reviewer (see `extraction/cleanup.py`).

---

## Network adapters

### Network technology for IB/EN and VPI cards

**What happens.** A card that runs both Ethernet and InfiniBand is described with "IB/EN" (or "EN/IB", or "VPI"). The model takes the technology from the speed name instead. It records "InfiniBand NDR", marked as stated, and ignores "IB/EN". This happened on both the PDF and the spreadsheet of the same quote.

**Example.**

```
NIC-CX7-1P-NDR(x4)900-9X000-0000-ST0
1xNDR400G IB/EN OSFP Gen5x16 NoCrypto CX7
```

The model gives: network technology "InfiniBand NDR" (stated).
Expected: "Ethernet and InfiniBand" (stated), as in the example in [05-network-adapter.md](03-component-library/05-network-adapter.md). NDR is the speed generation. It's kept in the port speed's wording (`1xNDR400G`).

**What the code does.** After extraction, a check finds the adapter's own part in the document. It looks for the vendor product ID, then the MPN, and as a last resort the port speed as written. Spaces and line breaks are ignored, because PDF text breaks codes across lines. If "IB/EN", "EN/IB" or "VPI" is written on that part, network technology is set to "Ethernet and InfiniBand", stated, with the reason "The document says IB/EN." Another part's IB/EN on the same line or in the next spreadsheet row doesn't count.

**What the reviewer does.** The reviewer corrects the field in these cases:

- the code didn't find the adapter's part, for example because the model recorded neither a code nor the port wording;
- the document describes the dual technology in other words, such as "Ethernet/InfiniBand" or "InfiniBand and Ethernet";
- the card is dual-technology but the quote doesn't say so.

**What the review screen should offer.** The reviewer should be able to type a short form and have it saved as the standard value: "EN/IB", "IB/EN" or "VPI" become "Ethernet and InfiniBand", "EN" becomes "Ethernet", and "IB" becomes "InfiniBand".

### Adapter type for IB/EN cards

**What happens.** On the same IB/EN card, the model infers the adapter type "HCA" (Host Channel Adapter), which is the term for an InfiniBand-only card. It makes the same mistake as with the technology: it treats the card as InfiniBand-only. The value is marked inferred, with a reason such as "NDR400G IB/EN indicates InfiniBand HCA".

**What the code does.** Nothing.

**What the reviewer does.** Chooses the adapter type for each dual-technology card. The choices in 05-network-adapter.md are NIC, SmartNIC, HCA and CNA. There's deliberately no rule for VPI cards, in the spec or in code: the reviewer decides card by card (decided 2026-11-18).

**What the review screen should offer.** The four categories as a choice, rather than free text. Because the value is inferred, it's shown unselected, as for every inferred value.

### Model when the quote gives only the manufacturer's SKU

**What happens.** NVIDIA networking cards have two manufacturer codes:

- a **SKU** in the form `900-9Xnnn-nnnn-nnn`, which is what quotes usually write;
- an **order number (OPN)** in the form `MCX…`, such as MCX755106AS-HEAT. This is the card's variant designation.

NVIDIA's firmware documentation lists both for each card. The quote gives only the SKU. The model records the SKU correctly as the MPN, but also copies it into "model". The spec wants "model" to be the variant designation, more specific than the family. Its example is Intel's E810-XXVDA2, from a manufacturer that has only one code.

**Example.** `NIC-CX7-1P-NDR(x4)900-9X000-0000-ST0 ...` gives MPN "900-9X000-0000-ST0" and model "900-9X000-0000-ST0".

**What the code does.** It clears an adapter's model when it's the same code as the MPN, ignoring spaces and letter case. The MPN is kept as written. A different model, such as E810-XXVDA2, is kept. Drives aren't affected, because a drive's model and MPN are often the same code.

**What the reviewer does.** Enters the OPN as the model, looked up from the SKU, or leaves it empty.

**Not to be automated by the model.** Don't ask the model to infer the OPN from the SKU. The mapping is obscure, and the model is likely to make up a plausible `MCX…` code. A made-up part number is worse than an empty field.

**What the review screen should offer.** An empty model field next to the MPN, so it's clear the model needs to be filled in. A later option: look the OPN up from the SKU in a table the catalog builds as reviewers enter them, so each SKU is typed in only once.

---

## All parts

### Vendor codes in a SKU or Part Number column

**Status: fixed on 2026-11-22, kept for its history.** After the chassis moved from the item's parts onto the item itself (see "The chassis is often left empty" below), the codes came through in 5 runs in a row. No instruction about SKU columns changed, so this is probably a side effect of how the model now reads the server row. If the codes go missing again, the model test below fails, and this entry applies again.

**What happened.** In a spreadsheet whose code column is called "SKU" (or, probably, "Part Number"), the model leaves the vendor's code out of every part. CPU, memory and power supply rows all came back without a vendor product ID. Vendor codes are read when the column is called "Product ID", or the vendor-named "ACME Product ID", as in the real quote's export. They're also read from a PDF's `CODE(xN)` lines. Found on 2026-11-19 with an invented BOM shaped like a server maker's export.

**Example.**

```
| Line | SKU | Description | Qty | Unit Price (USD) |
| 1 | 210-XXAA | Example R700 1U server chassis | 8 | 4200 |
| 3 | 370-XXCC | 32GB DDR5-4800 RDIMM | 128 | 190 |
| 4 | 450-XXDD | 1100W Titanium hot-plug PSU | 16 | 260 |
```

The model gives: no vendor product ID for the memory or the power supply.
Expected: vendor product ID "370-XXCC" and "450-XXDD", stated.

**What was tried.** One added instruction ("A spreadsheet's "SKU" or "Part Number" column is the vendor's code for each line: put it in that part's "vendor_product_id"") changed nothing. The codes were still missing, and every other result was the same. It was removed. A check in code was considered and not built. It would have to find each part's row by matching values such as "1100W" and the quantity, because the drafts don't keep the row's text, and that would be the least reliable of the cleanup checks.

**What the code does.** Nothing. A model test checks for the codes. It was marked as an expected failure until 2026-11-22, and is now a normal test, so a change that loses the codes again shows up as a failure.

**What the reviewer does.** Copies the code from the SKU or Part Number column into each part's vendor product ID.

**What the review screen should offer.** Show the source row next to each part, with its code cells, so the reviewer can copy the code with one click. A later option: keep each part's source row in the draft, which would also make a check in code reliable.

---

## Chassis

### The chassis is often left empty

**What happens.** Each quote item has a chassis: the enclosure of the server it quotes ([07-chassis.md](03-component-library/07-chassis.md)). It sits on the item rather than among its parts. When it was a part, the model made it from the item's own line, then started a new item at the next priced row, so a spreadsheet with a price on every row split into one quote per row. On the item, the split stopped, but the model often leaves the chassis empty. In the 2026-11-19 runs it was filled for both invented spreadsheets, had no rack height on the invented PDF and the two email quotes, and was empty on both redacted quotes. One try, on 2026-11-22, moved the chassis instructions up next to the item instructions. The rack height was still missing on the same three and two spreadsheet results got worse, so it was undone.

**Example.**

```
2 XS-2200-BASE-A, 2U DP RACK SERVER, BASEBOARD 48,500.00 97,000.00
XB-22, CHASSIS CX-210
```

The model gives: no rack height.
Expected: rack height "2U" and model "CX-210", both stated, and the identity where the exact model establishes it.

**What the code does.** When the model left them empty, it reads two things from the item's own line:

- a rack height such as "2U" or "(1U)", only when the line gives exactly one, and never from inside a code such as SYS-2U-X400;
- a code written after the word "CHASSIS" as the model, such as "CHASSIS CX-210".

Both are marked stated. The model's own values are never replaced. A chassis with nothing in it is dropped.

**What the reviewer does.** Fills in the chassis identity (manufacturer, family, model, MPN), the chassis type and the form factor, from the item's line or the manufacturer's documentation. A chassis code written without the "CHASSIS" label, as in some vendor descriptions, is one the reviewer recognizes and the code doesn't.

**What the review screen should offer.** The item's line next to the chassis fields, as for vendor codes. An empty chassis on a server item is shown as missing, not hidden.

### No flag when the model is the server's

**What happens.** 07-chassis.md section 3.3 asks for a review flag when the quote gives only the server's model, not a separate chassis model. The model added "This is the server's model, not the chassis's own." on one of the two email quotes and not the other, though both are written in the form "Example R660 (1U)". On a spreadsheet it once added the flag to a line that does name its chassis ("CHASSIS CX-210"), where it doesn't apply.

**What the code does.** Nothing.

**What the reviewer does.** Checks whether the chassis model is the enclosure's own or the server's, whatever the flag says.

**What the review screen should offer.** Show the chassis model next to the item's model and part number. When they're the same code, mark it, so the question is visible without relying on the flag.

### Rack height copied into the form factor

**What happens.** On a spreadsheet run, the model put "2U" in both rack height and form factor. The form factor is the mounting standard, such as 19-inch rackmount.

**What the code does.** Nothing.

**What the reviewer does.** Clears or corrects the form factor.

---

## Drives

### Form factor marked stated when it was inferred

**What happens.** A spreadsheet line gives only the connector and height, such as "U.3 15mm", not the form factor. The model recorded the form factor "2.5-inch" but marked it **stated**, with the reason "15mm height implies 2.5-inch". The reason describes an inference, so the basis is wrong. This happened in the 2026-11-14 spreadsheet runs. In the 2026-11-18 runs the same lines were correctly marked inferred ("U.3 15mm is 2.5-inch form factor"), but this is the model's own judgement and may happen again. On the PDF of the same quote, the lines write `SSD 2.5"`, so "stated" was correct there.

**Example.**

```
| SSD-XQ-960-U3 | ACME 7100 960GB NVMe PCIe 4.0 U.3 15mm, 1DWPD | 8 |
```

The model gives: form factor "2.5-inch", basis stated, reason "15mm height implies 2.5-inch".
Expected: form factor "2.5-inch", basis inferred, same reason.

**What the code does.** Nothing. A check that a stated value is actually written in the document (`2.5"`, `2.5-inch`, `2.5 in`) was considered and not added.

**What the reviewer does.** When the reason says a value was worked out ("implies", "typically", "indicates"), but the value is marked stated, the reviewer treats it as inferred. They confirm it or correct it.

**What the review screen should offer.** Always show the reason next to the value and its basis, so a mismatch is visible. Let the reviewer change the basis as well as the value.

### Reasons that ramble and contradict their value

**What happens.** Sometimes the model's reason is a long piece of thinking aloud instead of a short explanation. On the redacted PDF, one drive's connector came back as "U.2", inferred, with a reason of about 600 characters. The reason went back and forth over whether "E1" in the vendor's code meant the E1.S form factor. It ended with "Connector is not stated. I will leave it null." So the reason says the field should be empty, but the value is filled in.

The guess itself is uncertain. A 2.5" NVMe drive can be U.2 or U.3, and the spreadsheet of the same quote shows one drive of each. "U.2" happened to be right for that drive.

**Example.** A drive line `SSD-XQ-3T8-E1-015(x16)SSD 2.5" NVMe PCIe5 3.8TB 1DWPD`, which doesn't state the connector, gives connector "U.2", inferred, with a reason like:

> 'E1' in part number might suggest E1.S but description says 2.5". Wait, … Let's look closer. … I will trust description for form factor. Connector is not stated. I will leave it null.

**What the code does.** Nothing.

**What the reviewer does.** Reads the reason before accepting an inferred value. If the reason contradicts the value or says it's unknown, they clear the value or enter the right one from the other document or the drive's datasheet.

**What the review screen should offer.**

- Show long reasons folded, with a visible marker, so they don't fill the screen but aren't hidden either.
- Inferred values are offered unselected, so a rambling inference never reaches the catalog without someone choosing it.
- When a quote comes in two files, such as a PDF and a spreadsheet export, treat both as the same quote and show the other file's value next to this one. For this drive, the spreadsheet stated the connector.

---

## Adding to this list

Add an entry when a mistake should be fixed in review rather than in the model's instructions. Give the date, an invented example, what the code does about it, and what the review screen needs. Use made-up codes and names in examples, never the values of a real quote.
