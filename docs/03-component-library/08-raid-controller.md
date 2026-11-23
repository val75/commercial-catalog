# RAID Controller

## 1. Purpose

The RAID Controller component represents a dedicated hardware controller used to manage storage devices and provide RAID functionality or other storage-management capabilities.

It covers dedicated PCIe, mezzanine, and other standalone controller cards. RAID functionality integrated into a motherboard, chipset, or server platform is not represented as a separate RAID Controller component; it is captured as part of the System Library configuration.

A RAID Controller record stores reusable hardware identity and technical specifications. Quote-specific quantities and pricing belong to the Quote occurrence. Installed controller quantities, drive assignments, RAID configuration, and storage topology belong to the System Library configuration.

## 2. Component Properties

Only properties that help identify, differentiate, purchase, configure, or deploy the controller should be maintained. Properties should be populated from the quote or reliable manufacturer documentation when the exact model is known.

|Property|Description|Example|
|---|---|---|
|Manufacturer|Manufacturer of the controller|Broadcom|
|Product family|Manufacturer-defined product series|MegaRAID|
|Model|Commercial model designation|MegaRAID 9560-16i|
|Manufacturer Part Number (MPN)|Exact manufacturer part number, where available|05-50077-00|
|Controller type|General controller architecture or category|Hardware RAID, HBA, Tri-Mode|
|Host interface|Interface connecting the controller to the server|PCIe 4.0 x8|
|External ports|Number and type of external storage ports, if present|4 × SFF-8654|
|Internal ports|Number and type of internal storage ports, if present|16 × SAS/SATA|
|Supported drive interfaces|Drive interfaces supported by the controller|SAS, SATA, NVMe|
|Maximum drive count|Maximum number of drives supported, where specified|240|
|RAID levels|RAID levels supported by the controller|RAID 0, 1, 5, 6, 10, 50, 60|
|Cache capacity|Dedicated controller cache, if present|8 GB|
|Cache protection|Mechanism protecting cached data during power loss|CacheVault, flash-backed cache, battery backup|
|Boot support|Whether the controller supports booting from attached storage|Yes|

### Property Selection Notes

- **Controller type:** Distinguish hardware RAID controllers from HBAs and tri-mode controllers. An HBA should not be classified as a RAID controller merely because it connects storage devices.
- **Host interface:** Record the controller-to-server interface, not the drive interface. Include PCIe generation and lane width when available.
- **Internal and external ports:** Record port count and connector type separately for internal and external connections. Do not confuse physical connectors with the number of drives supported.
- **Supported drive interfaces:** Record SAS, SATA, NVMe, or other supported interfaces. Do not infer support for an interface from the connector alone.
- **Maximum drive count:** Capture only when the manufacturer specifies a supported maximum. The actual number of drives in a server is a System Library configuration property.
- **RAID levels:** Record the exact supported levels. Do not assume that all RAID levels are supported by every controller in a product family.
- **Cache capacity:** Record dedicated controller cache, not system memory or cache on attached drives.
- **Cache protection:** Distinguish battery-backed cache, flash-backed cache, and other protection mechanisms. Do not treat ordinary cache as protected cache.
- **Boot support:** Capture only when explicitly supported or documented for the exact controller model.

## 3. Extraction and Identification Rules

1. Preserve the exact manufacturer, model designation, and MPN as stated in the source.
2. Distinguish the controller's model from its product family and any vendor-specific SKU or product identifier.
3. Preserve identifiers whose type is uncertain as unclassified identifiers rather than assuming they are MPNs.
4. Identify whether the item is a hardware RAID controller, HBA, or tri-mode controller. If the source does not establish the type, leave it unresolved.
5. Extract internal and external ports independently. Do not combine them into one port count.
6. Record connector designations exactly as specified. Do not infer supported drive interfaces solely from the connector.
7. Extract supported RAID levels from documentation for the exact model or confirmed variant.
8. Distinguish cache capacity from cache protection capability.
9. When specifications are missing from the quote, use reliable manufacturer documentation for the exact model where available. Mark values obtained this way as inferred or externally established rather than quote-extracted.
10. Do not transfer specifications from a similar controller model or product family without confirming that they apply to the exact model.
11. Normalize units while preserving the original designation where it is meaningful.
12. If sources disagree, retain the conflicting evidence for review rather than silently choosing one value.

## 4. Component Occurrence in a Quote

A quote occurrence records the controller as a quoted commercial line item.

It should reference the reusable RAID Controller component and record:

- Component reference
- Quantity quoted
- Unit price
- Currency
- Quote-specific description or notes

If a quote identifies a controller only by a vendor SKU or abbreviated description, preserve that original identifier and description on the quote occurrence until the controller can be reliably matched to a reusable component record.

## 5. System Library Configuration

The System Library configuration records how RAID controllers are installed and used in a specific server configuration.

Relevant configuration information includes:

- RAID Controller component reference
- Quantity installed
- Controller assignment or role, where multiple controllers are present
- Drives connected to each controller
- Internal or external connection assignments
- RAID virtual disk and array configuration
- RAID level and drive membership
- Cache protection configuration or status, where operationally relevant
- Boot device assignment, where applicable

These are configuration properties, not reusable component specifications.

## 6. Data Ownership

|Information|Belongs to|
|---|---|
|Manufacturer, product family, model, MPN|RAID Controller component|
|Controller type, host interface, ports, supported drive interfaces|RAID Controller component|
|Maximum supported drive count and RAID levels|RAID Controller component|
|Cache capacity, cache protection capability, boot support|RAID Controller component|
|Quantity quoted|Quote occurrence|
|Unit price and currency|Quote occurrence|
|Quote-specific description and notes|Quote occurrence|
|Quantity installed|System Library configuration|
|Controller assignment and connected drives|System Library configuration|
|RAID arrays, virtual disks, RAID levels, and drive membership|System Library configuration|
|Actual cache protection hardware installed or operational status|System Library configuration, where applicable|

The reusable component record describes what the controller is capable of. The Quote occurrence describes what was commercially quoted. The System Library configuration describes what is installed and how it is configured.