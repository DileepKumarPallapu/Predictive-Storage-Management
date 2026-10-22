# AEGISSTOR APEX — Known Limitations & Research Boundaries (Phase 30)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** APEX-LIMIT-001  
**Integrity Standard:** Honest Academic Disclosure — Zero Overclaiming  

---

## 1. Technical & Architectural Boundaries

1. **Host Storage Mutation Safeguard:** AEGISSTOR operates with `PHYSICAL_MUTATION_DISABLED = True`. The platform intentionally refrains from autonomous raw block partition resizing, drive formatting, or hardware RAID reconstruction on host machines. All intervention actions execute within verified Digital Twin simulation sandboxes.
2. **Environmental OS Constraints:** Live block device sysfs metric scrapers (`/sys/block/sdX`) require Linux environments with administrative permissions. When executed on Windows workstations, the platform falls back to synthetic generators and recorded trace replay modes.
3. **Model Complexity Boundary:** Sequence forecasting employs autoregressive Ridge regression and LightGBM quantile trees rather than deep Transformer architectures. This design choice maintains low inference latency ($< 2\,\text{seconds}$) and bounded federated bandwidth ($2.05\,\text{KB}$ per round) suitable for commodity edge storage controllers.
4. **Federated Learning Topology:** In the current prototype, the 4 heterogeneous sites are executed within simulated isolated processes with local data partitions rather than real physical wide-area network nodes.
5. **Correlation vs Causation in Forensics:** The Oracle workload attribution engine computes queue depth contention correlations. While counterfactual simulations estimate causal effects, true physical causality requires controlled experimental hardware isolation.

---

## 2. Regulatory & Intellectual Property Boundaries

- **IEEE Publication Readiness:** While the architecture and empirical results are structured according to IEEE manuscript standards, acceptance in any specific peer-reviewed journal or conference depends on independent peer review.
- **Patent Status:** Pre-filing patent disclosure materials are maintained in `docs/invention/private/` for review with the institutional IP cell and a qualified patent attorney. No guarantee of patent grant or freedom-to-operate is claimed.
