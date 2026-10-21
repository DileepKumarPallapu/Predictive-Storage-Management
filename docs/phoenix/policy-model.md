# AEGISSTOR PHOENIX — Policy-as-Code Safety Model

## 1. Safety Invariants Specification
The AEGISSTOR Policy-as-Code Gateway enforces mandatory storage safety constraints. These constraints operate as hard mathematical guardrails and cannot be bypassed.

### Non-Bypassable Invariants:
1. **Capacity Reserve Invariant**:
   $$\text{Free Reserve \%} = 100.0 - \text{Projected Utilization \%} \ge \text{Min Free Reserve \% (10.0\%)}$$
   Any action proposal that yields projected capacity utilization $> 90.0\%$ (or leaves free space $< 10.0\%$) is strictly rejected with `REJECTED_BY_POLICY`.
2. **Tail Latency Ceiling Invariant**:
   $$\text{Projected Latency P95 (ms)} \le \text{Max Acceptable Latency (20.0 ms)}$$
   Proposals that would increase tail latency beyond the device or tier threshold are strictly rejected.
3. **Bus / Interconnect Bandwidth Ceiling**:
   $$\text{Aggregate Throughput (MB/s)} \le \text{Fabric Limit (6400.0 MB/s)}$$
   Prevents background rebalancing or backup operations from causing fabric starvation.
4. **Telemetry Freshness Invariant**:
   $$\Delta t_{\text{telemetry}} = t_{\text{now}} - t_{\text{latest}} \le \text{Max Telemetry Age (3600 s)}$$
   For physical/live telemetry, actions cannot be evaluated or dispatched against stale telemetry.

---

## 2. Policy Verdict Resolution Table

| Evaluated Conditions | Policy Verdict | Action Gateway Behavior |
|:---|:---|:---|
| Any hard invariant violated (Capacity, Latency, Bandwidth) | `REJECTED_BY_POLICY` | Hard execution block; operator approval blocked. |
| All invariants satisfied; Human review enabled | `REQUIRES_HUMAN_REVIEW` | Queued in Approval Workspace; requires authorized signoff. |
| All invariants satisfied; Fully automated policy | `ALLOWED_FOR_SIMULATION` | Eligible for automated simulation execution. |
| Missing or stale telemetry readings | `INSUFFICIENT_EVIDENCE` | Action blocked until fresh telemetry heartbeat received. |

---

## 3. High Recommendation Score Isolation
A fundamental design flaw in traditional automated orchestration is that a high machine learning model confidence score (e.g., $0.99$) can cause an orchestrator to execute actions that violate systemic constraints.

In PHOENIX, the recommendation score is strictly decoupled from the safety gate:
```python
# Even if recommendation_score == 0.999:
if violations:
    return "REJECTED_BY_POLICY", violations
```
This invariant was rigorously verified in **Drill C** (`test_drill_c_policy_as_code_hard_safety_gate`).
