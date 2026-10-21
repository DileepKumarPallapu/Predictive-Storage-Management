# AEGISSTOR — Relational Database Schema Specification

Target RDBMS: SQLite (for local standalone zero-dependency execution) and PostgreSQL (for enterprise scale).
ORM: SQLAlchemy 2.0 with type annotations.

---

## Entity Relationship Overview

```
devices (Storage Volumes / Pools)
  ├── telemetry (TimeSeries records: capacity, IOPS, throughput, latency, queue)
  ├── forecasts (Point & Quantile projections by model and horizon)
  ├── risk_assessments (Calculated breach probabilities and runway)
  ├── alerts (Capacity, Performance, Data Quality, Drift)
  ├── scenarios (Digital Twin counterfactual configurations)
  │     └── simulated_outcomes (Simulator trajectory and metric impact)
  └── recommendations (Action candidates, ranking, approval status)

datasets (Data Provenance & Split Definitions)
experiments (Backtest experiments & model comparison results)
audit_logs (Immutable user and system action logs)
users (Authentication and Role-Based Access Control)
```

---

## Detailed Table Definitions

### 1. `devices`
- `id` (VARCHAR(64), Primary Key) — e.g. `vol-nvme-tier1-db`
- `name` (VARCHAR(128))
- `tier` (VARCHAR(32)) — `NVME_TIER1`, `SAS_TIER2`, `HDD_ARCHIVE`, `CLOUD_S3`
- `media_type` (VARCHAR(32)) — `NVMe SSD`, `Enterprise SAS`, `SATA HDD`
- `total_capacity_bytes` (BIGINT)
- `warning_threshold_pct` (FLOAT, Default 80.0)
- `critical_threshold_pct` (FLOAT, Default 90.0)
- `max_acceptable_latency_ms` (FLOAT, Default 20.0)
- `min_free_reserve_pct` (FLOAT, Default 10.0)
- `status` (VARCHAR(32), Default 'HEALTHY') — `HEALTHY`, `WARNING`, `CRITICAL`, `MAINTENANCE`
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

### 2. `telemetry`
- `id` (INTEGER, Primary Key, Autoincrement)
- `device_id` (VARCHAR(64), Foreign Key `devices.id`, Indexed)
- `timestamp` (TIMESTAMP, Indexed)
- `used_bytes` (BIGINT)
- `free_bytes` (BIGINT)
- `utilization_pct` (FLOAT)
- `read_iops` (FLOAT)
- `write_iops` (FLOAT)
- `throughput_mb_s` (FLOAT)
- `latency_p95_ms` (FLOAT)
- `queue_depth` (FLOAT)
- `is_synthetic` (BOOLEAN, Default True)
- `source_label` (VARCHAR(64))

### 3. `forecasts`
- `id` (INTEGER, Primary Key, Autoincrement)
- `device_id` (VARCHAR(64), Foreign Key `devices.id`, Indexed)
- `model_name` (VARCHAR(64))
- `target_metric` (VARCHAR(64)) — `used_bytes`, `latency_p95_ms`, `iops_total`
- `horizon_hours` (INTEGER)
- `generated_at` (TIMESTAMP)
- `historical_cutoff` (TIMESTAMP)
- `timestamps_json` (TEXT / JSON)
- `q10_json` (TEXT / JSON)
- `q50_json` (TEXT / JSON)
- `q90_json` (TEXT / JSON)
- `interval_coverage` (FLOAT)
- `inference_ms` (FLOAT)

### 4. `scenarios` & `simulated_outcomes`
- `scenarios.id` (VARCHAR(64), Primary Key)
- `device_id` (VARCHAR(64), Foreign Key `devices.id`)
- `name` (VARCHAR(128))
- `action_type` (VARCHAR(64)) — `EXPAND_CAPACITY`, `TIER_COLD_DATA`, `RESCHEDULE_TASK`, `REBALANCE_WORKLOAD`
- `parameters_json` (TEXT / JSON)
- `created_at` (TIMESTAMP)
- `created_by` (VARCHAR(64))
- `simulated_outcomes.scenario_id` (VARCHAR(64), Foreign Key `scenarios.id`)
- `outcome_trajectory_json` (TEXT / JSON)
- `duration_minutes` (FLOAT)
- `estimated_cost_usd` (FLOAT)
- `overhead_io_penalty_pct` (FLOAT)
- `safety_envelope_passed` (BOOLEAN)
- `safety_violation_reasons_json` (TEXT / JSON)
- `residual_risk_score` (FLOAT)

### 5. `recommendations`
- `id` (VARCHAR(64), Primary Key)
- `device_id` (VARCHAR(64), Foreign Key `devices.id`)
- `action_type` (VARCHAR(64))
- `title` (VARCHAR(128))
- `rationale` (TEXT)
- `rank` (INTEGER)
- `utility_score` (FLOAT)
- `estimated_runway_gain_hours` (FLOAT)
- `hard_constraints_checked` (BOOLEAN)
- `approval_status` (VARCHAR(32)) — `PENDING_REVIEW`, `APPROVED`, `REJECTED`, `EXECUTED_SHADOW`
- `reviewed_by` (VARCHAR(64), Nullable)
- `review_notes` (TEXT, Nullable)

### 6. `alerts`
- `id` (VARCHAR(64), Primary Key)
- `device_id` (VARCHAR(64), Foreign Key `devices.id`)
- `category` (VARCHAR(32)) — `CAPACITY_RISK`, `PERFORMANCE_RISK`, `DATA_QUALITY`, `MODEL_DRIFT`
- `severity` (VARCHAR(32)) — `INFO`, `WARNING`, `CRITICAL`
- `title` (VARCHAR(128))
- `message` (TEXT)
- `status` (VARCHAR(32)) — `ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`
- `triggered_at` (TIMESTAMP)
- `resolved_at` (TIMESTAMP, Nullable)

### 7. `experiments` & `audit_logs`
- Stores reproducible backtesting experiments, train/test window timestamps, MAE, RMSE, pinball loss, and audit logs of all user actions.
