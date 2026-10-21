# AEGISSTOR SOVEREIGN — Experiment Protocol & Reproduction Standards
**Standard:** Prompt 19.0 Part 9 (Workbench) & Part 15 (Scientific Validation)  
**Target Environment:** Local Python 3.13.14, FastAPI REST, SQLite WAL  

---

## 1. Experimental Environment & Parameter Matrix

* **Runtime:** Python 3.13.14 (CPython)
* **Random Seed:** `42` (Fixed for deterministic synthetic generators and noise sampling)
* **Feature Dimension:** $d = 8$
* **Regularization Parameter ($\alpha$):** $1.0$ (Ridge L2 penalty)
* **Temporal Split:** 70% Train, 15% Validation, 15% Holdout Test
* **Simulated Sites:**
  1. `site-us-east-oltp`: OLTP E-Commerce NVMe Tier-1 ($n = 480$ train samples)
  2. `site-eu-west-analytics`: Analytics SAS Tier-2 ($n = 480$ train samples)
  3. `site-ap-south-edge`: Retail Edge Branch Store ($n = 120$ train samples)
  4. `site-sa-east-backup`: Cumulative Backup Disaster Target ($n = 480$ train samples)

---

## 2. Command Line Reproduction

### A. Run Automated Pytest Suite
```bash
cd backend
python -m pytest tests/test_sovereign_federated.py -v
# Expected: 10 passed in ~4s
```

### B. Execute Full Baseline Tournament via Python CLI
```bash
python -c "from app.database import SessionLocal; from app.services.sovereign_service import SovereignService; db = SessionLocal(); res = SovereignService.run_collaborative_tournament(db); print(res['scientific_findings']); db.close()"
```

### C. Trigger Collaborative Federated Round via cURL
```bash
curl -X POST "http://localhost:8000/api/v1/sovereign/rounds/run" \
     -H "Content-Type: application/json" \
     -d '{"round_number": 1, "aggregation_strategy": "RELIABILITY_AWARE"}'
```

---

## 3. Evaluated Baselines

1. **Baseline A (Local-Only):** Each site trains and predicts strictly on its own telemetry without inter-site communication.
2. **Baseline B (Conventional FedAvg):** Global model parameters aggregated using sample weighting ($w_k = n_k / N$).
3. **Baseline C (Personalized Adaptation):** Convex combination of local weights and global FedAvg parameters ($W_{\text{pers}} = 0.5 W_{\text{local}} + 0.5 W_{\text{global}}$).
4. **Baseline D (Reliability-Aware Aggregation):** Coordinator weights updates based on local validation RMSE and reliability score, downweighting drifted nodes.
