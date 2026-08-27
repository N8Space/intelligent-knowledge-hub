# Enterprise AI Governance: Generative AI & Copilot Deployment Guardrails
**Document ID:** `SOP-AI-004`  
**Classification:** Enterprise Internal / Approved  
**Version:** 2.0  
**Owner:** AI Enablement & Center of Excellence (CoE)  
**Last Audit Date:** 2025-02-01  

---

### 1. Mandatory Grounding & Architecture Standards
* **Retrieval-Augmented Generation (RAG):** Production copilots must use approved vector/hybrid search indexes (e.g., Azure AI Search) to ground responses. Unconstrained LLM generation is prohibited for enterprise decision-making.
* **Citation Grounding:** Responses must explicitly cite source documents and section markers to allow auditability.
* **Hallucination Refusal:** Models must be prompted to explicitly refuse to generate assertions when context is missing.

---

### 2. Safety & Security Guardrails
* **Prompt Injection & Content Safety:** Inbound user prompts must pass through Azure AI Content Safety filters for hate, jailbreak, sexual, and violence detection.
* **PII & Data Masking:** Data loss prevention (DLP) filters governed by Microsoft Entra ID must sanitize names, emails, API keys, and financial credentials before payloads reach model inference endpoints.
* **Telemetry & Cost Tracking:** All inference requests must log token consumption, latency, and retrieval quality scores to Azure Application Insights.
