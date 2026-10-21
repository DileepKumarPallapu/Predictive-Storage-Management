# AEGISSTOR ATLAS — Reality Calibration & Evidence Intelligence
## System Architecture & Technical Specification

### 1. Vision & Architectural Role
AEGISSTOR ATLAS provides a scientifically grounded mechanism for evaluating whether storage forecasts, Digital Twin counterfactuals, and automated intervention proposals are supported by empirical evidence from actual storage systems.

The core principle of ATLAS is **epistemic humility**: the platform must explicitly differentiate between what it knows from physical measurement and what it estimates through mathematical or simulation models.

```mermaid
flowchart TD
    Physical[Linux /proc/diskstats & Prometheus] --> Connectors[Reality Data Connector Layer]
    Benchmarks[FIO Controlled Traces] --> Connectors
    Synthetic[Offline Benchmark Generator] --> Connectors
    
    Connectors --> Normalizer[Schema Validation & Unit Normalization]
    Normalizer --> Sanitizer[TelemetryStreamSanitizer: Zero Missing Injection Prevented]
    
    Sanitizer --> CalibEngine[Digital Twin Calibration Engine]
    
    subgraph ChronologicalSplit [Chronological Separation: Leakage Prevention]
        TrainWindow[14-Day Calibration Window]
        EvalWindow[7-Day Held-Out Evaluation Window]
    end
    
    CalibEngine --> ChronologicalSplit
    ChronologicalSplit --> Discrepancy[Discrepancy Analysis Service]
    
    Discrepancy --> Residuals[Residuals e_t = y_t - y_hat]
    Discrepancy --> Bias[Systematic Bias & Regime Breakdown]
    Discrepancy --> Drift[Time-Dependent Horizon Drift]
    
    CalibEngine --> Fidelity[Fidelity Assessor & Scope Envelope]
    Fidelity --> Indicators[5-Dimensional Fidelity Indicators]
    
    ActionEvidence[Action-Effect Evidence Model] --> GatedPlanner[Evidence-Gated Recommendation Pipeline]
    Indicators --> GatedPlanner
    
    GatedPlanner --> Outcomes{Intervention Gating}
    Outcomes --> Supported[SUPPORTED_RECOMMENDATION]
    Outcomes --> SafeSim[SAFE_TO_SIMULATE]
    Outcomes --> ReqReview[REQUIRES_HUMAN_REVIEW]
    Outcomes --> ReqEvid[REQUIRES_ADDITIONAL_EVIDENCE]
    Outcomes --> Reject[REJECTED_BY_HARD_CONSTRAINT]
    
    VOE[Value-of-Experiment Planner] --> CandidateExps[Prioritized Next-Best Experiments]
```

### 2. Core Pillars of ATLAS
1. **Reality Data Connector Layer**:
   Typed adapters for Linux kernel diskstats, Prometheus metrics, node_exporter counters, and FIO benchmark block traces with unit normalization and provenance tags (`REAL_HARDWARE`, `PUBLIC_BENCHMARK`, `CONTROLLED_EXPERIMENT`, `SYNTHETIC_SIMULATION`).
2. **Chronological Calibration & Leakage Prevention**:
   Strict chronological partition separating training/calibration data from held-out evaluation periods. Parameter calibration is never performed on the evaluation window.
3. **Sim-to-Real Discrepancy Analysis**:
   Residual series calculation ($e_t = y_t - \hat{y}_t$), systematic bias determination, horizon error drift tracking, and workload regime breakdowns (Read-Intensive, Balanced OLTP, Write-Heavy, High Contention).
4. **Action-Effect Evidence Grounding**:
   Explicit categorization of action effects into simulated counterfactuals, controlled experiments, operational ledger outcomes, and theoretical assumptions.
5. **Digital Twin Fidelity Envelope**:
   Five-dimensional fidelity scorecard measuring Prediction Fidelity, Workload Coverage, Data Quality, Calibration Recency, and Action Evidence. Flags out-of-scope conditions with explicit operational warnings.
6. **Evidence-Gated Recommendations**:
   Gating pipeline ensuring candidate actions with weak evidence or out-of-envelope conditions are tagged for human investigation rather than presented as verified facts.
7. **Value-of-Experiment (VOE) Planner**:
   Ranks empirical follow-up experiments by expected reduction of epistemic uncertainty.
