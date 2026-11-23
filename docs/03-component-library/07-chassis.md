# Chassis Component

## 1. Purpose

The Chassis component represents a uniquely identifiable physical enclosure used to house server, storage, or other computing hardware.

The Component Library maintains reusable chassis records that can be referenced by multiple quotes and system configurations.

The chassis record describes the enclosure's physical characteristics, mounting requirements, internal capacity, and hardware accommodation capabilities.

It does not represent the complete server configuration. Components installed in the chassis, their quantities, and their configuration are managed separately.

Quantity quoted belongs to the Quote occurrence. Quantity installed and the relationship between the chassis and its installed components belong to the System Library configuration.

---

## 2. Component Properties

Capture the following properties when available and applicable.

| Property                         | Description                                                                                     | Example                     |
| -------------------------------- | ----------------------------------------------------------------------------------------------- | --------------------------- |
| Manufacturer                     | Chassis manufacturer                                                                            | Supermicro                  |
| Product family                   | Manufacturer's product family or series                                                         | SuperServer                 |
| Model                            | Commercial chassis or system enclosure designation                                              | CSE-829U                    |
| Manufacturer part number (MPN)   | Exact manufacturer's part number                                                                | CSE-829U2TS-R1K23LPB        |
| Chassis type                     | General enclosure type                                                                          | Rackmount, tower, blade     |
| Form factor                      | Physical enclosure or mounting standard                                                         | 19-inch rackmount           |
| Rack height                      | Vertical rack space occupied                                                                    | 2U                          |
| Dimensions                       | Physical external dimensions (width, height, depth)                                             | 437 × 89 × 647 mm           |
| Drive bay configuration          | Number, location, and type of drive bays                                                        | 12 × 3.5-inch hot-swap bays |
| Expansion slot configuration     | Number of expansion slots, PCIe generation, electrical lane width, and physical characteristics | 13 × PCIe 5.0 x16 FHFL      |
| PSU bay capacity and form factor | Number of physical PSU positions and supported PSU form factor                                  | 6 × CRPS                    |
| Cooling configuration            | Chassis fan arrangement and supported fan type                                                  | 6 × 80 mm hot-swap fans     |

Properties that are unavailable or not applicable should remain empty.

The table defines candidate properties, not a requirement to populate every field. Apply the property-selection principles in `00-overview.md` when deciding whether a property should be retained, removed, or refined.

---

## 3. Property Definitions and Extraction Rules

### 3.1 Manufacturer

Identify the manufacturer of the chassis itself.

Examples:

- Supermicro
- Dell
- HPE
- Lenovo
- NVIDIA

Do not automatically assume that the server vendor manufactured the enclosure. Where the actual chassis manufacturer is reliably established, capture it separately from the server brand.

### 3.2 Product Family

Capture the manufacturer's product family or series when available.

Examples:

- SuperServer
- PowerEdge
- ProLiant
- ThinkSystem

Use the manufacturer's actual product family designation. Do not create a family based solely on an inferred product grouping.

### 3.3 Model

Capture the manufacturer's model designation for the chassis.

The model should distinguish the enclosure from other products in the same family, including variants with different drive bay arrangements, backplanes, or power configurations.

Preserve the manufacturer's designation as written.

Where a quote identifies only a complete server model rather than a separately identifiable chassis model, do not automatically treat the server model as the chassis model. Record the available identifier and flag the distinction for review.

### 3.4 Manufacturer Part Number (MPN)

Capture the exact manufacturer's part number when available.

Rules:

- Preserve the original part number.
- Do not substitute a vendor SKU, quote reference, or reseller product code for the MPN.
- If the model and MPN are identical, retain both only if they serve distinct identification purposes; otherwise, recommend consolidating them.
- If the identifier's meaning is unclear, preserve it with its original label and flag it for review.
- Do not assume that two chassis with similar model designations are identical when their part numbers or configurations differ.

### 3.5 Chassis Type

Identify the general physical enclosure type.

Examples:

- Rackmount
- Tower
- Blade
- Modular enclosure

Rules:

- Use the manufacturer's designation where available.
- Do not confuse chassis type with rack height or mounting form factor.
- If the enclosure is a specialized or proprietary design, preserve its description rather than forcing it into an inaccurate category.

### 3.6 Form Factor

Capture the physical enclosure or mounting standard.

Examples:

- 19-inch rackmount
- EIA-310 rackmount
- Proprietary blade enclosure

Rules:

- Distinguish the mounting standard from the chassis type.
- Do not infer rack compatibility solely from the enclosure's width or appearance.
- Preserve proprietary or non-standard mounting descriptions.
- Do not use motherboard form factor as a substitute for chassis form factor.

### 3.7 Rack Height

Capture the vertical rack space occupied by the chassis.

Examples:

- 1U
- 2U
- 4U
- 8U

Rules:

- Normalize rack height using standard rack-unit notation.
- Do not infer rack height from external dimensions if the manufacturer provides an explicit designation.
- If the chassis is not designed for rack installation, leave this property empty or mark it not applicable.
- Distinguish the chassis rack height from any additional rack space required for installation, cooling, or servicing. Those requirements belong to deployment planning.

### 3.8 Dimensions

Capture the external physical dimensions when they provide practical value for rack planning, installation, or equipment compatibility.

Examples:

- 437 × 89 × 647 mm
- 482 × 178 × 800 mm

Rules:

- Normalize dimensions to millimetres (mm).
- Preserve the manufacturer's dimension order or labels (width, height, depth) where provided.
- Do not assume an order when the source does not identify the axes.
- Distinguish chassis dimensions from shipping or packaging dimensions.
- Do not estimate missing dimensions from photographs or unrelated product variants.

### 3.9 Drive Bay Configuration

Capture the number, location, and physical type of drive bays supported by the chassis.

Examples:

- 12 × 3.5-inch front hot-swap bays
- 24 × 2.5-inch front hot-swap bays
- 8 × 2.5-inch front bays and 4 × 2.5-inch rear bays
- 2 × internal M.2 positions

Rules:

- Distinguish bay count from the number of drives actually installed.
- Capture bay size and location when available.
- Distinguish hot-swap bays from fixed or internal mounting positions.
- Where the chassis supports multiple drive bay configurations, capture the relevant supported configurations without assuming that all are installed.
- Do not treat a drive bay as proof that a particular drive interface or protocol is supported. Backplane and controller compatibility may need separate verification.
- Do not calculate installed or usable storage capacity from the number of bays.

If the chassis supports multiple front or rear drive configurations depending on backplane or optional kits, preserve the variant information and flag configuration dependencies.

### 3.10 Expansion Slot Capacity and Characteristics

Capture the expansion slot configuration specified by the manufacturer for the chassis or its associated standard server platform.

Examples:

- 13 × PCIe 5.0 x16 full-height, full-length slots
- 7 × PCIe 4.0 x16 full-height, full-length slots
- 4 × PCIe 5.0 x16 low-profile slots

Rules:

- Capture the number of expansion slots and all available electrical and physical characteristics.
- Include PCIe generation, electrical lane width, physical height, physical length, and card width accommodation where specified.
- Use the manufacturer's published specifications for the exact chassis or associated server platform.
- Where the specifications describe a complete server platform rather than the chassis independently, retain that association in the component evidence.
- Do not assume that every slot can be occupied simultaneously. Preserve restrictions involving risers, adjacent card dimensions, GPU configurations, or other hardware dependencies where documented.
- Do not infer slot characteristics from chassis dimensions, rack height, or photographs.
- Where different chassis or platform revisions have different expansion configurations, distinguish them rather than combining their specifications.
- If a characteristic cannot be reliably established, leave it unknown rather than guessing.

### 3.11 PSU Bay Capacity and Form Factor

Capture the number of physical PSU positions supported by the chassis and their supported physical form factor, where available.

Examples:

- 2 × CRPS PSU positions
- 4 × hot-swap PSU positions
- 6 × proprietary PSU positions

Rules:

- Capture the number of PSU positions supported by the chassis, not the number of PSUs actually installed.
- Capture the supported PSU form factor or physical type when reliably established.
- Distinguish PSU bay capacity from the PSU models and wattages supported by the complete server platform.
- Do not infer PSU wattage, input voltage, input connector, or electrical compatibility from the number or form factor of PSU positions.
- Do not infer electrical redundancy from the number of PSU positions.
- Where PSU compatibility depends on specific chassis revisions, power distribution boards, or system configurations, preserve those dependencies and flag them for review.
- If the number or type of PSU positions cannot be reliably established, leave the property unknown rather than guessing.

Actual PSU models, installed quantities, redundancy configuration, and power feed assignments belong to the System Library configuration. Individual PSU specifications belong to the Power Supply component record.

### 3.12 Cooling Configuration

Capture the chassis' physical cooling arrangement where relevant to configuration and deployment.

Examples:

- 6 × 80 mm hot-swap fans
- 4 × 40 mm fan modules
- Front-to-rear airflow
- Liquid-cooling-ready chassis

Rules:

- Capture fan quantity, size, and arrangement when available and useful.
- Distinguish chassis-supported fan positions from fans actually installed.
- Do not infer airflow direction from chassis appearance alone.
- Capture liquid-cooling support only when the manufacturer explicitly establishes it.
- Do not include detailed thermal performance figures or fan speed curves unless a specific operational requirement justifies them.
- Installed fan models, quantities, and cooling configuration belong to the System Library configuration when they need to be tracked separately.

---

## 4. Component Identification and Reuse

When a chassis appears in a quote or system configuration:

1. Extract the manufacturer's model and part number, where available.
2. Determine whether the identifier refers to a chassis, barebones system, or complete server.
3. Search the Component Library for an existing chassis record.
4. Match using the most specific available identifiers.
5. Reuse an existing record when the identity is established.
6. Create a new record only when the chassis is determined to be a distinct component.
7. Flag ambiguous matches, conflicting identifiers, or incomplete identification for review.

A chassis model must not automatically be equated with a complete server model.

Different drive bay, backplane, riser, PSU, or enclosure variants must not automatically be treated as the same component.

A partially identified chassis may still be recorded, but its identity must remain appropriately qualified.

---

## 5. Component Properties: Extracted and Inferred

Properties may be established or enriched from:

- Vendor quotes
- Manufacturer documentation
- Manufacturer product specifications
- Manufacturer configuration guides
- Previously approved component records
- Reliable model-specific technical references

For each property:

- Record the value explicitly stated in the source when available.
- Infer missing properties only when the exact chassis model or part number reliably establishes them.
- Distinguish extracted values from inferred values.
- Flag ambiguous or conflicting values for review.
- Do not invent specifications based on generic chassis characteristics.

Manufacturer documentation may be used to enrich a component record even when the property was not present in the original quote, provided the information is reliably associated with the exact chassis variant.

### 5.1 Deployment-Relevant Property Enrichment

Some chassis properties may be absent from vendor quotes but are important for deployment planning.

Examples include:

- Rack height and external dimensions
- Drive bay capacity and configuration
- Expansion slot capacity and physical constraints
- PSU bay configuration
- Cooling configuration

When the chassis identity is sufficiently established, investigate and populate these properties using reliable manufacturer documentation.

Do not treat the absence of a property from a quote as evidence that the property is unsupported or not applicable.

---

## 6. Chassis Configuration and Quote Occurrences

The chassis component record describes the reusable physical enclosure.

A chassis appearing in a quote or system configuration has a separate occurrence containing:

|Property|Description|
|---|---|
|Component reference|Link to the reusable chassis component|
|Quantity|Number of chassis quoted or included|
|Unit price|Price per chassis, if separately quoted|
|Currency|Quoted currency|
|Review notes|Quote-specific identification or interpretation notes|

Ownership is defined as follows:

- Quantity quoted and quote-specific pricing belong to the Quote occurrence.
- Quantity installed belongs to the System Library configuration.
- Installed components and their relationships to the chassis belong to the System Library configuration.
- Supported physical capabilities and limits belong to the reusable Chassis component record.

For example, the chassis record may specify support for 12 drive bays and 2 PSU positions. The System Library configuration records the actual drives and PSUs installed in those positions.

Do not store installed component quantities or a particular server's hardware configuration as reusable chassis properties.

---

## 7. Component Evidence and History

Component properties may be established or enriched from multiple quotes and manufacturer references.

The system must maintain traceability between:

- The reusable chassis component
- The individual property values
- The quote component occurrences that provide evidence
- Manufacturer documentation used for enrichment
- Extracted, inferred, and corrected values
- Review decisions and approved changes

New evidence must not silently overwrite existing approved properties.

When conflicting specifications are encountered, preserve the existing approved value, record the conflicting evidence, and flag it for review.

Evidence must be associated with the relevant component property and, where applicable, the specific quote component occurrence that supports it.

Corrections and changes must remain traceable rather than silently replacing historical evidence.