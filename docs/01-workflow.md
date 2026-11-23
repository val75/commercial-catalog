# Workflow

## Quote Lifecycle

Received
    ↓
Uploaded
    ↓
Text Extracted
    ↓
AI Parsed
    ↓
Needs Review
    ↓
Approved
    ↓
Published
    ↓
Archived

---

## Upload

User uploads one or more documents.

Supported:

- PDF
- DOCX
- XLSX
- EML
- MSG

---

## AI Extraction

The system extracts:

- Quote metadata
- Vendor
- Systems
- Hardware components
- Pricing

Result:

Canonical JSON

---

## Review

User reviews extracted information.

The user may:

- edit values
- accept values
- reject values

---

## Approval

Approved quotes become searchable.

Original uploaded documents are never modified.

---

## Publishing

Approved configurations may be published into the internal hardware catalog.

Publishing is optional.

---

## Archive

Old quotes remain searchable.

Archived quotes are excluded from active catalog searches.