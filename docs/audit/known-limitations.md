# AEGISSTOR — Known Limitations & Operational Boundaries (v3.0)

**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Date:** 2026-10-21  

---

## 1. Operating Mode & Hardware Isolation
- **Shadow Mode Default**: `SHADOW_MODE_ENABLED: true` is strictly enforced. The platform does not issue raw NVMe-oF commands, SCSI unmap commands, or Ceph block device resizes to host hardware. Physical mutations remain intentionally disabled to safeguard production host disks.
- **Simulated Hardware**: Telemetry is generated via the physics-informed deterministic synthetic engine or replayed from historical traces. Real Linux host telemetry is collected strictly in read-only mode via OS virtual filesystems (`/proc/diskstats`, `psutil`).

## 2. Machine Learning Forecasting
- **Extrapolation Bounds**: Differenced Quantile LightGBM models project up to 168 hours (+7 days) ahead with high fidelity. Beyond 14 days, long-range uncertainty expands significantly ($\propto \sqrt{h}$), and the platform will flag forecast intervals with wide-band uncertainty warnings.
- **Cold-Start Requirements**: The forecasting pipeline requires a minimum of 24 contiguous hourly samples to extract reliable lag and cyclical features. When history is shorter than 24 hours, the system automatically falls back to the Seasonal-Naive or Persistence forecasters and logs an `INSUFFICIENT_HISTORY` alert.

## 3. Database & Concurrency
- **Local SQLite Engine**: The default development deployment uses SQLite (`sqlite:///./aegisstor.db`). While suitable for single-node development, production multi-tenant deployments should set `DATABASE_URL` in `.env` to a PostgreSQL 15+ cluster to support high-frequency concurrent telemetry ingestion.
- **In-Memory Ablations**: On-demand scientific ablation runs execute in background threads. On CPU-constrained hosts, running multi-model backtests across 4 devices simultaneously may take 10-15 seconds.

## 4. Network & Authentication
- **CORS Configuration**: By default, CORS allows all origins (`*`) for local paired frontend/backend development. For enterprise deployments, configure `CORS_ORIGINS` in `.env` to the explicit corporate domain.
- **JWT Expiration**: Default access token lifetime is set to 24 hours (`ACCESS_TOKEN_EXPIRE_MINUTES: 1440`). Expired tokens require re-authentication via the Auth modal.
