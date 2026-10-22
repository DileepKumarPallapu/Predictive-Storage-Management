# AEGISSTOR — Industry Minor Project Submission Package

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Product:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Release Candidate:** APEX / FORGE 21.0  
**Submission Date:** October 2026  
**Verification Gate Status:** 100% Passed (120/120 Tests | 20/20 Canonical Workflow Steps)  
**Master Cryptographic Hash:** `e26dcda4d2d45b67f9f0bc4978a3397434772f9e28fd6991f0d5eb3ce23d3638`  

---

## 1. Submission Overview

This submission package contains the complete academic and industry examination deliverables for **AEGISSTOR**. The system demonstrates a fully functional, reproducible, and scientifically defensible storage intelligence and incident recovery platform.

```
submission/
├── README.md                          # Master submission overview (this file)
├── architecture/                      # Topology, data flows, and subsystem boundaries
│   └── architecture-overview.md
├── installation/                      # Clean installation and local reproduction instructions
│   └── setup-and-reproduction.md
├── test-reports/                      # Complete test outcomes and 20-step verification proof
│   └── test-and-gate-verification.md
├── results/                           # Empirical benchmark tournament and baseline results
│   └── research-and-baselines.md
└── limitations/                       # Transparent boundaries and technical trade-offs
    └── known-limitations.md
```

---

## 2. Key Examination Credentials

- **Backend API:** FastAPI running on `http://127.0.0.1:8000` (Swagger docs at `/docs`).
- **Frontend Dashboard:** React 19 + TypeScript on `http://127.0.0.1:5173` (**Ember Noir** design system).
- **Core Verification Commands:**
  ```bash
  # 1. Run all 120 automated backend tests:
  python -m pytest backend/tests -v

  # 2. Run the 20-step canonical demonstration workflow:
  python scripts/run_canonical_demo.py
  ```

---

## 3. Important Safety & IP Notice

- **Host Safety Guard:** Physical disk mutation is strictly disabled (`PHYSICAL_MUTATION_DISABLED = True`). Host hardware drives are never modified.
- **Pre-Filing IP Confidentiality:** In compliance with patent review rules (e.g. Indian Patents Act Section 3(k)), confidential patent disclosure drafts are held privately and excluded from public version control.
