# AEGISSTOR GAUNTLET — Known Limitations & Technical Boundaries
**Standard:** Prompt 18.0 (Parts 1, 4, 5, 6, 7, 8, 17)  
**Status:** Explicit Public Disclosure for Industry Reviewers  

---

## 1. Primary Technical Limitations

In accordance with strict academic and industry examiner standards, the following limitations are explicitly disclosed:

### 1. NVMe SSD Internal Queue Opacity
* **Deficit:** Standard block telemetry (e.g. `iostat`, OS queue depth) reflects host-level queueing but cannot directly observe internal SSD flash translation layer (FTL) state.
* **Impact:** High-intensity write bursts occasionally induce internal garbage collection (GC) cycles and write amplification. These cause transient p99 latency spikes that cannot be predicted purely from host I/O arrival rates.
* **Mitigation:** The system flags internal flash latency anomalies as uncalibrated when host queue depth remains low while device latency rises.

### 2. Software-Simulated Interconnect Fabric Bounds
* **Deficit:** Physical SAN switches (Fibre Channel / InfiniBand / PCIe switches) do not all expose unified out-of-band telemetry APIs without proprietary vendor licensing.
* **Impact:** Cross-device interconnect contention bounds ($\text{Load}_{\text{post}}(B) \le \text{Capacity}(B)$) are evaluated against synthetic topology definitions mapped in the `Omega` graph model rather than live ASIC switch telemetry.
* **Mitigation:** Clearly labeled in the Capabilities Register as *"Demonstration only"* for physical firmware control.

### 3. Telemetry Missingness Boundary ($> 20\%$)
* **Deficit:** Conformal prediction intervals rely on historical distribution calibration. When telemetry packet loss exceeds 20% over a rolling 72-hour window, non-conformity scores degrade significantly.
* **System Action:** Rather than producing uncalibrated predictions, the Evidence-Sufficiency Gate automatically trips and shifts the system into `FALLBACK_TO_MANUAL_REVIEW`.

### 4. Absence of Real Physical Mutation Actuators
* **Deficit:** For system safety, physical block reallocation commands (e.g. LVM `lvextend`, ZFS `zpool add`, AWS EBS `ModifyVolume`) are simulated in memory using the Digital Twin engine.
* **Impact:** The system proves *decision feasibility* under modelled constraints but does not execute physical mutations against physical flash controller firmware.

### 5. Multi-Year Cloud Tiering Cost Claims
* **Deficit:** Claim `claim-gnt-004` (45% cost reduction) is derived from synthetic multi-tier rate cards. Longitudinal 12-month billing data from live enterprise clusters is not yet attached to the local testbed.
* **System Action:** Claim `claim-gnt-004` is classified as `UNVERIFIED` and excluded from publication conclusions until empirical billing telemetry is logged.
