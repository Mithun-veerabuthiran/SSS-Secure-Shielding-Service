# SSS Secure Shielding Service

> Privacy-first protection for sensitive information in AI interactions.

## Overview

SSS (Secure Shielding Service) is a privacy-focused system designed to reduce accidental exposure of personally identifiable information (PII) when users interact with AI services.

The system detects sensitive information in prompts and applies privacy-preserving transformations before the information reaches the AI service.

## Problem

AI assistants may receive sensitive information such as:

- Names
- Email addresses
- Phone numbers
- Addresses
- Identification numbers
- Organization information
- Other personally identifiable information

## Solution

SSS provides a privacy layer between the user and supported AI interactions.

```text
User Prompt
    ↓
Privacy Detection
    ↓
Anonymization / Redaction
    ↓
AI Service
    ↓
Protected Response
    ↓
Controlled Restoration
```

## Key Features

- Real-time PII detection
- Anonymization
- Pseudonymization
- Redaction
- Privacy-preserving AI interaction
- Encrypted mapping storage
- Browser-based workflow
- Machine-learning-assisted entity detection
- Privacy-focused processing pipeline

## Architecture

Please refer to the detailed [Architecture Documentation](docs/architecture/architecture.md) for system design, component breakdown, and sequence flow diagrams.

## Technology Stack

- Python
- Flask
- Chrome Extension (Manifest V3)
- Microsoft Presidio
- RoBERTa
- SQLite
- Docker
- Fernet encryption

## Privacy Model

SSS utilizes a zero-trust, client-side privacy architecture. Sensitive values are detected and transformed locally before prompts are sent to external AI platform servers. Reverse mappings are stored with AES-256 Fernet symmetric encryption and automatically purged after a 24-hour retention window. For full details, see the [Security Overview](docs/security/security-overview.md).

## Evaluation

Quantitative evaluation demonstrates high precision across PII categories and minimal end-to-end processing latency. Detailed benchmarking results, methodology, and performance charts are available in [Evaluation Results](docs/evaluation/results.md) and [Screenshots](docs/screenshots/screenshots.md).

## Screenshots

Architectural diagrams and benchmark metric charts can be viewed in the [Screenshots Overview](docs/screenshots/screenshots.md).

## Demo

Walkthrough guides and demonstration step breakdowns are documented in the [Demo Overview](demo/demo.md).

## Security

Security-related implementation details are intentionally not published in the public repository. High-level security principles are outlined in the [Security Overview](docs/security/security-overview.md).

## Source Code

The full implementation is maintained in a private repository.

Access may be provided to authorized reviewers, collaborators, recruiters, or evaluators when appropriate.

## License

This documentation and portfolio showcase is provided under the [Apache License 2.0](LICENSE).
