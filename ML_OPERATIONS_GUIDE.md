# AEGISSTOR — ML Operations Guide (Phase 6)

## 1. Dual-Model Champion-Challenger Architecture
- **Models:** LightGBM (`LGBMRegressor`) + SARIMAX / `HistGradientBoostingRegressor` + `RandomForestRegressor` (`backend/app/ml/champion_challenger.py`, `backend/app/ml/sklearn_engine.py`).
- **Leakage-Safe Calibration:** Split-conformal / quantile prediction intervals (`q10`, `q90`) calibrated on out-of-sample residuals.
- **Selection Rule:** Challenger replaces Champion only when validation/calibration-aware composite score improves; failed training never deactivates the current Champion.

## 2. Durable Artifact Storage & Integrity
- **Storage Abstraction:** `DurableObjectStorage` (`backend/app/services/object_storage.py`) uploads `.joblib` bundles to S3-compatible object storage (`s3://<bucket>/<prefix>/models/...`) when `OBJECT_STORAGE_BUCKET` and credentials are set, or `local://` in local dev.
- **SHA-256 Checksum Verification:** Every saved model records `artifact_sha256` and `artifact_uri` in `ModelVersion.feature_schema_json`. Loading verifies the SHA-256 digest via `object_storage.ensure_local_file(...)` and raises `ValueError` on mismatch (verified in `test_object_storage_checksum_and_tamper_detection`).

## 3. Background Worker Execution & Crash Recovery
- **Entrypoint:** `python worker.py` (Render Background Worker).
- **Stages:** `QUEUED -> VALIDATING_DATA -> PREPARING_FEATURES -> TRAINING -> EVALUATING -> SAVING_MODEL -> COMPLETED` (or `FAILED`).
- **Crash Recovery:** `worker.recover_stale_jobs()` marks abandoned `RUNNING` jobs as `FAILED` after `WORKER_STALE_JOB_TIMEOUT_SEC` (`600s`) so partial models are never promoted.
