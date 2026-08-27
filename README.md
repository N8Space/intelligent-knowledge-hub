# MemberAssist: Health Insurance Knowledge Hub 🏥⚡

[![CI/CD Azure App Service](https://github.com/N8Space/intelligent-knowledge-hub/actions/workflows/azure-app-service.yml/badge.svg)](https://github.com/N8Space/intelligent-knowledge-hub/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Azure AI Search](https://img.shields.io/badge/Azure%20AI%20Search-Hybrid%20%2B%20Semantic-0078D4.svg)](https://azure.microsoft.com/en-us/products/ai-services/ai-search)
[![Azure AI Foundry](https://img.shields.io/badge/Azure%20AI%20Foundry-Model%20Catalog-blue.svg)](https://ai.azure.com)
[![Compliance: HIPAA Ready](https://img.shields.io/badge/Compliance-HIPAA%20%2B%20No%20Surprises%20Act-emerald.svg)](https://www.hhs.gov/hipaa)

> **Enterprise AI Retrieval Assistant for Health Insurance Customer Service Representatives (CSRs) & Member Advocates**  
> Enables frontline call center agents to instantly resolve complex member inquiries regarding 2026 PPO benefit schedules, out-of-network coinsurance, prior authorization SLAs, No Surprises Act balance billing disputes, and HIPAA privacy rules with zero-hallucination policy grounding.

---

## 📌 Executive Summary & Business ROI

Health insurance call centers face high operational costs and member friction due to complex benefit schedules, changing clinical authorization policies, and strict compliance mandates:
* **Average Handle Time (AHT) Reduction:** Cuts policy lookup and verification time from 4–6 minutes down to **<700ms**, dramatically accelerating call wrap-up.
* **First Contact Resolution (FCR) Improvement:** Provides CSRs with verbatim member-facing readback scripts and step-by-step CRM workflows to resolve inquiries on the first call.
* **100% Policy Grounding:** Enforces strict citations against 2026 Plan Schedules (`PLAN-PPO-2026-BENEFITS`), Utilization Management SOPs (`SOP-UM-2026-004`), and Claims Guides (`GUIDE-CLM-2026-012`).
* **Regulatory Compliance:** Built-in validation for HIPAA 45 CFR disclosures and federal No Surprises Act (NSA) emergency/ancillary provider balance billing protections.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph CSR ["Frontline Representative Workspace"]
        UI["MemberAssist CSR Copilot UI<br/>(Call Scripts, Action Steps, Policy Cards)"]
        Filter["Call Category Filter<br/>(Benefits, Prior Auth, Claims, HIPAA)"]
    end

    subgraph API ["FastAPI Governance Backend"]
        Router["FastAPI Router<br/>/api/query & /api/ingest"]
        Guardrails["Health Compliance Guardrail<br/>Zero-PII & HIPAA Disclosure Checks"]
    end

    subgraph Search ["Azure AI Search Engine"]
        Index["Health Plan Knowledge Index<br/>(Hybrid Vector Dense + BM25)"]
        Semantic["Azure Semantic Ranker<br/>(L2 Deep Reranking)"]
    end

    subgraph LLM ["Azure AI Foundry & Model Catalog"]
        Copilot["GPT-4o-mini / Phi-4 Deployment<br/>(CSR Persona + Verbatim Scripting)"]
    end

    CSR --> Filter
    Filter --> Router
    Router --> Guardrails
    Guardrails --> Search
    Index --> Semantic
    Semantic -->|Top-K Policy Chunks| Router
    Router -->|Grounded Benefit Context| Copilot
    Copilot -->|Structured Readback Script & Actions| Router
    Router --> UI
```

---

## 📂 Health Insurance Policy Corpus (`data/policies/`)

| Document ID | Policy Title | Category | Key Regulatory Standards |
| :--- | :--- | :--- | :--- |
| `PLAN-PPO-2026-BENEFITS` | Commercial Premier & Standard PPO Schedule (2026) | Benefit Schedule | ACA Preventive ($0 Copay), Out-of-network MRI/Imaging, Rx Tiers |
| `SOP-UM-2026-004` | Prior Authorization & Clinical Appeals SOP | Prior Authorization | 72h Standard / 24h Urgent SLA, 5-Day Peer-to-Peer (P2P) Window |
| `GUIDE-CLM-2026-012` | Claims Denial Explanation & EOB Resolution Guide | Claims Operations | CO-16 Missing Records, No Surprises Act (NSA) Balance Billing Hold |
| `SOP-HIPAA-2026-001` | HIPAA Privacy Verification & Authorized Disclosures | Privacy & Compliance | 3 of 4 Identifier Check, Spouse/Dependent PHI-AUTH-01 Mandate |

---

## 🚀 Quick Start (Local Development)

### 1. Clone the Repository
```bash
git clone https://github.com/N8Space/intelligent-knowledge-hub.git
cd intelligent-knowledge-hub
```

### 2. Configure Environment & Run
```bash
# Copy environment configuration
cp .env.example .env

# Run FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open **`http://localhost:8000`** in your browser to access the CSR workspace.

---

## 📡 API Contract Overview (`POST /api/query`)

```json
{
  "query": "What is the member cost share for an out-of-network MRI under the Standard PPO plan?",
  "top_k": 3,
  "call_type": "Benefit Schedule",
  "strict_governance_only": true
}
```

---

## 🔗 Live Application & Portfolio Links

* **Live Cloud Application (Azure App Service):**  
  👉 **[https://intelligent-knowledge-hub-lesterlabs.azurewebsites.net](https://intelligent-knowledge-hub-lesterlabs.azurewebsites.net)**
* **Portfolio Showcase Case Study:**  
  👉 **[https://winelogbooks.com/projects/intelligent-knowledge-hub](https://winelogbooks.com/projects/intelligent-knowledge-hub)**
* **GitHub Repository:**  
  👉 **[https://github.com/N8Space/intelligent-knowledge-hub](https://github.com/N8Space/intelligent-knowledge-hub)**
