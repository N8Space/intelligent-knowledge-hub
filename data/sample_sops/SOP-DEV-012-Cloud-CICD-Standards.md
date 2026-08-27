# Enterprise Platform Engineering: Cloud Provisioning & CI/CD Pipeline Standards
**Document ID:** `SOP-DEV-012`  
**Classification:** Enterprise Internal / Approved  
**Version:** 4.1  
**Owner:** Platform Engineering & DevSecOps  
**Last Audit Date:** 2025-01-20  

---

### 1. Infrastructure as Code (IaC) Mandate
* All Azure resources (App Service, Azure AI Search, Azure OpenAI, Key Vault) must be declared in Bicep or Terraform.
* Manual changes via the Azure Portal in production environments are strictly disabled.

---

### 2. CI/CD Pipeline Quality & Security Gates
* **Automated Unit Testing:** Repositories must maintain $\ge 80\%$ test coverage prior to pull request merges.
* **Security Scanning:** Pipelines must run Trivy/Snyk container scanning and Bandit SAST checks on all commits.
* **Peer Reviews:** Merges to `main` require approval from at least two senior platform engineers.
* **Deployments:** Azure App Service and Container App deployments must utilize blue/green deployment slots or rolling zero-downtime updates.
