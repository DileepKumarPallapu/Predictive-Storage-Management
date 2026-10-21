# AEGISSTOR GAUNTLET — One-Click Reproduction Guide
**Audience:** Technical Reviewers, Academic Supervisors, and Independent Examiners  
**Standard:** Prompt 18.0 Part 9 (One-Click Reproduction Standard)  

---

## 1. Reproduction Workflow Overview

GAUNTLET provides an explicit reproduction mechanism that recreates past benchmark runs, checks numerical drift against defined tolerance thresholds, and emits a structured comparison report without overwriting prior records.

```
+-----------------------------------------------------------------------------------+
| 1. Select Run ID   -->   2. Verify Manifest Hash   -->   3. Bounded Re-execution |
|                                                                                   |
| 4. Extract Metrics -->   5. Compute Relative Drift -->   6. Evaluate Tolerance    |
+-----------------------------------------------------------------------------------+
```

---

## 2. CLI Reproduction (Command Line)

To reproduce a benchmark directly using the Python environment:

```bash
cd backend

# Execute the Gauntlet reproduction suite
python -c "from app.database import SessionLocal; from app.services.gauntlet_service import GauntletService; db = SessionLocal(); res = GauntletService.reproduce_benchmark(db, 'grun-canonical-cap-001', tolerance_pct=3.0); print(res['report_md']); db.close()"
```

### Expected Output
```markdown
# Reproduction Verification Report: grun-canonical-cap-001
**Reproduced Run ID:** repro-20261021...
**Examiner / Verifier:** examiner_reviewer
**Status:** REPRODUCED_WITHIN_TOLERANCE (Max Drift: 0.00% vs Limit: 3.00%)

## Numerical Comparison Table
| Metric | Original Value | Reproduced Value | Drift (%) | Within Tolerance? |
| :--- | :---: | :---: | :---: | :---: |
| `mae_gb` | 14.82 | 14.82 | 0.00% | YES |
| `rmse_gb` | 19.45 | 19.45 | 0.00% | YES |
| `coverage_pct` | 86.4% | 86.4% | 0.00% | YES |
| `interval_width_gb` | 64.20 | 64.20 | 0.00% | YES |
```

---

## 3. UI Reproduction (Examiner Workbench)

1. Open the dashboard at `http://localhost:5173`.
2. Navigate to **Gauntlet Research & Audit** (`/gauntlet` in sidebar under *6. RESEARCH*).
3. Select **Tab 7: One-Click Reproduction** (or click the "Reproduce" button on any past run card in Tab 3).
4. Set the acceptable drift tolerance (default: `3.0%`).
5. Click **Re-run**.
6. The system executes the benchmark in a memory-isolated process and renders the live numerical delta table with color-coded pass/drift indicators.

---

## 4. Understanding Numerical Drift & Tolerances

* **Deterministic Components:** Data splits, persistence forecasts, and heuristic rule calculations exhibit **0.00% drift** when executed with fixed random seeds.
* **Stochastic Components:** Multi-threaded tree ensemble regressors (HistGradientBoosting / LightGBM) may exhibit small floating-point variations across different CPU architectures (AVX-512 vs AVX2) or BLAS libraries.
* **Tolerance Boundary:** A relative drift $\le 3.0\%$ is accepted as scientifically equivalent. Any drift exceeding $3.0\%$ triggers `REPRODUCED_WITH_DRIFT`, prompting the examiner to investigate runtime library discrepancies.
