# CPU Component

## 1. Required Properties to Be Extracted

| Property       | Description                                     | Example |
| -------------- | ----------------------------------------------- | ------- |
| Manufacturer   | CPU manufacturer                                | AMD     |
| Product family | CPU product family                              | EPYC, Xeon       |
| Model          | Manufacturer's model designation                | 9654, Gold 6438N |
| CPU code name  | CPU architecture or product-generation codename | Turin   |
| Physical cores | Number of physical cores                        | 96      |
| Threads        | Number of logical threads                       | 192     |
| Base clock     | Base operating frequency (GHz)                  | 2.4     |
| Cache (MB)     | Total L3 cache                                  | 384     |
| TDP (W)        | Thermal design power                            | 360     |

## 2. Extraction Rules

1. Extract all available CPU properties from the vendor quote.
2. Preserve the CPU code name even when it is the only CPU information provided.
3. Use the manufacturer, product family, model and code name together when identifying the CPU.
4. Ask the model to infer the CPU's identity (manufacturer, product family and model) from other available information.
    - For example, a CPU code name such as Turin may suggest AMD as the manufacturer.
    - A model designation may help identify the product family.
5. Take technical specifications (code name, cores, threads, base clock, cache, TDP) only from the quote, and leave missing ones empty. Do not use the model's own knowledge to propose them: in testing, the values it proposed were often wrong (decided 2026-11-13). A reference source may fill them later.
6. Distinguish explicitly extracted values from inferred values. Flag inferred values for review.
7. If multiple CPU models could match the available information, flag the identification as ambiguous rather than selecting one without sufficient evidence.
8. Prefer exact manufacturer model designations over shortened or informal vendor descriptions.
    - A tier word such as Silver, Gold or Platinum is part of the model, not the product family. For example, Intel Xeon Gold 6438N is product family "Xeon" and model "Gold 6438N".
9. Preserve numerical values in consistent units:
    - Clock frequency: GHz
    - Cache: MB
    - TDP: W
    - Physical cores and threads: integer counts
10. If the vendor quote contains conflicting information, flag the discrepancy for review rather than silently choosing one value.
11. Do not discard partially identified CPU information simply because the exact model cannot be determined.

## 3. Server Configuration Properties

These properties describe how the CPU is included in a quoted server configuration.

|Property|Description|Example|
|---|---|---|
|CPU component reference|Reference to the CPU Component Library entry|CPU-0001|
|Quantity installed|Number of identical CPUs installed in the server|2|
|Unit price|Price per CPU, if separately quoted|1,250.00|
|Currency|Currency of the quoted price|USD|
