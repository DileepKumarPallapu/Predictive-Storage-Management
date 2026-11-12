# AEGISSTOR — Administrator User Guide (`ADMINISTRATOR_GUIDE.md`)

**Role:** `ADMIN` · **Landing Route:** `/admin`

## 1. First-Run System Setup
AEGISSTOR ships without publicly known default admin passwords. Initialize your first Administrator on a clean database via `/setup` (UI) or `POST /api/v1/auth/setup` (or via `AEGISSTOR_BOOTSTRAP_ADMIN_*` environment variables).

## 2. User, Role & Permission Governance (`/users`)
- **Provision Users**: Create `ADMIN`, `OPERATOR`, `VIEWER`, or `AUDITOR` accounts (passwords hashed with Argon2id; minimum 8 characters).
- **Manage Profiles & Status**: Update user emails, change roles, or deactivate compromised/departed accounts. Changing a role or deactivating an account immediately revokes all active `UserSession` records.
- **Session Revocation & Resets**: Click **Revoke** to force immediate sign-out across devices, **Reset** to generate an expiring single-use reset token, or **Security** to inspect failed login attempts, lockout status, and user audit events.
- **Role Permission Matrix Tab**: Toggle any of the 58 fine-grained permissions for `OPERATOR`, `VIEWER`, or `AUDITOR` live (`PUT /api/v1/permissions/roles/{role}`).
- **Approval Policy Toggle**: Enable or block `operator_can_self_approve` (recommended: **BLOCKED**).

## 3. Integrations, Secrets & Global Policies (`/integrations`, `/settings`, `/audit`)
- Register new telemetry connectors with credentials, issue and revoke `X-API-Key` collector keys (`/admin/api-keys`), run retention cleanup (`/admin/retention/run`), modify global threshold/retention settings (`PUT /settings`), and cryptographically verify the SHA-256 hash chain on `/audit` (`Verify Tamper Chain`).
