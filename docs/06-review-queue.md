# Review Queue

## Purpose

The Review Queue presents newly imported quotes that require user action before becoming part of the catalog.

The goal is to minimize manual work.

Users should only review information that could not be resolved automatically.

---

## Workflow

Uploaded

↓

Extracted

↓

Validated

↓

Matched

↓

Needs Review

↓

Approved

---

## Review Philosophy

The user is not expected to enter hardware manually.

The system extracts, validates and matches data automatically.

The user's job is to approve or correct uncertain information.

---

## Queue

The queue displays one row per quote.

Columns

- Status
- Vendor
- Quote Number
- Date
- Systems
- Issues
- Confidence
- Assigned To
- Last Updated

---

## Opening a Quote

Opening a quote displays

- Original document
- Extracted information
- Validation issues
- Component matches
- System matches

The original document is always visible.

---

## Approval

A quote cannot be approved while blocking issues exist.

Warnings may be approved.

Errors must be resolved.

---

## Result

Approving a quote

- stores the quote
- updates the component library
- updates the system library

The original document remains unchanged.