"""
Intelligent Knowledge Hub - Enterprise RAG API
FastAPI backend engine utilizing Azure AI Search (Hybrid RRF), Azure OpenAI (gpt-5.4-mini),
and Zero-Trust Microsoft Entra ID Authentication with an active LLMOps Data Flywheel.
"""

import json
import logging
import os
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import AzureOpenAI
from pydantic import BaseModel, Field

# Load environment configuration
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("intelligent_knowledge_hub")

# Configuration constants
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "https://kb-search-hub.search.windows.net")
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://kb-openai-lester-labs.openai.azure.com/")
STORAGE_ACCOUNT = os.getenv("STORAGE_ACCOUNT_NAME", "saintelligenthub0827")
EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-5.4-mini")
SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "kb-index")
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")

# Pricing constants for FinOps estimation (USD per 1,000 tokens)
COST_PER_1K_EMBEDDING_TOKENS = 0.00002  # text-embedding-3-small
COST_PER_1K_PROMPT_TOKENS = 0.00015  # gpt-5.4-mini / gpt-4o-mini class
COST_PER_1K_COMPLETION_TOKENS = 0.00060  # gpt-5.4-mini / gpt-4o-mini class

# Data paths for LLMOps Flywheel
DATA_DIR = "data"
TESTS_DIR = "tests"
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback_dataset.jsonl")
GOLDEN_EVAL_FILE = os.path.join(TESTS_DIR, "golden_eval_set.jsonl")
DPO_TUNING_FILE = os.path.join(DATA_DIR, "dpo_tuning_set.jsonl")

# Ensure required storage directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TESTS_DIR, exist_ok=True)

# App instance
app = FastAPI(
    title="Intelligent Knowledge Hub",
    description="Enterprise Zero-Trust RAG Platform with Hybrid Search, Telemetry, and Active Learning Flywheel",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Zero-Trust Clients Factory / Lazy Initializers
_credential: DefaultAzureCredential | None = None
_token_provider = None
_openai_client: AzureOpenAI | None = None
_search_client: SearchClient | None = None


def get_azure_credential() -> DefaultAzureCredential:
    """Returns singleton DefaultAzureCredential."""
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


def get_openai_client() -> AzureOpenAI:
    """Initializes AzureOpenAI client with Entra ID Bearer Token authentication, falling back to API key if present."""
    global _openai_client, _token_provider
    if _openai_client is None:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if api_key and api_key.strip():
            _openai_client = AzureOpenAI(
                azure_endpoint=OPENAI_ENDPOINT,
                api_key=api_key.strip(),
                api_version=OPENAI_API_VERSION,
            )
            logger.info("AzureOpenAI client initialized with API key.")
        else:
            try:
                credential = get_azure_credential()
                if _token_provider is None:
                    _token_provider = get_bearer_token_provider(
                        credential, "https://cognitiveservices.azure.com/.default"
                    )
                _openai_client = AzureOpenAI(
                    azure_endpoint=OPENAI_ENDPOINT,
                    azure_ad_token_provider=_token_provider,
                    api_version=OPENAI_API_VERSION,
                )
                logger.info("AzureOpenAI client initialized with DefaultAzureCredential.")
            except Exception as ex:
                logger.warning(f"Unable to initialize AzureOpenAI client immediately: {ex}")
                raise
    return _openai_client


def get_search_client() -> SearchClient:
    """Initializes Azure AI Search client with DefaultAzureCredential, falling back to API key if present."""
    global _search_client
    if _search_client is None:
        search_key = os.getenv("AZURE_SEARCH_API_KEY")
        if search_key and search_key.strip():
            from azure.core.credentials import AzureKeyCredential

            _search_client = SearchClient(
                endpoint=SEARCH_ENDPOINT,
                index_name=SEARCH_INDEX_NAME,
                credential=AzureKeyCredential(search_key.strip()),
            )
            logger.info(f"Azure SearchClient initialized for index '{SEARCH_INDEX_NAME}' with AzureKeyCredential.")
        else:
            try:
                credential = get_azure_credential()
                _search_client = SearchClient(
                    endpoint=SEARCH_ENDPOINT, index_name=SEARCH_INDEX_NAME, credential=credential
                )
                logger.info(f"Azure SearchClient initialized for index '{SEARCH_INDEX_NAME}'.")
            except Exception as ex:
                logger.warning(f"Unable to initialize SearchClient immediately: {ex}")
                raise
    return _search_client


# --------------------------------------------------------------------------
# Request / Response Pydantic Models
# --------------------------------------------------------------------------


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question to be answered by the knowledge hub")
    top_k: int = Field(default=3, ge=1, le=10, description="Top K relevant passages to retrieve")


class CitationItem(BaseModel):
    title: str = Field(..., description="Document source title or filename")
    chunk_id: str = Field(..., description="Unique chunk identifier in the search index")


class ContextItem(BaseModel):
    id: str
    title: str
    content: str
    score: float | None = None


class QueryMetrics(BaseModel):
    retrieval_latency_ms: float = Field(..., description="Latency for vectorization & hybrid search (ms)")
    llm_latency_ms: float = Field(..., description="Latency for LLM inference (ms)")
    total_latency_ms: float = Field(..., description="Total end-to-end query latency (ms)")
    prompt_tokens: int = Field(..., description="Number of tokens in prompt")
    completion_tokens: int = Field(..., description="Number of tokens in completion")
    total_tokens: int = Field(..., description="Total tokens consumed")
    estimated_cost_usd: float = Field(..., description="Calculated query cost in USD")
    formatted_cost: str = Field(..., description="Formatted string representation of query cost")


class QueryResponse(BaseModel):
    answer: str = Field(..., description="Grounded answer synthesized by the LLM")
    citations: list[CitationItem] = Field(default_factory=list, description="Unique source citations")
    context: list[ContextItem] = Field(default_factory=list, description="Raw context chunks used for grounding")
    metrics: QueryMetrics = Field(..., description="Operational and FinOps metrics")


class FeedbackRequest(BaseModel):
    query: str = Field(..., description="Original user prompt")
    response: str = Field(..., description="Generated answer from the knowledge engine")
    citations: list[Any] = Field(default_factory=list, description="List of cited documents/chunks")
    retrieved_context: list[Any] = Field(default_factory=list, description="Retrieved context items")
    rating: Literal["like", "dislike"] = Field(..., description="User sentiment rating: 'like' or 'dislike'")
    reason: str | None = Field(default=None, description="Optional categorization of issue if disliked")
    user_correction: str | None = Field(default=None, description="Human ground-truth correction or suggested response")


class FeedbackResponse(BaseModel):
    status: str
    message: str
    feedback_id: str
    timestamp: str


class FeedbackStatsResponse(BaseModel):
    total_feedback: int
    positive_count: int
    negative_count: int
    human_corrected_count: int
    golden_eval_count: int
    dpo_pairs_count: int
    satisfaction_rate_pct: float


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@app.get("/health/live", tags=["Probes"])
def liveness_probe():
    """
    Kubernetes / App Service Liveness Probe.
    Returns 200 OK if the web server process is alive and accepting requests.
    """
    return {
        "status": "healthy",
        "service": "intelligent-knowledge-hub",
        "version": "1.0.0",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/health/ready", tags=["Probes"])
def readiness_probe():
    """
    Deep Readiness Probe.
    Validates live connectivity to Azure AI Search and Azure OpenAI endpoints.
    """
    service_status = {"azure_search": "unknown", "azure_openai": "unknown"}
    is_ready = True
    errors = []

    # 1. Check Azure Search connectivity
    try:
        s_client = get_search_client()
        # Verify index count or query
        count = s_client.get_document_count()
        service_status["azure_search"] = f"healthy (index: {SEARCH_INDEX_NAME}, doc_count: {count})"
    except Exception as ex:
        is_ready = False
        err_msg = f"Search probe failed: {ex!s}"
        service_status["azure_search"] = err_msg
        errors.append(err_msg)
        logger.error(err_msg)

    # 2. Check Azure OpenAI connectivity
    try:
        o_client = get_openai_client()
        # Test a minimal embedding call to verify token provider & network path
        test_embed = o_client.embeddings.create(input="health_check", model=EMBEDDING_DEPLOYMENT)
        if test_embed.data:
            service_status["azure_openai"] = f"healthy (embedding: {EMBEDDING_DEPLOYMENT}, chat: {CHAT_DEPLOYMENT})"
        else:
            is_ready = False
            service_status["azure_openai"] = "no data returned from embedding check"
    except Exception as ex:
        is_ready = False
        err_msg = f"OpenAI probe failed: {ex!s}"
        service_status["azure_openai"] = err_msg
        errors.append(err_msg)
        logger.error(err_msg)

    response_payload = {
        "status": "ready" if is_ready else "unhealthy",
        "services": service_status,
        "index_name": SEARCH_INDEX_NAME,
        "embedding_deployment": EMBEDDING_DEPLOYMENT,
        "chat_deployment": CHAT_DEPLOYMENT,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if not is_ready:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=response_payload)

    return response_payload


@app.post("/query", response_model=QueryResponse, tags=["RAG Engine"])
def execute_rag_query(request: QueryRequest):
    """
    Executes Hybrid Vector + Keyword RAG Query against Azure AI Search & Azure OpenAI.
    Measures end-to-end telemetry and calculates real-time query unit economics.
    """
    start_time = time.perf_counter()

    try:
        openai_c = get_openai_client()
        search_c = get_search_client()
    except Exception as e:
        logger.error(f"Client initialization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Downstream Azure Services not accessible: {e!s}",
        ) from e

    # Step 1: Embed Query for Vector Search
    retrieval_start = time.perf_counter()
    try:
        embedding_res = openai_c.embeddings.create(input=request.question, model=EMBEDDING_DEPLOYMENT)
        query_vector = embedding_res.data[0].embedding
        embed_tokens = getattr(embedding_res.usage, "total_tokens", 8) if hasattr(embedding_res, "usage") else 8
    except Exception as ex:
        logger.error(f"Embedding generation failed: {ex}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to generate query embedding from Azure OpenAI: {ex!s}",
        ) from ex

    # Step 2: Hybrid Search (BM25 Keyword + Vector Search with RRF)
    try:
        vector_query = VectorizedQuery(vector=query_vector, k_nearest_neighbors=request.top_k, fields="contentVector")
        search_results = search_c.search(
            search_text=request.question,
            vector_queries=[vector_query],
            top=request.top_k,
            select=["id", "title", "content"],
        )

        retrieved_docs: list[ContextItem] = []
        seen_chunks = set()
        citations_list: list[CitationItem] = []

        for r in search_results:
            chunk_id = str(r.get("id", ""))
            title = str(r.get("title", "Untitled Document"))
            content = str(r.get("content", ""))
            score = float(r.get("@search.score", 0.0)) if r.get("@search.score") is not None else None

            retrieved_docs.append(ContextItem(id=chunk_id, title=title, content=content, score=score))

            if chunk_id not in seen_chunks:
                seen_chunks.add(chunk_id)
                citations_list.append(CitationItem(title=title, chunk_id=chunk_id))

    except Exception as ex:
        logger.error(f"Azure AI Search hybrid search failed: {ex}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Hybrid search query failed in Azure AI Search: {ex!s}",
        ) from ex

    retrieval_latency_ms = (time.perf_counter() - retrieval_start) * 1000

    # Step 3: Grounded Answer Synthesis with Azure OpenAI
    llm_start = time.perf_counter()

    # Format context passages for system prompt
    context_blocks = []
    for idx, doc in enumerate(retrieved_docs, start=1):
        context_blocks.append(f"--- PASSAGE {idx} [Document: {doc.title} | Chunk ID: {doc.id}] ---\n{doc.content}")
    formatted_context = "\n\n".join(context_blocks) if context_blocks else "No relevant documents found."

    system_prompt = (
        "You are the Intelligent Knowledge Hub AI assistant, an enterprise-grade retrieval-augmented knowledge expert.\n"
        "Your instructions:\n"
        "1. Answer the user's question strictly, concisely, and accurately based ONLY on the provided Retrieved Context passages.\n"
        "2. Do NOT extrapolate, hallucinate, or assume facts not present in the retrieved passages.\n"
        "3. If the retrieved context does not contain enough information to answer the question, state: "
        "'I cannot find sufficient information in the knowledge base to answer this question.'\n"
        "4. Always clearly reference the source document titles when explaining facts."
    )

    user_message = f"Retrieved Context Passages:\n{formatted_context}\n\nUser Question: {request.question}"

    try:
        chat_res = openai_c.chat.completions.create(
            model=CHAT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_completion_tokens=800,
        )
        answer = chat_res.choices[0].message.content or "No response generated."
        prompt_tokens = chat_res.usage.prompt_tokens if chat_res.usage else 0
        completion_tokens = chat_res.usage.completion_tokens if chat_res.usage else 0
        total_tokens = chat_res.usage.total_tokens if chat_res.usage else 0
    except Exception as ex:
        logger.error(f"OpenAI chat completion generation failed: {ex}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Chat generation failed on Azure OpenAI: {ex!s}",
        ) from ex

    llm_latency_ms = (time.perf_counter() - llm_start) * 1000
    total_latency_ms = (time.perf_counter() - start_time) * 1000

    # Step 4: Token Economics & FinOps Calculation
    est_cost = (
        (embed_tokens / 1000.0) * COST_PER_1K_EMBEDDING_TOKENS
        + (prompt_tokens / 1000.0) * COST_PER_1K_PROMPT_TOKENS
        + (completion_tokens / 1000.0) * COST_PER_1K_COMPLETION_TOKENS
    )
    formatted_cost = f"${est_cost:.6f}"

    metrics = QueryMetrics(
        retrieval_latency_ms=round(retrieval_latency_ms, 2),
        llm_latency_ms=round(llm_latency_ms, 2),
        total_latency_ms=round(total_latency_ms, 2),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=round(est_cost, 7),
        formatted_cost=formatted_cost,
    )

    return QueryResponse(answer=answer, citations=citations_list, context=retrieved_docs, metrics=metrics)


@app.post("/feedback", response_model=FeedbackResponse, tags=["LLMOps Flywheel"])
def submit_user_feedback(request: FeedbackRequest):
    """
    Submits user feedback on generated answers.
    Persists data to:
      1. Main feedback dataset: data/feedback_dataset.jsonl
      2. Golden Answer Evaluation Set: tests/golden_eval_set.jsonl (for positive ratings)
      3. DPO / SFT Alignment Set: data/dpo_tuning_set.jsonl (for negative ratings / corrections)
    """
    feedback_id = f"fb_{uuid.uuid4().hex[:10]}"
    timestamp = datetime.now(UTC).isoformat()

    # Prepare complete feedback entry
    feedback_record = {
        "id": feedback_id,
        "timestamp": timestamp,
        "query": request.query,
        "response": request.response,
        "citations": [
            c if isinstance(c, dict) else (c.model_dump() if hasattr(c, "model_dump") else str(c))
            for c in request.citations
        ],
        "retrieved_context": [
            c if isinstance(c, dict) else (c.model_dump() if hasattr(c, "model_dump") else str(c))
            for c in request.retrieved_context
        ],
        "rating": request.rating,
        "reason": request.reason,
        "user_correction": request.user_correction,
    }

    try:
        # 1. Append to primary feedback log
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_record, ensure_ascii=False) + "\n")

        # 2. Dataset curation routing
        if request.rating == "like":
            # Append to Golden Answer Evaluation Set
            golden_record = {
                "id": feedback_id,
                "timestamp": timestamp,
                "query": request.query,
                "expected_answer": request.response,
                "citations": feedback_record["citations"],
                "retrieved_context": feedback_record["retrieved_context"],
                "dataset": "golden_eval_set",
            }
            with open(GOLDEN_EVAL_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(golden_record, ensure_ascii=False) + "\n")

        elif request.rating == "dislike" or request.user_correction:
            # Append to DPO Preference Tuning Set
            dpo_record = {
                "id": feedback_id,
                "timestamp": timestamp,
                "prompt": request.query,
                "chosen": request.user_correction
                if request.user_correction
                else "(Human ground-truth correction needed)",
                "rejected": request.response,
                "issue_reason": request.reason,
                "retrieved_context": feedback_record["retrieved_context"],
                "dataset": "dpo_tuning_set",
            }
            with open(DPO_TUNING_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(dpo_record, ensure_ascii=False) + "\n")

    except Exception as ex:
        logger.error(f"Failed to persist feedback record: {ex}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store feedback: {ex!s}",
        ) from ex

    return FeedbackResponse(
        status="success",
        message="Feedback successfully recorded and routed to LLMOps continuous learning flywheel.",
        feedback_id=feedback_id,
        timestamp=timestamp,
    )


@app.get("/feedback/stats", response_model=FeedbackStatsResponse, tags=["LLMOps Flywheel"])
def get_feedback_statistics():
    """
    Returns aggregated metrics and counts across feedback, golden evaluation, and DPO datasets.
    """
    total_feedback = 0
    positive_count = 0
    negative_count = 0
    human_corrected_count = 0
    golden_eval_count = 0
    dpo_pairs_count = 0

    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        total_feedback += 1
                        if record.get("rating") == "like":
                            positive_count += 1
                        elif record.get("rating") == "dislike":
                            negative_count += 1
                        if record.get("user_correction") and str(record.get("user_correction")).strip():
                            human_corrected_count += 1
                    except json.JSONDecodeError:
                        continue
        except Exception as ex:
            logger.warning(f"Error reading feedback file: {ex}")

    if os.path.exists(GOLDEN_EVAL_FILE):
        try:
            with open(GOLDEN_EVAL_FILE, encoding="utf-8") as f:
                golden_eval_count = sum(1 for line in f if line.strip())
        except Exception as ex:
            logger.warning(f"Error reading golden eval file: {ex}")

    if os.path.exists(DPO_TUNING_FILE):
        try:
            with open(DPO_TUNING_FILE, encoding="utf-8") as f:
                dpo_pairs_count = sum(1 for line in f if line.strip())
        except Exception as ex:
            logger.warning(f"Error reading DPO tuning file: {ex}")

    satisfaction_rate = (positive_count / total_feedback * 100.0) if total_feedback > 0 else 100.0

    return FeedbackStatsResponse(
        total_feedback=total_feedback,
        positive_count=positive_count,
        negative_count=negative_count,
        human_corrected_count=human_corrected_count,
        golden_eval_count=golden_eval_count,
        dpo_pairs_count=dpo_pairs_count,
        satisfaction_rate_pct=round(satisfaction_rate, 1),
    )


# Mount Static Files for UI Dashboard
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def serve_ui():
    """Serves the Single Page Application UI Dashboard."""
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "app": "Intelligent Knowledge Hub",
        "status": "online",
        "ui": "Frontend static assets initializing. Please view /docs for API documentation.",
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
