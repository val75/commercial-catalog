# Screen Flows

## Purpose

This document defines the primary user flows through the Commercial Catalog.

It focuses on user journeys rather than visual design.

Screen layouts, styling and implementation details are intentionally omitted.

---

# Navigation

The application is centered around a persistent global search bar.

```
+------------------------------------------------------------------------+
| Commercial Catalog                                     🔍 Search...    |
+------------------------------------------------------------------------+

 Review Queue   Search   Components   Systems   Vendors   Settings
```

The navigation items represent different views into the same Commercial Catalog.

There is no traditional Home page.

When users open the application:

- If review tasks exist, the application opens the **Review Queue**.
- Otherwise, the application opens **Search**.

The application should immediately present useful work rather than a dashboard.

---

# Flow 1 — Import Quote

## Goal

Import a vendor quote into the Commercial Catalog.

```
Review Queue / Search

        │

        ▼

Upload Quote

        │

        ▼

Pipeline Processing

        │

        ▼

Review Queue

        │

        ▼

Approve

        │

        ▼

Quote Repository Updated

        │

        ▼

Search
```

---

# Flow 2 — Review Queue

## Goal

Resolve outstanding review tasks.

```
Review Queue

        │

        ▼

Select Task

        │

        ▼

Review Document

        │

        ▼

Resolve Issues

        │

        ▼

Approve

        │

        ▼

Next Task
```

Possible actions

- Approve
- Reject
- Merge
- Create Component
- Create System

The Review Queue is task-oriented rather than quote-oriented.

Users resolve issues, not documents.

---

# Flow 3 — Search

## Goal

Find information in the Commercial Catalog.

```
Search

        │

        ▼

Results

        │

        ▼

Choose View

        │

        ├────────────────┬────────────────┬───────────────┐
        ▼                ▼                ▼               ▼

   Quote View      System View    Component View    Vendor View
```

Users may switch between views without performing another search.

---

# Flow 4 — Quote History

## Goal

Review historical vendor quotes.

```
Search

        │

        ▼

Quote

        │

        ▼

Revision History

        │

        ▼

Original Document
```

Possible actions

- Download PDF
- Compare Revisions
- View System
- View Components

---

# Flow 5 — Component Management

## Goal

Maintain canonical hardware components.

```
Search

        │

        ▼

Component

        │

        ▼

Aliases

        │

        ▼

Relationships

        │

        ▼

Save
```

Possible actions

- Edit
- Add Alias
- Merge Components
- Archive

---

# Flow 6 — System Management

## Goal

Maintain canonical system definitions.

```
Search

        │

        ▼

System

        │

        ▼

Configuration

        │

        ▼

Related Quotes

        │

        ▼

Save
```

Possible actions

- Edit
- Compare
- Archive

---

# Flow 7 — Vendor Management

## Goal

Maintain vendor information.

```
Search

        │

        ▼

Vendor

        │

        ▼

Vendor Details

        │

        ▼

Quotes

        │

        ▼

Systems
```

Possible actions

- Edit Vendor
- Merge Vendors
- Archive Vendor

---

# Flow 8 — Administration

## Goal

Configure the application.

```
Settings

        │

        ├────────────────┬────────────────┐
        ▼                ▼                ▼

      Users          Vendors       AI Settings

        │                │                │

        └────────────────┴────────────────┘

                         │

                         ▼

                        Save
```

---

# Flow 9 — Error Recovery

## Goal

Recover failed imports.

```
Failed Import

        │

        ▼

View Error

        │

        ▼

Retry

        │

        ▼

Pipeline

        │

        ▼

Review Queue
```

Possible actions

- Retry
- Cancel
- Download Log

---

# Overall User Journey

```
                     Application Opens

                             │

             ┌───────────────┴───────────────┐

             ▼                               ▼

     Review Tasks Exist?                No Review Tasks

             │                               │

             ▼                               ▼

       Review Queue                     Search

             │                               │

             ├───────────────┐               │

             ▼               ▼               ▼

      Import Quote      Resolve Tasks    Explore Catalog

             │               │               │

             └───────────────┴───────────────┘

                             ▼

                  Commercial Catalog Updated
```

---

# User Experience Principles

- Start with work, not a dashboard.
- Search is the primary navigation.
- The Review Queue is the primary workspace.
- Minimize manual data entry.
- Review issues rather than records.
- Preserve original documents.
- Keep related information one click away.
- Prefer approval over editing.
- Reduce clicks through intelligent defaults.
- The system should become easier to use as Hermes learns.

---

# Success Criteria

A typical workflow should allow a user to:

- Import a new quote in under one minute.
- Review an existing hardware configuration in under thirty seconds.
- Find any previously imported quote in under ten seconds.
- Locate any component in under five seconds.
- Resolve common review tasks with a single click.

The goal of the application is not to eliminate user review.

The goal is to continuously reduce review effort by combining a structured Commercial Catalog with the organizational knowledge accumulated by Hermes.