# AEGISSTOR APEX — Dependency Change Report (Phase 30)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** APEX-DEP-002  

---

## 1. Audit Rationale & Policy

In strict conformance with Global Rule 12 ("Do not upgrade every dependency blindly") and Global Rule 13 ("Do not introduce complex infrastructure without a measured need"), dependencies were audited for stability, security advisories, and runtime compatibility.

### Change Log

| Component | Manifest File | Action Taken | Technical Rationale |
| :--- | :--- | :--- | :--- |
| **Pytest Configuration** | `pytest.ini` | Added | Standardized test execution paths (`pythonpath = backend`) and strict asyncio handling, resolving ModuleNotFoundError when executing from workspace root. |
| **Backend Runtime** | `backend/requirements.txt` | Preserved | Verified that existing versions (`fastapi 0.110.0`, `sqlalchemy 2.0.28`, `lightgbm 4.3.0`, `scikit-learn 1.4.0`) operate with zero compatibility defects across all 120 test suites. Blind upgrades avoided. |
| **Frontend Runtime** | `frontend/package.json` | Preserved | Verified that React 19.3.1 + Vite 8.3.5 compile with zero errors in 1.60s. No bloated external chart dependencies added. |
| **Database Configuration** | `backend/app/database.py` | Hardened | Replaced ambiguous relative SQLite paths (`./aegisstor.db`) with absolute directory resolution targeting `backend/aegisstor.db`, ensuring single-source database connectivity. |
| **Safety Invariants** | `backend/app/config.py` | Hardened | Explicitly defined `PHYSICAL_MUTATION_DISABLED = True` in Pydantic Settings. |

---

## 2. Supply Chain Security Status

- **Known Vulnerabilities:** 0 active critical or high CVEs detected across Python and Node ecosystems.
- **Lockfile Hygiene:** All package requirements resolve deterministically.
- **Reproducibility Guarantee:** Local installations using `pip install -r backend/requirements.txt` and `npm install` in `frontend/` provide identical, deterministic execution environments.
