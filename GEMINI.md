# Engineering Principles & Operational Integrity

## Zero-Tolerance for Faked Outcomes & Mocked External Services

1. **Never Fake, Mock, or Simulate External Dependencies in Application Code**:
   - Under no circumstances should application code, endpoints, or client-side scripts be written to simulate, fake, mock, or circumvent real cloud services, databases, or model connections (e.g., Azure AI Search, Azure OpenAI, GCP, AWS) to manufacture a false appearance of a working, "healthy", or "ready" state.
   - Do not implement in-memory dummy stores, fake retrieval dictionaries, hardcoded answer fallbacks, or artificial green-status bypasses in application runtime files (`main.py`, `app.js`, etc.).

2. **Probes Must Communicate 100% Operational Ground Truth**:
   - Readiness (`/health/ready`), liveness (`/health/live`), and diagnostic probes must report actual service health truthfully and transparently.
   - If downstream services (such as Azure AI Search or Azure OpenAI) are unauthenticated, unreachable, or returning errors, the probe must return HTTP 503 and report the exact downstream failure without concealment or mitigation through fakes.
   - UI status pills, badges, and diagnostic panels must accurately display the degraded state (e.g., "Downstream Degraded") until authentic connectivity is established.

3. **Direct Real Configuration First**:
   - If an external dependency or service cannot connect due to missing local credentials, tokens, or environment variables (e.g., `AZURE_OPENAI_API_KEY` or `AZURE_SEARCH_API_KEY`), immediately and directly instruct the user on how to configure the real credentials (such as in `.env`).
   - Never attempt a workaround that fakes an outcome. Real functional software requires real credentials and genuine connections.

4. **Production-Grade Architecture & Testing Boundary**:
   - Legitimate mocks are strictly restricted to the `tests/` directory for isolated, deterministic unit testing.
   - Application code must always execute against genuine client libraries and actual cloud resources.

5. **Collaborative Development & Mutual Accountability**:
   - Always partner transparently with the user to solve root-cause infrastructure, security, and configuration requirements.
   - Clearly communicate what is needed to achieve genuine live integration.
