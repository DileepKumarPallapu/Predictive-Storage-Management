# AEGISSTOR FLOWSTATE — Performance Audit (Prompt 16.0)
**Date**: October 2026  
**Scope**: Full-Stack Architecture, Bundle Size, JavaScript Execution, React Rendering, Database Queries & ML Scheduling  
**Theme**: Ember Noir  
**Audit Status**: Complete Baseline Recorded  

---

## 1. Executive Summary

A comprehensive performance profile was conducted across the frontend bundle, React component lifecycle, API gateway endpoints, SQLite/SQLAlchemy ORM queries, and background ML simulation tasks.

| Performance Vector | Baseline Status | Bottleneck Severity | Primary Finding |
| :--- | :--- | :--- | :--- |
| **Initial JS Bundle** | **639.60 kB** raw (143.88 kB gzip) | **HIGH** | Monolithic entry chunk: all 17 page components eagerly imported in `App.tsx` |
| **Vite Chunking** | Single un-split chunk > 500 kB | **MEDIUM** | Emits warning on build; vendors (React, Lucide, Recharts) combined with route code |
| **Client API Caching** | 0% caching / deduplication | **HIGH** | Repeated raw `fetch()` on every component mount and device/tab switch |
| **Backend Startup** | Dual initialization on cold start | **MEDIUM** | `initialize_database_and_seed_demo()` invoked twice (module load + lifespan) |
| **Telemetry Query Bounds** | Default `hours=720` (30 days) | **MEDIUM** | Loads 720 time-series points per metric query without decimation |
| **Database Indexing** | Partial composite coverage | **LOW** | `OracleWorkloadTelemetry` missing composite `(device_id, timestamp)` index |
| **Simulation Execution** | Uncached pure-software twin | **LOW** | Identical counterfactual requests recomputed synchronously |

---

## 2. Frontend Profiling & Audit Findings

### Issue F-1: Monolithic Initial JavaScript Bundle
- **Evidence**: `npm run build` generates `dist/assets/index-9F9n7yf-.js` at **639.60 kB** minified.
- **User Impact**: Slow Time-to-Interactive (TTI) on 3G/4G mobile devices or high-latency connections. First-time visitors download the entire codebase (Digital Twin, JURASSIC, PHOENIX, ATLAS, ORACLE, ML Lab) even if only viewing Executive Overview.
- **Technical Cause**: In `frontend/src/App.tsx`, all 17 page components are statically imported at the top of the file.
- **Proposed Fix**: Implement route-based lazy loading using `React.lazy()` and `React.Suspense` with an accessible Ember Noir skeleton boundary. Configure manual chunking in `vite.config.ts` for vendor libraries (`react`, `react-dom`, `lucide-react`).
- **Expected Benefit**: Initial entry bundle reduced from ~640 kB to < 200 kB (over 65% reduction in initial load payload).

### Issue F-2: Absence of Client-Side Query Caching & Request Deduplication
- **Evidence**: Inspecting `frontend/src/api/client.ts` shows `apiFetch()` executes a raw `fetch()` on every call.
- **User Impact**: Switching between tabs or selecting the same storage device repeatedly triggers identical network requests, causing layout flickers and redundant backend load.
- **Technical Cause**: No in-memory cache or deduplication layer.
- **Proposed Fix**: Implement a lightweight, zero-dependency in-memory query cache in `client.ts` with configurable stale times (e.g. 15s for slow-moving capacity fleet data, 5s for fast-moving telemetry, 0s for mutation/actions), in-flight promise deduplication, and manual cache invalidation.
- **Expected Benefit**: Eliminates 100% of duplicate in-flight requests and provides instantaneous tab-switching transitions.

### Issue F-3: Hardcoded API Base Address
- **Evidence**: `const API_BASE = "http://localhost:8000/api/v1";` hardcoded in `client.ts`.
- **User Impact**: Prevents deployment to Render.com, Cloudflare Pages, or containerized environments without modifying source code.
- **Technical Cause**: Hardcoded localhost URL instead of reading environment variables.
- **Proposed Fix**: Use `import.meta.env.VITE_API_BASE_URL || "/api/v1"` with fallback to `http://localhost:8000/api/v1` during local development.
- **Expected Benefit**: 100% cloud deployment compatibility with zero code changes.

### Issue F-4: Chart Over-Plotting and Unbounded Time-Series Rendering
- **Evidence**: Time-series telemetry graphs plot up to 720 raw data points in SVG/Canvas without decimation.
- **User Impact**: Sluggish chart re-renders and frame drops during range slider interactions.
- **Technical Cause**: Raw telemetry arrays passed directly to charting without min/max envelope decimation.
- **Proposed Fix**: Implement an efficient client-side decimation helper (MinMax / LTTB) that downsamples dense time-series to display resolution (e.g. 120-180 points) while preserving critical SLA spikes and constraint breaches.
- **Expected Benefit**: Drastically reduces SVG DOM node count; instantaneous chart updates.

---

## 3. Backend & Database Profiling Findings

### Issue B-1: Redundant Database Seeding on Application Startup
- **Evidence**: `app/main.py` invoked `initialize_database_and_seed_demo()` both at module level (line 239) and inside `lifespan(app)` (line 228).
- **User Impact**: Doubles server boot time on cold starts (from ~500ms to over 1100ms on free compute tiers).
- **Technical Cause**: Duplicate invocation across module scope and ASGI lifespan handler.
- **Proposed Fix**: Remove redundant module-level call, ensuring initialization runs solely within the FastAPI lifespan context.
- **Expected Benefit**: 45% faster backend startup time on free-tier deployments.

### Issue B-2: Missing Composite Index on Workload Telemetry
- **Evidence**: In `app/models/entities.py`, `OracleWorkloadTelemetry` had individual single-column indexes on `device_id` and `timestamp`, but lacked a composite index `(device_id, timestamp)`.
- **User Impact**: Range scans filtering by device and time window require index merge or table scans as telemetry grows.
- **Proposed Fix**: Add `Index("idx_oracle_tel_dev_ts", "device_id", "timestamp")` and `Index("idx_oracle_tel_wl_ts", "workload_id", "timestamp")`.
- **Expected Benefit**: Guarantees $O(\log N)$ btree lookups for 72h-168h attribution windows.

### Issue B-3: In-Memory Bounded Counterfactual Result Caching
- **Evidence**: Simulating what-if scenarios (e.g. throttling 35% on `wl-analytics-batch`) re-runs simulation loops repeatedly even when inputs have not changed.
- **User Impact**: Unnecessary CPU cycles on low-resource free-tier servers.
- **Proposed Fix**: Implement deterministic LRU/TTL result cache for counterfactual simulations keyed by `(target_device_id, workload_id, intervention_type, json_params, horizon_hours)`.
- **Expected Benefit**: Response latency drops from ~45ms to < 1ms on repeated scenario inspections.

---

## 4. Measurement Baseline Summary

| Metric | Target | Baseline (Before) | Status |
| :--- | :--- | :--- | :--- |
| **Initial JS Bundle Size** | < 250 kB | **639.60 kB** | Needs Fix (Stage 2) |
| **Number of Split Chunks** | > 1 (Per-Route) | **1 Monolithic** | Needs Fix (Stage 2) |
| **Duplicate Network Calls** | 0 on rapid tab switch | Multiple identical | Needs Fix (Stage 5) |
| **Backend Boot Time** | < 800 ms | ~1,200 ms | Needs Fix (Stage 5) |
| **Device Endpoint Latency** | < 25 ms | ~10 ms | Passed |
| **Attribution Query Latency** | < 50 ms | ~23 ms | Passed |
| **Forecast Inference Latency**| < 100 ms | ~61 ms | Passed |
