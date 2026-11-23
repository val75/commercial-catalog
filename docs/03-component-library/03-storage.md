# Storage Component

## 1. Required Properties to Be Extracted

| Property                       | Description                                                         | Example                               |
| ------------------------------ | ------------------------------------------------------------------- | ------------------------------------- |
| Manufacturer                   | Drive manufacturer                                                  | Samsung                               |
| Product family                 | Manufacturer's storage product family                               | PM9A3                                 |
| Model                          | Manufacturer's drive model designation                              | MZQL23T8HCLS-00A07                    |
| Manufacturer part number (MPN) | Manufacturer's unique product or ordering code                      | MZQL23T8HCLS-00A07                    |
| Storage type                   | Storage technology                                                  | SSD, HDD                              |
| Form factor                    | Physical drive form factor                                          | 2.5-inch, 3.5-inch, M.2 2280, E1.S    |
| Connector                      | Physical drive connector or connection type                         | U.2, U.3, M.2, SATA                   |
| Interface                      | Drive interface, including protocol and generation where applicable | PCIe 4.0 x4, SATA 6 Gb/s, SAS 12 Gb/s |
| Capacity                       | Nominal capacity per individual drive (GB or TB)                    | 3.84 TB                               |
| Recording / Flash technology   | Storage media technology, where specified                           | TLC, QLC, CMR, SMR                    |
| Endurance                      | Drive endurance rating, using the manufacturer's stated metric      | 1 DWPD, 7,000 TBW                     |
| Maximum power consumption      | Maximum specified drive power consumption (W)                       | 15                                    |
| Encryption support             | Drive-level hardware encryption capabilities, where specified       | SED, TCG Opal 2.0, FIPS 140-2         |

## 2. Extraction Rules

1. Extract all available storage drive properties from the vendor quote.
2. Preserve manufacturer, product family, model and MPN whenever available.
3. Distinguish between SSD and HDD storage types.
4. Distinguish the drive's interface from its physical form factor. For example, a 2.5-inch NVMe SSD and a 2.5-inch SAS SSD have different interfaces despite sharing a form factor.
5. Distinguish interface technology and protocol where applicable (e.g. PCIe/NVMe, SATA, SAS).
6. Extract capacity per individual drive, not the combined capacity of multiple drives.
7. Preserve the manufacturer's recording or flash technology designation (e.g. TLC, QLC, CMR, SMR) when available. Do not infer this property when the manufacturer does not specify it.
8. Extract maximum power consumption rather than typical or average power consumption. If only typical or average power is provided, preserve its original designation and flag the maximum value as unavailable.
9. Extract the physical connector type where specified. Distinguish connector from form factor and protocol/interface.
10. Extract endurance ratings using the manufacturer's stated metric, such as DWPD (Drive Writes Per Day) or TBW (Terabytes Written). Preserve the original metric and value; do not convert between metrics unless the required drive lifetime and capacity assumptions are known.
11. Extract encryption support where specified, including SED (Self-Encrypting Drive), TCG Opal, and FIPS certification. Distinguish hardware encryption capability from encryption that is merely supported by the host or software.
12. Ask the model to infer missing properties from known manufacturer, model or MPN information.
13. When a drive is identified by a sufficiently precise manufacturer and model designation, use the model's existing knowledge to infer missing technical specifications, even when they are not stated in the quote. Mark all inferred values as inferred rather than extracted.
14. Do not assume that specifications are identical across different capacities, firmware variants or OEM implementations. If the model designation does not uniquely identify the variant, flag uncertain or potentially variant-dependent specifications for review.
15. Distinguish explicitly extracted values from inferred values; flag inferred values for review.
16. If multiple possible drive models match the available information, flag the identification as ambiguous.
17. Preserve partial identification when the quote provides only a model, capacity, interface or another subset of properties.
18. Normalize numerical specifications to consistent units:
    - Capacity: GB or TB
    - Maximum power consumption: W
19. Preserve original numerical values and units where conversion or interpretation is uncertain. Do not silently change manufacturer specifications or mix decimal and binary capacity conventions.
20. Flag conflicting specifications rather than silently choosing one value.

## 3. Server Configuration Properties

A server configuration may contain multiple distinct groups of storage drives. Each group references a reusable Storage Component Library record and records its own quantity and pricing.

|Property|Description|Example|
|---|---|---|
|Storage component reference|Reference to the reusable Storage Component Library record|STR-0001|
|Quantity installed|Number of identical drives in this group|2|
|Unit price|Price per drive, if separately quoted|250.00|
|Currency|Currency of the quoted price|USD|

A server may contain multiple storage groups with different component references, capacities, interfaces or quantities.

**Example configuration:**

|Storage component reference|Capacity per drive|Quantity|Total raw capacity|
|---|---|---|---|
|STR-0001|960 GB|2|1.92 TB|
|STR-0002|7.68 TB|4|30.72 TB|

The groups are independent configuration entries. Do not combine them into one storage component or assume they serve a particular purpose based solely on capacity or quantity.