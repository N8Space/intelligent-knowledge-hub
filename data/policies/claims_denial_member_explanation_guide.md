# Operational Guide: Claims Denial Explanation & EOB Call Resolution
**Document ID:** `GUIDE-CLM-2026-012`  
**Classification:** Frontline CSR Enablement & Call Scripting  
**Department:** Claims Administration & Member Advocacy  
**Effective Date:** January 1, 2026  
**Regulatory Guardrail:** No Surprises Act (NSA) / Transparency in Coverage  

---

### Section 1: Top Claim Denial Codes & Plain-Language Explanations
* **Denial Code CO-16 (Claim Lacks Information / Incomplete Billing):**
  * *Root Cause:* Missing operative notes, modifier, or primary EOB (COB).
  * *CSR Action:* Verify if records were received. If missing from provider, advise member that provider must submit corrected claim within 90 days.
  * *Member Script:* *"Your provider submitted a bill that was missing specific clinical coding. We have notified their billing office to re-submit with the complete records. You do not owe this balance while under review."*
* **Denial Code PR-96 (Non-Covered Benefit / Cosmetic or Experimental):**
  * *Root Cause:* Service excluded under plan certificate or flagged by medical policy.
  * *CSR Action:* Offer right to file member appeal; provide formal benefit summary section reference.
* **Denial Code CO-242 (Prior Authorization Required but Not Obtained):**
  * *CSR Action:* Check if provider submitted retroactive authorization. If not allowed, advise provider has responsibility to request clinical waiver without billing the member.

---

### Section 2: Balance Billing & No Surprises Act (NSA) Protection
* **Emergency Services:** Non-participating providers and emergency facilities are legally prohibited from balance billing members for emergency care beyond in-network cost-sharing amounts.
* **Inadvertent Out-of-Network Facility Services:** Ancillary providers (anesthesiologists, radiologists, pathologists) at in-network facilities cannot balance bill above in-network deductible/coinsurance rates.
* **CSR Script for Balance Billing Complaints:**
  > *"Under federal No Surprises Act regulations and your plan policy, you are only responsible for your in-network cost-sharing for emergency care or ancillary facility services. I am opening an immediate Claims Payment Dispute and holding your financial liability."*
