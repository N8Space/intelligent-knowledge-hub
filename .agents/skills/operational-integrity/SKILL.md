---
name: operational-integrity
description: Enforces operational integrity across development workflows. Strictly prohibits mocking, faking, or simulating external dependencies in application code. Requires reporting ground truth on all health probes and directly guiding real credential setup.
---

# Operational Integrity & Genuine Infrastructure Integration

## Core Directive
Under no circumstances should any agent, script, or application code implement workarounds that fake an outcome, simulate cloud connectivity, or mock external service responses in production application files.

## Workflow Rules

### 1. Zero Tolerance for Faked Outcomes in Application Code
- **Never simulate dependencies**: Do not introduce in-memory mock datasets, fake query responders, or bypass flags into `main.py`, `app.js`, or other runtime application components.
- **Mocks belong only in tests**: Legitimate unit test mocks are strictly confined to `tests/`.

### 2. Truthful Health & Readiness Probes
- All probes (`/health/ready`, `/health/live`) must test actual connectivity to downstream services (e.g., Azure AI Search, Azure OpenAI).
- If downstream services are unauthenticated or failing:
  - Return HTTP 503 Service Unavailable.
  - Return the actual error message from the cloud provider in the diagnostic payload.
  - Display the truthful degraded status in the frontend UI (e.g., "Downstream Degraded").
  - NEVER convert a failure into a false success to cosmetically satisfy a status badge.

### 3. Direct Real Configuration First
- When an external service cannot authenticate in the local environment:
  - Immediately identify the missing credentials or configuration (e.g., `AZURE_OPENAI_API_KEY`, `AZURE_SEARCH_API_KEY`).
  - Instruct the user directly and transparently on how to populate the required values in `.env`.
  - Assist the user in verifying genuine connectivity once the real keys are configured.
