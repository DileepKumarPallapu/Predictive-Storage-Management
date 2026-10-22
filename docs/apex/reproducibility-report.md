# AEGISSTOR APEX — Reproducibility & Audit Verification Guide (Phase 30)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** APEX-REPRO-001  
**Master Cryptographic Hash:** `8f77347b6391370ed2b94e68efa706232f8d7e5087c440a711a640514dd5bfd6`  

---

## 1. Quick Reproduction Commands

Every metric, benchmark tournament result, and digital twin simulation reported in AEGISSTOR can be independently verified on any standard workstation running Python 3.10+ and Node 18+.

### Step A: Clone & Environment Setup
```bash
git clone <repository_url> aegisstor
cd aegisstor

# Set up Python environment
python -m venv env
# Windows:
.\env\Scripts\activate
# Linux/macOS:
# source env/bin/activate

pip install -r backend/requirements.txt
```

### Step B: Run Automated Backend Test Suite (120 Tests)
```bash
python -m pytest backend/tests -v
```
*Expected Result:* `120 passed in ~41s (100% green)`

### Step C: Execute Master 17-Step End-to-End Release Gate Harness
```bash
python scripts/verify_apex_release_gate.py
```
*Expected Result:* `ALL 17 RELEASE GATE STEPS SUCCESSFULLY VERIFIED (100% PASS)` with matching SHA-256 fingerprint `8f77347b...`.

### Step D: Build & Verify Frontend Application
```bash
cd frontend
npm install
npm run build
```
*Expected Result:* `✓ built in ~1.6s` with zero TypeScript compiler errors.

---

## 2. Seed Fixity & Mathematical Determinism

All stochastic processes, synthetic telemetry generation, and digital twin counterfactual runs are seeded with explicit pseudorandom generator states:
- `seed = 42` for standard simulation sandboxes.
- Telemetry timestamps are monotonically causal.
- Feature extraction enforces zero future leakage ($t \le T_{\text{train}}$).
- The SHA-256 provenance hash computed during independent reproduction runs matches the registered hash bit-for-bit.
