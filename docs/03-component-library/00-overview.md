# Component Library

## 1. Purpose

The Component Library is the central repository of hardware components identified in vendor quotes and server configurations.

It stores unique component identities and their technical specifications so that components can be consistently recognized, reused, compared and referenced across different quotes and systems.

Each distinct hardware component should have a single reusable library record, regardless of how many vendor quotes or server configurations reference it.

## 2. Component Types

Each component type has its own specification file defining the properties to be extracted, extraction rules and server configuration properties.

| File                  | Component type   |
| --------------------- | ---------------- |
| 01-cpu.md             | CPU              |
| 02-memory.md          | Memory / DIMM    |
| 03-storage.md         | Storage / Drives |
| 04-gpu.md             | GPU              |
| 05-network-adapter.md | Network adapters |
| 06-power-supply.md    | Power supply     |
| 07-chassis.md         | Chassis          |
| 08-raid-controller.md | RAID controller  |

Additional component types can be introduced as needed.

## 3. Component Identification

1. Components should be identified using the most specific information available in the vendor quote.
2. Manufacturer, product family, model, manufacturer part number and product code names should be captured where applicable.
3. Not every vendor quote will provide enough information to identify a component precisely.
4. Partial component identification is acceptable. Do not discard useful information simply because the exact model is unknown.
5. The same physical component should not be registered multiple times under different names or descriptions.
6. Existing component records should be checked before creating new ones.
7. Ambiguous identification or conflicting specifications must be flagged for review.

## 4. Technical Specifications

1. Each component type has its own defined set of properties, documented in its corresponding specification file.
2. Extract technical specifications explicitly stated in the vendor quote.
3. When information is missing, the model may propose values based on other available information and its existing knowledge.
4. Distinguish between explicitly extracted and inferred information.
5. Inferred values must be flagged for review and must not silently become verified catalog information.
6. Store numerical specifications using consistent units and formats.
7. Do not invent specifications when there is insufficient information to support a reasonable identification.

## 5. Component Records and Reuse

1. Each distinct hardware component has one record in the Component Library.
2. A component record stores the component's identity and reusable technical specifications.
3. Multiple quotes and server configurations can reference the same component record.
4. When a component already exists, reuse its existing record rather than creating a duplicate.
5. New component records and changes to existing component specifications require approval.
6. Additional information from subsequent quotes can be used to enrich existing component records, subject to review and approval.

## 6. Quote-Specific Component Occurrences

A component appearing in a vendor quote is represented by a separate occurrence linked to its Component Library record.

The occurrence stores information specific to that quote, including:

- Component reference
- Quantity
- Unit price, when separately quoted
- Currency
- Review notes relating to that particular quote occurrence

A component can therefore appear in multiple quotes, with each occurrence retaining its own quantity, price and review information.

Quote-specific information must not be stored directly in the reusable Component Library record.

## 7. Quote Occurrences vs. System Configuration

Quote occurrences and System Library configurations serve different purposes and must have clearly defined ownership of data.

### Quote Occurrences

A quote occurrence records what a vendor quoted. It preserves the commercial and configuration details associated with a specific quote.

Quote occurrence data includes:

- Component reference
- Quantity quoted
- Unit price
- Currency
- Quote-specific description
- Quote-specific notes
- Other commercial details associated with the quoted component

Quote occurrence data must reflect the source quote and must not be silently changed to reflect a subsequently approved system configuration.

### System Library Configuration

A System Library configuration records the hardware composition and configuration of a system.

Configuration data includes:

- Component reference
- Quantity installed or configured
- Component placement or assignment, where applicable
- Configuration-specific properties
- Redundancy configuration, where applicable
- Component roles and relationships within the system

System configuration data represents the intended or approved system configuration, rather than simply repeating the vendor's quote.

### Data Ownership and Relationship

Each data element must have a clearly defined owner. Quote occurrence data and System Library configuration data must not be treated as interchangeable.

The same type of information may exist in both contexts when it represents different facts. For example:

- **Quantity quoted** belongs to the Quote occurrence.
- **Quantity installed or configured** belongs to the System Library configuration.
- **Unit price and currency** belong to the Quote occurrence.
- **Redundancy configuration** belongs to the System Library configuration.

Where a quote is used to create or update a System Library configuration, maintain the relationship between the quoted component occurrence and the resulting system configuration as appropriate.

Differences between quoted and configured quantities, components, or specifications must not be silently reconciled. They must be identifiable and reviewable.

Do not duplicate quote-specific commercial information in the System Library, or system configuration information in the reusable Component Library, unless there is a clearly defined reason and ownership.

## 8. Component Evidence and History

Component properties may be established or enriched using information from multiple vendor quotes.

The system should retain the relationship between component properties and the sources or decisions supporting them.

This allows the system to:

- Identify which quotes provided information about a component.
- Distinguish explicitly extracted values from inferred values.
- Record approved corrections and changes to component specifications.
- Retain a history of how component information was established and updated.

Component evidence and history belong to the component's identification and maintenance history, not to individual quote occurrences alone.

## 9. Component Creation and Reuse

When processing a quote:

1. Identify the component type.
2. Extract the properties defined in the corresponding component specification file.
3. Search the existing Component Library for a matching component.
4. If a match exists, reference the existing component.
5. If new information is available, propose updates to the existing component record.
6. If no match exists, propose a new component record.
7. If identification is ambiguous, flag it for review.
8. Save new or updated component records only after approval.

## 10. Relationship with Other Libraries

- **Quote Repository:** Stores vendor quotes, quote revisions and quoted line items, including quote-specific component occurrences.
- **Component Library:** Stores reusable hardware component identities and technical specifications.
- **System Library:** Stores complete server configurations and their component relationships.

The Component Library does not own vendor quotes or complete server configurations.

## 11. Component Property Selection Principles

The Component Library should capture technical properties that provide practical value for component identification, differentiation, purchasing decisions, configuration, or operational requirements.

Do not include a technical property simply because it is available in a manufacturer's datasheet.

When defining or reviewing the properties for any component type, evaluate each property against the following criteria:

1. **Identification:** Does the property help identify or distinguish the component from other models or variants?
2. **Purchasing:** Does the property influence purchasing decisions, pricing, or commercial comparison?
3. **Configuration:** Is the property relevant when specifying or configuring a server or system?
4. **Operations:** Does the property support an actual operational, deployment, compatibility, or infrastructure requirement?
5. **Practical availability:** Is the property likely to appear in vendor quotes, or can it be reliably obtained from the component's manufacturer model or part number when needed?

Avoid properties that provide little practical value, are rarely available, duplicate other properties, or introduce unnecessary complexity.

A property does not need to appear in vendor quotes to be included if it provides meaningful value and can be reliably established from manufacturer documentation or other authoritative information.

### Model Review and Recommendations

Whenever the model analyzes a component type or reviews an existing component property list, it must evaluate the proposed properties against these principles.

The model should proactively suggest:

- Properties that should be removed because they provide little practical value, are redundant, or are unlikely to be useful.
- Properties that should be added because they are important for identification, purchasing, configuration, or operations.
- Properties that should be renamed, consolidated, or split to improve clarity.
- Properties that should remain optional because they are not consistently available in vendor quotes.

Recommendations must include a brief explanation of the practical value or reason for the proposed change.

The model must distinguish between recommendations and approved changes. It must not modify the component property definitions automatically; changes require user review and approval.