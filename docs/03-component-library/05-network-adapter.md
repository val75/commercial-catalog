# Network Adapter Component

## 1. Required Properties to Be Extracted

|Property|Description|Example|
|---|---|---|
|Manufacturer|Network adapter manufacturer|NVIDIA, Intel, Broadcom|
|Product family|Manufacturer's network adapter product family|ConnectX-7, Ethernet 800 Series|
|Model|Manufacturer's specific adapter model or variant designation, more specific than the family|E810-XXVDA2|
|Manufacturer part number (MPN)|Manufacturer's unique product or ordering code|MCX755106AS-HEAT|
|Vendor Product ID|The vendor's own product code for the line, kept apart from the MPN|NIC-CX7-2P-200G|
|Adapter type|Network adapter category|NIC, SmartNIC, Host Channel Adapter (HCA), Converged Network Adapter (CNA)|
|Network technology|Supported network technology and standard, where specified|Ethernet, InfiniBand NDR, Ethernet and InfiniBand (VPI)|
|Port count|Number of physical network ports|2|
|Port speed|Maximum speed per port; when several speeds are listed, as written|100 Gb/s, 400 Gb/s, 10/25 GbE|
|Port connector|Physical network port connector type|SFP28, QSFP28, QSFP56, QSFP-DD, OSFP, RJ45|
|Host interface|Interface connecting the adapter to the server|PCIe 4.0 x16, PCIe 5.0 x16|
|Form factor|Physical adapter form factor|PCIe full-height, PCIe low-profile, OCP 3.0 SFF|
|RDMA support|Remote Direct Memory Access capability and supported protocol|RoCE, RoCEv2, InfiniBand|
|Crypto|Crypto or security offload variant, as written, where specified|NoCrypto, Crypto Enabled|

## 2. Extraction Rules

1. Extract all available network adapter properties from the vendor quote.
2. Preserve manufacturer, product family, model and manufacturer part number (MPN) whenever available. Retain identifiers exactly as quoted and distinguish manufacturer identifiers from vendor product IDs and distributor SKUs.
3. Distinguish adapter type from network technology. For example, an Ethernet adapter and an InfiniBand adapter are different technologies, even if they have similar physical interfaces.
4. Extract the number of physical ports and the maximum speed per port. When several speeds are listed, such as 10/25 GbE, keep them as written. Do not interpret aggregate bandwidth across multiple ports as the speed of an individual port.
5. Distinguish port connector type from network technology and host interface. For example, QSFP28 describes a physical connector, while 100 GbE describes network speed and technology.
6. Distinguish the host interface from the network ports. PCIe 5.0 x16 describes the connection to the server; QSFP-DD describes a network port connector.
7. Preserve the complete host interface designation, including generation and lane configuration where specified.
8. Distinguish physical form factor from host interface. For example, PCIe low-profile describes the card's physical form factor, while PCIe 5.0 x16 describes its host interface. An OCP 3.0 card's form factor is OCP 3.0; its host interface is PCIe.
9. Extract RDMA support and the specific supported protocol where available. Do not assume RoCE or InfiniBand support solely from the adapter's Ethernet or InfiniBand classification.
10. Ask the model to infer missing properties from known manufacturer, model or MPN information.
11. When an adapter is identified by a sufficiently precise manufacturer and model designation, use the model's existing knowledge to infer missing technical specifications, even when the quote does not state them. Mark all inferred values as inferred rather than extracted.
12. Do not assume specifications are identical across different adapter variants, OEM implementations or firmware configurations. If the model designation does not uniquely identify the variant, flag uncertain specifications for review.
13. Distinguish explicitly extracted values from inferred values and flag inferred values for review.
14. If multiple possible network adapter models match the available information, flag the identification as ambiguous.
15. Preserve partial identification when the quote provides only a model, speed, port count or another subset of properties.
16. Normalize numerical specifications:
    - Port count: integer
    - Port speed: Gb/s
17. Preserve original numerical values and units where conversion or interpretation is uncertain. Do not silently combine port speeds or convert aggregate bandwidth into per-port bandwidth.
18. Flag conflicting specifications rather than silently choosing one value.
19. Keep the vendor's product ID apart from the MPN. When a spreadsheet has a plain "Product ID" column and one with the vendor's name in front of it, the Vendor Product ID comes from the vendor-named column.
20. Record the crypto variant exactly as the quote writes it, such as "NoCrypto". Do not infer it.
21. DPUs, such as BlueField, are not network adapters. They will have their own specification file.
22. Network ports built into the motherboard, such as "Dual 10GbE onboard", are not network adapter components. They belong to the server's system configuration.

## 3. Server Configuration Properties

| Property                            | Description                                       | Example  |
| ----------------------------------- | ------------------------------------------------- | -------- |
| Network adapter component reference | Reusable Network Adapter Component Library record | NIC-0001 |
| Quantity installed                  | Number of identical network adapters installed    | 2        |
| Unit price                          | Price per adapter, if separately quoted           | 450.00   |
| Currency                            | Currency of quoted price                          | USD      |