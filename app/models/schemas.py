from typing import List, Optional
from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    id: str = Field(..., description="Unique chunk or document identifier")
    title: str = Field(..., description="Document title")
    category: str = Field(..., description="Document category (e.g., SOP, Policy, Architecture)")
    snippet: str = Field(..., description="Retrieved relevant chunk excerpt")
    score: float = Field(..., description="Relevance / Search similarity score (0.0 to 1.0)")
    governance_status: str = Field(
        default="Approved", description="Governance status (Approved, Compliant, In-Review, Deprecated)"
    )
    last_reviewed: str = Field(default="2025-Q1", description="Last audit / review date")
    department: str = Field(default="Cross-Functional", description="Owning business unit or department")


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language question")
    top_k: int = Field(default=4, ge=1, le=10, description="Number of context sources to retrieve")
    filter_department: Optional[str] = Field(
        default=None, description="Optional department filter (e.g. Engineering, Security, HR)"
    )
    strict_governance_only: bool = Field(
        default=True, description="Enforce strict retrieval of approved governance content only"
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


class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[SourceCitation]
    metrics: QueryMetrics
    governance_passed: bool = True


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
