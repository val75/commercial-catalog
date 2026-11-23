 # Data Model

## Overview

The system stores vendor quotes and the hardware configurations contained within them.

The primary purpose is to preserve the original commercial information while building a reusable hardware catalog.

---

## Entity Overview

Vendor
    │
    |-----Quote
            │
		    |-------Attachment
            │
            ├── Revision
            │
            └── Quote Item
                    │
                    └── Configuration
                            │
                            ├── CPU
                            ├── Memory
                            ├── Storage
                            ├── GPU
                            ├── NIC
                            ├── PSU
                            └── Warranty

---

## Vendor

Represents the company that issued the quote.

Examples

- Dell
- Lenovo
- HPE
- Supermicro

---

## Quote

Represents one commercial quote received from a vendor.

A quote may contain one or more items.

A quote never changes.

If a vendor sends an updated quote, a new Revision is created.

---

## Attachment

Original uploaded document.

Examples

- PDF
- DOCX
- Email
- Excel

Attachments are immutable.

---

## Revision

Represents a revised version of a quote.

Each revision has its own extracted data.

---

## Quote Item

Represents one priced line item within a quote.

Usually one server configuration.

Contains

- quantity
- unit price
- extended price

---

## Configuration

Represents one hardware configuration.

Contains all hardware components.

Configurations may later become catalog items.

---

## CPU

Represents one installed processor.

---

## Memory

Represents installed memory modules.

---

## Storage

Represents installed storage devices.

---

## GPU

Represents installed accelerator devices.

---

## NIC

Represents network adapters.

---

## PSU

Represents installed power supplies.

---

## Warranty

Commercial support and warranty information.
