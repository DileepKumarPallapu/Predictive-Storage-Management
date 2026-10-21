# AEGISSTOR — Acceptance Criteria & Verification Checklist

## 1. Core Platform Capabilities
- [ ] **Deterministic Synthetic Telemetry**: Generates realistic multi-tier storage traces with diurnal patterns, write bursts, queue spikes, and synthetic indicators.
- [ ] **Multi-Horizon Forecasting**:
  - Persistence, Seasonal-Naive, and Quantile LightGBM models.
  - Multi-quantile outputs ($q_{10}, q_{50}, q_{90}$) showing widening uncertainty fan.
  - Zero future data leakage during lag creation and model training.
- [ ] **Reserve Runway & Risk Assessment**:
  - Calculates point-in-time breach probabilities for capacity and tail latency.
  - Computes remaining runway hours with confidence interval bounds.
- [ ] **Storage Resilience Digital Twin**:
  - Simulates 5 distinct scenarios: `DO_NOTHING`, `EXPAND_CAPACITY`, `TIER_COLD_DATA`, `RESCHEDULE_TASK`, `REBALANCE_WORKLOAD`.
  - Enforces Hard Safety Envelope (e.g. latency caps, minimum reserve floor).
  - Explicitly tags simulated trajectories as simulator estimates, not measured physical reality.
- [ ] **Intervention Studio & Recommendation Governance**:
  - Ranks actions transparently using multi-objective utility.
  - Rejects actions that breach hard safety constraints.
  - Human approval workflow (Approve / Reject with rationale) in Shadow Mode.
- [ ] **Research & Model Reliability**:
  - Calibration diagnostics (coverage vs nominal confidence).
  - Drift detection using residual error tracking.
  - Reproducible backtesting experiment runner with MAE, RMSE, Pinball Loss, and lead-time metrics.

## 2. User Experience ("Obsidian Aurora")
- [ ] Professional, calm, scientific aesthetic with dark (#080D18) and light theme tokens.
- [ ] 12 fully functional views with real navigation and zero dead buttons.
- [ ] Scientific canvas/SVG charts rendering historical solid line, forecast median, confidence band, limit line, and scenario overlay.
- [ ] Responsive, accessible, and fast (<200ms API response time).
