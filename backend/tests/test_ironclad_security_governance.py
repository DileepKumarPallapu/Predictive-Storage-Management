import pytest
import uuid
import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.entities import User, Device, AuditLog
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_AUDITOR
)
from app.services.audit_service import AuditService

client = TestClient(app)


# ==============================================================================
# 1. UNAUTHORIZED REQUESTS & TOKEN VALIDATION
# ==============================================================================

def test_unauthorized_token_rejection():
    """Validates that malformed, corrupted, or fake tokens are rejected with 401."""
    # 1. Malformed token
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt-token"}
    )
    assert resp.status_code == 401
    assert "Invalid or expired" in resp.json()["detail"]

    # 2. Expired token
    expired_token = create_access_token(
        data={"sub": "admin", "role": "ADMIN"},
        expires_delta=timedelta(seconds=-60)
    )
    resp2 = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert resp2.status_code == 401


def test_deactivated_account_access_denial():
    """Validates that deactivated users are forbidden from accessing protected resources."""
    db = SessionLocal()
    user_id = f"usr-deact-{uuid.uuid4().hex[:8]}"
    username = f"deactivated_{uuid.uuid4().hex[:6]}"
    try:
        user = User(
            id=user_id,
            username=username,
            email=f"{username}@test.internal",
            hashed_password=hash_password("Pass123!"),
            role="OPERATOR",
            organization_id="org-primary-enterprise",
            is_active=False
        )
        db.add(user)
        db.commit()

        token = create_access_token(data={"sub": username, "role": "OPERATOR"})
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403
        assert "deactivated" in resp.json()["detail"].lower()
    finally:
        db.query(User).filter(User.id == user_id).delete()
        db.commit()
        db.close()


# ==============================================================================
# 2. ROLE-BASED ACCESS CONTROL & PRIVILEGE ESCALATION
# ==============================================================================

def test_privilege_escalation_operator_blocked_from_admin_endpoints():
    """Validates that OPERATOR role cannot access ADMIN-only endpoints (e.g. register user, update thresholds)."""
    db = SessionLocal()
    op_user_id = f"usr-op-{uuid.uuid4().hex[:8]}"
    op_username = f"operator_{uuid.uuid4().hex[:6]}"
    try:
        op_user = User(
            id=op_user_id,
            username=op_username,
            email=f"{op_username}@test.internal",
            hashed_password=hash_password("OperatorPass123!"),
            role="OPERATOR",
            organization_id="org-primary-enterprise",
            is_active=True
        )
        db.add(op_user)
        db.commit()

        op_token = create_access_token(data={"sub": op_username, "role": "OPERATOR", "user_id": op_user_id})

        # 1. Attempt user registration (ADMIN required)
        reg_resp = client.post(
            "/api/v1/auth/register",
            headers={"Authorization": f"Bearer {op_token}"},
            json={"username": "hacked_admin", "email": "hacked@test.internal", "password": "123", "role": "ADMIN"}
        )
        assert reg_resp.status_code == 403
        assert "denied" in reg_resp.json()["detail"].lower()

        # 2. Attempt global system policy modification (ADMIN required)
        sett_resp = client.put(
            "/api/v1/settings",
            headers={"Authorization": f"Bearer {op_token}"},
            json={"capacity_thresholds": {"default_warning_pct": 50.0, "default_critical_pct": 90.0}}
        )
        assert sett_resp.status_code == 403
        assert "denied" in sett_resp.json()["detail"].lower()

    finally:
        db.query(User).filter(User.id == op_user_id).delete()
        db.commit()
        db.close()


def test_auditor_role_read_only_boundaries():
    """Validates that AUDITOR role has read-only access and is blocked from mutations."""
    db = SessionLocal()
    aud_id = f"usr-aud-{uuid.uuid4().hex[:8]}"
    aud_name = f"auditor_{uuid.uuid4().hex[:6]}"
    try:
        aud_user = User(
            id=aud_id,
            username=aud_name,
            email=f"{aud_name}@test.internal",
            hashed_password=hash_password("AuditorPass123!"),
            role="AUDITOR",
            organization_id="org-primary-enterprise",
            is_active=True
        )
        db.add(aud_user)
        db.commit()

        aud_token = create_access_token(data={"sub": aud_name, "role": "AUDITOR", "user_id": aud_id})

        # 1. Permitted: Read permissions
        perm_resp = client.get("/api/v1/auth/permissions", headers={"Authorization": f"Bearer {aud_token}"})
        assert perm_resp.status_code == 200
        assert "audit.export" in perm_resp.json()["permissions"]

        # 2. Blocked: Cannot approve recommendation
        recs_resp = client.get(
            "/api/v1/devices/vol-nvme-tier1-db/recommendations",
            headers={"Authorization": f"Bearer {aud_token}"},
        )
        rec_id = recs_resp.json()[0]["id"]
        app_resp = client.post(
            f"/api/v1/recommendations/{rec_id}/approve",
            headers={"Authorization": f"Bearer {aud_token}"},
            json={"notes": "Auditor unauthorized approval attempt"}
        )
        assert app_resp.status_code == 403
        assert "denied" in app_resp.json()["detail"].lower()

    finally:
        db.query(User).filter(User.id == aud_id).delete()
        db.commit()
        db.close()


# ==============================================================================
# 3. TENANT BOUNDARY ISOLATION & IDOR PREVENTION
# ==============================================================================

def test_tenant_boundary_isolation_and_idor_protection():
    """
    Validates that users from Tenant Alpha cannot read or modify resources
    belonging to Tenant Beta (Insecure Direct Object Reference protection).
    """
    db = SessionLocal()
    user_alpha_id = f"usr-alpha-{uuid.uuid4().hex[:6]}"
    dev_beta_id = f"vol-beta-{uuid.uuid4().hex[:6]}"
    try:
        # Create user in Tenant Alpha
        user_alpha = User(
            id=user_alpha_id,
            username=f"alpha_op_{uuid.uuid4().hex[:4]}",
            email="alpha@org-alpha.internal",
            hashed_password=hash_password("AlphaPass123!"),
            role="OPERATOR",
            organization_id="org-tenant-alpha",
            is_active=True
        )
        db.add(user_alpha)

        # Create device in Tenant Beta
        dev_beta = Device(
            id=dev_beta_id,
            name="Confidential Medical Records NVMe",
            tier="NVME_TIER1",
            media_type="NVMe SSD",
            total_capacity_bytes=5000 * (1024**3),
            warning_threshold_pct=80.0,
            critical_threshold_pct=90.0,
            max_acceptable_latency_ms=10.0,
            min_free_reserve_pct=10.0,
            status="HEALTHY",
            workload_profile="Healthcare EHR",
            organization_id="org-tenant-beta"
        )
        db.add(dev_beta)
        db.commit()

        token_alpha = create_access_token(data={
            "sub": user_alpha.username,
            "role": "OPERATOR",
            "organization_id": "org-tenant-alpha"
        })

        # User from Tenant Alpha attempts to access Tenant Beta's device directly via IDOR
        idor_resp = client.get(
            f"/api/v1/devices/{dev_beta_id}",
            headers={"Authorization": f"Bearer {token_alpha}"}
        )
        assert idor_resp.status_code == 403
        assert "Tenant boundary violation" in idor_resp.json()["detail"]

    finally:
        db.query(Device).filter(Device.id == dev_beta_id).delete()
        db.query(User).filter(User.id == user_alpha_id).delete()
        db.commit()
        db.close()


# ==============================================================================
# 4. STRUCTURED AUDIT TRAIL & TAMPER EVIDENCE HASH CHAIN
# ==============================================================================

def test_audit_trail_tamper_chain_integrity():
    """Validates cryptographic SHA-256 forward-linked Merkle chain verification and tamper detection."""
    db = SessionLocal()
    org_id = f"org-audit-test-{uuid.uuid4().hex[:6]}"
    try:
        # 1. Log three events sequentially
        e1 = AuditService.log_event(
            db=db,
            action="TEST_ACTION_1",
            target_type="VOLUME",
            target_id="vol-001",
            user="admin@test.internal",
            organization_id=org_id,
            details={"step": 1}
        )
        e2 = AuditService.log_event(
            db=db,
            action="TEST_ACTION_2",
            target_type="VOLUME",
            target_id="vol-002",
            user="admin@test.internal",
            organization_id=org_id,
            details={"step": 2}
        )
        e3 = AuditService.log_event(
            db=db,
            action="TEST_ACTION_3",
            target_type="POLICY",
            target_id="pol-003",
            user="admin@test.internal",
            organization_id=org_id,
            details={"step": 3}
        )

        # Check chain link
        assert e2.prev_hash == e1.entry_hash
        assert e3.prev_hash == e2.entry_hash

        # 2. Verify pristine chain
        verif = AuditService.verify_audit_chain(db, organization_id=org_id)
        assert verif["is_valid"] is True
        assert verif["tampered_count"] == 0
        assert verif["total_entries"] == 3

        # 3. Simulate unauthorized database modification (tampering)
        e2.details_json = json.dumps({"step": 2, "tampered_by_attacker": True})
        db.commit()

        # 4. Verify that tampering is immediately detected
        verif_tampered = AuditService.verify_audit_chain(db, organization_id=org_id)
        assert verif_tampered["is_valid"] is False
        assert verif_tampered["tampered_count"] >= 1
        tampered_ids = [t["entry_id"] for t in verif_tampered["tampered_entries"]]
        assert e2.id in tampered_ids

    finally:
        db.query(AuditLog).filter(AuditLog.organization_id == org_id).delete()
        db.commit()
        db.close()


# ==============================================================================
# 5. SECURE STORAGE OF PASSWORDS AND CREDENTIALS
# ==============================================================================

def test_secure_password_hashing():
    """Validates that credentials use salted Argon2id hashing and never plaintext."""
    raw_pass = "EnterpriseResilience@2026!"
    hashed = hash_password(raw_pass)

    # 1. Argon2id signature check ($argon2id$)
    assert hashed.startswith("$argon2id$")
    assert hashed != raw_pass

    # 2. Verification correctness
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False

    # 3. Unique salts: same password hashed twice yields distinct hashes
    hashed2 = hash_password(raw_pass)
    assert hashed != hashed2
