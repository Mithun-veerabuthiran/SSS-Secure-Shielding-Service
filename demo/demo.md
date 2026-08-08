# SSS Live Demonstration & Workflow Guide

## Demonstration Overview

This guide outlines how SSS (Secure Shielding Service) operates during a typical AI prompt shielding session.

## Workflow Step-by-Step

```text
Step 1: User Types Sensitive Input in AI Chat Interface
        "Hello ChatGPT, my SSN is 000-12-3456 and email is test@example.com."
                             ↓
Step 2: Extension Intercepts Submission & Sends to Local SSS Engine
                             ↓
Step 3: SSS Engine Applies Privacy Transformation (Pseudonymization / Redaction)
        - SSN -> [REDACTED_SSN_1]
        - Email -> synthetic.user@shielded-domain.org
                             ↓
Step 4: Transformed Shielded Prompt Submitted to AI Service
        "Hello ChatGPT, my SSN is [REDACTED_SSN_1] and email is synthetic.user@shielded-domain.org."
                             ↓
Step 5: AI Service Processes Shielded Prompt Safely
                             ↓
Step 6: Extension Performs In-Page Restoration for Rendered Response
        Original terms restored locally in user browser view using AES-256 session mappings.
```

## Supported Operational Modes

1. **Pseudonymization (`fake`)**: Replaces entity values with realistic synthetic data (e.g. realistic names, fake email addresses) using Faker library patterns while retaining context for LLM comprehension.
2. **Redaction (`redact`)**: Replaces entity values with deterministic tokens such as `[REDACTED_NAME_1]`, `[REDACTED_EMAIL_1]`.

## Platform Support Overview

- Current target platform: **ChatGPT Web** (`https://chatgpt.com/*`, `https://chat.openai.com/*`).
- Planned platform expansions: Claude Web, Google Gemini Web.
