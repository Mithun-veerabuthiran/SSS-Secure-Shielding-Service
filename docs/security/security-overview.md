# SSS Security & Privacy Model Overview

## Core Security Principles

SSS (Secure Shielding Service) is engineered around a **Zero-Trust Client-Side Privacy Model** designed to prevent accidental leakage of sensitive identifiers to external AI services.

### 1. Zero Third-Party Exposure
- Sensitive prompt data is processed and sanitized locally before any outgoing request leaves the browser interface.
- Original raw prompt content is never transmitted to cloud AI endpoints.

### 2. Symmetric Cryptographic Protection
- Reversible pseudonym mappings are encrypted using **AES-256 Fernet symmetric key encryption**.
- Master encryption keys (`SECRET.key`) are generated locally on host initialization and never checked into source control or transmitted externally.

### 3. Automatic Data Lifecycle Hygiene
- Encrypted mapping data stored in local databases (`mappings.db`) is bound by strict retention policies.
- Background worker threads periodically clean and purge expired mapping keys older than 24 hours.

### 4. Reversible In-Browser De-Anonymization
- Response restoration occurs strictly within the local client DOM environment using encrypted session keys.
- AI service providers only retain the anonymized/pseudonymized version of prompt histories.

## Security Architecture

```text
+-----------------------+     1. Raw Prompt     +-----------------------+
|  User Browser DOM     | --------------------> |  Local SSS Backend    |
|  (ChatGPT Web interface)                      |  (Flask + Presidio/   |
+-----------------------+                       |   RoBERTa Engine)     |
            ^                                   +-----------------------+
            |                                               |
            | 4. Local DOM                                  | 2. Encrypt Mappings
            |    De-anonymization                           v    (Fernet AES-256)
            |                                   +-----------------------+
            | 3. Transformed                    |  Local Encrypted      |
            |    Prompt Sent                    |  Database Storage     |
            v                                   +-----------------------+
+-----------------------+
|  External AI Service  |
|  (OpenAI / Claude)    |
+-----------------------+
```

## Responsible Disclosure & Compliance

For security inquiries, vulnerability reports, or architectural assessments, please refer to the primary project documentation or reach out to the project maintainers.
