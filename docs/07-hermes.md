# 07-hermes.md

# Hermes

## Purpose

Hermes is an AI-powered knowledge service that continuously improves the quality of the Commercial Catalog.

Hermes does **not** replace the application, database, or business logic.

Its role is to learn from every imported quote and every user review so that future imports require less manual work and produce better results.

The Commercial Catalog remains the system of record.

Hermes is the system of knowledge.

---

# Design Principles

- The database stores facts.
- Hermes stores knowledge.
- The application enforces business rules.
- Users approve all catalog changes.
- Hermes never modifies the catalog directly.
- Every recommendation should be explainable.

---

# Internal Architecture

Hermes consists of two independent services.

```
                    Hermes

           ┌─────────┴─────────┐

           │                   │

           ▼                   ▼

   Hermes Reasoning      Hermes Memory
```

This separation allows the knowledge accumulated over time to remain independent of any specific AI model.

Reasoning engines may change.

The accumulated knowledge should not.

---

# Hermes Memory

## Purpose

Hermes Memory is the long-term knowledge base.

It stores everything the system has learned from approved quotes and user decisions.

Hermes Memory is persistent.

It is not tied to any particular LLM.

### Responsibilities

- Hardware aliases
- Vendor terminology
- Vendor document patterns
- Component mappings
- System mappings
- Decision history
- Review history
- Confidence history
- Organizational knowledge

Hermes Memory never performs reasoning.

It answers questions such as:

- Have we seen this before?
- What did we decide last time?
- Why was that decision made?

---

# Hermes Reasoning

## Purpose

Hermes Reasoning analyzes the current quote and produces recommendations.

It consumes:

- Canonical JSON
- Validation results
- Hermes Memory
- Commercial Catalog

It produces:

- Component suggestions
- System suggestions
- Duplicate detection
- Confidence scores
- Explanations

Hermes Reasoning is stateless.

It does not permanently store information.

---

# Responsibilities

Hermes is responsible for:

- Learning hardware aliases
- Learning vendor terminology
- Learning document patterns
- Improving component matching
- Improving system matching
- Detecting duplicate quotes
- Detecting duplicate systems
- Remembering user decisions
- Explaining recommendations

Hermes is **not** responsible for:

- OCR
- PDF parsing
- Business rules
- Pricing
- Product creation
- Quote generation
- Updating the database

---

# Architecture

```
Vendor Quote

        │

        ▼

Document Extraction

        │

        ▼

Canonical JSON

        │

        ▼

Validation Engine

        │

        ▼

Hermes Reasoning

        │
        ├── Query Hermes Memory
        ├── Query Commercial Catalog
        ├── Analyze Quote
        ├── Generate Recommendations
        └── Produce Confidence Scores
        │

        ▼

Review Queue

        │

        ▼

User Approval

        │

        ▼

Commercial Catalog

        │

        ▼

Hermes Memory Updated
```

Hermes participates in the ingestion pipeline by making recommendations.

The Review Queue decides what the user needs to see.

The Commercial Catalog changes only after user approval.

Hermes Memory is updated only after approved decisions.

---

# Knowledge Domains

## 1. Component Knowledge

Canonical hardware definitions.

Examples

- Intel Xeon Gold 6530
- Samsung PM9A3 3.84TB
- NVIDIA L40S
- Mellanox ConnectX-6

Hermes learns aliases for these components.

---

## 2. Vendor Knowledge

Hermes learns vendor-specific terminology and quoting conventions.

Examples

Dell

- Option codes
- iDRAC licenses
- Rail kits

Lenovo

- Option naming
- Warranty packaging

Supermicro

- Motherboard naming
- NIC descriptions

This knowledge improves future imports.

---

## 3. System Knowledge

Hermes recognizes complete hardware configurations.

Example

Dell R760

- 2 × Xeon Gold 6530
- 512 GB RAM
- 8 × 3.84TB NVMe

Future imports containing the same hardware should resolve to the same System Library entry.

---

## 4. Alias Knowledge

Hermes maintains an expanding alias dictionary.

Example

Canonical Component

Intel Xeon Gold 6530

Known aliases

- Intel Xeon Gold 6530
- Xeon Gold 6530
- Intel® Xeon® Gold 6530 Processor
- 338-CHQX

Aliases are suggestions until approved.

---

## 5. Decision Memory

Hermes remembers user decisions.

Example

Decision

338-CHQX

↓

CPU-000481

Reason

Observed in 41 approved Dell quotes.

Future recommendations include this evidence.

Decision Memory records:

- what was chosen
- why it was chosen
- confidence
- supporting evidence

Decision Memory grows over time.

---

# Learning Sources

Hermes learns only from approved data.

Learning sources include:

- Approved quote reviews
- Approved component mappings
- Approved system mappings
- Approved aliases
- User corrections

Hermes ignores:

- Unapproved imports
- Rejected suggestions
- Deleted records

---

# Recommendation Model

Every recommendation contains:

- Suggested object
- Confidence
- Reason
- Supporting evidence

Example

Suggested Component

CPU-000481

Confidence

99.6%

Reason

Dell option code 338-CHQX has been mapped to CPU-000481 in 41 approved quotes.

---

# Human Authority

Hermes is advisory.

Hermes may recommend.

Users approve.

Only approved decisions modify the Commercial Catalog.

---

# Independence from AI Models

Hermes Memory is model-agnostic.

The reasoning engine may evolve over time.

Examples include:

- GPT
- Claude
- Gemini
- Local LLMs
- Multiple reasoning engines operating simultaneously

Regardless of the reasoning engine used, Hermes Memory remains the single source of accumulated organizational knowledge.

This allows the platform to adopt new AI models without losing years of learned experience.

---

# Future Capabilities

Possible future capabilities include:

- Vendor-specific extraction strategies
- Procurement recommendations
- Hardware compatibility analysis
- Price anomaly detection
- Component lifecycle recommendations
- Suggested replacements
- Catalog consistency auditing
- Natural language catalog search
- Hardware recommendation engine

Outside the scope of Phase 1.

---

# Long-Term Vision

Over time Hermes should evolve from a matching engine into an organizational knowledge engine.

The goal is not simply to recognize hardware.

The goal is to capture and reuse the company's accumulated knowledge about:

- vendors
- hardware
- configurations
- procurement
- review decisions
- catalog evolution

Every approved quote should make the next quote easier to process.

The Commercial Catalog stores the company's data.

Hermes Memory stores the company's experience.

Hermes Reasoning applies that experience to every new quote.