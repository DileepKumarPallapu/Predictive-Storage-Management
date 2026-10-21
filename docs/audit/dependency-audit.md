# AEGISSTOR — Dependency Audit & Runtime Compatibility Report

**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Audit Date:** 2026-10-21  
**Runtime Environment:** Python 3.13.14 (Win32), Node.js v24.14.1, npm 11.11.0  

---

## 1. Python Backend Dependencies Audit

| Package | Installed / Declared | Target Version | Status / Notes | Action Taken |
| :--- | :--- | :--- | :--- | :--- |
| `fastapi` | `>=0.110.0` | `0.115.0` | Compatible with Python 3.13 | Kept declared range |
| `uvicorn` | `>=0.28.0` | `0.30.6` | High performance ASGI server | Kept declared range |
| `pydantic` | `>=2.6.0` | `2.9.2` | V2 schema validation | Kept declared range |
| `pydantic-settings` | `>=2.2.0` | `2.5.2` | Settings management | Kept declared range |
| `sqlalchemy` | `>=2.0.28` | `2.0.35` | Core ORM and engine | Kept declared range |
| `alembic` | *(Installed but missing from requirements.txt)* | `>=1.13.0` | Required for database migrations | **Added to requirements.txt** |
| `pandas` | `>=2.2.0` | `2.2.3` | Time-series processing | Verified binary compatibility |
| `numpy` | `>=1.26.0` | `2.1.2` | Numerical computing | Python 3.13 compatible |
| `scikit-learn` | `>=1.4.0` | `1.5.2` | ML estimators & metrics | Python 3.13 compatible |
| `lightgbm` | `>=4.3.0` | `4.5.0` | Gradient boosting for quantiles | HistGradientBoosting fallback available if OpenMP missing |
| `pytest` | `>=8.0.0` | `8.3.3` | Test suite runner | Verified 25 tests pass |
| `httpx` | `>=0.27.0` | `0.27.2` | Async & TestClient HTTP requests | Kept declared range |
| `python-multipart`| `>=0.0.9` | `0.0.12` | Form-data parsing | Kept declared range |
| `pyjwt` | *Missing* | `>=2.9.0` | JWT token encode/decode for RBAC | **Added for Phase 12 Security** |
| `passlib[bcrypt]` or `bcrypt` | *Missing* | `>=4.1.0` | Password hashing for user store | **Added for Phase 12 Security** |
| `prometheus-client` | *Missing* | `>=0.20.0` | Prometheus `/metrics` exporter | **Added for Phase 6 Telemetry** |

---

## 2. Frontend Dependencies Audit

| Package | Installed Version | Status / Notes | Action Taken |
| :--- | :--- | :--- | :--- |
| `react` | `^19.3.1` | Modern React 19 runtime | Supported |
| `react-dom` | `^19.3.1` | Modern React 19 DOM | Supported |
| `vite` | `^8.3.4` | Vite 8 bundler | Verified builds in 704ms |
| `typescript` | `~6.0.3` | Strict typechecker | Passed `tsc -b` with 0 errors |
| `tailwindcss` | `^3.4.17` | Utility-first CSS | Centralized tokens in config |
| `lucide-react` | `^1.61.0` | Iconography | Lightweight, accessible SVG |
| `clsx` | `^2.1.1` | Class string utility | Supported |
| `tailwind-merge` | `^3.7.0` | Class merging | Supported |
| `echarts` & `echarts-for-react` | *Optional* | Interactive telemetry time-series | Evaluated for optional rich charting; custom SVG fan chart remains primary low-overhead baseline |

---

## 3. Security & Vulnerability Check

1. **Host Mutation Prevention**: Zero host disk writes or destructive benchmarks exist in codebase (`SHADOW_MODE_ENABLED: true`).
2. **SQL Injection**: All database queries strictly use SQLAlchemy 2.0 parameterized queries (`select(...)`, `filter(...)`); zero string interpolation in queries.
3. **CORS Configuration**: Restricted to configurable `CORS_ORIGINS` (default `http://localhost:5173`).
4. **Token Handling**: Moving from unauthenticated mock user headers to cryptographic JWT bearer tokens with expiration and signature verification.
