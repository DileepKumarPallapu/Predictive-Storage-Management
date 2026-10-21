# AEGISSTOR ATLAS — Controlled Experiment Protocol & Sandbox Safety

## 1. Safety Rules for Storage Testing
Running uncontrolled storage I/O benchmarks on production storage systems can cause tail latency spikes, cache eviction, and controller queue starvation.

ATLAS enforces the following non-negotiable safety rules:
1. **Host Disk Protection**: No destructive block commands (`dd`, `mkfs`, `fdisk`, `blkdiscard`) or arbitrary shell executions are permitted.
2. **Dedicated Test Resources**: Physical device trials require an explicitly designated test volume isolated from tenant I/O paths.
3. **Execution Mode Isolation**: Default benchmark runs execute inside simulated sandbox environments (`ISOLATED_TEST_SANDBOX`).
4. **Rate Limiting**: Benchmark generators are clamped to maximum throughput ($500\text{ MB/s}$) and queue depth bounds ($\le 16$) to prevent controller thermal throttling.

---

## 2. Supported Experiment Types

| Experiment Type | Research Purpose | Evaluation Metrics |
|:---|:---|:---|
| `SIM_TO_REAL_COMPARISON` | Quantifies residual gaps between simulator trajectories and actual observations. | MAE, RMSE, Systematic Bias, Horizon Expansion Ratio. |
| `FORECAST_BACKTEST` | Evaluates multi-horizon conformal quantile forecasts against historical traces. | Pinball Loss, Interval Coverage, Interval Width. |
| `WORKLOAD_REPLAY` | Replays recorded diurnal access patterns against test volumes. | Tail Latency P95, IOPS Saturation Point. |
| `MODEL_CALIBRATION` | Tunes simulator physics coefficients (e.g. queue depth weighting) on training data. | Parameter Convergence, Optimization Loss. |
| `ACTION_DURATION_BENCHMARK` | Measures true operational elapsed time of storage actions (e.g. volume resizing). | Duration Minutes, Metadata Pause Time. |
| `INTERVENTION_EFFECT_VALIDATION`| Verifies headroom gain and side-effect bandwidth contention under controlled loads. | Reclaim GB, Secondary Latency Degradation \%. |
