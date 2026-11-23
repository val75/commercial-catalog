# Power Supply Component

## 1. Purpose

The Power Supply component represents a uniquely identifiable power supply unit (PSU) used in server, storage, or other hardware configurations.

The Component Library maintains reusable PSU records that can be referenced by multiple quotes and system configurations.

The component record captures technical and identification properties of the PSU. Quantity quoted and quote-specific pricing belong to the **Quote occurrence**. Quantity installed and redundancy configuration belong to the **System Library configuration**.

---

## 2. Component Properties

Capture the following properties when available and applicable.

| Property                          | Description                                                           | Example                                                |
| --------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------ |
| Manufacturer                      | PSU manufacturer                                                      | Delta, Lite-On, Supermicro                             |
| Product family                    | Product family or series                                              | Titanium Power Supply                                  |
| Model                             | Manufacturer's model designation                                      | PWS-1K28P-SQ                                           |
| Manufacturer part number (MPN)    | Exact manufacturer's part number                                      | PWS-1K28P-SQ                                           |
| Rated output power (W)            | Maximum rated output power                                            | 1280 W                                                 |
| Power supply type                 | AC or DC input type                                                   | AC                                                     |
| AC input phase configuration      | AC input phase configuration supported by the PSU                     | Y (Wye) / Delta                                        |
| Input voltage                     | Supported input voltage range                                         | 100–240 V AC                                           |
| Input frequency                   | Supported input frequency                                             | 50/60 Hz                                               |
| Input connector / connection type | Physical input connection used to connect the PSU to its power source | IEC C14, IEC C20, IEC C22, terminal block, proprietary |
| Efficiency certification          | Efficiency certification or rating                                    | 80 PLUS Platinum                                       |
| Form factor                       | Physical PSU form factor or standard                                  | CRPS                                                   |
| Hot-swap support                  | Whether the PSU supports hot replacement                              | Yes                                                    |

Properties that are unavailable or not applicable should remain empty.

---

## 3. Property Definitions and Extraction Rules

### 3.1 Manufacturer

Identify the manufacturer of the power supply itself, not necessarily the server manufacturer.

Examples:

- Delta
- Lite-On
- Murata
- FSP
- Supermicro

A PSU supplied under an OEM or server manufacturer's branding should retain that branding while identifying the actual manufacturer when reliably established.

### 3.2 Product Family

Capture the manufacturer's product series or family when available.

Examples: Delta DPS series, Lite-On PS series, or other manufacturer-defined product families.

Do not use generic PSU form-factor standards, such as CRPS, as product family values.

Do not create a product family based solely on assumptions.

### 3.3 Model

Capture the manufacturer's model designation.

The model should distinguish the PSU from other products in the same family, including variants with different wattages, input types, or connector configurations.

Preserve the manufacturer's designation as written.

### 3.4 Manufacturer Part Number (MPN)

Capture the exact manufacturer's part number when available.

Rules:

- Preserve the original part number.
- Do not substitute a vendor SKU or quote reference for the manufacturer's part number.
- If the model and MPN are identical, retain both properties only if they serve distinct identification purposes; otherwise, recommend consolidating them.
- If the identifier's meaning is unclear, preserve it and flag it for review.

### 3.5 Rated Output Power

Capture the PSU's rated output power in watts (W).

Examples:

- 750 W
- 1200 W
- 1600 W
- 3200 W

Rules:

- Capture the PSU's rated output capacity, not its actual consumption.
- Distinguish individual PSU capacity from total installed capacity.
- Do not calculate total system PSU capacity in the component record.
- Do not confuse input power with output power.
- If a PSU has different ratings depending on input voltage or operating conditions, preserve the relevant ratings and flag the difference if necessary.

### 3.6 Power Supply Type

Identify whether the PSU accepts AC or DC input.

Examples:

- AC
- DC

Where the type is not explicitly specified, infer it only when the exact model reliably establishes it.

### 3.7 AC Input Phase Configuration

Capture the PSU's supported AC input phase configuration where applicable.

Examples:

- Wye (Y)
- Delta (Δ)
- Single-phase
- 3-phase

Rules:

- Capture the input phase configuration supported by the PSU.
- Distinguish Wye (Y) and Delta (Δ) compatibility where specified.
- Do not infer phase configuration from input voltage alone.
- This property may not be available in vendor quotes and may require enrichment from manufacturer documentation.
- When the exact PSU model is known, investigate and populate this property when reliably established.
- If the PSU supports multiple input configurations, capture all supported configurations.
- If the configuration cannot be established, leave it unknown rather than guessing.

This property is particularly important for deployment planning and verifying compatibility with the facility's electrical distribution infrastructure.

### 3.8 Input Voltage

Capture the supported input voltage range.

Examples:

- 100–240 V AC
- 200–240 V AC
- 48 V DC

Rules:

- Preserve the supported range.
- Normalize voltage units to volts (V).
- Do not assume that a PSU supports universal input unless confirmed by the model or manufacturer specifications.

### 3.9 Input Frequency

Capture the supported AC input frequency when available.

Examples:

- 50 Hz
- 60 Hz
- 50/60 Hz

This property is applicable to AC power supplies and should remain empty for DC-only power supplies.

### 3.10 Input Connector / Connection Type

Capture the physical input connector or connection type used to connect the PSU to its power source.

Examples:

- IEC C14
- IEC C20
- IEC C22
- Terminal block
- Proprietary connector
- Blind-mate power connection

Rules:

- Capture the PSU's physical input connection type where applicable.
- Distinguish the PSU inlet/connection from the power cable or cord used to connect it.
- Preserve the exact connector designation when known.
- Do not infer connector type from rated power, input voltage, or PSU form factor alone.
- This property may not appear in vendor quotes and should be populated through manufacturer documentation when the exact PSU model is known.
- Where the PSU uses a proprietary or blind-mate connection, preserve the manufacturer's description.
- If the connection type cannot be reliably established, leave it unknown.

This property is important for deployment planning, power cable selection, rack PDU compatibility, and facility power integration.

### 3.11 Efficiency Certification

Capture the manufacturer's stated efficiency certification or rating where available.

Examples:

- 80 PLUS Gold
- 80 PLUS Platinum
- 80 PLUS Titanium
- 80 PLUS Titanium certified

Rules:

- Preserve the certification level.
- Do not infer certification from efficiency percentages alone.
- Do not include detailed efficiency curves or efficiency at individual load percentages.
- If no certification is stated, leave the property empty.

### 3.12 Form Factor

Capture the PSU physical form factor or standard when available.

Examples:

- CRPS (Common Redundant Power Supply)
- Flex ATX
- ATX
- Proprietary server PSU form factor

Rules:

- Preserve the manufacturer's designation.
- Do not infer compatibility with a server or chassis solely from the form factor.
- Where a proprietary form factor is used, retain the designation or description provided by the manufacturer.

### 3.13 Hot-Swap Support

Identify whether the PSU supports hot replacement while the system remains operational.

Values:

- Yes
- No
- Unknown

Rules:

- Capture this property only when explicitly stated or reliably established from the exact PSU model or supported system specification.
- Do not assume hot-swap support solely because the PSU is designed for server use.
- System-level hot-swap capability may also depend on chassis, power distribution, and system design.

---

## 4. Component Identification and Reuse

When a PSU appears in a quote or configuration:

1. Extract the manufacturer's model and part number, where available.
2. Search the Component Library for an existing PSU record.
3. Match using the most specific available identifiers.
4. Reuse an existing record when the identity is established.
5. Create a new record only when the PSU is determined to be a distinct component.
6. Flag ambiguous matches, conflicting identifiers, or incomplete identification for review.

Different wattage variants, input variants, connector variants, or model revisions must not automatically be treated as the same component.

A partially identified PSU may still be recorded, but its identity must remain appropriately qualified.

---

## 5. Component Properties: Extracted and Inferred

Properties may be established from:

- Vendor quotes
- Manufacturer documentation
- Manufacturer product specifications
- Previously approved component records
- Reliable model-specific technical references

For each property:

- Record the value explicitly stated in the source when available.
- Infer missing properties only when the exact PSU model or part number reliably establishes them.
- Distinguish extracted values from inferred values.
- Flag ambiguous or conflicting values for review.
- Do not invent specifications based on generic PSU characteristics.

Manufacturer documentation may be used to enrich a component record even when the property was not present in the original quote, provided the information is reliably associated with the exact component.

---

## 6. PSU Configuration and Quote Occurrences

The PSU component record describes the reusable power supply itself.

A PSU appearing in a quote or server configuration has a separate occurrence containing:

|Property|Description|
|---|---|
|Component reference|Link to the reusable PSU component|
|Quantity|Number of PSUs included or installed|
|Unit price|Price per PSU, if separately quoted|
|Currency|Quoted currency|
|Review notes|Quote-specific identification or interpretation notes|

PSU quantity and configuration must not be stored as reusable component properties.

Examples of configuration-level information include:

- Two PSUs installed in a server
- 1+1 redundant PSU configuration
- 2+2 redundant PSU configuration
- Total installed PSU capacity
- Power redundancy configuration
- PSU allocation across power feeds

Quantity quoted belongs to the Quote occurrence. Quantity installed, redundancy configuration, total installed PSU capacity, and power feed assignments belong to the System Library configuration.

---

## 7. Component Evidence and History

Component properties may be established or enriched from multiple quotes and manufacturer references.

The system must maintain traceability between:

- The reusable PSU component
- The individual property values
- The quote component occurrences that provide evidence
- Manufacturer documentation used for enrichment
- Extracted, inferred, and corrected values
- Review decisions and approved changes

New evidence must not silently overwrite existing approved properties.

When conflicting specifications are encountered, preserve the existing approved value, record the conflicting evidence, and flag it for review.