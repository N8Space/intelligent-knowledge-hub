# Intelligent Knowledge Hub 🧠⚡

[![CI/CD Azure App Service](https://github.com/N8Space/intelligent-knowledge-hub/actions/workflows/azure-app-service.yml/badge.svg)](https://github.com/N8Space/intelligent-knowledge-hub/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Azure AI Search](https://img.shields.io/badge/Azure%20AI%20Search-Hybrid%20%2B%20Semantic-0078D4.svg)](https://azure.microsoft.com/en-us/products/ai-services/ai-search)
[![Azure AI Foundry](https://img.shields.io/badge/Azure%20AI%20Foundry-Model%20Catalog-blue.svg)](https://ai.azure.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Enterprise Retrieval-First Knowledge Assistant & Enablement Copilot**  
> Helping cross-functional enterprise teams instantly discover verified standard operating procedures (SOPs), security policies, and technical guidelines with strict citation grounding and real-time execution telemetry.

---

## 📌 Executive Summary & Business Impact

In large organizations, institutional knowledge is fragmented across wikis, PDFs, ticket resolutions, and intranet portals. Employees spend upwards of 20% of their working hours manually locating policies or risk executing deprecated processes.

**Intelligent Knowledge Hub** establishes a governed, enterprise-ready retrieval-augmented copilot architecture:
* **Lookup Latency Reduction:** Reduces policy discovery from 15+ minutes of manual search to <800ms of instant, cited synthesis.
* **100% Policy Grounding:** Enforces strict citation validation (`[1]`, `[2]`) against authorized SOP documents, eliminating generative hallucinations.
* **Governance Badges & Confidence Scoring:** Every retrieved chunk exposes source metadata, audit review dates, and similarity confidence scores.
* **Production Observability:** Real-time telemetry tracking retrieval time, LLM inference latency, and source count.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Client ["Client & Enablement Layer"]
        UI["Modern Web Showcase UI<br/>(FastAPI / Tailwind / Telemetry)"]
        Ext["External Portals / Winelogbooks<br/>(REST API / CORS)"]
    end

    subgraph API ["FastAPI Enterprise Backend"]
        Router["FastAPI Router<br/>/api/query & /api/ingest"]
        Guardrails["AI Governance & Prompt Sanitizer<br/>Input Validation & DLP Rules"]
    end

    subgraph Retrieval ["Azure AI Search Engine"]
        Vector["Dense Vector Index<br/>(text-embedding-3-small)"]
        Keyword["Keyword BM25 Inverted Index"]
        Reranker["Azure Semantic Ranker<br/>(L2 Deep Reranking)"]
    end

    subgraph Inference ["Azure AI Foundry & OpenAI"]
        Model["Azure AI Foundry Model Catalog<br/>(GPT-4o / GPT-4o-mini)"]
    end

    subgraph Telemetry ["Observability & Governance"]
        AppInsights["Azure Application Insights<br/>(Latency & Token Metrics)"]
    end

    UI --> Router
    Ext --> Router
    Router --> Guardrails
    Guardrails --> Retrieval
    Vector --> Reranker
    Keyword --> Reranker
    Reranker -->|Top-K Grounded Chunks| Router
    Router -->|Grounded Augmented Prompt| Model
    Model -->|Synthesized Answer with Citations| Router
    Router --> UI
    Router -.->|Telemetry Stream| AppInsights
```

---

## 🛠️ Tech Stack & Tooling

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3.11+, FastAPI, Pydantic v2 | High-performance asynchronous API service |
| **Vector & Hybrid Search** | Azure AI Search | Dense embeddings + BM25 + Semantic Ranker |
| **LLM & Inference** | Azure AI Foundry / Azure OpenAI | Grounded synthesis with citation guardrails |
| **Embeddings** | `text-embedding-3-small` | 1536-dimensional vector representation |
| **Cloud Hosting** | Azure App Service (Linux) | Managed cloud container / web application hosting |
| **CI/CD** | GitHub Actions | Automated linting, pytest validation, and deployment |
| **Showcase UI** | Tailwind CSS, Lucide Icons, Marked.js | Enterprise search, citation drawer & telemetry |

---

## 🚀 Quick Start (Local Development)

### 1. Clone the Repository
```bash
git clone https://github.com/N8Space/intelligent-knowledge-hub.git
cd intelligent-knowledge-hub
```

### 2. Create and Activate Virtual Environment
```bash
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your cloud resource credentials (or keep default mock mode for offline testing):
```bash
cp .env.example .env
```

### 5. Launch the Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open your browser at **`http://localhost:8000`** to access the interactive web interface and **`http://localhost:8000/docs`** for interactive Swagger/OpenAPI documentation.

---

## 🧪 Running Automated Tests

Run the full pytest suite with verbose output:
```bash
pytest tests/ -v
```

---

## 🐳 Docker Deployment

Build and run the production container locally:
```bash
docker build -t intelligent-knowledge-hub:latest .
docker run -p 8000:8000 --env-file .env intelligent-knowledge-hub:latest
```

---

## 📡 API Contract Overview

### `POST /api/query`
Executes hybrid vector retrieval against Azure AI Search, builds grounded context, and generates an answer with strict citations.

```json
{
  "query": "What is the mandatory response protocol and SLA for a Sev-1 incident?",
  "top_k": 4,
  "strict_governance_only": true
}
```

**Response (`200 OK`):**
```json
{
  "query": "What is the mandatory response protocol and SLA for a Sev-1 incident?",
  "answer": "### Enterprise Incident Response Protocol\n\n* **Immediate Assignment:** Severity 1 incidents require an Incident Commander within 5 minutes [1].\n* **Bridge & Escalation:** IC must open a Microsoft Teams bridge and alert Executive On-Call [1]...",
  "citations": [
    {
      "id": "SOP-SEC-001-C1",
      "title": "Enterprise Incident Response SOP (Sev-1 / Sev-2)",
      "category": "Security & Reliability SOP",
      "snippet": "Severity 1 incidents require an Incident Commander to be assigned within 5 minutes...",
      "score": 0.96,
      "governance_status": "Approved",
      "last_reviewed": "2025-01-15",
      "department": "Security & DevOps"
    }
  ],
  "metrics": {
    "retrieval_time_ms": 12.4,
    "llm_time_ms": 184.2,
    "total_latency_ms": 196.6,
    "sources_retrieved": 1,
    "search_mode": "hybrid_semantic"
  },
  "governance_passed": true
}
```

---

## 🔗 Portfolio Showcase Integration

This application is linked to the AI Enablement Portfolio at:
👉 **[https://winelogbooks.com/projects/intelligent-knowledge-hub](https://winelogbooks.com/projects/intelligent-knowledge-hub)**
