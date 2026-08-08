# SSS Architecture & System Design

## Overview

SSS (Secure Shielding Service) is designed as a privacy-focused intermediary layer between end users and external web-based AI services (e.g., ChatGPT Web). The system intercepts prompt inputs in real time, identifies sensitive personally identifiable information (PII) using a hybrid detection engine, applies privacy-preserving transformations, and safely renders AI responses in the user interface.

## System Topology

```mermaid
flowchart TD
    User([User Prompt Input]) --> Ext[Chrome Extension MV3]
    Ext -->|POST /anonymize| Backend[Flask Privacy Backend]
    
    subgraph Privacy Engine
        Backend --> Presidio[Microsoft Presidio Engine]
        Backend --> RoBERTa[RoBERTa NER Transformer]
        Backend --> CustomRules[Custom Regex Recognizers]
    end

    Privacy Engine --> Shielding[Transformation Engine]
    Shielding -->|Pseudonymize / Redact| TransformedPrompt[Shielded Prompt]
    Shielding -->|Store Fernet-Encrypted Mappings| DB[(SQLite Encrypted Storage)]

    TransformedPrompt -->|Submitted safely| AIService[External AI Platform]
    AIService -->|AI Response Payload| Ext

    Ext -->|GET /get_mappings| Backend
    Backend -->|Fetch & Decrypt Mappings| Ext
    Ext -->|Client-side DOM De-anonymization| UserView([Rendered User View])
```

## Core Components

### 1. Browser Extension Layer (Manifest V3)
- **Prompt Interception**: Captures text inputs within supported web interfaces.
- **In-Page Action Trigger**: Injects non-intrusive action controls into target AI input forms.
- **DOM De-anonymization**: Restores anonymized terms locally in the rendered response stream without sending sensitive raw data back to external endpoints.

### 2. Backend Privacy Server
- **Hybrid PII Detection**: Combines statistical pattern matching (Presidio), custom recognizers (Aadhaar, SSN, financial IDs, URLs), and deep-learning named entity recognition (RoBERTa).
- **Transformation Pipeline**: Offers two operational modes:
  - **Pseudonymization**: Replaces entities with realistic synthetic equivalents via Faker while retaining structural context.
  - **Redaction**: Replaces entities with deterministic `[REDACTED_<ENTITY>_<INDEX>]` placeholders.
- **Encryption & Key Management**: Encrypts mapping metadata using AES-256 Fernet symmetric keys generated per local instance.

### 3. Data Retention & Storage
- **Isolated SQLite Storage**: Maintains session-bound reverse mapping tables in local encrypted storage.
- **Automatic Retention Purging**: Background cleanup routines automatically expire and erase cached mapping keys after 24 hours.
