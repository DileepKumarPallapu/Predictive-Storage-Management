# AEGISSTOR FORGE — Known Limitations & Research Boundaries (Release Candidate 21.0)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Product:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** FORGE-LIMIT-001  
**Integrity Standard:** Academic Transparency — Zero Overclaiming  

---

## 1. Technical & Environmental Boundaries

1. **Host Storage Non-Mutation Safeguard:** The platform enforces `PHYSICAL_MUTATION_DISABLED = True` at the core interface level. Destructive raw partition resizing, block zeroing, or disk reformatting are intentionally prohibited on host operating systems. Interventions are evaluated inside validated Digital Twin simulation sandboxes.
2. **OS Platform Scraper Limitations:** Live Linux block layer metric collection (`/sys/block/*`) cannot run on native Windows workstations. The platform falls back cleanly to deterministic synthetic generation and recorded trace replay modes.
3. **Forecasting Model Architecture:** Sequence forecasting relies on autoregressive Ridge regression and LightGBM quantile trees rather than deep Transformer architectures. This conscious design trade-off keeps CPU inference latency $<2\,\text{seconds}$ and federated payload size at $2.05\,\text{KB}$.
4. **Federated Learning Environment:** In the current Release Candidate, multi-site collaboration is simulated across 4 isolated local worker datasets rather than real distributed wide-area network nodes.
5. **Statistical Forensics vs Causation:** Oracle workload attribution calculates statistical correlation between workload bursts and device queue depth spikes; controlled counterfactual experiments provide directional insights rather than formal physical causality.

---

## 2. Institutional Disclosures

- **Academic Examination Scope:** Prepared for an undergraduate / postgraduate minor project review.
- **Intellectual Property Notice:** Pre-filing patent disclosure materials are held in non-public directories (`docs/invention/private/`) for review with institutional patent counsel. No unconditional novelty or patent grant is claimed.
