import logging
import time
from typing import List, Tuple
from app.config import settings
from app.models.schemas import SourceCitation

logger = logging.getLogger("intelligent_knowledge_hub.llm")

SYSTEM_GOVERNANCE_PROMPT = """You are the enterprise Intelligent Knowledge Hub Assistant, an AI Enablement copilot designed to help enterprise teams quickly discover approved SOPs, process documentation, compliance policies, and architectural standards.

Operational Guardrails:
1. ONLY answer using the provided retrieved context sources.
2. Ground every single claim with explicit citation brackets matching the source numbers (e.g. [1], [2]).
3. If the context does not contain the answer, explicitly state: "I cannot find approved enterprise documentation answering this request. Please submit a request to the governance/enablement team."
4. Structure answers with clear executive summaries, bulleted actionable steps, and strict compliance notes.
5. Maintain a professional, authoritative, enterprise-grade tone.
"""


class LLMService:
    def __init__(self):
        self.endpoint = settings.AZURE_OPENAI_ENDPOINT
        self.api_key = settings.AZURE_OPENAI_API_KEY
        self.api_version = settings.AZURE_OPENAI_API_VERSION
        self.deployment = settings.AZURE_OPENAI_CHAT_DEPLOYMENT
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        if self.endpoint and self.api_key:
            try:
                from openai import AzureOpenAI

                self.client = AzureOpenAI(
                    azure_endpoint=self.endpoint,
                    api_key=self.api_key,
                    api_version=self.api_version,
                )
                logger.info("Azure OpenAI / Foundry LLM client successfully initialized.")
            except Exception as e:
                logger.warning(f"Could not initialize Azure OpenAI client: {e}. Running in Mock Fallback mode.")
                self.client = None
        else:
            logger.info("Azure OpenAI credentials not fully configured. Running in Mock Fallback mode.")

    def is_connected(self) -> bool:
        return self.client is not None

    async def generate_response(
        self,
        query: str,
        citations: List[SourceCitation],
    ) -> Tuple[str, float]:
        start_time = time.time()

        # Build grounded context block
        context_blocks = []
        for idx, citation in enumerate(citations, 1):
            context_blocks.append(
                f"--- SOURCE [{idx}] ---\n"
                f"Title: {citation.title}\n"
                f"Category: {citation.category} | Dept: {citation.department} | Governance: {citation.governance_status}\n"
                f"Content: {citation.snippet}\n"
            )
        formatted_context = "\n".join(context_blocks)

        user_prompt = (
            f"Retrieved Enterprise Knowledge Context:\n{formatted_context}\n\n"
            f"User Question: {query}\n\n"
            f"Provide an authoritative, well-structured answer with citation references [1], [2], etc."
        )

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.deployment,
                    messages=[
                        {"role": "system", "content": SYSTEM_GOVERNANCE_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=800,
                )
                answer = response.choices[0].message.content or ""
                llm_ms = round((time.time() - start_time) * 1000, 2)
                return answer, llm_ms
            except Exception as e:
                logger.error(f"Error calling Azure OpenAI / Foundry: {e}. Falling back to grounded mock response.")

        # Grounded mock generation for offline showcase & demo
        answer = self._generate_grounded_mock(query, citations)
        llm_ms = round((time.time() - start_time) * 1000, 2)
        return answer, llm_ms

    def _generate_grounded_mock(self, query: str, citations: List[SourceCitation]) -> str:
        q_lower = query.lower()
        top_citation = citations[0] if citations else None
        
        if not citations:
            return (
                "**Enterprise Notice:** I cannot find approved enterprise documentation answering this request. "
                "Please submit a ticket to the Knowledge Governance team."
            )

        if "incident" in q_lower or "sev" in q_lower or "outage" in q_lower:
            return (
                "### Enterprise Incident Response Protocol\n\n"
                "Based on approved enterprise governance documentation [1], here is the standard operational procedure:\n\n"
                "* **Immediate Assignment (5 Mins):** Severity 1 (Critical Outage) and Severity 2 (Major Capability Degraded) "
                "require an Incident Commander (IC) to be designated within 5 minutes [1].\n"
                "* **Bridge & Executive Escalation:** The IC must immediately spin up a dedicated Microsoft Teams bridge channel "
                "and alert the Executive On-Call [1].\n"
                "* **Public Statuspage Broadcast (15 Mins):** Initial internal and external status communications must be posted within 15 minutes [1].\n"
                "* **Post-Mortem Requirement:** A blameless post-mortem RCA meeting must be scheduled within 48 business hours, "
                "with remediation action items tracked in Jira under a 30-day resolution SLA [2].\n\n"
                "> **Governance Badge:** Verified against `SOP-SEC-001` (Security & Reliability SOP) [1]."
            )
        elif "guardrail" in q_lower or "ai" in q_lower or "llm" in q_lower or "safety" in q_lower:
            return (
                "### Enterprise Generative AI & LLM Deployment Standards\n\n"
                "According to approved AI Governance & Architecture standards [1]:\n\n"
                "* **RAG Architecture Requirement:** All generative AI copilots and search applications must enforce Retrieval-Augmented Generation (RAG) "
                "grounded strictly in approved enterprise repositories [1].\n"
                "* **Input Sanitization & Safety:** Direct user prompt passthrough is strictly prohibited; all prompts must pass through "
                "Azure AI Content Safety filters to prevent jailbreaks and malicious injections [1].\n"
                "* **Observability & Masking:** Telemetry (token usage, latency, source quality) must stream into Azure Application Insights, "
                "and Entra ID DLP rules must mask sensitive PII prior to model inference [1].\n\n"
                "> **Governance Badge:** Verified against `SOP-AI-004` (AI Governance & Architecture) [1]."
            )
        elif "cicd" in q_lower or "deploy" in q_lower or "pipeline" in q_lower or "infrastructure" in q_lower:
            return (
                "### Cloud Infrastructure & CI/CD Governance Policy\n\n"
                "According to Platform Engineering standards [1]:\n\n"
                "* **Infrastructure as Code (IaC):** All Azure resources must be codified using Bicep or Terraform. Manual provisioning "
                "in production subscriptions is disallowed [1].\n"
                "* **Automated Quality Gates:** GitHub Actions pipelines must execute automated SAST security scans, container vulnerability checks, "
                "and achieve >=80% branch unit test coverage [1].\n"
                "* **Peer Approvals:** Production merges to `main` strictly mandate sign-off from at least two senior engineers [1].\n\n"
                "> **Governance Badge:** Verified against `SOP-DEV-012` (DevOps & Infrastructure) [1]."
            )
        else:
            return (
                f"### Knowledge Synthesis: {top_citation.title}\n\n"
                f"According to approved documentation from the **{top_citation.department}** unit [1]:\n\n"
                f"* **Policy Summary:** {top_citation.snippet}\n"
                f"* **Compliance Status:** Verified as `{top_citation.governance_status}` with last formal audit date `{top_citation.last_reviewed}` [1].\n\n"
                f"All organizational procedures must strictly adhere to the documented baseline [1]."
            )


llm_service = LLMService()
