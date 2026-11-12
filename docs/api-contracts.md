# AEGISSTOR — API Contracts Specification (v1)

Base URL: `/api/v1`

---

## 1. System & Health
- `GET /api/v1/health`
  Response:
  ```json
  {
    "status": "ok",
    "version": "1.0.0",
    "mode": "demo" | "replay" | "live",
    "database": "connected",
    "collector_status": "healthy",
    "models_loaded": 3,
    "timestamp": "2026-10-21T13:40:00Z"
  }
  ```

- `GET /api/v1/system/mode`
- `POST /api/v1/system/mode`
  Body: `{"mode": "demo" | "replay" | "live"}`

---

## 2. Storage Fleet & Devices
- `GET /api/v1/devices`
  Query params: `tier`, `pool_id`, `health_status`, `search`
  Response: List of `StorageDeviceSummary` with current utilization, IOPS, latency, and reserve runway.

- `GET /api/v1/devices/{device_id}`
  Detailed metadata, physical pool, disk tech (NVMe/SAS/HDD/Cloud), hard constraint thresholds.

- `PATCH /api/v1/devices/{device_id}/thresholds`
  Update device specific warning/critical capacity thresholds and latency limits.

---

## 3. Telemetry Ingestion & Querying
- `GET /api/v1/devices/{device_id}/telemetry`
  Query params: `metric` (used_bytes, free_bytes, iops_read, iops_write, throughput_mb, latency_p95_ms, queue_depth), `start_time`, `end_time`, `sampling_interval_min`
  Response:
  ```json
  {
    "device_id": "vol-nvme-01",
    "metric": "used_bytes",
    "is_synthetic": true,
    "total_capacity_bytes": 10995116277760,
    "timestamps": ["2026-10-20T00:00:00Z", ...],
    "values": [7420102000000, ...],
    "missing_intervals": []
  }
  ```

- `POST /api/v1/telemetry/ingest`
  Ingest live or synthetic telemetry batch with schema and range validation.

- `GET /api/v1/telemetry/export`
  Export telemetry in CSV format for research and diagnostics.

---

## 4. Multi-Horizon Forecasting & Uncertainty
- `GET /api/v1/devices/{device_id}/forecasts`
  Query params: `target_metric`, `model_type` (`lightgbm_quantile`, `seasonal_naive`, `persistence`), `horizon_hours` (e.g. 24, 72, 168)
  Response:
  ```json
  {
    "device_id": "vol-nvme-01",
    "target_metric": "used_bytes",
    "model_name": "LightGBM Multi-Quantile Regressor v1.2",
    "forecast_horizon_hours": 72,
    "generated_at": "2026-10-21T13:30:00Z",
    "historical_cutoff": "2026-10-21T13:00:00Z",
    "timestamps": ["2026-10-21T14:00:00Z", ...],
    "q10": [7500000000000, ...],
    "q50": [7550000000000, ...],
    "q90": [7630000000000, ...],
    "hard_constraint_value": 9895604649984,
    "calibration_interval_coverage": 0.885,
    "inference_latency_ms": 14.2
  }
  ```

---

## 5. Risk Assessment & Reserve Runway
- `GET /api/v1/devices/{device_id}/risks`
  Computes capacity breach probability, latency SLA breach probability, and estimated Reserve Runway:
  ```json
  {
    "device_id": "vol-nvme-01",
    "current_capacity_pct": 82.4,
    "runway_hours_estimate": 46.5,
    "runway_hours_lower_bound": 38.0,
    "runway_hours_upper_bound": 61.2,
    "risk_level": "ELEVATED",
    "capacity_breach_prob_24h": 0.12,
    "capacity_breach_prob_72h": 0.78,
    "latency_breach_prob_24h": 0.04,
    "risk_contributors": [
      {"factor": "Analytical Nightly ETL Write Spike", "impact_score": 0.65},
      {"factor": "Diurnal Workload Volume Growth", "impact_score": 0.28}
    ]
  }
  ```

---

## 6. Digital Twin & Counterfactual Simulator
- `POST /api/v1/scenarios`
  Create a new counterfactual simulation:
  ```json
  {
    "name": "Offload Cold Analytics to S3 Archive",
    "device_id": "vol-nvme-01",
    "action_type": "TIER_COLD_DATA",
    "parameters": {
      "tier_target": "s3-glacier-or-cold-pool",
      "data_volume_gb": 1500,
      "migration_rate_mb_s": 150
    }
  }
  ```

- `POST /api/v1/scenarios/{scenario_id}/run`
  Executes the deterministic digital twin simulator and returns:
  - Base forecast vs simulated counterfactual forecast
  - Action duration estimate
  - Resource and I/O overhead during migration
  - Estimated financial cost
  - Hard constraint compliance status
  - Side effects and simulator limitations notes

---

## 7. Recommendations & Governance
- `GET /api/v1/devices/{device_id}/recommendations`
  Ranked list of feasible actions evaluated against the Hard Safety Envelope.
- `POST /api/v1/recommendations/{rec_id}/approve`
  Operator human approval (records audit trail).
- `POST /api/v1/recommendations/{rec_id}/reject`
  Operator rejection with required rationale.

---

## 8. Experiments, Reliability & Audit
- `GET /api/v1/experiments` / `POST /api/v1/experiments`
  Run backtesting experiments comparing baselines vs quantile ML.
- `GET /api/v1/models/reliability`
  Drift scores, conformal coverage diagnostics, interval widths.
- `GET /api/v1/alerts` / `POST /api/v1/alerts/{alert_id}/acknowledge`
- `GET /api/v1/audit`
  Immutable log of approvals, mode changes, threshold updates.

---

## 9. Enterprise Modules (v2 Endpoints — `/api/v1/...` and `/api/...`)
- **Authentication & Users**:
  - `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`, `POST /api/v1/auth/register`, `POST /api/v1/auth/change-password`
  - `GET/POST /api/v1/users`, `PATCH/DELETE /api/v1/users/{user_id}` (`ADMIN` only)
- **Storage Inventory CRUD**:
  - `GET /api/v1/storage`, `GET /api/v1/storage/{id}`, `POST /api/v1/storage`, `PUT /api/v1/storage/{id}`, `DELETE /api/v1/storage/{id}?confirm=true`
- **Data Ingestion & Preprocessing Quality**:
  - `GET /api/v1/ingestion/template`, `POST /api/v1/ingestion/csv/preview`, `POST /api/v1/ingestion/csv/import`
  - `POST /api/v1/ingestion/manual`, `GET /api/v1/ingestion/jobs`, `GET /api/v1/ingestion/jobs/{job_id}/errors`
  - `GET /api/v1/data-quality`, `GET /api/v1/data-quality/{storage_id}`
- **Dual-Model ML Engine (`RandomForestRegressor` + `HistGradientBoostingRegressor`) & Runway**:
  - `POST /api/v1/models/train/{storage_id}`, `GET /api/v1/models`, `GET /api/v1/models/{storage_id}`
  - `POST /api/v1/forecasts/generate/{storage_id}?horizon_days=30`, `GET /api/v1/forecasts/{storage_id}`, `GET /api/v1/forecasts/{storage_id}/runway`
- **Performance Monitoring & Risk Alerts**:
  - `GET /api/v1/performance/{storage_id}?start_date=...&end_date=...`
  - `POST /api/v1/alerts/evaluate/{storage_id}`, `POST /api/v1/alerts/{id}/acknowledge`, `POST /api/v1/alerts/{id}/resolve`, `POST /api/v1/alerts/{id}/reopen`
- **Digital Twin Lifecycle**:
  - `POST /api/v1/digital-twin/scenarios`, `GET /api/v1/digital-twin/scenarios/{id}`, `PUT /api/v1/digital-twin/scenarios/{id}`, `DELETE /api/v1/digital-twin/scenarios/{id}`
  - `POST /api/v1/digital-twin/compare`, `GET /api/v1/digital-twin/scenarios/{id}/export`
- **Recommendations, Reports & Settings**:
  - `GET /api/v1/recommendations`, `POST /api/v1/recommendations/generate/{storage_id}`
  - `GET /api/v1/reports/types`, `GET/POST /api/v1/reports/generate?report_type=...&format=json|csv|pdf`, `GET /api/v1/reports/history`
  - `GET/PUT /api/v1/settings`, `GET /api/v1/health`
