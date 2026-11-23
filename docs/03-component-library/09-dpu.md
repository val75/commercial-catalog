# Data Processing Unit (DPU) Component

## 1. Purpose

The Data Processing Unit (DPU) component represents a programmable data-processing accelerator designed to offload infrastructure and data-processing tasks from the host CPU.

A DPU typically combines general-purpose processing cores, network interfaces, and specialized hardware acceleration capabilities. Depending on the product, it may provide networking, security, storage, virtualization, and other infrastructure offloads.

A DPU is maintained as a distinct component type because its capabilities extend beyond those of a conventional Network Adapter or GPU.

This component covers dedicated DPU cards and modules, including products such as NVIDIA BlueField and AMD Pensando.

The reusable DPU record stores hardware identity and technical specifications. Quote-specific quantities and pricing belong to the Quote occurrence. Installed quantities, host assignments, network connections, and enabled offload configurations belong to the System Library configuration.

## 2. Component Properties

Only properties that help identify, differentiate, purchase, configure, or deploy the DPU should be maintained. Properties should be populated from the quote or reliable manufacturer documentation when the exact model is known.

|Property|Description|Example|
|---|---|---|
|Manufacturer|Manufacturer of the DPU|NVIDIA|
|Product family|Manufacturer-defined product series|BlueField|
|Model|Commercial model designation, including generation and variant|BlueField-3 DPU|
|Manufacturer Part Number (MPN)|Exact manufacturer part number, where available|Manufacturer-specific part number|
|Processor architecture|Architecture or processor family used by the DPU's general-purpose cores|ARM Cortex-A78|
|CPU cores|Number of general-purpose CPU cores integrated into the DPU|16|
|Network technology|Supported networking technology|Ethernet, InfiniBand|
|Port count|Number of physical network ports|2|
|Port speed|Supported speed per port|200 Gb/s|
|Port connector|Physical network connector type|QSFP112|
|Host interface|Interface connecting the DPU to the host server|PCIe 5.0 x16|
|Onboard memory|Memory integrated into the DPU for its own processing functions|32 GB|
|Hardware acceleration capabilities|Integrated hardware acceleration functions|Crypto, compression, packet processing|
|Storage connectivity|Storage interfaces or protocols supported by the DPU|NVMe, NVMe-oF|
|Form factor|Physical implementation of the DPU|PCIe add-in card, OCP 3.0|

### Property Selection Notes

- **Processor architecture:** Capture the architecture of the DPU's general-purpose processing cores, not the host server's CPU architecture.
- **CPU cores:** Record the number of cores integrated into the DPU. Do not confuse these with host CPU cores or accelerator engines.
- **Network technology:** Record the supported networking technology, such as Ethernet or InfiniBand. Do not assume that every DPU supports both.
- **Port count, speed, and connector:** Treat these as separate properties. Record port speed per port and preserve the exact connector designation.
- **Host interface:** Record the DPU-to-host connection, such as PCIe generation and lane width. Do not confuse it with the DPU's network ports.
- **Onboard memory:** Record memory physically integrated into or dedicated to the DPU. Do not include host system memory.
- **Hardware acceleration capabilities:** Capture manufacturer-documented functions such as cryptography, packet processing, compression, storage acceleration, and virtualization offload. Preserve specific terminology where possible rather than reducing all capabilities to a generic accelerator label.
- **Storage connectivity:** Capture supported storage interfaces and protocols where relevant. Distinguish physical interfaces from protocols such as NVMe-oF.
- **Form factor:** Distinguish PCIe add-in cards from OCP or proprietary modules. Do not infer form factor from the host interface alone.

## 3. Extraction and Identification Rules

1. Preserve the exact manufacturer, product family, model designation, and MPN as stated in the source.
2. Distinguish the commercial DPU model from its processor architecture, CPU core configuration, and silicon generation.
3. Preserve vendor-specific product identifiers and SKUs separately from the MPN. Do not assume that every identifier in a quote is a manufacturer part number.
4. Extract CPU core count and processor architecture only when they are established for the exact model or variant.
5. Extract network port count, speed, and connector independently. Do not infer one from another.
6. Distinguish the host interface from the network interfaces exposed by the DPU.
7. Record onboard memory capacity and type when specified. Do not assume that a DPU's onboard memory is equivalent to host memory or GPU memory.
8. Capture hardware acceleration capabilities using manufacturer terminology. Distinguish dedicated hardware engines from software features or capabilities that depend on optional licensing.
9. Record storage connectivity and supported protocols only when documented for the exact model.
10. Use reliable manufacturer documentation to complete missing specifications when the exact model is known. Mark these values as inferred or externally established rather than quote-extracted.
11. Do not transfer specifications between generations or variants without confirming that they apply to the exact model.
12. Normalize units while preserving meaningful original designations.
13. If sources disagree, retain the conflicting evidence for review rather than silently choosing one value.
14. If the source describes a product as a DPU, preserve that classification unless reliable manufacturer documentation establishes otherwise. Do not automatically classify a SmartNIC or conventional Network Adapter as a DPU based only on its networking or offload capabilities.
    

## 4. Component Occurrence in a Quote

A quote occurrence records the DPU as a quoted commercial line item.

It should reference the reusable DPU component and record:

- Component reference
- Quantity quoted
- Unit price
- Currency
- Quote-specific description or notes

If a quote identifies a DPU only by a vendor SKU or abbreviated description, preserve that original identifier and description on the quote occurrence until the product can be reliably matched to a reusable component record.

## 5. System Library Configuration

The System Library configuration records how DPUs are installed and used in a specific server configuration.

Relevant configuration information includes:

- DPU component reference
- Quantity installed
- Host server assignment
- PCIe slot or module position
- Network port assignments and connections
- Storage connections, where applicable
- Enabled infrastructure offload functions
- DPU operating mode or deployment role, where applicable
- Network and storage configuration associated with the DPU

These are configuration properties, not reusable DPU specifications.

The DPU's onboard network ports are part of the DPU component. They should not also be recorded as separate Network Adapter components.

## 6. Data Ownership

|Information|Belongs to|
|---|---|
|Manufacturer, product family, model, MPN|DPU component|
|Processor architecture and CPU cores|DPU component|
|Network technology, port count, port speed, connector|DPU component|
|Host interface and form factor|DPU component|
|Onboard memory|DPU component|
|Hardware acceleration capabilities|DPU component|
|Storage connectivity and supported protocols|DPU component|
|Quantity quoted|Quote occurrence|
|Unit price and currency|Quote occurrence|
|Quote-specific description and notes|Quote occurrence|
|Quantity installed|System Library configuration|
|Host server and slot assignment|System Library configuration|
|Network and storage port connections|System Library configuration|
|Enabled offload functions and deployment role|System Library configuration|

The reusable component record describes what the DPU is and what it supports. The Quote occurrence describes what was commercially quoted. The System Library configuration describes where it is installed and how it is used.