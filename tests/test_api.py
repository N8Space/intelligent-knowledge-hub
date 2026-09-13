"""
Unit and Integration Tests for Intelligent Knowledge Hub FastAPI API.
Tests cover health probes, RAG hybrid search pipeline, feedback flywheel, and dataset generation.
"""

import os
import sys
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# Ensure root workspace directory is in python module path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app

client = TestClient(app)


def test_liveness_probe():
    """Verify GET /health/live returns 200 OK and healthy status."""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "intelligent-knowledge-hub"
    assert "version" in data
    assert "timestamp" in data


def test_readiness_probe_healthy():
    """Verify GET /health/ready returns 200 OK when Azure services are accessible."""
    mock_search_client = MagicMock()
    mock_search_client.get_document_count.return_value = 39

    mock_openai_client = MagicMock()
    mock_embed_res = MagicMock()
    mock_embed_res.data = [MagicMock(embedding=[0.1] * 1536)]
    mock_openai_client.embeddings.create.return_value = mock_embed_res

    with (
        patch("main.get_search_client", return_value=mock_search_client),
        patch("main.get_openai_client", return_value=mock_openai_client),
    ):
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "healthy" in data["services"]["azure_search"]
        assert "healthy" in data["services"]["azure_openai"]
        assert data["index_name"] == "kb-index"


def test_readiness_probe_service_failure():
    """Verify GET /health/ready returns 503 when downstream service fails."""
    mock_search_client = MagicMock()
    mock_search_client.get_document_count.side_effect = Exception("Connection timeout to Search Hub")

    with patch("main.get_search_client", return_value=mock_search_client):
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "failed" in data["services"]["azure_search"].lower()


def test_query_validation_error():
    """Verify POST /query returns 422 for empty or invalid payload."""
    response = client.post("/query", json={"question": "", "top_k": 3})
    assert response.status_code == 422

    response = client.post("/query", json={"top_k": 3})
    assert response.status_code == 422


def test_query_rag_success():
    """Verify POST /query executes embedding, hybrid search, chat completion and returns metrics."""
    mock_openai_client = MagicMock()

    # Mock Embedding
    mock_embed_res = MagicMock()
    mock_embed_res.data = [MagicMock(embedding=[0.05] * 1536)]
    mock_embed_res.usage = MagicMock(total_tokens=12)
    mock_openai_client.embeddings.create.return_value = mock_embed_res

    # Mock Chat Completion
    mock_chat_res = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "The Intelligent Knowledge Hub leverages Zero-Trust Entra ID auth with Hybrid Search."
    mock_chat_res.choices = [mock_choice]
    mock_chat_res.usage = MagicMock(prompt_tokens=250, completion_tokens=45, total_tokens=295)
    mock_openai_client.chat.completions.create.return_value = mock_chat_res

    # Mock Azure Search Client
    mock_search_client = MagicMock()
    mock_search_client.search.return_value = [
        {
            "id": "arch_doc_1",
            "title": "Architecture Overview.pdf",
            "content": "Zero-trust authentication is achieved via DefaultAzureCredential.",
            "@search.score": 0.0333,
        },
        {
            "id": "sec_doc_2",
            "title": "Security Model.pdf",
            "content": "RBAC roles are assigned directly to the App Service Managed Identity.",
            "@search.score": 0.0285,
        },
    ]

    with (
        patch("main.get_openai_client", return_value=mock_openai_client),
        patch("main.get_search_client", return_value=mock_search_client),
    ):
        payload = {"question": "How does the architecture achieve zero-trust security?", "top_k": 3}
        response = client.post("/query", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "Zero-Trust" in data["answer"]
        assert len(data["citations"]) == 2
        assert data["citations"][0]["title"] == "Architecture Overview.pdf"
        assert data["citations"][0]["chunk_id"] == "arch_doc_1"
        assert len(data["context"]) == 2
        assert data["context"][0]["id"] == "arch_doc_1"

        # Verify Telemetry & FinOps Metrics
        metrics = data["metrics"]
        assert metrics["retrieval_latency_ms"] >= 0
        assert metrics["llm_latency_ms"] >= 0
        assert metrics["total_latency_ms"] >= 0
        assert metrics["prompt_tokens"] == 250
        assert metrics["completion_tokens"] == 45
        assert metrics["total_tokens"] == 295
        assert metrics["estimated_cost_usd"] > 0
        assert "$" in metrics["formatted_cost"]


def test_feedback_flywheel_positive(tmp_path, monkeypatch):
    """Verify POST /feedback routes positive ratings to golden_eval_set.jsonl."""
    fb_file = tmp_path / "feedback_dataset.jsonl"
    golden_file = tmp_path / "golden_eval_set.jsonl"
    dpo_file = tmp_path / "dpo_tuning_set.jsonl"

    monkeypatch.setattr("main.FEEDBACK_FILE", str(fb_file))
    monkeypatch.setattr("main.GOLDEN_EVAL_FILE", str(golden_file))
    monkeypatch.setattr("main.DPO_TUNING_FILE", str(dpo_file))

    payload = {
        "query": "What is the token cost of text-embedding-3-small?",
        "response": "text-embedding-3-small costs $0.00002 per 1,000 tokens.",
        "citations": [{"title": "Token Economics.pdf", "chunk_id": "econ_1"}],
        "retrieved_context": [{"id": "econ_1", "title": "Token Economics.pdf", "content": "Sample content"}],
        "rating": "like",
        "reason": None,
        "user_correction": None,
    }

    response = client.post("/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "feedback_id" in data

    # Verify written files
    assert fb_file.exists()
    assert golden_file.exists()
    assert not dpo_file.exists()

    # Verify stats
    stats_res = client.get("/feedback/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_feedback"] == 1
    assert stats["positive_count"] == 1
    assert stats["negative_count"] == 0
    assert stats["golden_eval_count"] == 1
    assert stats["dpo_pairs_count"] == 0
    assert stats["satisfaction_rate_pct"] == 100.0


def test_feedback_flywheel_negative_with_correction(tmp_path, monkeypatch):
    """Verify POST /feedback routes negative ratings & corrections to dpo_tuning_set.jsonl."""
    fb_file = tmp_path / "feedback_dataset.jsonl"
    golden_file = tmp_path / "golden_eval_set.jsonl"
    dpo_file = tmp_path / "dpo_tuning_set.jsonl"

    monkeypatch.setattr("main.FEEDBACK_FILE", str(fb_file))
    monkeypatch.setattr("main.GOLDEN_EVAL_FILE", str(golden_file))
    monkeypatch.setattr("main.DPO_TUNING_FILE", str(dpo_file))

    payload = {
        "query": "What is the chat model deployed?",
        "response": "The model is gpt-3.5-turbo.",
        "citations": [],
        "retrieved_context": [],
        "rating": "dislike",
        "reason": "Inaccurate Fact",
        "user_correction": "The chat model deployed is gpt-5.4-mini on Azure OpenAI.",
    }

    response = client.post("/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify DPO tuning set was created
    assert fb_file.exists()
    assert dpo_file.exists()
    assert not golden_file.exists()

    stats_res = client.get("/feedback/stats")
    stats = stats_res.json()
    assert stats["total_feedback"] == 1
    assert stats["negative_count"] == 1
    assert stats["human_corrected_count"] == 1
    assert stats["dpo_pairs_count"] == 1
    assert stats["satisfaction_rate_pct"] == 0.0


def test_serve_ui_root():
    """Verify GET / returns 200 and loads static index.html."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Intelligent Knowledge Hub" in response.text


def test_prompt_rag_success():
    """Verify POST /prompt executes with multi-turn history and returns conversational response."""
    mock_openai_client = MagicMock()
    mock_embed_res = MagicMock()
    mock_embed_res.data = [MagicMock(embedding=[0.05] * 1536)]
    mock_embed_res.usage = MagicMock(total_tokens=10)
    mock_openai_client.embeddings.create.return_value = mock_embed_res

    mock_chat_res = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Under SOP-101, verify the caller by asking for full name, DOB, and member ID."
    mock_chat_res.choices = [mock_choice]
    mock_chat_res.usage = MagicMock(prompt_tokens=200, completion_tokens=35, total_tokens=235)
    mock_openai_client.chat.completions.create.return_value = mock_chat_res

    mock_search_client = MagicMock()
    mock_search_client.search.return_value = [
        {
            "id": "sop_101_chunk_1",
            "title": "sop-101_caller_verification.pdf",
            "content": "Verify member identity using 3-point demographic verification.",
            "@search.score": 0.033,
        }
    ]

    with (
        patch("main.get_search_client", return_value=mock_search_client),
        patch("main.get_openai_client", return_value=mock_openai_client),
    ):
        payload = {
            "prompt": "How do I verify a caller before giving account details?",
            "top_k": 2,
            "history": [
                {"role": "user", "content": "Hi, I need help with verification."},
                {"role": "assistant", "content": "I'd be glad to help with caller verification."},
            ],
        }
        response = client.post("/prompt", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "SOP-101" in data["answer"]
        assert len(data["citations"]) == 1
        assert data["metrics"]["total_tokens"] == 235


def test_kpi_metrics_endpoint():
    """Verify GET /metrics/kpis returns live operational KPI metrics."""
    response = client.get("/metrics/kpis")
    assert response.status_code == 200
    data = response.json()
    assert "first_contact_resolution_pct" in data
    assert "avg_latency_ms" in data
    assert "search_time_reduction_pct" in data
    assert "zero_trust_violations" in data
    assert "auth_mode" in data
    assert "total_prompts_session" in data
