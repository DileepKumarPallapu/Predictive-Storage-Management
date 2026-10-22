# AEGISSTOR FORGE — Security, Safety & Threat Defense (Viva Guide)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Product:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** FORGE-DEF-SEC-001  
**Viva Examination Target:** Fail-Closed Storage Safety, Federated Privacy & Application Security  

---

## 1. Storage Physical Safety Barrier

### Question: "What prevents AEGISSTOR from corrupting or wiping real enterprise storage disks?"
**Defensible Answer:**
1. **Immutable Invariant:** `PHYSICAL_MUTATION_DISABLED = True` is declared in `backend/app/config.py`.
2. **Interface Interception:** The `action_gateway.py` enforces a strict interceptor barrier. Any action request that would invoke OS-level storage alteration (`hdparm`, `sg_format`, `ioctl`, partition resizing) is intercepted and routed exclusively to the Digital Twin sandbox.
3. **Automated Continuous Assertion:** In both `scripts/verify_apex_release_gate.py` and `scripts/run_canonical_demo.py`, Step 20 executes an assertion that `PHYSICAL_MUTATION_DISABLED` is actively `True`.

---

## 2. Federated Learning Threat Model (SOVEREIGN)

### Question: "Does federated learning guarantee complete data privacy?"
**Defensible Answer (Honest Technical Answer):**
- **No:** Standard FedAvg does NOT guarantee complete mathematical privacy because gradients or weight updates can theoretically leak training data under gradient inversion attacks.
- **AEGISSTOR's Multi-Layered Defense:**
  1. **Strict Data Boundary:** Raw telemetry database rows never leave local sites. Only parameter vectors ($W \in \mathbb{R}^8$) are exchanged.
  2. **Adversarial Update Integrity Shield:** Incoming updates are inspected before aggregation:
     - Dimension must match $d=8$.
     - Numerical values must be finite (rejects NaN/Inf poisoning).
     - Norm bound: $||W||_2 \le 1000.0$ (rejects model poisoning attacks).
  3. **Differential Privacy:** An $(\epsilon, \delta)$-bounded Gaussian perturbation mechanism with $L_2$ clipping ($C = 50.0$) is applied to provide formal privacy bounds.

---

## 3. Nexus AI Copilot Boundary

### Question: "Can the AI Copilot execute arbitrary shell commands or SQL queries?"
**Defensible Answer:**
- **No:** Nexus AI operates strictly over deterministic REST tool contracts.
- Prompts cannot generate or execute raw SQL or shell commands. All answers must reference validated database IDs, and any intervention scenario created by the AI enters as a `DRAFT` that requires human operator submission.
