# AEGISSTOR PHOENIX — Approval Governance & Safe Action Gateway

## 1. Zero Physical Mutations Guarantee
AEGISSTOR is explicitly engineered to prevent unintentional physical damage to host storage controllers and operating filesystems.
- The platform operates strictly in **Shadow Mode** (`SHADOW_MODE_ENABLED: True`).
- The Safe Action Gateway rejects arbitrary shell commands, raw block disk operations (`dd`, `fdisk`, `mkfs`), or file deletions.
- Actions execute either as high-fidelity scenario models in the Digital Twin (`MODE_A_SIMULATE`) or as non-destructive controller diagnostic queries (`MODE_B_DIAGNOSTIC_READONLY`).
- Controlled host execution (`MODE_C_CONTROLLED_EXECUTION`) is disabled by default via `ENABLE_CONTROLLED_EXECUTION = False`.

---

## 2. Cryptographic Proposal Tamper Protection
To ensure that an approved proposal cannot be tampered with prior to dispatch, each proposal generates a SHA-256 fingerprint:
$$\mathcal{H} = \text{SHA256}(\text{action\_type} \parallel \text{target\_resource\_id} \parallel \text{sorted\_json}(\text{parameters}))$$

### Integrity Validation Protocol:
1. Upon proposal generation, $\mathcal{H}$ is stored in `phoenix_action_proposals.proposal_hash`.
2. When an engineer approves the proposal, their identity, timestamp, and rationale are recorded.
3. At the exact moment of execution dispatch, the Safe Action Gateway recomputes $\mathcal{H}'$ from current database values.
4. If $\mathcal{H}' \ne \mathcal{H}$:
   - Status transitions immediately to `INVALIDATED`.
   - Execution is aborted with `ActionGatewayError: Proposal hash mismatch`.
   - Security audit event is logged.

This guarantee is validated in **Drill E** (`test_drill_e_human_approval_integrity_and_tamper_invalidation`).

---

## 3. Idempotent Execution Dispatch
Distributed systems and automated agents often retry network requests. To prevent re-executing steps, callers must provide a unique `idempotency_token`.
- If an execution record with the given token exists, the Action Gateway returns the existing record immediately without re-dispatching steps.
- Validated in **Drill F** (`test_drill_f_idempotency_token_deduplication`).
