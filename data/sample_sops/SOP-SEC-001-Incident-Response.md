# Enterprise Standard Operating Procedure: Major Incident Management & Response
**Document ID:** `SOP-SEC-001`  
**Classification:** Enterprise Internal / Approved  
**Version:** 3.2  
**Owner:** Security & Platform Operations Team  
**Last Audit Date:** 2025-01-15  

---

### 1. Scope & Severity Classifications
* **Severity 1 (Sev-1):** Critical business interruption, entire platform or primary revenue workflow unavailable.
* **Severity 2 (Sev-2):** Significant degradation of a core capability with no immediate workaround.
* **Severity 3 (Sev-3):** Minor degradation, non-critical bugs, or localized issues.

---

### 2. SLA & Response Timelines
1. **Incident Commander (IC) Assignment:** Within **5 minutes** of automated alert triggering for Sev-1 and Sev-2 incidents.
2. **War Room Activation:** IC opens a dedicated Microsoft Teams bridge and invites technical Leads, SRE, and On-Call Engineers.
3. **Executive Broadcast:** Notify VP of Engineering and Head of Operations within **15 minutes**.
4. **Statuspage Broadcast:** Post initial public/internal acknowledgment within **15 minutes**, updating every **30 minutes** thereafter until resolution.

---

### 3. Post-Mortem Requirements
* All Sev-1 and Sev-2 incidents mandate a blameless post-mortem RCA meeting held within **48 business hours**.
* Actionable preventative tasks must be filed in Jira with target resolution within **30 days**.
