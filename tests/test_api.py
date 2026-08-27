import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "MemberAssist" in data["app_name"]
    assert data["version"] == "2.0.0"


def test_sample_queries():
    response = client.get("/api/sample-queries")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    assert "query" in data[0]
    assert "category" in data[0]


def test_list_documents():
    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "id" in data[0]
    assert "Approved" in data[0]["governance_status"]


def test_knowledge_query_csr():
    payload = {
        "query": "What is the member's cost share for an out-of-network MRI under the Standard PPO plan?",
        "top_k": 3,
        "call_type": "Benefit Schedule",
        "strict_governance_only": True,
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["citations"]) > 0
    assert "metrics" in data
    assert data["metrics"]["total_latency_ms"] >= 0
    assert data["governance_passed"] is True
    assert data["guidance"] is not None
    assert "plain_language_script" in data["guidance"]
    assert len(data["guidance"]["action_steps"]) > 0


def test_document_ingestion():
    payload = {
        "documents": [
            {
                "id": "PLAN-DENTAL-2026",
                "title": "Comprehensive Dental Benefit Rider (2026)",
                "category": "Benefit Schedule",
                "department": "Dental Operations",
                "content": "Routine cleanings and examinations are covered twice per calendar year at 100% in-network ($0 member copay).",
                "governance_status": "Approved 2026 Policy",
                "version": "1.0",
            }
        ]
    }
    response = client.post("/api/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["indexed_documents"] == 1
    assert data["indexed_chunks"] >= 1
