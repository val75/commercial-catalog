# GPU Component

## 1. Required Properties to Be Extracted

| Property                       | Description                                                          | Example                         |
| ------------------------------ | -------------------------------------------------------------------- | ------------------------------- |
| Manufacturer                   | GPU chip manufacturer                                                | NVIDIA                          |
| Board manufacturer             | Card manufacturer, such as an OEM for an OEM-branded card, if named  | Dell, HPE, PNY                  |
| Product family                 | GPU product family                                                   | Tesla, Data Center GPU, GeForce |
| Model                          | Manufacturer's GPU model designation                                 | H100 SXM 80GB                   |
| Manufacturer part number (MPN) | Card manufacturer's unique product or ordering code                  | 900-21010-0000-000              |
| Vendor Product ID              | Vendor's own product identifier or SKU                               | GPU-H100-80G-SXM (example)      |
| GPU architecture               | GPU architecture or codename                                         | Hopper                          |
| GPU chip                       | Specific GPU processor designation, if available                     | GH100                           |
| GPU memory capacity            | Total onboard memory (GB)                                            | 80                              |
| GPU memory type                | Type of onboard memory                                               | HBM2e, HBM3, GDDR6              |
| GPU memory bandwidth           | Memory bandwidth (GB/s)                                              | 2,000                           |
| GPU memory interface width     | Memory bus width (bits)                                              | 5120                            |
| CUDA cores / Stream processors | Number of GPU processing cores, using the manufacturer's terminology | 16,896 CUDA cores               |
| Tensor cores                   | Number of tensor processing cores, if applicable                     | 528                             |
| GPU base clock                 | Base GPU clock frequency (MHz), if specified                         | 1095                            |
| GPU boost clock                | Boost GPU clock frequency (MHz), if specified                        | 1980                            |
| Interface                      | Host interface and generation                                        | PCIe 5.0 x16                    |
| Form factor                    | Physical card form factor                                            | PCIe add-in card, SXM           |
| Cooling type                   | GPU cooling design                                                   | Passive, active                 |
| Power consumption (W)          | Maximum board power or specified power limit, where identified       | 700                             |
| Power connector                | Required auxiliary power connector, if specified                     | 16-pin                          |
| NVLink support                 | Whether NVLink is supported                                          | Yes                             |
| NVLink bandwidth               | NVLink bandwidth, if specified (GB/s)                                | 900                             |

## 2. Extraction Rules

1. Extract all available GPU properties from the vendor quote.
2. Preserve manufacturer, product family, model, manufacturer part number (MPN), GPU architecture and GPU chip designation whenever available. Retain identifiers exactly as quoted and distinguish manufacturer identifiers from vendor product IDs and distributor SKUs.
3. Distinguish between the GPU chip manufacturer and the board or card manufacturer when both are identified.
4. Extract GPU memory capacity as total onboard memory per GPU, not the combined memory of multiple GPUs.
5. Distinguish GPU memory type from GPU memory capacity and bandwidth.
6. Preserve the manufacturer's terminology for processing cores (e.g. CUDA cores or Stream processors). Do not treat different manufacturers' core counts as directly comparable.
7. Distinguish PCIe interface generation and lane width (e.g. PCIe 5.0 x16).
8. Distinguish physical form factor (e.g. PCIe add-in card or SXM) from cooling type (e.g. passive or active).
9. Distinguish maximum board power, configured power limit and typical power consumption. Do not combine them into one value without identifying what the quote specifies.
10. Extract NVLink support and bandwidth only when explicitly stated or reliably established from the exact GPU model.
11. Ask the model to infer missing properties from known manufacturer, model, MPN or GPU architecture information.
12. Distinguish explicitly extracted values from inferred values; flag inferred values for review.
13. If multiple possible GPU models match the available information, flag the identification as ambiguous.
14. Preserve partial identification when the quote provides only a model, memory capacity or another subset of properties.
15. Normalize numerical specifications to consistent units:
    - GPU memory capacity: GB
    - GPU memory bandwidth: GB/s
    - GPU memory interface width: bits
    - GPU base and boost clock: MHz
    - Power consumption: W
    - NVLink bandwidth: GB/s
    - Processing core counts: integer
16. Preserve original numerical values and units where conversion or interpretation is uncertain. Do not silently change manufacturer specifications or mix decimal and binary capacity conventions.
17. Flag conflicting specifications rather than silently choosing one value.
18. When a GPU is identified by a sufficiently precise manufacturer and model designation, use the model's existing knowledge to infer missing technical specifications, even when they are not stated in the quote. This may include architecture, GPU chip, memory capacity and type, memory bandwidth, processing core counts, clock speeds, interface, form factor, cooling type, power consumption and NVLink capabilities. Mark all inferred values as inferred rather than extracted.
19. Do not assume that specifications are identical across different card variants, OEM implementations or power configurations. If the model designation does not uniquely identify the variant, flag uncertain or potentially variant-dependent specifications for review rather than assigning potentially incorrect values.

## 3. Server Configuration Properties

|Property|Description|Example|
|---|---|---|
|GPU component reference|Reference to the reusable GPU Component Library record|GPU-0001|
|Quantity installed|Number of identical GPUs installed|8|
|Unit price|Price per GPU, if separately quoted|25,000.00|
|Currency|Currency of the quoted price|USD|