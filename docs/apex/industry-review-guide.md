# AEGISSTOR APEX — Industry Reviewer & Examiner Guide (Phase 30)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** APEX-REV-001  
**Audience:** Academic Supervisors, External Industry Examiners, and Storage Architecture Reviewers  

---

## 1. Guided 8-Step Examiner Walkthrough

For an efficient 15-minute examination of the live running software:

1. **Executive Overview (`/`):**
   - Inspect the monitored fleet aggregate capacity ($36.38\,\text{TB}$), overall utilization ($69.8\%$), and active runway timeline.
   - Note the **Ember Noir** editorial glassmorphic visual identity and explicit data-mode badge (`SYNTHETIC DEMO DATA`).

2. **Storage Fleet & Topology (`/fleet` & `/omega`):**
   - Review the 4 heterogeneous tiers: NVMe Tier 1 (OLTP), SAS Tier 2 (Analytics), SATA HDD Archive, and Object Storage.
   - Inspect cross-pool dependencies and shared bus contention risks.

3. **ML Prediction Lab & Uncertainty (`/ml-lab` & `/reliability`):**
   - Select `vol-nvme-tier1-db`. View the 24-hour ahead quantile forecast ($p_{10}, p_{50}, p_{90}$).
   - Verify that the confidence band widens over the prediction horizon, reflecting real predictive uncertainty.

4. **Workload Attribution & Bottleneck Forensics (`/oracle`):**
   - Inspect how the Oracle engine attributes I/O pressure across 5 workload profiles (OLTP, Analytics, Backup, Streaming, Residual).
   - Review contention diagnostics showing queue depth spikes correlated with uncoordinated backup jobs.

5. **Evidence-Gated Intervention Studio (`/interventions`):**
   - Compare candidate mitigation scenarios: Cold Data Tiering vs Capacity Expansion vs Workload Rebalancing.
   - Observe the Evidence Gate: actions violating migration lead time or causing secondary pool exhaustion are automatically rejected.

6. **Incident Orchestration & Safe Recovery (`/phoenix`):**
   - Review an active correlated incident.
   - Walk through the human-in-the-loop policy signoff gate.
   - Verify that recovery is declared only after 6 consecutive post-action monitoring cycles confirm stabilization.

7. **Examiner Research Workbench (`/gauntlet`):**
   - Inspect the Claim-to-Evidence Matrix.
   - Every empirical claim links directly to an immutable experiment ID, dataset hash, and ablation study.

8. **Federated Multi-Site Intelligence (`/sovereign`):**
   - Inspect the 4 simulated global sites.
   - Verify the formal privacy boundary: zero raw telemetry leaves local sites; only bounded weight updates ($2.05\,\text{KB}$) are exchanged.

---

## 2. Answers to Essential Architectural Questions

Every major screen in AEGISSTOR is engineered to answer five questions:
1. **What am I looking at?** Clear headers, volume identifiers, tier classifications, and measurement units (GB, MB/s, ms).
2. **Why does it matter?** Financial, capacity-exhaustion, or latency SLA breach consequences are clearly quantified.
3. **What evidence supports the result?** Backed by recorded telemetry timestamps, LightGBM quantile splits, and Atlas discrepancy scores.
4. **What can I do next?** Transparent intervention actions with simulated trade-offs.
5. **What remains uncertain?** Explicit display of prediction intervals ($p_{10} - p_{90}$), simulator assumptions, and unverified causal hypotheses.
