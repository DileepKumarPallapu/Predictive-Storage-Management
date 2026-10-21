# AEGISSTOR FLOWSTATE — Free-Tier Cloud Limitations & Durability Notice
**Module**: FLOWSTATE Hosting Governance  
**Environment**: Free Cloud Tiers (Render, Railway, Fly.io, Neon)  
**Status**: Disclosed & Governed  

---

## 1. Hosting Ephemerality & Persistence Boundaries

When deployed on free cloud hosting services, administrators and operators must understand the structural physical constraints:

### Free Web Service Spin-Down (Cold Starts)
- Free instances automatically spin down to zero compute after 15 minutes of inactivity to conserve resources.
- The next incoming request triggers a container cold start taking approximately **30 to 50 seconds**.
- **FLOWSTATE Safeguard**: The frontend displays an informative connecting state rather than an unhandled network error during cold starts.

### Ephemeral Filesystem Reset
- On Render and similar free web containers, the local container filesystem is **ephemeral**.
- Any SQLite database file (`aegisstor.db`) created locally in the container is deleted when the container restarts or re-deploys.
- **FLOWSTATE Safeguard**: AEGISSTOR never pretends that lost ephemeral data still exists. In `DEMO_MODE=true`, the platform deterministically regenerates baseline storage telemetry, workloads, and alert states with identical seeds.
- **Production Recommendation**: For durable persistence, connect an external managed PostgreSQL database (e.g. Supabase, Neon, or Render PostgreSQL) by supplying the `DATABASE_URL` environment variable.

### Memory Cap (512 MB RAM)
- Free tier containers provide 512 MB of total system RAM.
- **FLOWSTATE Safeguard**: Uvicorn runs with a single lean worker process (`--workers 1`), model weights and simulation arrays are streamed, and telemetry queries default to bounded time horizons, ensuring the backend stays safely under ~120 MB RAM.

---

## 2. Zero-Cost Maintenance Protocol

To keep the platform operational indefinitely without incurring expenses:
1. **Periodic Data Export**: Use ORACLE, ATLAS, and PHOENIX report export tools (`.csv` and `.md`) to archive incident ledgers and hypothesis histories locally before maintenance windows.
2. **Deterministic Seed Verification**: Synthetic telemetry generators use fixed seeds (`seed=42`), ensuring that all chart trends, step changepoints, and reserve runway breach projections remain 100% reproducible across cold restarts.
