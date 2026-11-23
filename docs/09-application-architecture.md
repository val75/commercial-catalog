# Application Architecture

## Purpose

The Commercial Catalog is implemented as a modular monolith.

The application is organized into independent modules, each with clear ownership and responsibilities.

Each business object has a single owning module.

Modules communicate through well-defined interfaces and domain events.

The architecture is designed so that modules can be extracted into independent services in the future without changing the business model.

---

# Design Principles

- Modular Monolith
- Single source of truth
- Single ownership
- High cohesion
- Low coupling
- Business logic over CRUD
- AI assists but never owns business logic
- Human approval for catalog changes

---

# High-Level Architecture

```
                    Commercial Catalog

┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Document Manager                                             │
│                                                              │
│  Ingestion Pipeline                                           │
│                                                              │
│  Quote Repository                                             │
│                                                              │
│  Review Queue                                                 │
│                                                              │
│  Search                                                       │
│                                                              │
│  Component Library                                            │
│                                                              │
│  System Library                                               │
│                                                              │
│  Hermes                                                       │
│                                                              │
│  Administration                                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

# Module Responsibilities

## Document Manager

### Purpose

Owns all imported documents.

### Responsibilities

- Upload documents
- Store original files
- Attachment management
- OCR
- Text extraction
- Document versioning

### Owns

- Documents
- Attachments

### Does Not Own

- Quotes
- Components
- Systems

---

## Ingestion Pipeline

### Purpose

Coordinates the complete ingestion process.

The pipeline orchestrates work but owns no business data.

### Responsibilities

- Pipeline execution
- Stage orchestration
- Progress tracking
- Retry management
- Error handling

### Owns

- Pipeline execution

### Does Not Own

- Documents
- Quotes
- Components
- Systems

---

## Quote Repository

### Purpose

Maintains the commercial history of all vendor quotes.

The Quote Repository is the authoritative source for vendor quotations.

### Responsibilities

- Quote lifecycle
- Quote revisions
- Quote metadata
- Quote line items
- Commercial history
- Quote relationships

### Owns

- Quotes
- Quote Revisions
- Quote Line Items

### Does Not Own

- Components
- Systems

---

## Review Queue

### Purpose

Presents unresolved issues requiring user action.

### Responsibilities

- Review workflow
- Validation issues
- Component approval
- System approval
- Quote approval

### Owns

- Review Tasks
- Review Decisions

### Does Not Own

- Matching logic
- Quote storage

---

## Search

### Purpose

Provides a unified interface for exploring the Commercial Catalog.

### Responsibilities

- Global search
- Search ranking
- Filters
- Saved views
- Related object navigation

### Owns

- Search indexes
- Search configuration

### Does Not Own

- Business data

---

## Component Library

### Purpose

Maintains canonical hardware components.

### Responsibilities

- Component lifecycle
- Alias management
- Component metadata
- Manufacturer information

### Owns

- Components
- Component Aliases

### Does Not Own

- Systems
- Quotes

---

## System Library

### Purpose

Maintains canonical hardware configurations.

### Responsibilities

- System definitions
- Installed components
- Configuration fingerprints
- Similarity detection

### Owns

- Systems
- Configuration Fingerprints

### Does Not Own

- Components
- Quotes

---

## Hermes

### Purpose

Provides organizational knowledge and recommendations.

Hermes consists of two internal services.

- Hermes Memory
- Hermes Reasoning

### Hermes Memory

Responsibilities

- Knowledge storage
- Vendor knowledge
- Alias knowledge
- Decision history
- Learning history

### Hermes Reasoning

Responsibilities

- Recommendations
- Similarity analysis
- Duplicate detection
- Confidence scoring
- Explanations

Hermes never modifies the Commercial Catalog.

---

## Administration

### Purpose

Maintains application configuration.

### Responsibilities

- Vendors
- Users
- Roles
- Permissions
- AI configuration
- Import settings
- System settings

### Owns

- Administrative data

---

# Module Relationships

```
                Document Manager
                        │
                        ▼
              Ingestion Pipeline
                        │
                        ▼
               Hermes Reasoning
                        │
                        ▼
                 Review Queue
                        │
                        ▼
               Quote Repository
                 │            │
                 ▼            ▼
      Component Library   System Library
                 │            │
                 └──────┬─────┘
                        ▼
                     Search

Hermes Memory is consulted throughout the process
and updated only after approved decisions.
```

---

# Ownership Rules

Each business object has one owner.

| Business Object | Owning Module |
|-----------------|---------------|
| Documents | Document Manager |
| Attachments | Document Manager |
| Quotes | Quote Repository |
| Quote Revisions | Quote Repository |
| Quote Line Items | Quote Repository |
| Review Tasks | Review Queue |
| Components | Component Library |
| Component Aliases | Component Library |
| Systems | System Library |
| Configuration Fingerprints | System Library |
| Knowledge | Hermes Memory |
| Users | Administration |
| Vendors | Administration |
| Search Index | Search |

Modules interact through published interfaces.

Modules never update another module's data directly.

---

# Persistence

The application uses a shared PostgreSQL database.

Module boundaries define ownership.

The physical database may be shared.

The logical model remains modular.

---

# Domain Events

Modules communicate using business events.

Examples

```
Document Uploaded

↓

Text Extracted

↓

Canonical JSON Generated

↓

Validation Completed

↓

Hermes Analysis Completed

↓

Review Created

↓

Review Approved

↓

Quote Created

↓

Components Updated

↓

Systems Updated

↓

Hermes Memory Updated

↓

Search Index Updated
```

Events describe business activities rather than technical operations.

---

# Error Handling

Operational failures are handled by the module where they occur.

Business issues are routed to the Review Queue.

Failures in one module must not corrupt the Commercial Catalog.

---

# Security

Permissions are enforced by module.

Examples

Document Manager

- Upload
- Download

Quote Repository

- View Quotes
- View Revisions

Review Queue

- Approve
- Reject

Component Library

- Create
- Edit
- Archive

System Library

- Create
- Edit
- Archive

Administration

- Configure
- Manage Users

---

# Extensibility

Future modules may include:

- Product Catalog
- Pricing Engine
- Customer Quote Builder
- Inventory
- Procurement
- Supplier Portal
- ERP Integration
- Provisioning

These modules should integrate through published interfaces without changing ownership of existing modules.

---

# Technology Direction

Suggested implementation

Frontend

- React

Backend

- FastAPI

Database

- PostgreSQL

Object Storage

- S3-compatible object storage

AI

- Hermes Memory
- Hermes Reasoning
- External and/or local LLMs

Deployment

- Docker

Optional

- Kubernetes

Technology choices may change without affecting module boundaries.

---

# Long-Term Vision

The Commercial Catalog is the foundation of a broader Commercial Hardware Intelligence Platform.

The first capability is vendor quote ingestion and cataloging.

Future capabilities—including productization, pricing, procurement analytics, inventory management, and customer quote generation—will build upon the same catalog and reuse the same architectural principles.

Every module has a clear owner.

Every business object has a single source of truth.

Every approved quote increases the intelligence of the platform through Hermes Memory.