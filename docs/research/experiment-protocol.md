# AEGISSTOR — Empirical Experiment Protocol & Reproducibility Standard
**Module:** Evidence-Gated, Multi-Resource Storage Intervention Planner  
**Project:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Version:** 1.0.0 (Research Artifact for Prompt 17.0 Phase 7)

---

## 1. Experimental Environment & Hardware Specifications

To guarantee exact reproducibility across heterogeneous environments, all benchmarks and experiments are conducted under documented, bounded parameters:

* **Host Architecture:** x86_64, Windows 11 Enterprise (compatible with Linux Ubuntu 22.04 LTS).
* **Execution Runtime:** Python 3.13.14 (CPython).
* **Package Dependencies:**
  * `fastapi >= 0.115.0`
  * `sqlalchemy >= 2.0.0`
  * `pydantic >= 2.0.0`
  * `pytest >= 9.1.1`
  * `numpy >= 1.26.0`
  * `scipy >= 1.11.0`
* **Database Engine:** SQLite 3 with Write-Ahead Logging (`WAL` mode) and foreign keys enabled.
* **Deterministic Seeds:**
  * Python random seed: `42`
  * NumPy seed: `42`
  * Forecast simulation horizon: `72` hours (hourly steps $\Delta t = 1.0\,\text{h}$).

---

## 2. Telemetry Dataset Provenance & Synthesized Workload

The experimental evaluations are benchmarked against standardized storage topologies representing high-density enterprise tiers:

1. **Volume 1 (`vol-nvme-tier1-db`):**
   * Class: Enterprise NVMe Solid-State Drive (Tier-1 OLTP Workload).
   * Total Capacity: 10,000 GB (10.0 TB).
   * Critical Ceiling Threshold: 90.0% (9,000 GB).
   * Baseline Utilization: 70.0% (7,000 GB) under steep diurnal growth trajectory.
   * Interconnection: Shared PCIe Gen4 x8 Switch `sw-pcie-root0`.

2. **Volume 2 (`vol-ssd-tier2-app`):**
   * Class: SAS SSD (Tier-2 Application & Log Storage).
   * Total Capacity: 24,000 GB (24.0 TB).
   * Critical Ceiling Threshold: 85.0% (20,400 GB).
   * Interconnection: Connected to Shared SAS HBA Bus `hba-sas-shared0`.

3. **Intervention Action Catalog:**
   * $A_1$: **Online Pool Block Allocation (+3TB)** ($T_{\text{exec}} = 1.0\,\text{h}$, Cost = \$120, Shared Bus Contention Penalty = +5%).
   * $A_2$: **Workload Rebalancing (35% IOPS Relocation)** ($T_{\text{exec}} = 0.25\,\text{h}$, Cost = \$15, Contention Penalty = -12%).
   * $A_3$: **Reschedule Batch Job to Off-Peak (+4h Shift)** ($T_{\text{exec}} = 0.1\,\text{h}$, Cost = \$5, Contention Penalty = -25%).
   * $A_4$: **Tier Cold Snapshot Data to S3** ($T_{\text{exec}} = 3.5\,\text{h}$, Cost = \$45, Contention Penalty = +18%).
   * $A_0$: **Maintain Existing Configurations (Do Nothing)** ($T_{\text{exec}} = 0.0\,\text{h}$, Cost = \$0, Contention Penalty = 0%).

---

## 3. Step-by-Step Reproduction Instructions

### Step 1: Environment Activation
```bash
cd backend
# Verify active python runtime
python --version
# Expected: Python 3.11+ / 3.13+
```

### Step 2: Database Initialization & Verification
```bash
python run.py --dry-run-check
# Or directly execute test suite to verify model schemas
python -m pytest tests/test_evidence_gated_planner.py -v
```

### Step 3: Execute Empirical Baseline and Ablation Benchmarks
```bash
python scripts/run_research_benchmarks.py
```
**Expected Terminal Output:**
* Baseline evaluation table listing Baselines A through F with lead time, false alarm rate (FAR), missed breach rate, and residual risk.
* Ablation study summary listing Ablations 0 through 7.
* Generation of `docs/industry-readiness/benchmark_empirical_raw.json`.

### Step 4: Verify Full Regression Suite
```bash
python -m pytest -q
```
**Expected Result:** `101 passed` in ~40 seconds.

---

## 4. Evaluation Metrics Formal Definitions

1. **Lead Time Feasibility Indicator ($\mathbf{1}_{\text{feasible}}$):**
   $$\mathbf{1}_{\text{feasible}}(a, h^*) = \begin{cases} 1 & \text{if } T_{\text{exec}}(a) < h^* \\ 0 & \text{if } T_{\text{exec}}(a) \ge h^* \end{cases}$$
2. **False Alarm Rate (FAR):**
   $$\text{FAR} = \frac{\text{False Positives}}{\text{False Positives} + \text{True Negatives}}$$
3. **Missed Breach Rate (MBR):**
   $$\text{MBR} = \frac{\text{False Negatives}}{\text{False Negatives} + \text{True Positives}}$$
4. **Action Net Utility Score ($U(a)$):**
   $$U(a) = \Delta \text{Runway}(a) \cdot \left(\frac{\text{Fidelity}}{100}\right) - \left(\frac{\text{ContentionPenalty}}{100} \cdot 100\right) - \left(\frac{\text{CostUSD}}{10}\right)$$
   Actions with $T_{\text{exec}}(a) \ge h^*$ or downstream topology saturation are disqualified ($U(a) = -\infty$).
