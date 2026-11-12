# AEGISSTOR Authentication, RBAC & Production Setup Guide

## 1. Security Model Overview

AEGISSTOR implements database-backed **Role-Based Access Control (RBAC)** with persistent server-side sessions (`user_sessions`), Argon2id password hashing (`argon2-cffi`), CSRF protection (`X-CSRF-Token` double-submit for cookie-authenticated mutations), failed-login lockout (`>= 5` consecutive invalid attempts -> 15-minute lock), and immutable chained audit logging (`audit_logs`).

- **No silent admin fallback**: Unauthenticated requests to protected endpoints return HTTP `401 Unauthorized`.
- **Server-side authorization**: Authenticated requests missing the required permission key return HTTP `403 Forbidden` and write an `ACCESS_DENIED` entry to `audit_logs`.
- **Live session & role invalidation**: Deactivating a user, changing their role, or completing a password reset immediately revokes active `UserSession` records.

---

## 2. First-Run Administrator Bootstrap (Production)

AEGISSTOR never seeds publicly known default credentials in production. On a clean database (`0` active `ADMIN` users), initialize your first Administrator using **either**:

1. **Web First-Run Setup (`/setup`)**:
   - Navigate to `/setup` in the UI (automatically routed when `/api/v1/auth/setup-status` reports `setup_required: true`).
   - Submit username, valid email, and password (minimum 8 characters).
   - Once created, `/api/v1/auth/setup` is permanently locked (`409 Conflict`).

2. **Environment Variable Bootstrap (Headless / Container Startup)**:
   Set the following environment variables before starting the backend:
   ```env
   SECRET_KEY=<64-char-cryptographic-random-secret>
   AEGISSTOR_BOOTSTRAP_ADMIN_USERNAME=secadmin
   AEGISSTOR_BOOTSTRAP_ADMIN_EMAIL=secadmin@company.com
   AEGISSTOR_BOOTSTRAP_ADMIN_PASSWORD=<strong-unique-password>
   AEGISSTOR_COOKIE_SECURE=true
   ```

---

## 3. Local Development Synthetic Accounts (Opt-In Only)

To seed local test accounts (`admin`, `operator`, `viewer`) strictly on a developer workstation:

```powershell
cd backend
python -m scripts.seed_dev_users
```

Or enable dev seeding during local startup only by explicitly setting `AEGISSTOR_ALLOW_DEV_SEED=true` (keep `false` in staging and production).

---

## 4. Roles & Operational Capabilities

| Role | Intended Persona | Landing Route | Operational Scope |
| :--- | :--- | :--- | :--- |
| `ADMIN` | Platform / Security Administrator | `/admin` | Full operational access + User & Role management, Role Permission Matrix editor, System Security Settings, Audit Governance, API Key / Connector Secret management. |
| `OPERATOR` | Storage Operations Engineer | `/operator` | Full day-to-day operational workflow: Storage registration & edits, CSV/Prometheus telemetry ingestion & collection, Data Quality & Regime analysis, LightGBM & SARIMAX model training, Forecasting, Capacity & Performance Risk evaluation, Alert ack/assign/resolve/reopen, Digital Twin simulation, Optimization, Recommendation review/submit/non-self-approval, Report generation & export. Blocked (`403`) from IAM/User Management, Role Permission changes, Global Security Policies, Audit log deletion, and raw Connector Secrets. |
| `VIEWER` | Executive / Read-Only Stakeholder | `/viewer` | Read-only access to dashboards, inventory, telemetry, quality metrics, forecasts, ML comparison metrics, risks, alerts, Digital Twin simulation history, recommendations, and reports. Blocked (`403`) from all state-changing operations. |
| `AUDITOR` | Governance & Compliance Examiner | `/overview` | Read-only access to operational views plus `audit.read` and `audit.export`. |
