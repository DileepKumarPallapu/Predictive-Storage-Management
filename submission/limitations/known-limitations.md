# Submission Deliverable: Known Limitations & Operational Boundaries

**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document:** SUBMISSION-LIMIT-001  

---

## 1. Technical & Environmental Boundaries

1. **Host Storage Protection Barrier:** AEGISSTOR operates strictly with `PHYSICAL_MUTATION_DISABLED = True`. The platform evaluates interventions inside discrete-event Digital Twin simulation sandboxes and does not execute real block device repartitioning or drive wiping commands on the host machine.
2. **OS Platform Disparity:** Live block device sysfs metric scrapers (`/sys/block/*`) require Linux kernel environments with administrative privileges. On Windows workstations, the system automatically and cleanly falls back to deterministic synthetic generators or recorded trace replay modes.
3. **Model Complexity Boundary:** Sequence forecasting uses autoregressive Ridge regression and LightGBM quantile regression rather than multi-billion parameter deep Transformers. This ensures fast CPU inference ($< 2\,\text{seconds}$) and lightweight federated updates ($2.05\,\text{KB}$ per site round).
4. **Federated Learning Topology:** In the present prototype, multi-site federated storage intelligence is simulated across 4 isolated in-process worker environments rather than a real geo-distributed wide-area network cluster.
5. **Correlation vs Causation in Forensics:** Oracle workload attribution calculates statistical correlations between workload I/O bursts and device queue depths; true physical causality requires isolated hardware testbeds.

---

## 2. Institutional & Legal Disclosures

- **Academic Scope:** This platform is developed as an academic minor engineering project. While designed according to IEEE manuscript standards, official publication remains subject to external peer review.
- **Intellectual Property:** Pre-filing patent disclosure materials are maintained in private non-public directories (`docs/invention/private/`) for review with institutional patent counsel. No unconditional guarantee of patent grant or freedom-to-operate is claimed.
