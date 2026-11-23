# System Library

## Purpose

The Configuration Library stores reusable hardware configurations.

A configuration represents a complete server build.

Configurations are independent of vendor quotes and pricing.

Multiple vendor quotes may reference the same configuration.

---

## Goals

- Eliminate duplicate server definitions
- Reuse known hardware builds
- Enable hardware search
- Compare vendor pricing for identical systems
- Form the basis of the internal product catalog

---

## Definition

A Configuration is a collection of installed components.

It answers the question:

"What hardware is installed?"

It does not answer:

"Who sold it?"

"What did it cost?"

"When was it quoted?"

---

## Relationships

Vendor Quote

↓

Quote Item

↓

Configuration

↓

Installed Components

↓

Canonical Components

---

## Configuration Identity

Every configuration has a unique internal identifier.

Example

CFG-000184

Name

Dell R760 - Dual 6530 - 512GB - 8x3.84TB

Status

Approved

---

## Configuration Contents

Each configuration contains

- Chassis
- Motherboard (optional)
- CPU(s)
- Memory
- Storage
- GPU(s)
- NIC(s)
- PSU(s)
- RAID Controller
- HBA
- TPM
- Warranty Profile (optional)

---

## Configuration Status

Draft

Created automatically.

Needs Review

Matched with low confidence.

Approved

Verified by a user.

Deprecated

No longer offered.

Archived

Hidden from normal searches.

---

## Configuration Matching

When importing a quote the system attempts to find an existing configuration.

Matching order

1. Exact configuration fingerprint

2. Same chassis + identical components

3. Similar configuration

4. No match

If multiple matches exist

User review required.

---

## Configuration Fingerprint

Every approved configuration has a deterministic fingerprint.

The fingerprint is calculated from the installed components.

The fingerprint ignores

- vendor
- quote number
- price
- quantity
- warranty
- shipping
- discounts

The fingerprint changes if hardware changes.

Examples

Same configuration

Dell R760

2 × Xeon Gold 6530

8 × 64GB

8 × 3.84TB NVMe

↓

Same fingerprint

---

Different configuration

Dell R760

2 × Xeon Gold 6530

16 × 64GB

8 × 3.84TB NVMe

↓

Different fingerprint

---

## Versioning

Configurations are immutable.

If hardware changes

Create a new configuration.

Do not overwrite an approved configuration.

---

## Search

Configurations may be searched by

- Manufacturer
- Chassis
- CPU
- Core count
- Memory
- Storage
- GPU
- NIC
- Power
- Form factor
- Tags

---

## Tags

Optional user-defined tags.

Examples

AI

Virtualization

Storage

Ceph

GPU

Database

General Purpose

High Memory

---

## Publishing

Approved configurations may be published to the Product Catalog.

Publishing is optional.

---

## Future

Configurations may later include

- benchmark results
- power measurements
- thermal measurements
- inventory availability
- deployment templates
- operating system compatibility
- firmware compatibility

Outside the scope of Phase 1.