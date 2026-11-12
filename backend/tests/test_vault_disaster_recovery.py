import os
import json
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.auth_helper import attach_admin_auth
from app.database import get_db, Base, engine, SessionLocal
from app.config import settings
from app.services.vault_backup_engine import VaultBackupEngine
from app.models.entities import VaultBackupRecord, Device, AuditLog, User
from app.auth.security import create_access_token

client = attach_admin_auth(TestClient(app))


@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Ensure test user
    test_user = db.query(User).filter_by(username="vault_admin").first()
    if not test_user:
        test_user = User(
            id="usr-vault-admin",
            username="vault_admin",
            email="vault_admin@aegisstor.internal",
            hashed_password="fakehashforadmin",
            role="ADMIN",
            is_active=True,
            organization_id="AEGISSTOR_CORE"
        )
        db.add(test_user)
        db.commit()
    db.close()
    yield
    # Cleanup


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def admin_token():
    return create_access_token(data={"sub": "vault_admin", "role": "ADMIN", "org": "AEGISSTOR_CORE"})


def test_vault_backup_creation_and_manifest(setup_db, db_session):
    """Verifies atomic snapshot creation, manifest structure, and secrets exclusion."""
    manifest = VaultBackupEngine.create_backup(
        db=db_session,
        created_by="vault_admin",
        notes="Automated test baseline snapshot"
    )

    backup_id = manifest["backup_id"]
    backup_path = os.path.join(settings.BACKUP_STORAGE_DIR, backup_id)
    assert os.path.isdir(backup_path), f"Backup directory {backup_path} does not exist"

    # Verify manifest fields
    assert manifest["format_version"] == "AEGISSTOR_VAULT_V1"
    assert manifest["backup_id"] == backup_id
    assert manifest["created_by"] == "vault_admin"
    assert "database.sqlite" in manifest["files"]
    assert "config_safe.json" in manifest["files"]
    assert "model_metadata.json" in manifest["files"]

    # Verify safe config excludes secrets
    safe_config_path = os.path.join(backup_path, "config_safe.json")
    with open(safe_config_path, "r", encoding="utf-8") as f:
        safe_cfg = json.load(f)
    assert "SECRET_KEY" not in safe_cfg
    assert "JWT_SECRET" not in safe_cfg
    assert "DATABASE_URL" not in safe_cfg

    # Verify DB record was persisted
    rec = db_session.query(VaultBackupRecord).filter_by(id=backup_id).first()
    assert rec is not None
    assert rec.checksum_status == "SHA256_VERIFIED"
    assert rec.restoration_status == "PENDING_VERIFICATION"


def test_vault_verify_backup_integrity_success(setup_db, db_session):
    """Verifies that an uncorrupted backup passes SHA-256 verification."""
    manifest = VaultBackupEngine.create_backup(db=db_session, created_by="vault_admin")
    backup_id = manifest["backup_id"]

    res = VaultBackupEngine.verify_backup_integrity(backup_id)
    assert res["checksum_status"] == "SHA256_VERIFIED"
    for fname, is_valid in res["verified_files"].items():
        assert is_valid is True, f"File {fname} failed checksum"


def test_vault_failure_simulation_checksum_mismatch(setup_db, db_session):
    """Failure simulation: verifies corruption detection when bytes are mutated."""
    manifest = VaultBackupEngine.create_backup(db=db_session, created_by="vault_admin")
    backup_id = manifest["backup_id"]
    backup_path = os.path.join(settings.BACKUP_STORAGE_DIR, backup_id)
    db_file = os.path.join(backup_path, "database.sqlite")

    # Corrupt 1 byte in the backup database file
    with open(db_file, "r+b") as f:
        f.seek(10)
        orig_byte = f.read(1)
        f.seek(10)
        # Flip the byte
        f.write(bytes([orig_byte[0] ^ 0xFF]))

    res = VaultBackupEngine.verify_backup_integrity(backup_id)
    assert res["checksum_status"] == "CORRUPTED_CHECKSUM_MISMATCH"
    assert res["verified_files"]["database.sqlite"] is False


def test_vault_failure_simulation_missing_file(setup_db, db_session):
    """Failure simulation: detects when an essential file is missing from the bundle."""
    manifest = VaultBackupEngine.create_backup(db=db_session, created_by="vault_admin")
    backup_id = manifest["backup_id"]
    backup_path = os.path.join(settings.BACKUP_STORAGE_DIR, backup_id)
    meta_file = os.path.join(backup_path, "model_metadata.json")
    if os.path.exists(meta_file):
        os.remove(meta_file)

    res = VaultBackupEngine.verify_backup_integrity(backup_id)
    assert res["checksum_status"] == "FILE_MISSING"
    assert "model_metadata.json" in res["error"]


def test_vault_failure_simulation_missing_manifest(setup_db, db_session):
    """Failure simulation: handles missing manifest.json gracefully."""
    manifest = VaultBackupEngine.create_backup(db=db_session, created_by="vault_admin")
    backup_id = manifest["backup_id"]
    backup_path = os.path.join(settings.BACKUP_STORAGE_DIR, backup_id)
    manifest_file = os.path.join(backup_path, "manifest.json")
    if os.path.exists(manifest_file):
        os.remove(manifest_file)

    res = VaultBackupEngine.verify_backup_integrity(backup_id)
    assert res["checksum_status"] == "MANIFEST_NOT_FOUND"


def test_vault_isolated_sandbox_restoration(setup_db, db_session):
    """
    Verifies that disaster recovery test runs in an isolated disposable sandbox,
    measures real RTO and RPO against SLAs, checks SQLite PRAGMA integrity,
    verifies table counts, and guarantees zero production mutation.
    """
    manifest = VaultBackupEngine.create_backup(db=db_session, created_by="vault_admin")
    backup_id = manifest["backup_id"]

    res = VaultBackupEngine.test_isolated_restoration(backup_id, db_session)
    assert res["status"] == "RESTORE_TEST_SUCCESS"
    assert res["integrity_check_passed"] is True
    assert res["measured_rto_seconds"] > 0
    assert res["rto_sla_met"] is True  # SLA target is < 60s
    assert res["measured_rpo_hours"] >= 0
    assert isinstance(res["rpo_sla_met"], bool)
    assert "devices" in res["verified_tables"]
    assert "telemetry" in res["verified_tables"]
    assert res["safety_guarantee"] == "RESTORE_PERFORMED_IN_DISPOSABLE_SANDBOX_ZERO_PRODUCTION_MUTATION"

    # Check updated record in DB
    rec = db_session.query(VaultBackupRecord).filter_by(id=backup_id).first()
    assert rec.restoration_status == "RESTORE_TESTED_SUCCESS"
    assert rec.last_test_rto_seconds == res["measured_rto_seconds"]
    assert rec.last_test_rpo_hours == res["measured_rpo_hours"]


def test_vault_retention_policy_pruning(setup_db, db_session):
    """Verifies that backups exceeding MAX_BACKUPS_RETAINED are automatically pruned."""
    # Temporarily set retention limit to 3
    original_max = settings.MAX_BACKUPS_RETAINED
    settings.MAX_BACKUPS_RETAINED = 3
    try:
        created_ids = []
        for i in range(5):
            m = VaultBackupEngine.create_backup(
                db=db_session,
                created_by="vault_admin",
                notes=f"Retention test {i}"
            )
            created_ids.append(m["backup_id"])

        active_backups = VaultBackupEngine.list_backups(db_session)
        assert len(active_backups) <= 3

        # Ensure oldest backups were pruned from disk
        pruned_id = created_ids[0]
        pruned_path = os.path.join(settings.BACKUP_STORAGE_DIR, pruned_id)
        assert not os.path.exists(pruned_path)
    finally:
        settings.MAX_BACKUPS_RETAINED = original_max


def test_vault_endpoints_api_flow(setup_db, admin_token):
    """End-to-end API tests for Vault endpoints."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create backup via POST /vault/backups
    resp = client.post("/api/v1/vault/backups", json={"notes": "API test backup"}, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "BACKUP_CREATED_SUCCESS"
    backup_id = data["backup"]["backup_id"]

    # 2. List backups via GET /vault/backups
    list_resp = client.get("/api/v1/vault/backups", headers=headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["backups_count"] >= 1
    found = any(b["id"] == backup_id for b in list_data["backups"])
    assert found is True

    # 3. Verify integrity via GET /vault/backups/{id}/integrity
    integ_resp = client.get(f"/api/v1/vault/backups/{backup_id}/integrity", headers=headers)
    assert integ_resp.status_code == 200
    integ_data = integ_resp.json()
    assert integ_data["checksum_status"] == "SHA256_VERIFIED"

    # 4. Test isolated restoration via POST /vault/backups/{id}/test-restore
    test_resp = client.post(f"/api/v1/vault/backups/{backup_id}/test-restore", headers=headers)
    assert test_resp.status_code == 200
    test_data = test_resp.json()
    assert test_data["status"] == "RESTORE_TEST_SUCCESS"
    assert test_data["rto_sla_met"] is True
    assert isinstance(test_data["rpo_sla_met"], bool)

    # 5. Production restore protection gate: fails with invalid token
    bad_restore = client.post(
        f"/api/v1/vault/backups/{backup_id}/restore-production",
        json={"confirmation_token": "WRONG_TOKEN"},
        headers=headers
    )
    assert bad_restore.status_code == 400


def test_vault_rpo_fresh_telemetry_sla_met(setup_db, db_session):
    """Verifies that with fresh telemetry (< 1h), RPO SLA is calculated as met."""
    from datetime import datetime, timezone, timedelta
    from app.models.entities import Telemetry
    # Insert a fresh telemetry record
    fresh_sample = Telemetry(
        device_id="dev-tier1-nvme-01",
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=10),
        used_bytes=500_000_000_000,
        free_bytes=500_000_000_000,
        utilization_pct=50.0,
        is_synthetic=False,
        source_label="vault_test_probe"
    )
    db_session.add(fresh_sample)
    db_session.commit()

    manifest = VaultBackupEngine.create_backup(db=db_session, created_by="vault_admin")
    backup_id = manifest["backup_id"]

    res = VaultBackupEngine.test_isolated_restoration(backup_id, db_session)
    assert res["status"] == "RESTORE_TEST_SUCCESS"
    assert res["measured_rpo_hours"] <= 0.5
    assert res["rpo_sla_met"] is True

