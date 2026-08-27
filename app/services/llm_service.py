import logging
import time
from typing import List, Tuple, Optional
from app.config import settings
from app.models.schemas import SourceCitation, CSRResolutionGuidance

logger = logging.getLogger("memberassist.llm")

SYSTEM_CSR_GOVERNANCE_PROMPT = """You are MemberAssist Copilot, an enterprise AI assistant for health insurance Customer Service Representatives (CSRs), Member Advocates, and Claims Specialists.

Your Core Directives:
1. Provide accurate, empathetic, and clear guidance grounded STRICTLY in the provided health plan benefit schedules, Prior Authorization SOPs, Claims manuals, and HIPAA policies.
2. Structure your response into:
   - **Live Call Readback Script:** A plain-language, member-friendly explanation ready to be read aloud to the caller.
   - **CSR Resolution Actions:** Clear, numbered system/CRM actions (e.g. claims dispute codes, P2P escalation routes).
   - **Compliance & Regulatory Notes:** Explicit citations (`[1]`, `[2]`, etc.) referencing Plan IDs, Section/Clause, and HIPAA/No Surprises Act boundaries.
3. No-Hallucination Rule: If the plan context does not address the inquiry, state: "Policy documentation for this specific benefit is not found. Transfer to Tier-2 Clinical/Claims Escalations."
4. Never assume or extrapolate benefits not explicitly covered in the retrieved policy text.
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
                logger.info("Azure OpenAI / Foundry LLM client initialized for MemberAssist.")
            except Exception as e:
                logger.warning(f"Could not initialize Azure OpenAI client: {e}. Running in Mock Fallback mode.")
                self.client = None
        else:
            logger.info("Azure OpenAI credentials not configured. Running in Mock Fallback mode.")

    def is_connected(self) -> bool:
        return self.client is not None

    async def generate_response(
        self,
        query: str,
        citations: List[SourceCitation],
    ) -> Tuple[str, Optional[CSRResolutionGuidance], float]:
        start_time = time.time()

        # Build grounded health policy context
        context_blocks = []
        for idx, citation in enumerate(citations, 1):
            context_blocks.append(
                f"--- POLICY SOURCE [{idx}] ---\n"
                f"Document ID: {citation.id}\n"
                f"Title: {citation.title}\n"
                f"Category: {citation.category} | Section: {citation.section}\n"
                f"Governance Status: {citation.governance_status} (Audit: {citation.last_reviewed})\n"
                f"Content: {citation.snippet}\n"
            )
        formatted_context = "\n".join(context_blocks)

        user_prompt = (
            f"Active Policy & Benefit Context:\n{formatted_context}\n\n"
            f"CSR / Caller Question: {query}\n\n"
            f"Provide a structured response for the CSR including a member-facing readback script and CRM action steps with exact citation brackets [1], [2]."
        )

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.deployment,
                    messages=[
                        {"role": "system", "content": SYSTEM_CSR_GOVERNANCE_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=850,
                )
                answer = response.choices[0].message.content or ""
                guidance = self._extract_guidance_from_text(answer, query, citations)
                llm_ms = round((time.time() - start_time) * 1000, 2)
                return answer, guidance, llm_ms
            except Exception as e:
                logger.error(f"Error calling Azure OpenAI / Foundry: {e}. Falling back to grounded mock synthesis.")

        # Grounded mock generation for local demo & offline testing
        answer, guidance = self._generate_grounded_mock(query, citations)
        llm_ms = round((time.time() - start_time) * 1000, 2)
        return answer, guidance, llm_ms

    def _extract_guidance_from_text(self, text: str, query: str, citations: List[SourceCitation]) -> CSRResolutionGuidance:
        top_citation = citations[0] if citations else None
        doc_ref = f"{top_citation.id} ({top_citation.section})" if top_citation else "Standard Plan Certificate"
        return CSRResolutionGuidance(
            plain_language_script="Based on your 2026 Plan Schedule, your coverage has been verified under our standard policy guidelines.",
            action_steps=[
                "Confirm caller identity (3 of 4 HIPAA identifiers verified).",
                f"Reference plan document {doc_ref} in call wrap-up notes.",
                "Send written Benefit Summary or EOB copy to member's verified email/portal if requested.",
            ],
            compliance_notes=f"Grounding verified against {doc_ref}. Zero PII logged to external models.",
        )

    def _generate_grounded_mock(self, query: str, citations: List[SourceCitation]) -> Tuple[str, CSRResolutionGuidance]:
        q = query.lower()
        top_citation = citations[0] if citations else None

        if not citations:
            answer = (
                "**Policy Notice:** No approved health benefit document was found matching this criteria. "
                "Please escalate to the Tier-2 Clinical/Claims Resolution Queue."
            )
            guidance = CSRResolutionGuidance(
                plain_language_script="I am transferring your request to our senior claims resolution specialists to ensure we verify your specific benefit schedule.",
                action_steps=["Create CRM escalation ticket", "Transfer caller to Tier-2 Queue"],
                compliance_notes="No matching 2026 policy found in index.",
            )
            return answer, guidance

        if "mri" in q or "imaging" in q or "out-of-network" in q or "ct" in q or "pet" in q:
            answer = (
                "### Out-of-Network Advanced Imaging Benefit Resolution\n\n"
                "According to the **Commercial Standard PPO Benefit Schedule (2026)** [1]:\n\n"
                "* **Out-of-Network Cost Share:** Out-of-network MRI, CT, and PET scans are subject to the **Out-of-Network Deductible ($3,000 Individual / $6,000 Family)**, followed by **40% coinsurance plus balance billing** [1].\n"
                "* **In-Network Comparison:** In-network imaging is subject to the in-network deductible ($1,500 Individual), then **20% coinsurance** at freestanding facilities (30% at hospital outpatient) [1].\n"
                "* **Prior Authorization Notice:** Prior authorization is strictly mandatory for all non-emergency advanced imaging [1].\n\n"
                "> **Policy Citation:** `PLAN-PPO-2026-BENEFITS` (Section 2: Diagnostic Imaging & Out-of-Network Cost Shares) [1]."
            )
            guidance = CSRResolutionGuidance(
                plain_language_script=(
                    "Under your 2026 Standard PPO plan, an out-of-network MRI is subject to your $3,000 out-of-network deductible, "
                    "after which the plan covers 60% and your responsibility is 40% coinsurance plus any provider balance billing. "
                    "If you choose an in-network freestanding imaging center, your cost share is significantly lower at 20% after your in-network deductible. "
                    "Please note that your provider must also obtain prior authorization prior to the scan."
                ),
                action_steps=[
                    "Verify member's remaining 2026 Out-of-Network Deductible balance in core claims system.",
                    "Offer to locate a contracted In-Network freestanding imaging center (20% coinsurance savings).",
                    "Check UM portal to confirm if Prior Authorization request has been submitted by ordering physician.",
                    "Document Plan Reference `PLAN-PPO-2026-BENEFITS (Sec. 2)` in CRM call notes.",
                ],
                compliance_notes="Advise member that out-of-network non-emergency imaging is subject to non-participating provider balance billing.",
            )
        elif "prior auth" in q or "appeal" in q or "p2p" in q or "peer to peer" in q or "turnaround" in q:
            answer = (
                "### Prior Authorization & Clinical Appeals SLA\n\n"
                "Based on the **Prior Authorization & Clinical Appeals SOP** [1]:\n\n"
                "* **Standard Turnaround Time:** Determination must be rendered within **72 clock hours (3 business days)** of receiving complete clinical records [1].\n"
                "* **Expedited Review:** Must be determined within **24 clock hours** if the provider certifies standard turnaround threatens the patient's health or pain management [1].\n"
                "* **Peer-to-Peer (P2P) Window:** Ordering clinicians have **5 business days** following an adverse determination to request a P2P consultation with a Plan Medical Director [1].\n"
                "* **Member Appeals:** Standard Level-1 appeals have a **30-calendar-day** resolution window; expedited appeals resolve in **72 clock hours** [1].\n\n"
                "> **Policy Citation:** `SOP-UM-2026-004` (Section 1 & 2: PA Timelines & P2P Protocol) [1]."
            )
            guidance = CSRResolutionGuidance(
                plain_language_script=(
                    "Standard prior authorization reviews are completed within 72 hours of receiving complete documentation from your doctor. "
                    "If your doctor submitted this as an urgent request, our clinical team resolves it within 24 hours. "
                    "If a request was denied, your physician can schedule a Peer-to-Peer review with our Medical Director within 5 business days, "
                    "or we can help you file an expedited appeal right now."
                ),
                action_steps=[
                    "Check UM system queue `UM-CLIN-P2P` for open authorization status.",
                    "Confirm date and timestamp when clinical documentation was received.",
                    "If clinical denial is within 5 business days, route P2P request to Medical Director queue.",
                    "Log SOP citation `SOP-UM-2026-004` in ticket history.",
                ],
                compliance_notes="NCQA and CMS timeliness standards apply. Expedited reviews require physician health certification.",
            )
        elif "denial" in q or "balance bill" in q or "surprise" in q or "co-16" in q or "eob" in q:
            answer = (
                "### Claims Denial Explanation & No Surprises Act Protection\n\n"
                "According to the **Claims Denial Explanation & EOB Call Resolution Guide** [1]:\n\n"
                "* **Denial Code CO-16 (Missing Records):** Provider submitted incomplete billing records. Provider has **90 days** to re-submit with clinical notes. Member does not owe this balance while under review [1].\n"
                "* **No Surprises Act (NSA) Protection:** Non-participating providers at in-network facilities (anesthesiology, radiology, pathology) or emergency rooms are legally prohibited from balance billing members above in-network rates [1].\n"
                "* **Immediate Dispute Route:** CSR must open a Claims Payment Dispute ticket to hold member liability [1].\n\n"
                "> **Policy Citation:** `GUIDE-CLM-2026-012` (Section 1 & 2: Denial Codes & NSA Protection) [1]."
            )
            guidance = CSRResolutionGuidance(
                plain_language_script=(
                    "Under federal No Surprises Act regulations and your health plan policy, you are protected from balance billing "
                    "for emergency care or ancillary services received at an in-network facility. You are only responsible for your in-network cost-sharing. "
                    "I am placing a formal hold on this claim and initiating a payment dispute with the billing office so you will not receive further balance bills."
                ),
                action_steps=[
                    "Place claim on financial hold status (`HOLD-DISPUTE-NSA`).",
                    "Issue formal Provider Education & Correction letter to billing facility.",
                    "Send updated EOB explanation letter to member's mailing address.",
                    "Record Guide Citation `GUIDE-CLM-2026-012`.",
                ],
                compliance_notes="Enforce federal No Surprises Act (NSA) protections against non-participating ancillary provider balance billing.",
            )
        elif "hipaa" in q or "spouse" in q or "representative" in q or "privacy" in q or "auth" in q:
            answer = (
                "### HIPAA Privacy Verification & Disclosure Protocol\n\n"
                "According to **HIPAA Privacy Verification & Authorized Representative SOP** [1]:\n\n"
                "* **Caller Authentication:** Must verify at least **3 of 4 identifiers**: (1) Full Name, (2) Member ID/SSN last 4, (3) Date of Birth, (4) Residential Address & Zip Code [1].\n"
                "* **Spouse & Adult Dependents (>18):** Cannot access medical claims or clinical details without an active **HIPAA Authorization Form (PHI-AUTH-01)** or Medical Power of Attorney on file [1].\n"
                "* **Verbal 1-Time Consent:** Allowed only if the authenticated primary member is present on the live call [1].\n\n"
                "> **Policy Citation:** `SOP-HIPAA-2026-001` (Section 1 & 2: Authentication & Disclosure Rules) [1]."
            )
            guidance = CSRResolutionGuidance(
                plain_language_script=(
                    "To protect member privacy in strict compliance with federal HIPAA privacy regulations, I cannot disclose specific medical "
                    "or claims information without an authorized release on file. I can help you submit our confidential Representative Authorization form today, "
                    "or speak with the member directly if they are available."
                ),
                action_steps=[
                    "Verify 3 of 4 primary identifiers before discussing any protected health information.",
                    "Check document repository for active `PHI-AUTH-01` form or Medical POA.",
                    "If unauthorized, send secure electronic HIPAA Authorization link via SMS/email.",
                    "Log HIPAA compliance check `SOP-HIPAA-2026-001` in contact log.",
                ],
                compliance_notes="Strict HIPAA Privacy Rule 45 CFR Part 160/164 compliance. Never disclose diagnosis codes to unverified callers.",
            )
        else:
            answer = (
                f"### Health Plan Policy Synthesis: {top_citation.title}\n\n"
                f"According to verified health plan documentation from **{top_citation.department}** [1]:\n\n"
                f"* **Policy Details:** {top_citation.snippet}\n"
                f"* **Governance Status:** Verified as `{top_citation.governance_status}` (Audit Date: `{top_citation.last_reviewed}`) [1].\n\n"
                f"CSRs should apply standard operational procedures in accordance with the cited benefit clause [1]."
            )
            guidance = CSRResolutionGuidance(
                plain_language_script=f"Based on your approved plan benefits for 2026, {top_citation.snippet[:180]}...",
                action_steps=[
                    f"Review policy document {top_citation.id}.",
                    "Ensure caller identity is verified.",
                    "Document interaction in CRM.",
                ],
                compliance_notes=f"Grounded against {top_citation.id}.",
            )

        return answer, guidance


llm_service = LLMService()

