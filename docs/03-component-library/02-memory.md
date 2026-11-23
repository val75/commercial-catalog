# Memory Component

## 1. Required Properties to Be Extracted

| Property                       | Description                                           | Example                           |
| ------------------------------ | ----------------------------------------------------- | --------------------------------- |
| Manufacturer                   | Memory module manufacturer                            | Samsung                           |
| Product family                 | Memory product family, if identifiable                | DDR5 Server Memory                |
| Model                          | Manufacturer's model designation                      | M321R8GA0BB0-CQK                  |
| Manufacturer part number (MPN) | Manufacturer's unique product or ordering code        | M321R8GA0BB0-CQK                  |
| Vendor Product ID              | Vendor's own product identifier or SKU                | MEM-DR596NC-ER64                  |
| Memory type                    | Memory technology                                     | DDR4, DDR5                        |
| Form factor                    | Physical module type                                  | RDIMM, LRDIMM, UDIMM, SODIMM      |
| Capacity                       | Capacity of one module (GB)                           | 64                                |
| Data rate                      | Effective memory data rate (MT/s)                     | 4800                              |
| Operating frequency            | Memory clock frequency, if explicitly specified (MHz) | 2400                              |
| ECC support                    | Whether the module supports Error Correction Code     | Yes                               |
| Rank                           | Memory rank configuration                             | 2                                 |
| DRAM device organization       | Width of each DRAM device                             | x4                                |
| DRAM chip density              | Density of individual DRAM chips (Gb)                 | 24                                |
| Module height                  | Physical height classification of the memory module   | Low Profile (LP), Standard Height |
| Voltage                        | Operating voltage (V)                                 | 1.1                               |
| CAS latency (CL)               | CAS latency, if specified                             | 40                                

## 2. Extraction Rules

1. Extract all available memory properties from the vendor quote.
2. Preserve manufacturer, product family, model and MPN whenever available.
3. Distinguish memory technology (DDR4, DDR5) from form factor (RDIMM, LRDIMM, UDIMM).
4. Extract capacity per module, not total installed memory, unless the quote explicitly describes a combined configuration.
5. Normalize all numerical specifications to consistent units:
    - Capacity: GB
    - Data rate: MT/s
    - Operating frequency: MHz
    - Voltage: V
    - CAS latency: clock cycles
    - DRAM chip density: Gb
    - Rank: integer
    - DRAM device organization: standard notation (x4, x8, x16)
6. Distinguish data rate (MT/s) from operating clock frequency (MHz). Do not treat them as interchangeable.
7. Extract module height exactly as specified in the quote (e.g. LP). Preserve the original designation. If its meaning is known, store the normalized interpretation separately without replacing the original value.
8. Ask the model to infer missing properties from known manufacturer, model or MPN information.
9. Distinguish explicitly extracted values from inferred values; flag inferred values for review.
10. If multiple possible memory modules match the available information, flag the identification as ambiguous.
11. Preserve partial identification when the quote provides only capacity, type or another subset of properties.
12. Flag conflicting specifications rather than silently choosing one value.
13. Do not infer compatibility with a particular server or CPU from the memory component specifications alone.

## 3. Server Configuration Properties

|Property|Description|Example|
|---|---|---|
|Memory component reference|Reference to the reusable Memory Component Library record|MEM-0001|
|Quantity installed|Number of identical modules installed|8|
|Unit price|Price per module, if separately quoted|185.00|
|Currency|Currency of the quoted price|USD|