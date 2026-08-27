import time
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from app.config import settings
from app.models.schemas import (
    QueryRequest,
    QueryResponse,
    QueryMetrics,
    IngestRequest,
    IngestResponse,
    HealthResponse,
)
from app.services.search_service import search_service, MOCK_KNOWLEDGE_STORE
from app.services.llm_service import llm_service

logger = logging.getLogger("intelligent_knowledge_hub.api")
router = APIRouter(prefix="/api", tags=["Enterprise Knowledge Hub API"])


@router.get("/health", response_model=HealthResponse, summary="App Service Health Check Probe")
async def health_check() -> HealthResponse:
    """
    Standard Azure App Service health probe verifying service status,
    Azure AI Search connectivity, and Azure OpenAI / Foundry model integration.
    """
    search_conn = search_service.is_connected()
    openai_conn = llm_service.is_connected()
    mock_mode = not (search_conn and openai_conn)

    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version="1.0.0",
        environment=settings.APP_ENV,
        azure_search_connected=search_conn,
        azure_openai_connected=openai_conn,
        mock_mode_active=mock_mode,
    )


@router.post("/query", response_model=QueryResponse, summary="Knowledge Retrieval & Grounded Synthesis")
async def query_knowledge_hub(request: QueryRequest) -> QueryResponse:
    """
    Retrieves governance-approved SOPs and knowledge chunks via Azure AI Search (Hybrid Vector + Semantic Ranker),
    constructs the grounded context prompt, and synthesizes an authoritative answer with exact source citations.
    """
    overall_start = time.time()
    try:
        # Step 1: Search & Retrieval
        citations, retrieval_ms, search_mode = await search_service.search(
            query=request.query,
            top_k=request.top_k,
            department=request.filter_department,
            strict_governance_only=request.strict_governance_only,
        )

        # Step 2: Grounded LLM Synthesis
        answer, llm_ms = await llm_service.generate_response(
            query=request.query,
            citations=citations,
        )

        total_latency_ms = round((time.time() - overall_start) * 1000, 2)

        metrics = QueryMetrics(
            retrieval_time_ms=retrieval_ms,
            llm_time_ms=llm_ms,
            total_latency_ms=total_latency_ms,
            sources_retrieved=len(citations),
            search_mode=search_mode,
        )

        return QueryResponse(
            query=request.query,
            answer=answer,
            citations=citations,
            metrics=metrics,
            governance_passed=True,
        )
    except Exception as e:
        logger.error(f"Error processing query request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process knowledge query: {str(e)}",
        )


@router.post("/ingest", response_model=IngestResponse, summary="Ingest & Vectorize SOP Documents")
async def ingest_documents(request: IngestRequest) -> IngestResponse:
    """
    Administrative ingestion endpoint to chunk, vectorize, and index enterprise SOPs into Azure AI Search.
    """
    try:
        doc_count, chunk_count = await search_service.ingest_documents(request.documents)
        return IngestResponse(
            status="success",
            indexed_documents=doc_count,
            indexed_chunks=chunk_count,
            message=f"Successfully indexed {doc_count} enterprise documents across {chunk_count} vector chunks.",
        )
    except Exception as e:
        logger.error(f"Ingestion failure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {str(e)}",
        )


@router.get("/sample-queries", summary="Pre-configured enterprise demonstration queries")
async def get_sample_queries() -> List[Dict[str, str]]:
    """
    Curated prompts for portfolio showcases demonstrating compliance, security, and enablement workflows.
    """
    return [
        {
            "category": "Security & Incident Response",
            "query": "What is the mandatory response protocol and SLA timeline for a Sev-1 production outage?",
            "icon": "shield-alert",
        },
        {
            "category": "AI Governance & Architecture",
            "query": "What guardrails and content safety rules are required before deploying an LLM to Azure?",
            "icon": "cpu",
        },
        {
            "category": "Platform & DevOps",
            "query": "What are the CI/CD pipeline and Infrastructure as Code (IaC) standards for Azure deployments?",
            "icon": "git-merge",
        },
        {
            "category": "Data Access & RBAC",
            "query": "How is access control and Key Vault credential rotation enforced for production data?",
            "icon": "lock",
        },
    ]


@router.get("/documents", summary="List indexed knowledge base documents")
async def list_indexed_documents() -> List[Dict[str, Any]]:
    """
    Returns the metadata of all currently indexed SOPs and policies.
    """
    return [
        {
            "id": doc["id"],
            "title": doc["title"],
            "category": doc["category"],
            "department": doc["department"],
            "governance_status": doc["governance_status"],
            "last_reviewed": doc["last_reviewed"],
        }
        for doc in MOCK_KNOWLEDGE_STORE
    ]
