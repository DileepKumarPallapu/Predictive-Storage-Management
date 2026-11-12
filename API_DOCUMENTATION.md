# AEGISSTOR — REST API Reference (`API_DOCUMENTATION.md`)

**Base Prefix:** `/api/v1` (OpenAPI interactive schema available at `/docs`)  
**Authentication:** `Authorization: Bearer <jwt>` OR `HttpOnly` cookie `aegisstor_session` + `X-CSRF-Token` on mutations, OR `X-API-Key` for telemetry ingestion collectors. Unauthenticated access to protected routes returns HTTP `401`. Missing RBAC permissions return HTTP `403`.

---

## 1. Authentication, Sessions & Access Control
| Method & Path | Permission / Auth | Purpose |
| :--- | :--- | :--- |
| `GET /api/v1/auth/setup-status` | Public | Returns `{ needs_setup, setup_required, setup_token_required }` |
| `POST /api/v1/auth/setup` | Public (locked after 1st Admin) | Bootstraps first `ADMIN` user (Argon2id hashed) |
| `POST /api/v1/auth/login` | Public | Authenticates username or email -> returns JWT, CSRF token, permissions, `landing_route` & sets `HttpOnly` cookie |
| `POST /api/v1/auth/logout` | Authenticated | Revokes `UserSession` & clears cookies |
| `GET /api/v1/auth/me` | Authenticated | Returns active user profile, effective `permissions[]`, `landing_route` |
| `POST /api/v1/auth/forgot-password` | Public | Creates expiring single-use SHA-256 reset token |
| `POST /api/v1/auth/reset-password` | Public (token) | Sets new Argon2id password, unlocks account & revokes active sessions |
| `POST /api/v1/auth/change-password` | Authenticated | Changes own password & revokes prior sessions |
| `GET /api/v1/auth/sessions` | Authenticated | Lists active/revoked sessions for user |
| `DELETE /api/v1/auth/sessions/{id}` | Authenticated | Revokes a specific session |
| `GET /api/v1/auth/login-history` | Authenticated | Lists login attempts & lockout events |
| `GET /api/v1/permissions/catalog` | `users.assign_role` | Lists 58-key catalog & persisted `role_matrix` |
| `PUT /api/v1/permissions/roles/{role}` | `users.assign_role` | Updates permitted permissions for `OPERATOR` / `VIEWER` / `AUDITOR` |
| `GET / POST /api/v1/users`, `PATCH / DELETE /api/v1/users/{id}` | `users.read/create/update/deactivate` | Admin CRUD, live role switch/deactivation revokes sessions immediately |
| `POST /api/v1/users/{id}/revoke-sessions`, `trigger-reset`, `GET audit` | `users.*` | Admin session revocation, out-of-band reset token issuance, per-user audit inspection |

## 2. Storage Infrastructure & Telemetry Collection
- `GET /api/v1/overview` (`storage.read`), `GET /api/v1/operator/dashboard` (`storage.read`)
- `GET / POST /api/v1/storage` (`storage.read` / `storage.create`), `GET / PUT / DELETE /api/v1/storage/{id}` (`storage.read/update/delete`), `GET /api/v1/storage/topology` (`storage.read`)
- `PATCH /api/v1/storage/{id}/thresholds` (`risk.configure`)
- `GET /api/v1/connectors` (`integrations.read`), `POST / DELETE /api/v1/connectors` (`integrations.configure`), `PUT /api/v1/connectors/{id}` (`telemetry.configure`, secret modification guarded by `integrations.manage_secrets`), `POST /api/v1/connectors/{id}/test` & `/collect` (`telemetry.collect`)
- `GET / POST / DELETE /api/v1/admin/api-keys` (`integrations.manage_secrets`)

## 3. Telemetry Ingestion, Quality & Workload Intelligence
- `GET /api/v1/devices/{id}/telemetry` (`telemetry.read`), `POST /api/v1/telemetry/ingest` (`telemetry.ingest`), `GET /api/v1/telemetry/records` (`telemetry.read`), `GET /api/v1/telemetry/export` (`telemetry.read`)
- `GET /api/v1/ingestion/template` (`ingestion.export`), `POST /api/v1/ingestion/csv/preview` (`ingestion.preview`), `POST /api/v1/ingestion/csv/import` (`ingestion.commit`), `POST /api/v1/ingestion/manual` (`telemetry.ingest`), `GET /api/v1/ingestion/jobs` (`quality.read`), `GET /api/v1/ingestion/jobs/{id}/errors` (`ingestion.export`)
- `GET /api/v1/data-quality` & `/{id}` (`quality.read`), `GET/POST /api/v1/reliability/data/{id}` (`quality.read/process`)
- `GET/POST /api/v1/workload-regime/{id}` (`workload.read/analyse`), `/api/v1/oracle/*` (`workload.read/analyse`)

## 4. Machine Learning, Forecasting, Risk & Performance
- `POST /api/v1/v2/models/train/{id}` & `/v2/models/train-async/{id}` (`models.train`), `POST /api/v1/models/train/{id}` (`models.train`), `GET /api/v1/jobs/{job_id}` (`models.read`)
- `GET /api/v1/v2/models/by-family`, `GET /api/v1/v2/models/reliability`, `GET /api/v1/v2/models/{id}`, `GET /api/v1/models` (`models.read`)
- `POST /api/v1/v2/forecasts/generate/{id}` & `/forecasts/generate/{id}` (`forecasts.generate`), `GET /api/v1/v2/forecasts/{id}` & `/forecasts/{id}` (`forecasts.read`)
- `GET /api/v1/risk/capacity/{id}` (`risk.read`), `POST /api/v1/risk/capacity/{id}` (`risk.evaluate`), `GET /api/v1/forecasts/{id}/runway` (`risk.read`), `GET /api/v1/devices/{id}/risk-assessment` (`risk.read`)
- `GET /api/v1/performance/compare` & `/performance/{id}` (`performance.read`)

## 5. Digital Twin, Decision Optimization, Alerts, Reports & Audit
- `GET / POST /api/v1/digital-twin/scenarios` (`digital_twin.read/create`), `PUT / DELETE /api/v1/digital-twin/scenarios/{id}` (`digital_twin.update/delete`), `POST /api/v1/digital-twin/compare` (`digital_twin.read`), `GET /api/v1/digital-twin/scenarios/{id}/export` (`digital_twin.export`), `POST /api/v1/digital-twin/optimize/{id}` (`optimisation.execute`)
- `GET /api/v1/recommendations` (`recommendations.read`), `POST /api/v1/recommendations/generate/{id}` (`recommendations.review`), `POST /api/v1/recommendations/{id}/submit` (`approvals.submit`), `POST /api/v1/recommendations/{id}/approve` (`approvals.approve`, non-self-approval enforced), `POST /api/v1/recommendations/{id}/reject` (`approvals.reject`)
- `GET /api/v1/alerts` (`alerts.read`), `POST /api/v1/alerts/evaluate` (`risk.evaluate`), `POST /api/v1/alerts/{id}/acknowledge` (`alerts.acknowledge`), `POST /api/v1/alerts/{id}/assign` (`alerts.assign`), `POST /api/v1/alerts/{id}/resolve` (`alerts.resolve`), `POST /api/v1/alerts/{id}/reopen` (`alerts.reopen`), `POST /api/v1/alerts/{id}/escalate` (`alerts.assign`)
- `GET /api/v1/reports/types` & `/history` (`reports.read`), `GET /api/v1/reports/generate?format=json|csv|pdf` (`reports.read` + `reports.export`), `POST /api/v1/reports/generate` (`reports.generate`)
- `GET /api/v1/settings` (`settings.read`), `PUT /api/v1/settings` (`settings.update`), `GET /api/v1/audit` (`audit.read`), `DELETE /api/v1/audit` (`403 Forbidden`), `GET /api/v1/auth/audit/verify-chain` (`audit.export`)
- `GET /api/v1/health` (public health probe), `GET /api/v1/metrics` (Prometheus scrape endpoint)
