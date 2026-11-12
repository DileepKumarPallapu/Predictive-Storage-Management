# AEGISSTOR — Database Design (`DATABASE_DESIGN.md`)

**ORM:** SQLAlchemy 2.0 (`backend/app/models/entities.py`)  
**Migrations:** Alembic (`backend/alembic/versions/`)  
**Engines:** PostgreSQL 16 (production / Docker Compose) & SQLite (local/test isolation)

---

## 1. Authentication, Sessions & RBAC Schema
| Table | Purpose | Key Columns & Constraints |
| :--- | :--- | :--- |
| `users` | Registered system accounts | `id` (PK), `username` (UNIQUE), `email` (UNIQUE), `hashed_password` (Argon2id), `role`, `is_active`, `failed_login_attempts`, `locked_until`, `last_login_at`, `password_changed_at` |
| `roles` | Canonical platform roles | `name` (PK: `ADMIN`, `OPERATOR`, `VIEWER`, `AUDITOR`), `description`, `is_system` |
| `permissions` | Fine-grained 58-key catalog | `key` (PK, e.g. `storage.create`), `module`, `description` |
| `role_permissions` | Dynamic role-to-permission grants | `id` (PK), `role_name` (FK `roles.name`), `permission_key` (FK `permissions.key`), `is_allowed` |
| `user_sessions` | Persistent active/revoked sessions | `id` (PK), `user_id` (FK `users.id`), `session_token_hash` (UNIQUE), `csrf_token_hash`, `role_at_issue`, `is_revoked`, `revoked_reason`, `expires_at` |
| `password_reset_tokens` | Single-use hashed reset tokens | `id` (PK), `user_id` (FK `users.id`), `token_hash` (UNIQUE), `expires_at`, `used_at` |
| `login_attempts` | Brute-force & auth history tracking | `id` (PK), `identifier`, `user_id` (FK), `success`, `failure_reason`, `client_ip`, `attempted_at` |
| `revoked_tokens` | Explicitly invalidated JWT JTIs | `id` (PK), `token_jti` (UNIQUE), `revoked_at` |

## 2. Storage Infrastructure & Telemetry Collection
| Table | Purpose | Key Columns |
| :--- | :--- | :--- |
| `storage_systems` | Physical arrays / hosts | `id` (PK), `name`, `vendor`, `location`, `environment` |
| `storage_pools` | Pools inside systems | `id` (PK), `system_id` (FK), `name`, `tier`, `total_capacity_bytes` |
| `devices` | Monitored storage volumes/pools | `id` (PK), `name`, `tier`, `storage_type`, `environment_location`, `total_capacity_bytes`, `warning_threshold_pct`, `critical_threshold_pct`, `max_acceptable_latency_ms`, `status`, `organization_id`, `last_telemetry_at` |
| `resource_relationships` | Topology & provenance edges | `id` (PK), `source_id`, `target_id`, `relationship`, `provenance` |
| `telemetry_connectors` | Linux/Prometheus/API/CSV connectors | `id` (PK), `name`, `connector_type`, `endpoint_url`, `target_storage_id`, `config_json` (secrets redacted in API), `is_enabled`, `last_status`, `last_collected_at` |
| `telemetry` | Validated time-series observations | `id` (PK), `device_id` (FK `devices.id`), `timestamp`, `total_capacity_bytes`, `used_bytes`, `free_bytes`, `utilization_pct`, `read_iops`, `write_iops`, `read_latency_ms`, `write_latency_ms`, `latency_p95_ms`, `throughput_mb_s`, `queue_depth`, `is_synthetic`, `source_label` |
| `ingestion_jobs` | Import & batch audit records | `id` (PK), `storage_id` (FK), `source_type`, `filename`, `idempotency_key`, `status`, `total_rows`, `accepted_rows`, `rejected_rows`, `duplicate_rows`, `errors_json`, `uploaded_by` |
| `data_quality_results` | Preprocessing quality scores | `id` (PK), `device_id` (FK), `completeness_pct`, `duplicate_count`, `outlier_count`, `quality_score`, `decisions_json` |
| `data_reliability_profiles` | Multi-factor telemetry trust | `id` (PK), `storage_id` (FK), `reliability_score`, `reliability_tier`, `completeness_score`, `freshness_score`, `is_stale`, `weights_json` |

## 3. ML Training, Forecasting, Risk, Twin & Governance
| Table | Purpose | Key Columns |
| :--- | :--- | :--- |
| `workload_events` / `workload_regime_events` | Detected regime shifts & bursts | `id`, `storage_id`/`device_id`, `regime_label`, `event_type`, `severity`, `confidence`, `explanation` |
| `model_versions` | Saved ML model artifacts | `id`, `storage_id`, `name`, `model_type` (`LIGHTGBM`, `SARIMAX`, etc.), `version_tag`, `feature_version`, `artifact_path`, `is_active`, `mae`, `rmse`, `interval_coverage`, `trained_at` |
| `model_metrics` | Detailed validation scores | `id`, `model_version_id` (FK), `mae`, `rmse`, `r2_score`, `mape`, `mase`, `pinball_loss`, `is_selected`, `selection_reason` |
| `background_jobs` | Async training job tracker | `id`, `job_type`, `storage_id`, `status`, `result_json`, `error_message`, `triggered_by` |
| `forecasts` | Calibrated multi-horizon forecasts | `id`, `device_id` (FK), `model_version_id`, `model_name`, `horizon_hours`, `horizon_days`, `daily_predictions_json`, `projected_capacity_breach`, `breach_timestamp` |
| `risk_assessments` & `capacity_risk_evaluations` | Runway & exceedance prob. | `id`, `device_id`/`storage_id`, `risk_level`, `estimated_days_to_threshold`, `threshold_crossing_probability`, `details_json` |
| `scenarios` & `simulated_outcomes` | Digital Twin simulations | `id`, `device_id` (FK), `action_type`, `parameters_json`, `safety_envelope_passed`, `residual_risk_score`, `estimated_cost_usd`, `trajectory_json` |
| `alerts` & `operational_assignments` | Alert lifecycle & ownership | `alerts.id`, `device_id`, `severity`, `status`, `acknowledged_by`, `resolution_details`; `operational_assignments.assigned_to_user_id` (FK `users.id`) |
| `recommendations` & `recommendation_verifications` | Decision approvals & checks | `id`, `device_id`, `action_type`, `approval_status`, `reviewed_by`, `details_json` (`submitted_by`) |
| `report_history` | Export audit history | `id`, `report_type`, `format`, `storage_id`, `row_count`, `generated_by`, `created_at` |
| `application_settings` & `api_keys` | Global thresholds, policy & collector keys | `application_settings.key`/`value_json`; `api_keys.key_hash`/`role`/`is_active` |
| `audit_logs` | Tamper-evident hash-chained ledger | `id`, `timestamp`, `user`, `user_id`, `user_role`, `outcome`, `action`, `target_type`, `target_id`, `prev_hash`, `entry_hash` |
