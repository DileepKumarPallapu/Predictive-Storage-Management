"""
Comprehensive Authentication, Session Security, RBAC, and End-to-End
Operator Operational Verification Suite (TEST A through TEST E).
"""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.database import Base, get_db
from app.models.entities import (
    Alert,
    AuditLog,
    CapacityRiskEvaluation,
    Device,
    Forecast,
    IngestionJob,
    ModelVersion,
    OperationalAssignment,
    Recommendation,
    ReportHistory,
    Scenario,
    Telemetry,
    User,
    UserSession,
)
from app.auth.security import create_access_token, hash_password, verify_password
from app.auth.permissions import seed_roles_and_permissions


@pytest.fixture()
def isolated_env(tmp_path):
    """Creates an isolated SQLite DB per test with seeded RBAC catalog and no default admin."""
    db_file = tmp_path / "rbac_isolated.db"
    db_url = f"sqlite:///{db_file}"
    eng = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    Base.metadata.create_all(bind=eng)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    # Seed roles & permissions + 1 baseline device (without any users yet)
    db = TestingSession()
    seed_roles_and_permissions(db)
    dev = Device(
        id="vol-test-nvme-01",
        name="Test Production NVMe Pool",
        tier="NVME_TIER1",
        media_type="NVMe SSD",
        storage_type="SAN",
        environment_location="DC-Primary",
        total_capacity_bytes=2 * (1024 ** 4),
        warning_threshold_pct=80.0,
        critical_threshold_pct=90.0,
        max_acceptable_latency_ms=15.0,
        min_free_reserve_pct=10.0,
        status="HEALTHY",
        workload_profile="OLTP Benchmark",
    )
    db.add(dev)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for i in range(60):
        ts = now - timedelta(hours=60 - i)
        used = int((1.1 + i * 0.005) * (1024 ** 4))
        total = dev.total_capacity_bytes
        db.add(Telemetry(
            device_id=dev.id,
            timestamp=ts,
            total_capacity_bytes=total,
            used_bytes=used,
            free_bytes=total - used,
            utilization_pct=round((used / total) * 100.0, 2),
            read_iops=4200.0 + i * 10,
            write_iops=2800.0 + i * 8,
            throughput_mb_s=480.0 + i * 2,
            latency_p95_ms=1.8 + (i % 5) * 0.2,
            read_latency_ms=1.1,
            write_latency_ms=2.2,
            queue_depth=12.0,
            is_synthetic=False,
            source_label="test_fixture",
        ))
    db.commit()
    db.close()

    with TestClient(app) as client:
        yield client, TestingSession

    app.dependency_overrides.clear()
    eng.dispose()


def _login(client: TestClient, identifier: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"username": identifier, "password": password})
    assert resp.status_code == 200, f"Login failed for {identifier}: {resp.text}"
    data = resp.json()
    return {
        "data": data,
        "headers": {
            "Authorization": f"Bearer {data['access_token']}",
            "X-CSRF-Token": data["csrf_token"],
        },
    }


def _bootstrap_admin_and_users(client: TestClient):
    # 1. Confirm setup required before any admin exists
    st = client.get("/api/v1/auth/setup-status")
    assert st.status_code == 200
    assert st.json()["setup_required"] is True

    # 2. Create initial admin via /auth/setup
    admin_pass = "Adm!nStrong#2026"
    r_setup = client.post("/api/v1/auth/setup", json={
        "username": "sec_admin",
        "email": "sec_admin@example.org",
        "password": admin_pass,
    })
    assert r_setup.status_code == 201, r_setup.text

    # 3. Subsequent /auth/setup must fail (403)
    r_setup_2 = client.post("/api/v1/auth/setup", json={
        "username": "rogue_admin",
        "email": "rogue@example.org",
        "password": "AnotherPassword1!",
    })
    assert r_setup_2.status_code in (403, 409)

    # 4. Login as admin and provision Operator + Viewer
    admin_auth = _login(client, "sec_admin@example.org", admin_pass)
    assert admin_auth["data"]["role"] == "ADMIN"
    assert admin_auth["data"]["landing_route"] == "/admin"

    op_pass = "Oper!Strong#2026"
    r_op = client.post("/api/v1/users", headers=admin_auth["headers"], json={
        "username": "ops_engineer",
        "email": "ops_engineer@example.org",
        "password": op_pass,
        "role": "OPERATOR",
    })
    assert r_op.status_code == 201, r_op.text

    vw_pass = "View!Strong#2026"
    r_vw = client.post("/api/v1/users", headers=admin_auth["headers"], json={
        "username": "stakeholder_vw",
        "email": "viewer@example.org",
        "password": vw_pass,
        "role": "VIEWER",
    })
    assert r_vw.status_code == 201, r_vw.text

    return {
        "admin": admin_auth,
        "admin_creds": ("sec_admin", admin_pass),
        "op_creds": ("ops_engineer", op_pass),
        "vw_creds": ("stakeholder_vw", vw_pass),
        "op_id": r_op.json()["id"],
        "vw_id": r_vw.json()["id"],
    }


def test_argon2id_hashing_and_lockout_and_reset_flow(isolated_env):
    client, SessionMaker = isolated_env
    ctx = _bootstrap_admin_and_users(client)

    # Verify Argon2id hash prefix stored in DB
    db = SessionMaker()
    op_user = db.query(User).filter(User.username == "ops_engineer").first()
    assert op_user is not None
    assert op_user.hashed_password.startswith("$argon2id$"), op_user.hashed_password
    assert verify_password(ctx["op_creds"][1], op_user.hashed_password)
    db.close()

    # Wrong password increments failures & locks after 5 attempts (6th gets 429)
    for attempt in range(5):
        bad = client.post("/api/v1/auth/login", json={"username": "ops_engineer", "password": "WrongPassword!"})
        assert bad.status_code == 401
    sixth = client.post("/api/v1/auth/login", json={"username": "ops_engineer", "password": "WrongPassword!"})
    assert sixth.status_code == 429

    # Clear lock via forgot + reset password flow and verify active session revocation
    op_session = _login(client, "sec_admin", ctx["admin_creds"][1])
    trig = client.post(f"/api/v1/users/{ctx['op_id']}/trigger-reset", headers=op_session["headers"])
    assert trig.status_code == 200
    reset_tok = trig.json()["reset_token"]
    assert reset_tok

    new_op_pw = "Oper!NewPass#2027"
    r_reset = client.post("/api/v1/auth/reset-password", json={"token": reset_tok, "new_password": new_op_pw})
    assert r_reset.status_code == 200

    # Single-use token replay fails cleanly
    r_reuse = client.post("/api/v1/auth/reset-password", json={"token": reset_tok, "new_password": "AnotherNewPassword1!"})
    assert r_reuse.status_code == 400

    # Login with updated password succeeds by email
    re_login = _login(client, "ops_engineer@example.org", new_op_pw)
    assert re_login["data"]["username"] == "ops_engineer"


def test_a_admin_full_capabilities_and_governance(isolated_env):
    client, _ = isolated_env
    ctx = _bootstrap_admin_and_users(client)
    hdrs = ctx["admin"]["headers"]

    assert client.get("/api/v1/users", headers=hdrs).status_code == 200
    cat = client.get("/api/v1/permissions/catalog", headers=hdrs)
    assert cat.status_code == 200
    assert len(cat.json()["permissions"]) >= 50

    # Admin updates email and role for viewer, then restores
    patch_res = client.patch(f"/api/v1/users/{ctx['vw_id']}", headers=hdrs, json={"email": "viewer_updated@example.org"})
    assert patch_res.status_code == 200
    assert patch_res.json()["email"] == "viewer_updated@example.org"

    # Admin checks user audit & security telemetry
    u_audit = client.get(f"/api/v1/users/{ctx['op_id']}/audit", headers=hdrs)
    assert u_audit.status_code == 200
    assert "login_attempts" in u_audit.json()

    # Admin updates global security/threshold settings
    s_upd = client.put("/api/v1/settings", headers=hdrs, json={
        "capacity_thresholds": {"default_warning_pct": 78.0, "default_critical_pct": 88.0},
        "approval_policy": {"operator_can_self_approve": False},
    })
    assert s_upd.status_code == 200
    assert s_upd.json()["capacity_thresholds"]["default_warning_pct"] == 78.0

    # Admin creates & revokes API key
    k_create = client.post("/api/v1/admin/api-keys", headers=hdrs, json={"name": "prom-scraper-key", "role": "OPERATOR"})
    assert k_create.status_code == 200
    k_id = k_create.json()["id"]
    assert client.delete(f"/api/v1/admin/api-keys/{k_id}", headers=hdrs).status_code == 200


def test_b_operator_full_19_step_operational_workflow_and_e_persistence(isolated_env):
    client, SessionMaker = isolated_env
    ctx = _bootstrap_admin_and_users(client)
    op_auth = _login(client, ctx["op_creds"][0], ctx["op_creds"][1])
    op_hdrs = op_auth["headers"]
    adm_hdrs = ctx["admin"]["headers"]

    # Step 1 & 2: Operator identity & operational dashboard
    me = client.get("/api/v1/auth/me", headers=op_hdrs).json()
    assert me["role"] == "OPERATOR"
    assert me["landing_route"] == "/operator"
    dash = client.get("/api/v1/operator/dashboard", headers=op_hdrs)
    assert dash.status_code == 200
    assert dash.json()["kpis"]["managed_storage_count"] >= 1

    # Step 3: Register storage resource & edit it
    st_id = "vol-op-workflow-01"
    cap_bytes = 4 * (1024 ** 4)
    cr = client.post("/api/v1/storage", headers=op_hdrs, json={
        "name": "Operator Workflow Pool",
        "id": st_id,
        "storage_type": "SAN",
        "media_type": "NVMe SSD",
        "total_capacity_bytes": cap_bytes,
        "initial_used_bytes": int(cap_bytes * 0.55),
        "environment_location": "Region-West-AZ1",
        "warning_threshold_pct": 80.0,
        "critical_threshold_pct": 90.0,
        "max_acceptable_latency_ms": 18.0,
    })
    assert cr.status_code == 201, cr.text

    up = client.put(f"/api/v1/storage/{st_id}", headers=op_hdrs, json={"environment_location": "Region-West-AZ2"})
    assert up.status_code == 200
    assert up.json()["environment_location"] == "Region-West-AZ2"

    # Step 4: Configure delegated thresholds
    th = client.patch(f"/api/v1/storage/{st_id}/thresholds", headers=op_hdrs, json={
        "warning_threshold_pct": 75.0,
        "critical_threshold_pct": 88.0,
        "max_acceptable_latency_ms": 16.0,
    })
    assert th.status_code == 200

    # Step 5 & 6: CSV preview + CSV import (80 hourly rows so ML training has >= 48 records) + Manual telemetry entry
    base_t = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
    csv_lines = ["timestamp,storage_id,total_capacity_bytes,used_capacity_bytes,read_iops,write_iops,read_latency_ms,write_latency_ms,throughput_mbps"]
    for h in range(80):
        t_str = (base_t + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")
        used_b = int(cap_bytes * (0.56 + h * 0.0032))
        csv_lines.append(f"{t_str},{st_id},{cap_bytes},{used_b},{3500 + h*15},{2100 + h*10},{1.2},{2.4},{420.0 + h}")
    csv_payload = "\n".join(csv_lines)

    prev = client.post("/api/v1/ingestion/csv/preview", headers=op_hdrs, data={"csv_content": csv_payload, "default_storage_id": st_id})
    assert prev.status_code == 200
    assert prev.json()["accepted_rows"] == 80

    imp = client.post("/api/v1/ingestion/csv/import", headers=op_hdrs, data={"csv_content": csv_payload, "default_storage_id": st_id})
    assert imp.status_code == 200
    assert imp.json()["accepted_rows"] == 80

    man = client.post("/api/v1/ingestion/manual", headers=op_hdrs, json={
        "storage_id": st_id,
        "timestamp": (base_t + timedelta(hours=80)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_capacity_bytes": cap_bytes,
        "used_capacity_bytes": int(cap_bytes * 0.82),
        "read_iops": 5100.0,
        "write_iops": 3200.0,
        "read_latency_ms": 1.6,
        "write_latency_ms": 3.0,
        "throughput_mbps": 560.0,
    })
    assert man.status_code == 201, man.text

    # Step 7: Ingestion jobs & Data quality & Reliability scoring
    jobs = client.get(f"/api/v1/ingestion/jobs?storage_id={st_id}", headers=op_hdrs)
    assert jobs.status_code == 200 and len(jobs.json()) >= 2
    dq = client.get(f"/api/v1/data-quality/{st_id}", headers=op_hdrs)
    assert dq.status_code == 200
    rel = client.post(f"/api/v1/reliability/data/{st_id}", headers=op_hdrs, json={})
    assert rel.status_code == 200

    # Step 8: Workload regime analysis
    wr = client.post(f"/api/v1/workload-regime/{st_id}", headers=op_hdrs)
    assert wr.status_code == 200

    # Step 9: ML training (v2 Champion-Challenger LightGBM + SARIMAX & legacy RandomForest/HistGBR)
    tr_v2 = client.post(f"/api/v1/v2/models/train/{st_id}", headers=op_hdrs)
    assert tr_v2.status_code == 200, tr_v2.text
    tr_v1 = client.post(f"/api/v1/models/train/{st_id}", headers=op_hdrs)
    assert tr_v1.status_code == 200, tr_v1.text
    assert client.get(f"/api/v1/v2/models/{st_id}", headers=op_hdrs).json()["count"] >= 1

    # Step 10: Generate calibrated capacity forecast
    fc_v2 = client.post(f"/api/v1/v2/forecasts/generate/{st_id}", headers=op_hdrs, json={"horizon_days": 30, "persist": True})
    assert fc_v2.status_code == 200, fc_v2.text
    fc_v1 = client.post(f"/api/v1/forecasts/generate/{st_id}?horizon_days=30", headers=op_hdrs)
    assert fc_v1.status_code == 200, fc_v1.text

    # Step 11: Evaluate capacity & performance risk + alerts
    risk_ev = client.post(f"/api/v1/risk/capacity/{st_id}", headers=op_hdrs, json={"horizon_days": 30})
    assert risk_ev.status_code == 200, risk_ev.text
    al_ev = client.post(f"/api/v1/alerts/evaluate/{st_id}", headers=op_hdrs)
    assert al_ev.status_code == 200, al_ev.text

    alerts_list = client.get(f"/api/v1/alerts?storage_id={st_id}", headers=op_hdrs).json()
    assert len(alerts_list) >= 1, "Expected at least one alert after 82% utilization (>75% warning threshold)"
    al_id = alerts_list[0]["id"]

    # Step 12: Alert Acknowledge -> Assign -> Resolve -> Reopen
    assert client.post(f"/api/v1/alerts/{al_id}/acknowledge", headers=op_hdrs).status_code == 200
    asg = client.post(f"/api/v1/alerts/{al_id}/assign", headers=op_hdrs, json={"assigned_to": "ops_engineer", "notes": "Triaging pool capacity"})
    assert asg.status_code == 200
    assert asg.json()["assigned_to"] == "ops_engineer"
    assert client.post(f"/api/v1/alerts/{al_id}/resolve", headers=op_hdrs, json={"resolution_details": "Verified mitigation plan"}).status_code == 200
    assert client.post(f"/api/v1/alerts/{al_id}/reopen", headers=op_hdrs).status_code == 200

    # Step 13: Digital Twin create, read, edit/rerun, compare, optimize, export
    sc1 = client.post("/api/v1/digital-twin/scenarios", headers=op_hdrs, json={
        "device_id": st_id,
        "name": "Op Archive Offload 20%",
        "action_type": "TIER_COLD_DATA",
        "parameters": {"offload_pct": 20.0},
    })
    assert sc1.status_code == 201, sc1.text
    sc1_id = sc1.json()["scenario_id"]

    sc2 = client.post("/api/v1/digital-twin/scenarios", headers=op_hdrs, json={
        "device_id": st_id,
        "name": "Op Rebalance 30%",
        "action_type": "WORKLOAD_REBALANCING",
        "parameters": {"migrate_pct": 30.0},
    })
    assert sc2.status_code == 201
    sc2_id = sc2.json()["scenario_id"]

    assert client.put(f"/api/v1/digital-twin/scenarios/{sc1_id}", headers=op_hdrs, json={"parameters": {"offload_pct": 25.0}}).status_code == 200
    assert client.post("/api/v1/digital-twin/compare", headers=op_hdrs, json={"scenario_ids": [sc1_id, sc2_id]}).status_code == 200
    assert client.post(f"/api/v1/digital-twin/optimize/{st_id}", headers=op_hdrs, json={"decision_horizon_days": 30}).status_code == 200
    assert client.get(f"/api/v1/digital-twin/scenarios/{sc1_id}/export?format=csv", headers=op_hdrs).status_code == 200

    # Step 14 & 15: Recommendations + non-self-approval rule
    recs = client.post(f"/api/v1/recommendations/generate/{st_id}", headers=op_hdrs)
    assert recs.status_code == 200, recs.text
    rec_id = recs.json()["recommendations"][0]["id"]

    # Operator CANNOT self-approve their own generated/submitted recommendation while policy disabled
    self_app = client.post(f"/api/v1/recommendations/{rec_id}/approve", headers=op_hdrs, json={"notes": "Self try"})
    assert self_app.status_code == 403

    # If Admin generates another recommendation, Operator CAN approve Admin's submitted recommendation!
    adm_recs = client.post(f"/api/v1/recommendations/generate/vol-test-nvme-01", headers=adm_hdrs)
    assert adm_recs.status_code == 200
    adm_rec_id = adm_recs.json()["recommendations"][0]["id"]
    op_approve_other = client.post(f"/api/v1/recommendations/{adm_rec_id}/approve", headers=op_hdrs, json={"notes": "Peer review passed"})
    assert op_approve_other.status_code == 200

    # Step 16: Generate & Export Reports (JSON POST, CSV GET, PDF GET)
    rep_json = client.post("/api/v1/reports/generate", headers=op_hdrs, json={
        "report_type": "capacity_risk",
        "format": "json",
        "storage_id": st_id,
    })
    assert rep_json.status_code == 200, rep_json.text
    assert client.get(f"/api/v1/reports/generate?report_type=storage_inventory&format=csv&storage_id={st_id}", headers=op_hdrs).status_code == 200
    pdf_resp = client.get(f"/api/v1/reports/generate?report_type=capacity_risk&format=pdf&storage_id={st_id}", headers=op_hdrs)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"].startswith("application/pdf")

    # Step 17: Permitted operational audit log access
    assert client.get("/api/v1/audit", headers=op_hdrs).status_code == 200

    # Step 18: Operator STRICTLY BLOCKED (403) from Admin IAM / Secrets / Settings / Audit Tamper
    assert client.get("/api/v1/users", headers=op_hdrs).status_code == 403
    assert client.post("/api/v1/users", headers=op_hdrs, json={"username": "x", "email": "x@y.com", "password": "Password1!", "role": "VIEWER"}).status_code == 403
    assert client.get("/api/v1/permissions/catalog", headers=op_hdrs).status_code == 403
    assert client.put("/api/v1/permissions/roles/OPERATOR", headers=op_hdrs, json={"permissions": {"users.create": True}}).status_code == 403
    assert client.put("/api/v1/settings", headers=op_hdrs, json={"capacity_thresholds": {"default_warning_pct": 50.0, "default_critical_pct": 90.0}}).status_code == 403
    assert client.get("/api/v1/admin/api-keys", headers=op_hdrs).status_code == 403
    assert client.post("/api/v1/connectors", headers=op_hdrs, json={"name": "RogueConn", "connector_type": "HTTP_API", "endpoint_url": "http://example.org"}).status_code == 403
    assert client.delete("/api/v1/audit", headers=op_hdrs).status_code == 403
    assert client.get("/api/v1/auth/audit/verify-chain", headers=op_hdrs).status_code == 403

    # TEST E — Verify cross-session database persistence
    db = SessionMaker()
    assert db.query(Device).filter(Device.id == st_id).first() is not None
    assert db.query(Telemetry).filter(Telemetry.device_id == st_id).count() >= 81
    assert db.query(IngestionJob).filter(IngestionJob.storage_id == st_id).count() >= 2
    assert db.query(ModelVersion).filter(ModelVersion.storage_id == st_id).count() >= 2
    assert db.query(Forecast).filter(Forecast.device_id == st_id).count() >= 2
    assert db.query(CapacityRiskEvaluation).filter(CapacityRiskEvaluation.storage_id == st_id).count() >= 1
    assert db.query(Alert).filter(Alert.id == al_id).first() is not None
    assert db.query(OperationalAssignment).filter(OperationalAssignment.target_id == al_id).first() is not None
    assert db.query(Scenario).filter(Scenario.id == sc1_id).first() is not None
    assert db.query(Recommendation).filter(Recommendation.id == adm_rec_id).first().approval_status == "APPROVED_SHADOW"
    assert db.query(ReportHistory).filter(ReportHistory.storage_id == st_id).count() >= 2
    assert db.query(AuditLog).filter(AuditLog.user == "ops_engineer").count() >= 5
    db.close()


def test_c_viewer_read_only_and_write_blocking(isolated_env):
    client, _ = isolated_env
    ctx = _bootstrap_admin_and_users(client)
    vw_auth = _login(client, ctx["vw_creds"][0], ctx["vw_creds"][1])
    assert vw_auth["data"]["landing_route"] == "/viewer"
    vw_hdrs = vw_auth["headers"]

    # Allowed reads
    assert client.get("/api/v1/overview", headers=vw_hdrs).status_code == 200
    assert client.get("/api/v1/operator/dashboard", headers=vw_hdrs).status_code == 200
    assert client.get("/api/v1/storage", headers=vw_hdrs).status_code == 200
    assert client.get("/api/v1/devices/vol-test-nvme-01/telemetry", headers=vw_hdrs).status_code == 200
    assert client.get("/api/v1/data-quality/vol-test-nvme-01", headers=vw_hdrs).status_code == 200
    assert client.get("/api/v1/models", headers=vw_hdrs).status_code == 200
    assert client.get("/api/v1/forecasts/vol-test-nvme-01", headers=vw_hdrs).status_code == 200
    assert client.get("/api/v1/risk/capacity/vol-test-nvme-01", headers=vw_hdrs).status_code == 200
    assert client.get("/api/v1/alerts", headers=vw_hdrs).status_code == 200
    assert client.get("/api/v1/digital-twin/scenarios", headers=vw_hdrs).status_code == 200
    assert client.get("/api/v1/recommendations", headers=vw_hdrs).status_code == 200
    assert client.get("/api/v1/reports/history", headers=vw_hdrs).status_code == 200
    assert client.get("/api/v1/reports/generate?report_type=storage_inventory&format=csv", headers=vw_hdrs).status_code == 200

    # Blocked writes (ALL must return 403 Forbidden)
    assert client.post("/api/v1/storage", headers=vw_hdrs, json={"name": "Nope", "storage_type": "SAN", "media_type": "NVMe", "total_capacity_bytes": 10**12}).status_code == 403
    assert client.post("/api/v1/ingestion/manual", headers=vw_hdrs, json={"storage_id": "vol-test-nvme-01", "timestamp": "2026-10-10T00:00:00Z", "used_capacity_bytes": 1000}).status_code == 403
    assert client.post("/api/v1/v2/models/train/vol-test-nvme-01", headers=vw_hdrs).status_code == 403
    assert client.post("/api/v1/forecasts/generate/vol-test-nvme-01", headers=vw_hdrs).status_code == 403
    assert client.post("/api/v1/digital-twin/scenarios", headers=vw_hdrs, json={"device_id": "vol-test-nvme-01", "name": "Blocked Twin", "action_type": "ARCHIVE_TIER", "parameters": {}}).status_code == 403
    assert client.post("/api/v1/alerts/evaluate", headers=vw_hdrs).status_code == 403
    assert client.post("/api/v1/reports/generate", headers=vw_hdrs, json={"report_type": "storage_inventory", "format": "json"}).status_code == 403
    assert client.get("/api/v1/users", headers=vw_hdrs).status_code == 403
    assert client.put("/api/v1/settings", headers=vw_hdrs, json={}).status_code == 403


def test_d_security_unauthenticated_and_revocation(isolated_env):
    client, SessionMaker = isolated_env
    ctx = _bootstrap_admin_and_users(client)

    # 1. Unauthenticated access blocked with 401 on fresh cookie-free client (no silent admin fallback!)
    anon = TestClient(app)
    assert anon.get("/api/v1/overview").status_code == 401
    assert anon.get("/api/v1/storage").status_code == 401
    assert anon.get("/api/v1/users").status_code == 401
    assert anon.get("/api/v1/settings").status_code == 401
    assert anon.get("/api/v1/operator/dashboard").status_code == 401
    assert anon.post("/api/v1/storage", json={}).status_code == 401
    assert anon.post("/api/v1/v2/models/train/vol-test-nvme-01").status_code == 401

    # 2. Immediate deactivation revokes live session (401 on subsequent request)
    op_auth = _login(client, ctx["op_creds"][0], ctx["op_creds"][1])
    assert client.get("/api/v1/auth/me", headers=op_auth["headers"]).status_code == 200
    deact = client.patch(f"/api/v1/users/{ctx['op_id']}", headers=ctx["admin"]["headers"], json={"is_active": False})
    assert deact.status_code == 200
    assert client.get("/api/v1/auth/me", headers=op_auth["headers"]).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": ctx["op_creds"][0], "password": ctx["op_creds"][1]}).status_code == 403

    # 3. Expired UserSession fails with 401
    vw_auth = _login(client, ctx["vw_creds"][0], ctx["vw_creds"][1])
    db = SessionMaker()
    sess = db.query(UserSession).filter(UserSession.user_id == ctx["vw_id"]).first()
    assert sess is not None
    sess.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
    db.commit()
    db.close()
    assert client.get("/api/v1/auth/me", headers=vw_auth["headers"]).status_code == 401

    # 4. Cookie-only mutation enforces X-CSRF-Token
    adm_cookie_client = TestClient(app)
    r_login = adm_cookie_client.post("/api/v1/auth/login", json={"username": ctx["admin_creds"][0], "password": ctx["admin_creds"][1]})
    assert r_login.status_code == 200
    csrf_tok = r_login.json()["csrf_token"]
    # Mutation via cookie without X-CSRF-Token header -> 403
    no_csrf = adm_cookie_client.put("/api/v1/settings", json={"capacity_thresholds": {"default_warning_pct": 79.0, "default_critical_pct": 89.0}})
    assert no_csrf.status_code == 403
    # Mutation via cookie WITH X-CSRF-Token header -> 200
    with_csrf = adm_cookie_client.put(
        "/api/v1/settings",
        headers={"X-CSRF-Token": csrf_tok},
        json={"capacity_thresholds": {"default_warning_pct": 79.0, "default_critical_pct": 89.0}},
    )
    assert with_csrf.status_code == 200
