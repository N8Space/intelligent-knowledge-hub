# Operational Integrity & Real Infrastructure Connections

## Mandate: Zero Faking or Mocking in Application Code

1. **No Simulated Fallbacks in Source Code**:
   - Under no circumstances should source code in `main.py`, `app.js`, or any application layer simulate, fake, mock, or bypass connections to external cloud providers (e.g. Azure OpenAI, Azure AI Search, Cloud Storage) to manufacture a false appearance of success.
   - Do not add dummy in-memory stores, hardcoded question-answering dictionaries, or fake readiness probe statuses.

2. **Probes Must Communicate Ground Truth**:
   - Readiness (`/health/ready`) and liveness (`/health/live`) probes must report actual service health. If downstream cloud resources are unauthenticated or failing, the probe must truthfully return unhealthy (HTTP 503) and the UI must communicate this reality without concealment.

3. **Prompt User for Real Credentials First**:
   - Whenever an external connection fails due to unauthenticated local environments, always directly instruct the user to configure the genuine credentials/secrets in their environment (e.g., in `.env` with `AZURE_OPENAI_API_KEY` and `AZURE_SEARCH_API_KEY`).
   - Never create workarounds that fake an outcome. Always work with the user to establish real, functional applications.

4. **Testing Separation**:
   - Mocks are only permitted inside `tests/` for unit testing. Production runtime code must always point to real services and valid configurations.
