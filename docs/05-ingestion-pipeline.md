# Ingestion Pipeline

## Purpose

The Ingestion Pipeline defines how information flows from an uploaded vendor document into the Commercial Catalog.

Each stage has a single responsibility.

The output of one stage becomes the input of the next.

No data is committed to the Commercial Catalog until the review process has been completed and the quote has been approved.

---

# Pipeline Overview

```
Upload Document
        │
        ▼
Store Original Document
        │
        ▼
Extract Text
        │
        ▼
Generate Canonical JSON
        │
        ▼
Validate
        │
        ▼
Resolve Components
        │
        ▼
Resolve Systems
        │
        ▼
Review Queue
        │
        ▼
User Approval
        │
        ▼
Persist to Commercial Catalog
```

---

# Stage 1 — Upload

## Purpose

Receive one or more vendor documents.

Supported document types:

- PDF
- DOCX
- XLSX
- EML
- MSG

### Output

A stored document with a unique Document ID.

Example

```
DOC-000142
```

No parsing occurs during this stage.

---

# Stage 2 — Store Original Document

## Purpose

Preserve the uploaded document exactly as received.

The original document is immutable.

It is retained for:

- audit purposes
- future reprocessing
- comparison with extracted data

No modifications are ever made to the original document.

---

# Stage 3 — Extract Text

## Purpose

Convert the document into machine-readable text.

Examples

```
PDF
    ↓
Extract Text
```

or

```
Scanned PDF
    ↓
OCR
    ↓
Extract Text
```

### Output

Raw extracted text.

At the end of this stage every document has a text representation.

---

# Stage 4 — Generate Canonical JSON

## Purpose

Convert extracted text into a structured representation.

The LLM is used only during this stage.

### Input

Raw text.

### Output

Canonical JSON representing:

- quote
- quote items
- hardware configuration
- pricing
- metadata

Nothing is written to the database.

The Canonical JSON is only a proposal.

---

# Stage 5 — Validate

## Purpose

Perform deterministic validation.

Examples

- Vendor exists
- Currency exists
- Unit price present
- Quantity greater than zero
- CPU count valid
- Memory capacity valid

Validation is performed entirely by application logic.

No AI is used.

Validation produces:

- Errors
- Warnings
- Informational messages

---

# Stage 6 — Resolve Components

## Purpose

Match extracted hardware against the Component Library.

Example

```
Intel Xeon Gold 6530

↓

CPU-000481
```

Matching order

1. Manufacturer part number
2. Exact model
3. Known alias
4. Normalized text
5. Hermes recommendation

If no match exists:

Create a Component Candidate.

Nothing is added to the Component Library automatically.

---

# Stage 7 — Resolve Systems

## Purpose

Determine whether the complete hardware configuration already exists.

Matching order

1. Exact system fingerprint
2. Exact component match
3. Similar system
4. Hermes recommendation

If no match exists:

Create a System Candidate.

Nothing is added to the System Library automatically.

---

# Stage 8 — Review Queue

## Purpose

Present unresolved items to the user.

Examples

- Unknown components
- Unknown systems
- Validation issues
- Duplicate quotes
- Low confidence matches

The goal is to minimize manual work.

Users review decisions rather than entering data.

---

# Stage 9 — User Approval

## Purpose

Finalize the import.

The user may:

- approve
- correct
- reject

Only approved data becomes part of the Commercial Catalog.

---

# Stage 10 — Persist

## Purpose

Store approved information.

The following objects may be created or updated:

- Quote
- Quote Revision
- Quote Items
- Component Library
- System Library
- Vendor Aliases
- Hermes Memory

The original uploaded document is never modified.

---

# Error Handling

Pipeline failures stop at the current stage.

Examples

Document upload failure

↓

Stop

Invalid PDF

↓

Stop

Validation error

↓

Send to Review Queue

Unknown component

↓

Create Component Candidate

Unknown system

↓

Create System Candidate

Errors should never corrupt the Commercial Catalog.

---

# Design Principles

- One responsibility per stage.
- Original documents are immutable.
- Canonical JSON is temporary.
- Validation is deterministic.
- Hermes provides recommendations, not decisions.
- Users approve catalog changes.
- The Commercial Catalog is the system of record.
- Hermes Memory learns only from approved decisions.

---

# Future

Possible future enhancements include:

- Bulk imports
- Email mailbox monitoring
- Vendor portal integration
- OCR optimization
- Automatic approval for high-confidence imports
- Parallel extraction pipelines
- Background reprocessing of historical documents

Outside the scope of Phase 1.