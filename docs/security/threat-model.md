# AEGISSTOR — Storage Resilience Threat Model & STRIDE Assessment

**Document Version:** 5.0 (Titan Hardened)  
**Classification:** Enterprise Operational Security  
**Target:** Storage Resilience Intelligence Platform  

---

## 1. System Overview & Asset Identification

AEGISSTOR processes real and synthetic storage telemetry, generates calibrated multi-horizon capacity forecasts, and plans preventive operational interventions using a Storage Resilience Digital Twin.

### Critical Assets:
1. **Physical Storage State & Data Integrity**: Protection of physical disks, RAID LUNs, and block devices from unauthorized mutation or destructive commands.
2. **Telemetry Provenance & Quality**: Preventing adversarial injection of fabricated storage capacity metrics designed to manipulate automated provisioning or trigger false migrations.
3. **Audit Trail & Governance Logs**: Append-only log integrity recording scenario simulations, administrative approvals, and role updates.
4. **Authentication Credentials & Tokens**: Cryptographic security of JWT secrets, user sessions, and bcrypt password hashes.

---

## 2. STRIDE Threat Analysis

| STRIDE Threat Category | Threat Description & Attack Surface | Impact Level | Implemented Architectural Mitigation | Status |
| :--- | :--- | :---: | :--- | :---: |
| **Spoofing Identity** | Attacker attempts unauthorized API calls pretending to be `admin` without valid credentials. | **HIGH** | RFC 7519 Cryptographic JWT with HS256 algorithm and 24-hour expiration (`ACCESS_TOKEN_EXPIRE_MINUTES: 1440`). Passwords salted with bcrypt (cost=12). | **MITIGATED & VERIFIED** |
| **Tampering with Data** | Attacker tampers with historical telemetry or manipulates forecast intervals to force panic expansion. | **CRITICAL** | Strict parameter typing via Pydantic V2 schemas. Telemetry queries bounded by timestamps. SQL queries use parameterized SQLAlchemy 2.0 ORM (zero string interpolation). | **MITIGATED & VERIFIED** |
| **Repudiation** | An operator approves a risky migration and denies authorizing it. | **MEDIUM** | Append-only `audit_logs` table records every scenario creation, approval, mode switch, and parameter update with timestamp and user ID. | **MITIGATED & VERIFIED** |
| **Information Disclosure** | Stack traces, database file paths, or private host environment variables leaked via API error responses. | **MEDIUM** | Global exception middleware catches unhandled exceptions, sanitizes responses into standard JSON error envelopes, and injects unique `X-Request-ID`. | **MITIGATED & VERIFIED** |
| **Denial of Service** | Unbounded telemetry queries or concurrent heavy simulations exhausting backend RAM/CPU. | **HIGH** | Telemetry queries enforce max 720-hour window limit. Model inference uses shallow gradient boosted trees ($N_{\text{est}} \le 45$). Response headers include process latency metrics. | **MITIGATED & VERIFIED** |
| **Elevation of Privilege** | An `OPERATOR` account attempts administrative actions (user registration, system threshold alterations). | **HIGH** | Backend role-based authorization dependency (`require_role(["ADMIN"])`) enforces server-side role validation regardless of UI state. | **MITIGATED & VERIFIED** |

---

## 3. Storage Hardware Isolation (Shadow Mode)

### Core Invariant:
```
SHADOW_MODE_ENABLED: true
```
Physical storage mutations (NVMe-oF block resizes, filesystem format, SCSI unmap commands) are strictly disabled at the architectural layer. Digital Twin simulations execute exclusively against cloned virtual states in memory.
