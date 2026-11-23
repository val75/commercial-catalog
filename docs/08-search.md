# Search

## Purpose

Search is the primary way users interact with the Commercial Catalog.

The Commercial Catalog is a single body of information.

Users explore it through search and different views rather than through separate application modules.

The search experience should feel similar to a modern search engine rather than an ERP system.

---

# Design Principles

- Search is the primary navigation.
- One search bar.
- One catalog.
- Multiple views.
- Everything is searchable.
- Filters refine results.
- Results should be fast.
- Users should never need SQL.

---

# Navigation Model

The application is organized around a persistent global search bar.

```
+-----------------------------------------------------------------------+
| Commercial Catalog                                     🔍 Search...   |
+-----------------------------------------------------------------------+

 Home   Review Queue   Components   Systems   Vendors   Settings
```

The search bar is available on every page.

The navigation items are not separate applications.

Each represents a predefined view into the same Commercial Catalog.

Examples

Components

→ Component View

Systems

→ System View

Vendors

→ Vendor View

Review Queue

→ Review View

Home

→ Recent Activity

All navigation ultimately queries the same underlying catalog.

---

# Search Scope

Search includes:

- Quotes
- Systems
- Components
- Vendors
- Attachments

Future phases may include:

- Products
- Inventory
- Purchase Orders
- Customer Quotes

---

# Global Search

The application contains a single global search bar.

Examples

```
Dell R760

Xeon Gold 6530

L40S

338-CHQX

3.84TB NVMe

Quote Q-10291

Dell

2026
```

Global search returns the most relevant objects regardless of type.

---

# Search Views

Every search result may be viewed from different perspectives.

The underlying data does not change.

Only the presentation changes.

## Quote View

Answers

"What quotes have we received?"

Displays

- Quote Number
- Vendor
- Date
- Status
- Systems
- Total Price

Actions

- Open Quote
- Download Attachment
- Compare Revisions

---

## System View

Answers

"What systems do we know?"

Displays

- System Name
- Manufacturer
- CPU
- Memory
- Storage
- GPU
- Number of Quotes
- Vendors

Actions

- View Configuration
- Show Quotes
- Compare Systems

---

## Component View

Answers

"Where is this component used?"

Displays

- Component Name
- Component Type
- Manufacturer
- Number of Systems
- Number of Quotes
- Known Aliases

Actions

- View Component
- Show Systems
- Show Quotes

---

## Vendor View

Answers

"What do we know about this vendor?"

Displays

- Vendor
- Quotes
- Systems
- Components
- Latest Activity

Actions

- View Quotes
- View Systems
- Compare Pricing

---

# Filters

Search results may be filtered using:

General

- Vendor
- Manufacturer
- Status
- Date Range

System

- Chassis
- CPU
- CPU Count
- Total Cores
- Memory Capacity
- Storage Capacity
- Storage Type
- GPU
- GPU Count
- NIC Speed
- Form Factor

Commercial

- Currency
- Unit Price
- Quantity

Catalog

- Tags
- Approval Status

Filters remain visible while navigating between views.

---

# Facets

Search results display dynamic facets.

Example

Vendor

```
Dell (84)

Lenovo (39)

HPE (17)

Supermicro (26)
```

GPU

```
L40S (12)

H100 (4)

A100 (9)

None (95)
```

Selecting a facet immediately filters the current view.

---

# Search Modes

## Keyword Search

Matches text.

Example

```
R760
```

---

## Structured Search

Filters using known attributes.

Example

```
Vendor = Dell

Memory >= 512GB

GPU = L40S
```

---

## Natural Language Search (Future)

Examples

```
Show me every Dell system with at least 512GB RAM.

Find all quotes containing L40S GPUs.

Show systems similar to this one.

What is the cheapest R760 we've received?

Which vendors have quoted this CPU?
```

Outside the scope of Phase 1.

---

# Search Results

Results should display enough information to identify the object without opening it.

Example

```
Dell PowerEdge R760

2 × Xeon Gold 6530

512 GB

8 × 3.84TB NVMe

Quoted by

Dell

Lenovo

HPE

Latest Quote

2026-07-18
```

Results should provide direct navigation to related objects.

---

# Related Objects

Every object is connected.

Example

```
Quote

↓

System

↓

Components

↓

Vendor

↓

Other Quotes

↓

Similar Systems
```

Users should navigate through relationships rather than repeatedly searching.

---

# Saved Views

The application provides predefined views into the catalog.

Examples

- Needs Review
- Recently Imported
- Components
- Systems
- Vendors
- GPU Systems
- High Memory Systems
- Ceph Systems
- AI Systems

Saved views are simply predefined searches with filters.

Users may also save their own searches.

---

# Duplicate Detection

Search identifies possible duplicates.

Examples

- Duplicate Quotes
- Similar Systems
- Similar Components

Possible duplicates are highlighted within search results.

---

# Search Ranking

Results are ranked by relevance.

Ranking considers:

- Exact matches
- Alias matches
- Component matches
- System matches
- Recently imported records
- User activity

---

# Future

Future capabilities include:

- Semantic search
- Similar system recommendations
- Procurement analytics
- Price trend visualization
- Component popularity
- Vendor comparison
- AI-assisted search
- Hardware recommendation engine

Outside the scope of Phase 1.