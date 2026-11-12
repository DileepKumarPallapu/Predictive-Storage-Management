# AEGISSTOR — Patent-Grade Storage Resilience Intelligence Architecture Blueprint

**Research Title:** Predictive Storage Capacity and Performance Management Based on Machine Learning  
**Architecture Standard:** 18-Domain Closed-Loop Storage Intelligence Platform  

---

## 1. Existing-System Assessment & Target Upgrades

| Domain | Prior State | Target Engineered State |
| :--- | :--- | :--- |
| **Telemetry Collection** | Static host partition reads & basic batch ingest | Pluggable `ConnectorRegistry` (`LinuxStorageConnector`, `PrometheusConnector`, `CsvHistoricalConnector`, `HttpIngestionConnector`), `X-API-Key` auth, idempotency protection |
| **Data Reliability** | Basic duplicate/outlier check | Explicit 9-factor **Data Reliability Engine** (`0.0..1.0` composite score) with configurable weights gating forecast uncertainty |
| **Workload Behaviour** | Drift score only | Dedicated **Workload Regime & Drift Engine** (OLS trend slopes, autocorrelation, changepoint Z-scores, KS/PSI drift) |
| **ML Forecasting** | Single quantile regressor / SKLearn | **Champion-Challenger Dual-Model Engine**: **LightGBM** (`lightgbm`) vs **SARIMAX** (`statsmodels`) + **Seasonal-Naive** baseline with chronological 3-way split & rolling-origin validation |
| **Uncertainty Calibration** | Fixed heuristic spread | **Split Conformal Prediction** on chronological calibration holdout + data-reliability uncertainty scaling |
| **Capacity Risk** | Linear threshold ratio | **Probabilistic Capacity Risk Engine** computing residual-CDF crossing probability, Brier validation, expected shortfall, exhaustion & safety-threshold dates |
| **Decision Optimisation** | Simulation only | **Constrained Decision Optimizer** evaluating budget, max utilization, min free margin, max latency, transfer cap with binding constraint explanations |
| **Recommendations & Approvals** | Shadow approve/reject | 5-state lifecycle (`PENDING`, `APPROVED`, `REJECTED`, `COMPLETED`, `FAILED`) with strict non-execution guard |
| **Enterprise Backend** | Basic FastAPI | Multi-user RBAC, API keys (`api_keys`), background training jobs (`background_jobs`), rate limiting, retention runner, Alembic migrations |

---

## 2. Database Relationship Diagram (ERD)

```
+---------------+       +------------------+       +-------------------------+
|    users      |1---*  |    api_keys      |       |     revoked_tokens      |
+---------------+       +------------------+       +-------------------------+
        |
        | 1..*
        v
+---------------+1-----*|    telemetry     |       +-------------------------+
|    devices    |------>| (telemetry_recs) |       | telemetry_connectors    |
+---------------+       +------------------+       +-------------------------+
   |   |   |   |                 |
   |   |   |   +---* +--------------------------+
   |   |   |         | data_reliability_profiles|
   |   |   +-------* +--------------------------+
   |   |             | workload_regime_events   |
   |   +-----------* +--------------------------+
   |                 | model_versions & metrics |
   |                 +--------------------------+
   |                        |
   |                        v
   |                 +---------------+       +-------------------------+
   +---------------* |   forecasts   |------>| capacity_risk_evals     |
   |                 +---------------+       +-------------------------+
   |
   +---------------* +---------------+       +-------------------------+
                     |   scenarios   |------>|   simulated_outcomes    |
                     +---------------+       +-------------------------+
```

---

## 3. Data-Flow & Closed-Loop Intelligence Pipeline

```
[Linux Collector / Prometheus / CSV / HTTP API]
                     │  (X-API-Key / JWT + Idempotency-Key + Schema Validation)
                     ▼
        [Persisted Telemetry Table (Immutable Raw Source)]
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
[Data Reliability Engine]  [Workload Regime Engine]
 (9 Factors -> Score 0..1)  (OLS Trend, Changepoints, Periodicity)
         │                       │
         └───────────┬───────────┘
                     ▼
   [Leak-Free Feature Builder (Strictly <= t)]
                     │
         ┌───────────┴──────────────────┐
         ▼                              ▼
 [Model A: LightGBM]            [Model B: SARIMAX]
         └───────────┬──────────────────┘
                     ▼   (+ Seasonal-Naive Benchmark)
 [Chronological Walk-Forward Evaluation & Champion Selection]
                     │
                     ▼
 [Leakage-Safe Conformal Uncertainty Calibrator + Reliability Scaling]
                     │
                     ▼
 [Multi-Horizon P10/P50/P90 Forecasts (1d, 7d, 14d, 30d, 60d, 90d)]
                     │
         ┌───────────┴──────────────────┐
         ▼                              ▼
 [Capacity Risk Engine]       [Digital Twin & Constrained Optimizer]
 (Exhaustion, Shortfall, CDF)  (Budget, Margin, Latency Binding Rules)
                     │
                     ▼
 [Traceable Recommendations -> Approval Workflow -> Alerts & Reports]
```

---

## 4. 18-Domain Component & API Map

1. **Auth & Access Control**: `/api/v1/auth/*`, `/api/v1/users/*`, `/api/v1/admin/api-keys*`
2. **Storage Asset Management**: `/api/v1/storage*`, `/api/v1/devices*`
3. **Telemetry Collection & Connectors**: `/api/v1/connectors*`, `/api/v1/telemetry/live-host`, `/api/v1/telemetry/prometheus/scrape`
4. **Data Ingestion & Validation**: `/api/v1/ingestion/*`, `/api/v1/telemetry/ingest`
5. **Data Quality & Reliability**: `/api/v1/reliability/data/{storage_id}`, `/api/v1/data-quality/{storage_id}`
6. **Workload Behaviour Analysis**: `/api/v1/workload-regime/{storage_id}`
7. **Feature Engineering**: `LeakFreeFeatureBuilder` (`used`, `total`, `free`, `util`, `lags`, `growth`, `rolling`, `IOPS/latency`, `calendar`, `regime`)
8. **ML Model Training & Registry**: `/api/v1/v2/models/train/{storage_id}`, `/api/v1/v2/models/train-async/{storage_id}`, `/api/v1/jobs/{job_id}`
9. **Forecast Generation**: `/api/v1/v2/forecasts/generate/{storage_id}` (`1d, 7d, 14d, 30d, 60d, 90d`)
10. **Uncertainty Calibration**: `ConformalCalibrator` (residuals on chronological holdout scaled by horizon + reliability tier)
11. **Storage Capacity Risk Engine**: `/api/v1/risk/capacity/{storage_id}`
12. **Performance Monitoring**: `/api/v1/performance/{storage_id}`, `/api/v1/performance/compare`
13. **Digital Twin Simulation**: `/api/v1/digital-twin/scenarios*`
14. **Decision Optimisation**: `/api/v1/digital-twin/optimize/{storage_id}`
15. **Recommendations & Approvals**: `/api/v1/recommendations/*` (`PENDING`, `APPROVED`, `REJECTED`, `COMPLETED`, `FAILED`)
16. **Alerts & Notifications**: `/api/v1/alerts/*`
17. **Reporting & Audit**: `/api/v1/reports/*`, `/api/v1/audit`
18. **System Administration**: `/api/v1/settings`, `/api/v1/admin/retention/run`, `/api/v1/health`
