# AEGISSTOR — Dependency Change Report (v3.0)

**Date:** 2026-10-21  
**Project:** AEGISSTOR Storage Resilience Intelligence Platform  

---

## 1. Summary of Changes

| Package | Ecosystem | Previous State | New State | Motivation / Architectural Justification | Breaking Changes Reviewed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `alembic` | Python | Installed in env, unpinned in requirements | `alembic>=1.13.0` | Required for database migrations and schema evolution | None. Backward compatible with SQLAlchemy 2.0 |
| `pyjwt` | Python | Missing | `pyjwt>=2.9.0` | Implements RFC 7519 cryptographic JWT tokens for user session and RBAC | None. Replaces mock header strings |
| `bcrypt` | Python | Missing | `bcrypt>=4.1.0` | Secure one-way salt-hashed passwords for user authentication store | None. Cryptographically secure standard |
| `prometheus-client` | Python | Missing | `prometheus-client>=0.20.0` | Exposes `/api/v1/metrics` in Prometheus format for storage telemetry scraping | None. Standard Prometheus exposition |
| `react` & `react-dom` | JavaScript | `^19.3.1` | `^19.3.1` | Maintained modern React 19 runtime with ErrorBoundary support | None. Fully verified |
| `vite` | JavaScript | `^8.3.4` | `^8.3.4` | Verified builds in 533ms | None. Stable build pipeline |
| `lucide-react` | JavaScript | `^1.61.0` | `^1.61.0` | Iconography for CommandPalette and AuthModal | None. Modular SVG imports |

---

## 2. Verification Status
- Python backend test suite: **31 / 31 tests passed** (including new auth, RBAC, tracing, and Prometheus metric tests).
- Frontend production bundle: **`tsc -b && vite build` passed with zero errors** (1,954 modules transformed, 352 kB JS bundle).
