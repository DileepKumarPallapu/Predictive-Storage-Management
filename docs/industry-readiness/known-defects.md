# AEGISSTOR — Known Defects, Limitations & Engineering Gaps
**Document**: Known Defects & Limitations Register  
**Standard**: IEEE 1044 Standard Classification for Software Anomalies  
**Status**: Open Audit Log  

---

## 1. Technical Limitations & Gaps

The following limitations, assumptions, and known engineering gaps are explicitly disclosed to ensure scientific reproducibility and prevent misleading claims:

### Defect / Gap 1: Epistemic Indeterminacy in Hardware-Level NVMe Queue Arbitration
- **Description**: While the platform tracks software queue depth and OS-level I/O arrival rates, modern enterprise NVMe SSDs feature up to 64,000 internal submission queues and hardware wear-leveling arbiters.
- **Limitation**: The software agent cannot observe intra-controller flash channel bus contention without hardware bus analyzers.
- **Mitigation in Platform**: Oracle explicitly flags contention associations as `SUSPECTED_CONTENTION` rather than proven physical causation.

### Defect / Gap 2: Filesystem Metadata & Inode Residual Allocation
- **Description**: In copy-on-write filesystems (e.g. ZFS, Btrfs), space consumed by internal metadata, snapshot reference trees, and journal superblocks is multiplexed at the block layer.
- **Limitation**: Individual user processes cannot be assigned 100% of physical block consumption.
- **Mitigation in Platform**: Method B aggregate reconciliation isolates unexplained growth into `wl-unattributed-residual` (`attribution_available=False`) rather than artificially distributing it across known business workloads.

### Defect / Gap 3: Ephemeral Filesystem Reset on Free Cloud Tiers
- **Description**: Free web hosting containers (e.g. Render.com free tier) do not provide persistent local storage.
- **Limitation**: Local SQLite files (`aegisstor.db`) are wiped on container restart or after 15 minutes of inactivity.
- **Mitigation in Platform**: The platform operates in idempotent `DEMO_MODE=true` with deterministic seed regeneration on startup, and supports an external managed PostgreSQL connection via `DATABASE_URL`.

### Defect / Gap 4: Conversational Copilot is Rule-Based, Not Generative LLM
- **Description**: The platform contains an operational conversational interface, but it uses structured rule-based intent matching rather than an external large language model.
- **Limitation**: Cannot answer arbitrary open-ended natural language questions outside the storage resilience domain.
- **Justification**: Eliminates recurring paid API token costs, prevents hallucinations of non-existent storage devices, and operates completely offline and private.

### Defect / Gap 5: Digital Twin Uses Physics-Based Parametric Queueing ($Q^{1.3}$)
- **Description**: The Digital Twin simulates tail latency using a non-linear power-law function of queue depth rather than cycle-accurate hardware register simulation.
- **Limitation**: Does not model thermal throttling or individual NAND die read-disturb bit flips.
- **Mitigation in Platform**: Atlas measures the exact sim-to-real discrepancy between simulator predictions and held-out physical telemetry, gating recommendations when discrepancy exceeds configured error margins.
