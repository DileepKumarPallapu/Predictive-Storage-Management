# AEGISSTOR FORGE — Industry Examiner Demonstration Script (Viva Guide)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Product:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** FORGE-DEF-DEMO-001  
**Target Duration:** 12 to 15 Minutes Live Walkthrough  

---

## 1. Step-by-Step Live Demonstration Script

| Minute | Screen / Route | Action to Perform | Key Examiner Talking Point |
| :---: | :--- | :--- | :--- |
| **00:00 - 02:00** | **Executive Overview** (`/`) | Point to aggregate capacity ($360\,\text{TB}$ total pool), current utilization, reserve runway timeline ($242.4\,\text{h}$ on NVMe), and explicit `SYNTHETIC DEMO DATA` status badge. | "AEGISSTOR replaces reactive 85% alerts with continuous reserve runway forecasting and causal risk estimation." |
| **02:00 - 04:00** | **Storage Fleet & Topology** (`/fleet`, `/omega`) | Filter fleet by NVMe, SAS, HDD, Cloud tiers. Click on `vol-nvme-tier1-db` to inspect SLA constraints (max latency $20\,\text{ms}$, reserve $10\%$). | "Storage tiers are not isolated silos; AEGISSTOR models shared bus contention and cross-pool dependency propagation." |
| **04:00 - 06:00** | **ML Prediction Lab** (`/ml-lab`) | Inspect the 24h LightGBM forecast. Toggle between $p_{10}, p_{50}, p_{90}$ quantile curves. Point out how the confidence cone broadens with horizon. | "Notice that prediction uncertainty is explicit: the $p_{90}$ upper bound warns operators long before median $p_{50}$ crosses the critical threshold." |
| **06:00 - 08:00** | **Oracle Attribution Forensics** (`/oracle`) | Select `vol-nvme-tier1-db`. View the 5-workload attribution breakdown (OLTP, Analytics, Backup, Streaming, Residual). Highlight queue depth contention spikes. | "Oracle separates baseline transactional write demand from rogue uncoordinated background backup spikes." |
| **08:00 - 10:00** | **Evidence-Gated Intervention Studio** (`/interventions`) | Click "Evaluate Interventions". Compare `TIER_COLD_DATA` against `EXPAND_CAPACITY`. Show the Evidence Gate rejecting actions exceeding lead time. | "Here is our primary research contribution: Evidence-Gated Planning (EGSIP). Infeasible migrations are rejected before they cause downtime." |
| **10:00 - 12:00** | **Phoenix Incident Command** (`/phoenix`) | View an active correlated incident. Review runbook steps, policy signoff requirement, and the 6-cycle recovery verification monitor. | "An action completing successfully is not recovery: Phoenix verifies telemetry stability across 6 consecutive cycles before closing the ticket." |
| **12:00 - 14:00** | **Sovereign Federated Learning** (`/sovereign`) | Show the 4-site decentralized simulation. Point out the $2.05\,\text{KB}$ payload budget and Adversarial Update Integrity Shield. | "Collaborative multi-cluster forecasting without sending raw telemetry rows to a central server." |
| **14:00 - 15:00** | **Examiner Workbench & CLI Proof** (`/gauntlet`) | Switch to terminal and run: `python scripts/run_canonical_demo.py`. Show the 20-step verification pass and SHA-256 fingerprint. | "Every metric on screen is backed by a reproducible cryptographic hash and 120 passing automated tests." |
