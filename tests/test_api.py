import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Intelligent Knowledge Hub" in data["app_name"]
    assert "version" in data


def test_sample_queries():
    response = client.get("/api/sample-queries")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    assert "query" in data[0]


def test_list_documents():
    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "id" in data[0]
    assert "governance_status" in data[0]


def test_knowledge_query():
    payload = {
        "query": "What is the mandatory timeline and protocol for a Sev-1 incident?",
        "top_k": 3,
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


def test_document_ingestion():
    payload = {
        "documents": [
            {
                "id": "SOP-TEST-999",
                "title": "Automated Quality Assurance Testing SOP",
                "category": "Quality Engineering",
                "department": "Engineering",
                "content": "All automated end-to-end and regression test suites must run upon pull request creation and achieve 100% pass rate before staging deployment.",
                "governance_status": "Approved",
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
