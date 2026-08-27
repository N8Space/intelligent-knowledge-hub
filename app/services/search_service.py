import logging
import time
from typing import List, Optional, Tuple
from app.config import settings
from app.models.schemas import SourceCitation, IngestDocument

logger = logging.getLogger("intelligent_knowledge_hub.search")

# High-fidelity mock knowledge base for local showcase & offline evaluation
MOCK_KNOWLEDGE_STORE = [
    {
        "id": "SOP-SEC-001-C1",
        "title": "Enterprise Incident Response SOP (Sev-1 / Sev-2)",
        "category": "Security & Reliability SOP",
        "department": "Security & DevOps",
        "governance_status": "Approved",
        "last_reviewed": "2025-01-15",
        "content": (
            "Severity 1 (Critical Outage) and Severity 2 (Degraded Major Capability) incidents require an Incident Commander (IC) "
            "to be assigned within 5 minutes. The IC must initiate a dedicated Bridge channel in Microsoft Teams, notify the Executive On-Call, "
            "and publish initial status updates to the internal Statuspage within 15 minutes. All remediation actions must be recorded "
            "with UTC timestamps in the Incident Log before production configuration changes are applied."
        ),
    },
    {
        "id": "SOP-SEC-001-C2",
        "title": "Enterprise Incident Response SOP (Post-Mortem Policy)",
        "category": "Security & Reliability SOP",
        "department": "Security & DevOps",
        "governance_status": "Approved",
        "last_reviewed": "2025-01-15",
        "content": (
            "Blameless Post-Mortems are mandatory for all Sev-1 and Sev-2 incidents. The root cause analysis (RCA) meeting must occur "
            "within 48 business hours of incident resolution. The resulting Post-Mortem document must detail: timeline of events, root cause, "
            "contributing technical factors, preventative action items with assigned Jira tickets, and target completion dates under 30 days."
        ),
    },
    {
        "id": "SOP-AI-004-C1",
        "title": "Enterprise Generative AI & LLM Deployment Guardrails",
        "category": "AI Governance & Architecture",
        "department": "AI Enablement & Engineering",
        "governance_status": "Approved",
        "last_reviewed": "2025-02-01",
        "content": (
            "All LLM applications deployed to Azure App Service or AKS must enforce retrieval-augmented grounded prompts (RAG) with source verification. "
            "Direct user prompt passthrough without input sanitization and Azure AI Content Safety filtering is strictly prohibited. "
            "All production AI deployments must log token consumption, latency, and retrieval quality metrics to Azure Application Insights, "
            "and sensitive PII (Personally Identifiable Information) must be masked via Entra ID-governed DLP rules prior to LLM submission."
        ),
    },
    {
        "id": "SOP-DEV-012-C1",
        "title": "Cloud Infrastructure Provisioning & CI/CD Pipeline Standards",
        "category": "DevOps & Infrastructure",
        "department": "Platform Engineering",
        "governance_status": "Approved",
        "last_reviewed": "2025-01-20",
        "content": (
            "All Azure cloud resources must be provisioned via Infrastructure as Code (Bicep or Terraform). Manual Azure Portal provisioning "
            "in staging and production subscriptions is prohibited. GitHub Actions workflows must enforce automated linting, security scans "
            "(e.g., Trivy container scan, Bandit/SonarQube SAST), unit tests with >=80% branch coverage, and peer review approval from at least "
            "two senior engineers prior to merging to the `main` branch."
        ),
    },
    {
        "id": "SOP-DATA-008-C1",
        "title": "Data Governance, Access Control & Azure Role-Based Access (RBAC)",
        "category": "Data Governance",
        "department": "Data Platform & Security",
        "governance_status": "Approved",
        "last_reviewed": "2025-01-10",
        "content": (
            "Access to production Azure AI Search indexes and Azure Blob Storage containers must adhere to the Principle of Least Privilege (PoLP). "
            "Service-to-service authentication must utilize Azure Managed Identities (System-Assigned or User-Assigned) rather than long-lived API keys. "
            "Admin-level API keys must be stored strictly in Azure Key Vault with automated 90-day key rotation enabled."
        ),
    },
    {
        "id": "SOP-HR-003-C1",
        "title": "Global Remote Work, Security Equipment & Travel Policy",
        "category": "Corporate Policy",
        "department": "Human Resources & Security",
        "governance_status": "Approved",
        "last_reviewed": "2024-11-30",
        "content": (
            "Employees operating remotely must connect via the corporate ZTNA / GlobalProtect VPN when accessing internal development clusters. "
            "Company-issued MacBooks and Windows laptops must have BitLocker/FileVault encryption enabled and SentinelOne EDR active. "
            "International travel requires a security travel notification filed with IT Security at least 10 business days in advance to configure travel geo-policies."
        ),
    },
]


class SearchService:
    def __init__(self):
        self.endpoint = settings.AZURE_SEARCH_SERVICE_ENDPOINT
        self.api_key = settings.AZURE_SEARCH_API_KEY
        self.index_name = settings.AZURE_SEARCH_INDEX_NAME
        self.semantic_config_name = settings.AZURE_SEARCH_SEMANTIC_CONFIG_NAME
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        if self.endpoint and self.api_key:
            try:
                from azure.core.credentials import AzureKeyCredential
                from azure.search.documents import SearchClient

                self.client = SearchClient(
                    endpoint=self.endpoint,
                    index_name=self.index_name,
                    credential=AzureKeyCredential(self.api_key),
                )
                logger.info("Azure AI Search client successfully initialized.")
            except Exception as e:
                logger.warning(f"Could not initialize Azure AI Search client: {e}. Running in Mock Fallback mode.")
                self.client = None
        else:
            logger.info("Azure AI Search credentials not fully configured. Running in Mock Fallback mode.")

    def is_connected(self) -> bool:
        return self.client is not None

    async def search(
        self,
        query: str,
        top_k: int = 4,
        department: Optional[str] = None,
        strict_governance_only: bool = True,
    ) -> Tuple[List[SourceCitation], float, str]:
        start_time = time.time()
        
        # If Azure AI Search is available, attempt real hybrid/semantic search
        if self.client:
            try:
                citations, mode = await self._azure_ai_search(
                    query=query,
                    top_k=top_k,
                    department=department,
                    strict_governance_only=strict_governance_only,
                )
                retrieval_ms = round((time.time() - start_time) * 1000, 2)
                return citations, retrieval_ms, mode
            except Exception as e:
                logger.error(f"Error querying Azure AI Search: {e}. Falling back to grounded mock store.")

        # Grounded mock search
        citations = self._mock_search(
            query=query,
            top_k=top_k,
            department=department,
            strict_governance_only=strict_governance_only,
        )
        retrieval_ms = round((time.time() - start_time) * 1000, 2)
        return citations, retrieval_ms, "mock_grounded"

    async def _azure_ai_search(
        self,
        query: str,
        top_k: int = 4,
        department: Optional[str] = None,
        strict_governance_only: bool = True,
    ) -> Tuple[List[SourceCitation], str]:
        # Filter construction
        filters = []
        if strict_governance_only:
            filters.append("governance_status eq 'Approved'")
        if department:
            filters.append(f"department eq '{department}'")
        
        filter_expr = " and ".join(filters) if filters else None

        results = self.client.search(
            search_text=query,
            filter=filter_expr,
            top=top_k,
            query_type="semantic",
            semantic_configuration_name=self.semantic_config_name,
            select=["id", "title", "category", "department", "content", "governance_status", "last_reviewed"],
        )

        citations = []
        for doc in results:
            score = round(float(getattr(doc, "@search.reranker_score", getattr(doc, "@search.score", 0.85)) or 0.85) / 4.0, 2)
            citations.append(
                SourceCitation(
                    id=doc.get("id", "doc-1"),
                    title=doc.get("title", "Enterprise Document"),
                    category=doc.get("category", "SOP"),
                    snippet=doc.get("content", "")[:320] + "...",
                    score=min(max(score, 0.50), 0.99),
                    governance_status=doc.get("governance_status", "Approved"),
                    last_reviewed=doc.get("last_reviewed", "2025-Q1"),
                    department=doc.get("department", "Cross-Functional"),
                )
            )

        return citations, "hybrid_semantic"

    def _mock_search(
        self,
        query: str,
        top_k: int = 4,
        department: Optional[str] = None,
        strict_governance_only: bool = True,
    ) -> List[SourceCitation]:
        query_words = set(query.lower().split())
        scored_docs = []

        for doc in MOCK_KNOWLEDGE_STORE:
            if strict_governance_only and doc.get("governance_status") != "Approved":
                continue
            if department and doc.get("department") != department:
                continue

            doc_text = f"{doc['title']} {doc['category']} {doc['department']} {doc['content']}".lower()
            # Simple keyword overlap / relevance scoring for demo mode
            matches = sum(1 for w in query_words if len(w) > 2 and w in doc_text)
            score = 0.70 + (min(matches, 5) * 0.05)

            scored_docs.append((score, doc))

        # Sort descending by relevance score
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        selected = scored_docs[:top_k] if scored_docs else [(0.80, MOCK_KNOWLEDGE_STORE[0])]

        return [
            SourceCitation(
                id=doc["id"],
                title=doc["title"],
                category=doc["category"],
                snippet=doc["content"],
                score=round(score, 2),
                governance_status=doc["governance_status"],
                last_reviewed=doc["last_reviewed"],
                department=doc["department"],
            )
            for score, doc in selected
        ]

    async def ingest_documents(self, documents: List[IngestDocument]) -> Tuple[int, int]:
        total_chunks = 0
        
        for doc in documents:
            # Chunking logic (approx 500 character chunks for SOP documentation)
            content = doc.content
            chunks = [content[i : i + 500] for i in range(0, len(content), 450)]
            total_chunks += len(chunks)

            # Store in in-memory store for instant demonstration capability
            for idx, chunk in enumerate(chunks):
                chunk_id = f"{doc.id or 'DOC'}-C{idx+1}"
                MOCK_KNOWLEDGE_STORE.append(
                    {
                        "id": chunk_id,
                        "title": doc.title,
                        "category": doc.category,
                        "department": doc.department,
                        "governance_status": doc.governance_status,
                        "last_reviewed": "Just Now",
                        "content": chunk,
                    }
                )

        return len(documents), total_chunks


search_service = SearchService()
