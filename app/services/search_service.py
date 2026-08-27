import logging
import time
from typing import List, Optional, Tuple
from app.config import settings
from app.models.schemas import SourceCitation, IngestDocument

logger = logging.getLogger("memberassist.search")

# Curated, synthetic health insurance knowledge store
HEALTH_INSURANCE_KNOWLEDGE_STORE = [
    {
        "id": "PLAN-PPO-2026-BENEFITS",
        "title": "Commercial Premier & Standard PPO Benefit Schedule (2026)",
        "category": "Benefit Schedule",
        "section": "Section 2: Diagnostic Imaging & Out-of-Network Cost Shares",
        "department": "Plan Administration",
        "governance_status": "Approved 2026 Policy",
        "last_reviewed": "2026-01-01",
        "content": (
            "Advanced Diagnostic Imaging (MRI, CT, PET Scan): Under the Standard PPO plan, in-network advanced imaging is subject to the "
            "in-network deductible ($1,500 individual), then 20% coinsurance at participating freestanding imaging centers (30% at hospital outpatient facility). "
            "Out-of-network advanced imaging is subject to the out-of-network deductible ($3,000 individual), then 40% coinsurance plus balance billing. "
            "All non-emergency advanced imaging requires prior authorization before service."
        ),
    },
    {
        "id": "PLAN-PPO-2026-DEDUCTIBLE",
        "title": "Commercial Premier & Standard PPO Benefit Schedule (2026)",
        "category": "Benefit Schedule",
        "section": "Section 1: Annual Deductibles and Out-of-Pocket Maximums",
        "department": "Plan Administration",
        "governance_status": "Approved 2026 Policy",
        "last_reviewed": "2026-01-01",
        "content": (
            "Standard PPO In-Network Individual Deductible is $1,500 per calendar year ($3,000 Family). "
            "Standard PPO Out-of-Network Individual Deductible is $3,000 per calendar year ($6,000 Family). "
            "In-Network Annual Out-of-Pocket Maximum (OOPM) is $6,000 Individual / $12,000 Family. "
            "Preventive services are covered at 100% with $0 copay in-network. Routine PCP visits have a $25 copay with deductible waived; "
            "specialist visits have a $50 copay with deductible waived (no PCP referral needed for PPO members)."
        ),
    },
    {
        "id": "SOP-UM-2026-004",
        "title": "Prior Authorization & Clinical Appeals SOP",
        "category": "Prior Authorization",
        "section": "Section 1 & 2: PA Timelines & Peer-to-Peer Protocol",
        "department": "Utilization Management (UM)",
        "governance_status": "Approved 2026 Policy",
        "last_reviewed": "2026-01-01",
        "content": (
            "Standard non-urgent prior authorization decisions must be communicated within 72 clock hours (3 business days) of receiving complete clinical records. "
            "Expedited/urgent reviews must be determined within 24 clock hours when the ordering provider certifies delay could jeopardize health or pain control. "
            "Ordering clinicians have 5 business days following an adverse determination to request a Peer-to-Peer (P2P) review with a Plan Medical Director. "
            "CSRs can initiate P2P scheduling via UM queue UM-CLIN-P2P, which must occur within 2 business days."
        ),
    },
    {
        "id": "GUIDE-CLM-2026-012",
        "title": "Claims Denial Explanation & EOB Call Resolution Guide",
        "category": "Claims Resolution",
        "section": "Section 1 & 2: Denial Codes & No Surprises Act Protection",
        "department": "Claims Operations",
        "governance_status": "Approved 2026 Policy",
        "last_reviewed": "2026-01-01",
        "content": (
            "Code CO-16 indicates missing clinical notes or modifier; advise member the provider has 90 days to re-bill with records and member holds no liability during review. "
            "Under federal No Surprises Act (NSA) protections, non-participating emergency providers and inadvertent out-of-network ancillary providers "
            "(anesthesiology, pathology, radiology) at in-network facilities are legally prohibited from balance billing members above in-network cost-sharing. "
            "CSRs must immediately open a Claims Payment Dispute ticket for balance billing complaints."
        ),
    },
    {
        "id": "SOP-HIPAA-2026-001",
        "title": "HIPAA Privacy Verification & Authorized Representative Disclosures SOP",
        "category": "HIPAA & Compliance",
        "section": "Section 1 & 2: Caller Authentication & Representative Rules",
        "department": "Privacy & Compliance Office",
        "governance_status": "Approved 2026 Policy",
        "last_reviewed": "2026-01-01",
        "content": (
            "Before disclosing PHI or claims data, CSRs must authenticate 3 of 4 identifiers: (1) Full Legal Name, (2) Member ID or last 4 SSN, "
            "(3) Date of Birth (MM/DD/YYYY), (4) Residential Address & Zip Code. "
            "Spouses and adult dependents (>18 years) cannot access each other's medical claims without a signed HIPAA Authorization Form (PHI-AUTH-01) or POA on file. "
            "Verbal 1-time authorization is valid only if the authenticated primary member is present on the active telephone call."
        ),
    },
    {
        "id": "PLAN-PPO-2026-RX",
        "title": "Commercial Formulary & Prescription Benefit Schedule (2026)",
        "category": "Prescription / Pharmacy",
        "section": "Section 3: Formulary Tiers & Specialty Fulfillment",
        "department": "Pharmacy Operations",
        "governance_status": "Approved 2026 Policy",
        "last_reviewed": "2026-01-01",
        "content": (
            "Tier 1 Preferred Generics: $10 copay (30-day retail) or $20 (90-day mail order). "
            "Tier 2 Preferred Brand: $40 copay after pharmacy deductible. "
            "Tier 3 Non-Preferred Brand: $85 copay after pharmacy deductible. "
            "Tier 4 Specialty Biologics: 20% coinsurance up to $250 maximum per 30-day fill, requiring mandatory fulfillment through Plan Specialty Pharmacy."
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
                logger.info("Azure AI Search client successfully initialized for health plan index.")
            except Exception as e:
                logger.warning(f"Could not initialize Azure AI Search client: {e}. Running in Mock Fallback mode.")
                self.client = None
        else:
            logger.info("Azure AI Search credentials not configured. Running in Mock Fallback mode.")

    def is_connected(self) -> bool:
        return self.client is not None

    async def search(
        self,
        query: str,
        top_k: int = 4,
        call_type: Optional[str] = None,
        strict_governance_only: bool = True,
    ) -> Tuple[List[SourceCitation], float, str]:
        start_time = time.time()

        if self.client:
            try:
                citations, mode = await self._azure_ai_search(
                    query=query,
                    top_k=top_k,
                    call_type=call_type,
                    strict_governance_only=strict_governance_only,
                )
                retrieval_ms = round((time.time() - start_time) * 1000, 2)
                return citations, retrieval_ms, mode
            except Exception as e:
                logger.error(f"Error querying Azure AI Search: {e}. Falling back to grounded mock store.")

        # Grounded mock search for local demo & offline evaluations
        citations = self._mock_search(
            query=query,
            top_k=top_k,
            call_type=call_type,
            strict_governance_only=strict_governance_only,
        )
        retrieval_ms = round((time.time() - start_time) * 1000, 2)
        return citations, retrieval_ms, "mock_grounded"

    async def _azure_ai_search(
        self,
        query: str,
        top_k: int = 4,
        call_type: Optional[str] = None,
        strict_governance_only: bool = True,
    ) -> Tuple[List[SourceCitation], str]:
        filters = []
        if strict_governance_only:
            filters.append("governance_status eq 'Approved 2026 Policy'")
        if call_type and call_type != "All":
            filters.append(f"category eq '{call_type}'")

        filter_expr = " and ".join(filters) if filters else None

        results = self.client.search(
            search_text=query,
            filter=filter_expr,
            top=top_k,
            query_type="semantic",
            semantic_configuration_name=self.semantic_config_name,
            select=["id", "title", "category", "section", "department", "content", "governance_status", "last_reviewed"],
        )

        citations = []
        for doc in results:
            score = round(float(getattr(doc, "@search.reranker_score", getattr(doc, "@search.score", 0.88)) or 0.88) / 4.0, 2)
            citations.append(
                SourceCitation(
                    id=doc.get("id", "PLAN-DOC-1"),
                    title=doc.get("title", "Health Plan Policy Document"),
                    category=doc.get("category", "Benefit Schedule"),
                    section=doc.get("section", "General"),
                    snippet=doc.get("content", "")[:320] + "...",
                    score=min(max(score, 0.60), 0.99),
                    governance_status=doc.get("governance_status", "Approved 2026 Policy"),
                    last_reviewed=doc.get("last_reviewed", "2026-01-01"),
                    department=doc.get("department", "Member Operations"),
                )
            )

        return citations, "hybrid_semantic"

    def _mock_search(
        self,
        query: str,
        top_k: int = 4,
        call_type: Optional[str] = None,
        strict_governance_only: bool = True,
    ) -> List[SourceCitation]:
        query_words = set(query.lower().split())
        scored_docs = []

        for doc in HEALTH_INSURANCE_KNOWLEDGE_STORE:
            if strict_governance_only and "Approved" not in doc.get("governance_status", ""):
                continue
            if call_type and call_type != "All" and call_type.lower() not in doc.get("category", "").lower():
                continue

            doc_text = f"{doc['title']} {doc['category']} {doc.get('section', '')} {doc['content']}".lower()
            matches = sum(1 for w in query_words if len(w) > 2 and w in doc_text)
            score = 0.72 + (min(matches, 6) * 0.04)

            scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        selected = scored_docs[:top_k] if scored_docs else [(0.85, HEALTH_INSURANCE_KNOWLEDGE_STORE[0])]

        return [
            SourceCitation(
                id=doc["id"],
                title=doc["title"],
                category=doc["category"],
                section=doc.get("section", "General"),
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
            content = doc.content
            chunks = [content[i : i + 500] for i in range(0, len(content), 450)]
            total_chunks += len(chunks)

            for idx, chunk in enumerate(chunks):
                chunk_id = f"{doc.id or 'DOC'}-C{idx+1}"
                HEALTH_INSURANCE_KNOWLEDGE_STORE.append(
                    {
                        "id": chunk_id,
                        "title": doc.title,
                        "category": doc.category,
                        "section": f"Section {idx+1}",
                        "department": doc.department,
                        "governance_status": doc.governance_status,
                        "last_reviewed": "2026-01-01",
                        "content": chunk,
                    }
                )

        return len(documents), total_chunks


search_service = SearchService()

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
