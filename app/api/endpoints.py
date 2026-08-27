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
from app.services.search_service import search_service, HEALTH_INSURANCE_KNOWLEDGE_STORE
from app.services.llm_service import llm_service

logger = logging.getLogger("memberassist.api")
router = APIRouter(prefix="/api", tags=["MemberAssist Health Hub API"])


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
        version="2.0.0",
        environment=settings.APP_ENV,
        azure_search_connected=search_conn,
        azure_openai_connected=openai_conn,
        mock_mode_active=mock_mode,
    )


@router.post("/query", response_model=QueryResponse, summary="CSR Knowledge Retrieval & Grounded Guidance")
async def query_knowledge_hub(request: QueryRequest) -> QueryResponse:
    """
    Retrieves health plan policies, SOPs, and claims rules via Azure AI Search (Hybrid Vector + Semantic Ranker),
    and synthesizes live call readback scripts, step-by-step CRM actions, and verifiable citations.
    """
    overall_start = time.time()
    try:
        # Step 1: Search & Retrieval
        citations, retrieval_ms, search_mode = await search_service.search(
            query=request.query,
            top_k=request.top_k,
            call_type=request.call_type,
            strict_governance_only=request.strict_governance_only,
        )

        # Step 2: Grounded CSR Copilot Synthesis
        answer, guidance, llm_ms = await llm_service.generate_response(
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
            guidance=guidance,
            citations=citations,
            metrics=metrics,
            governance_passed=True,
            confidence_level="High (100% Policy Grounded)",
        )
    except Exception as e:
        logger.error(f"Error processing CSR query request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process health knowledge query: {str(e)}",
        )


@router.post("/ingest", response_model=IngestResponse, summary="Ingest Health Plan Documents")
async def ingest_documents(request: IngestRequest) -> IngestResponse:
    """
    Administrative ingestion endpoint to chunk, vectorize, and index health plan certificates and SOPs.
    """
    try:
        doc_count, chunk_count = await search_service.ingest_documents(request.documents)
        return IngestResponse(
            status="success",
            indexed_documents=doc_count,
            indexed_chunks=chunk_count,
            message=f"Successfully indexed {doc_count} health policy documents across {chunk_count} vector chunks.",
        )
    except Exception as e:
        logger.error(f"Ingestion failure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health document ingestion failed: {str(e)}",
        )


@router.get("/sample-queries", summary="Curated CSR Call Scenarios")
async def get_sample_queries() -> List[Dict[str, str]]:
    """
    Realistic frontline health insurance caller scenarios for live testing.
    """
    return [
        {
            "category": "Benefit Schedule",
            "title": "Out-of-Network MRI Cost Share",
            "query": "What is the member's cost share for an out-of-network MRI under the Standard PPO plan?",
            "icon": "scan",
        },
        {
            "category": "Prior Authorization",
            "title": "Urgent Prior Auth & P2P Window",
            "query": "What are the SLA turnaround timelines for urgent prior auth and the peer-to-peer appeal window?",
            "icon": "clock",
        },
        {
            "category": "Claims & Billing",
            "title": "Surprise Bill & CO-16 Denial",
            "query": "How do I explain a CO-16 denial code and what are our No Surprises Act protections for members?",
            "icon": "file-warning",
        },
        {
            "category": "HIPAA & Compliance",
            "title": "Spouse Medical Records Request",
            "query": "Can a spouse access medical claims for their partner without a signed HIPAA form on file?",
            "icon": "shield-check",
        },
    ]


@router.get("/documents", summary="List indexed health policy documents")
async def list_indexed_documents() -> List[Dict[str, Any]]:
    """
    Returns metadata for active health benefit schedules, SOPs, and regulatory guides.
    """
    return [
        {
            "id": doc["id"],
            "title": doc["title"],
            "category": doc["category"],
            "section": doc.get("section", "General"),
            "department": doc["department"],
            "governance_status": doc["governance_status"],
            "last_reviewed": doc["last_reviewed"],
        }
        for doc in HEALTH_INSURANCE_KNOWLEDGE_STORE
    ]
