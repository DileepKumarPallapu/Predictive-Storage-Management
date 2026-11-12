# AEGISSTOR — Security & Access Control Architecture (`SECURITY.md`)

## 1. Password Security & Storage
- Primary password hashing uses **Argon2id** (`argon2-cffi` `PasswordHasher`). Legacy bcrypt hashes are verified seamlessly via backward-compatible verification if present.
- Passwords are never stored or returned in plaintext in API responses or logs. Minimum password length is **8 characters** on `/auth/setup`, `/users`, `/auth/reset-password`, and `/auth/change-password`.

## 2. First-Run Administrator Bootstrap
- No insecure default credentials (`admin/admin`, `admin123`) are seeded in production deployments.
- On an empty database (`0` active `ADMIN` accounts), the initial administrator must be created either via:
  1. Protected `/setup` UI or `POST /api/v1/auth/setup` (optionally guarded by `AEGISSTOR_SETUP_TOKEN` env var), which permanently locks (`403`) once an administrator exists.
  2. Headless environment bootstrap (`AEGISSTOR_BOOTSTRAP_ADMIN_USERNAME`, `AEGISSTOR_BOOTSTRAP_ADMIN_EMAIL`, `AEGISSTOR_BOOTSTRAP_ADMIN_PASSWORD`).

## 3. Session Lifecycle, Revocation & CSRF Protection
- `POST /api/v1/auth/login` creates a persistent row in `user_sessions` (storing SHA-256 `session_token_hash` and `csrf_token_hash`), returns an HS256 JWT + CSRF token, and sets an `HttpOnly` cookie (`aegisstor_session`).
- Cookie-authenticated mutating requests (`POST`, `PUT`, `PATCH`, `DELETE`) MUST supply a matching `X-CSRF-Token` header; requests missing or mismatching the CSRF token receive HTTP `403`.
- **Fail-Closed Auth**: `get_current_user()` returns HTTP `401 Unauthorized` when missing credentials, inactive users, expired/revoked `UserSession`, revoked JWT `jti`, or tokens issued prior to `user.password_changed_at`. There is **zero silent fallback to `admin`**.
- Deactivating a user, changing their role, triggering a password reset completion, or clicking **Revoke Sessions** immediately marks active `user_sessions` rows `is_revoked = True`.

## 4. Brute-Force Lockout & Password Recovery
- Consecutive failed login attempts increment `user.failed_login_attempts` and append to `login_attempts`.
- Reaching `>= 5` consecutive failures activates a 15-minute `locked_until` window, returning HTTP `429 Too Many Requests`.
- Password reset uses SHA-256 hashed, 15/30-minute expiring single-use tokens in `password_reset_tokens`. Completing reset clears lockouts and revokes all active user sessions.

## 5. Central DB-Backed RBAC & Non-Self-Approval
- All protected endpoints use `require_permission("<key>")` or `require_method_permission("<read_key>", "<write_key>")` evaluated dynamically against persisted `role_permissions`.
- Failed permission checks return HTTP `403 Forbidden` and write an `ACCESS_DENIED` (`outcome="DENIED"`) entry to `audit_logs`.
- Operators are explicitly blocked (`403`) from IAM (`/users*`), Role Permissions (`/permissions/*`), global system settings (`PUT /settings`), API key management (`/admin/api-keys*`), registering global connector credentials (`POST/DELETE /connectors`), mutating connector secrets, verifying full cryptographic audit chains, or deleting `audit_logs` (`DELETE /audit*` always returns `403` and logs tamper attempts).
- **Non-Self-Approval Rule**: Operators cannot self-approve recommendations they submitted (`403 SELF_APPROVAL_BLOCKED`) unless an Administrator explicitly enables `approval_policy.operator_can_self_approve`.

## 6. Immutable Audit Ledger
- Every authentication event, resource change, ingestion, ML training run, forecast, risk evaluation, alert assignment/resolution, approval, report export, and access denial records `prev_hash` + SHA-256 `entry_hash` in `audit_logs`. Administrators can verify cryptographic integrity via `GET /api/v1/auth/audit/verify-chain`.
