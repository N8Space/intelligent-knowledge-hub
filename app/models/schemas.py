from typing import List, Optional
from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    id: str = Field(..., description="Document ID or Policy reference code (e.g. PLAN-PPO-2026-BENEFITS)")
    title: str = Field(..., description="Policy or SOP document title")
    category: str = Field(..., description="Category (e.g. Benefit Schedule, Prior Auth, Claims, HIPAA)")
    section: Optional[str] = Field(default="General", description="Document section or clause number")
    snippet: str = Field(..., description="Exact policy clause / retrieved text chunk")
    score: float = Field(..., description="Search similarity / reranker confidence score (0.0 - 1.0)")
    governance_status: str = Field(
        default="Approved 2026 Policy", description="Regulatory or approval status"
    )
    last_reviewed: str = Field(default="2026-01-01", description="Last audit / compliance review date")
    department: str = Field(default="Member Operations", description="Owning operational division")


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, description="CSR inquiry during member call")
    top_k: int = Field(default=4, ge=1, le=10, description="Top policy chunks to retrieve")
    call_type: Optional[str] = Field(
        default=None, description="Optional call type filter (e.g. Benefits, Prior Auth, Claims, HIPAA)"
    )
    strict_governance_only: bool = Field(
        default=True, description="Only search approved, active health plan documents"
    )
    stream: bool = Field(default=False, description="Whether to stream response tokens")


class QueryMetrics(BaseModel):
    retrieval_time_ms: float = Field(..., description="Azure AI Search retrieval latency in ms")
    llm_time_ms: float = Field(..., description="Azure AI Foundry generation latency in ms")
    total_latency_ms: float = Field(..., description="Total roundtrip latency in ms")
    sources_retrieved: int = Field(..., description="Total retrieved source count")
    search_mode: str = Field(
        default="hybrid_semantic",
        description="Search execution mode (hybrid_semantic, vector, or mock_grounded)",
    )


class CSRResolutionGuidance(BaseModel):
    plain_language_script: str = Field(
        ..., description="Direct member-facing explanation script for live phone readback"
    )
    action_steps: List[str] = Field(
        default_factory=list, description="Step-by-step resolution actions for the CSR in the CRM"
    )
    compliance_notes: Optional[str] = Field(
        default=None, description="Regulatory and HIPAA compliance reminders"
    )


class QueryResponse(BaseModel):
    query: str
    answer: str
    guidance: Optional[CSRResolutionGuidance] = None
    citations: List[SourceCitation]
    metrics: QueryMetrics
    governance_passed: bool = True
    confidence_level: str = "High (100% Policy Grounded)"


class IngestDocument(BaseModel):
    id: Optional[str] = None
    title: str = Field(..., description="Document title")
    category: str = Field(default="SOP", description="Category of document")
    department: str = Field(default="Engineering", description="Owning department")
    content: str = Field(..., min_length=10, description="Full text or markdown content")
    governance_status: str = Field(default="Approved", description="Governance approval status")
    version: str = Field(default="1.0", description="Document version")


class IngestRequest(BaseModel):
    documents: List[IngestDocument] = Field(..., min_length=1)


class IngestResponse(BaseModel):
    status: str
    indexed_documents: int
    indexed_chunks: int
    message: str


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    environment: str
    azure_search_connected: bool
    azure_openai_connected: bool
    mock_mode_active: bool
