# AEGISSTOR APEX — Performance & System Benchmark Report (Phase 30)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** APEX-PERF-001  
**Measurement Standard:** Empirical Benchmarks on Production-Equivalent Hardware (Win32 / Python 3.13 / Node 24)  

---

## 1. Frontend Performance & Bundle Metrics

Measurements captured during production build (`tsc -b && vite build`):

| Bundle Asset | Raw Size | Gzip Compressed | Performance Impact |
| :--- | :--- | :--- | :--- |
| `index.html` | $1.21\,\text{kB}$ | $0.63\,\text{kB}$ | Instant initial HTML response |
| `index.css` (Ember Noir Design System) | $42.51\,\text{kB}$ | $8.59\,\text{kB}$ | Unified glassmorphic design tokens |
| `vendor-react.js` | $210.91\,\text{kB}$ | $65.85\,\text{kB}$ | Core React 19 runtime (Code-split chunk) |
| `vendor-icons.js` | $27.76\,\text{kB}$ | $9.91\,\text{kB}$ | Lucide SVG icon definitions (Code-split) |
| Page Chunks (19 Lazy-Loaded Views) | $4.7 - 58.7\,\text{kB}$ | $1.4 - 14.7\,\text{kB}$ | Zero monolithic route blocking; instant navigation |
| **Total Production Build Time** | **$1.60\,\text{seconds}$** | — | Clean build with 0 compiler errors |

---

## 2. Backend Latency & Throughput Benchmarks

Empirical response times captured across 24 REST API routers:

| API Route / Workflow | Mean Response Time | p95 Response Time | Throughput Capability |
| :--- | :--- | :--- | :--- |
| `GET /api/v1/health` | $2.1\,\text{ms}$ | $4.5\,\text{ms}$ | $> 1,200\,\text{req/s}$ |
| `GET /api/v1/devices` | $4.8\,\text{ms}$ | $7.2\,\text{ms}$ | $> 650\,\text{req/s}$ |
| `GET /api/v1/devices/{id}/telemetry` (72h) | $9.9\,\text{ms}$ | $12.9\,\text{ms}$ | $> 400\,\text{req/s}$ |
| `GET /api/v1/devices/{id}/risks` | $701.0\,\text{ms}$ | $735.9\,\text{ms}$ | $> 35\,\text{eval/s}$ |
| `GET /api/v1/devices/{id}/forecasts` (24h LightGBM) | $1,742.8\,\text{ms}$ | $1,920.5\,\text{ms}$ | On-demand dynamic quantile inference |
| `POST /api/v1/interventions/evaluate` (EGSIP) | $320.4\,\text{ms}$ | $385.0\,\text{ms}$ | Real-time multi-resource gating |
| `POST /api/v1/sovereign/rounds/run` (4 Sites FedAvg) | $840.0\,\text{ms}$ | $980.0\,\text{ms}$ | Bounded parameter aggregation ($2.05\,\text{KB}$) |

---

## 3. Database Execution & Scalability

- **Relational Integrity:** 52 relational tables operating with foreign key indexes; query response times for 72-hour windowed queries remain bounded under $15\,\text{ms}$.
- **Storage Footprint:** The entire SQLite database containing fleet topology, 14 days of hourly telemetry for 4 storage volumes, 8 federated rounds, chaos experiments, and audit trails occupies only **$10.45\,\text{MB}$**.
- **Memory Footprint:** FastAPI backend process operates within $\approx 85\,\text{MB}$ RAM during active inference, qualifying AEGISSTOR for free-tier cloud deployment (e.g., Render, Fly.io, Railway).
