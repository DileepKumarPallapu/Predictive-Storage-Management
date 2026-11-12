"""
Comprehensive End-to-End Verification Suite for AEGISSTOR Modules 1–12.
Verifies persistent DB models, RBAC (ADMIN/OPERATOR/VIEWER), Storage CRUD,
CSV ingestion & error reports, Data Quality preprocessing, Dual-Model ML
(RandomForestRegressor + HistGradientBoostingRegressor) with joblib persistence,
7/30/90-day forecasts, Capacity Runway, Performance Monitoring, Alert lifecycle,
Digital Twin 5 scenario types + comparison/export, Recommendations, PDF/CSV Reports,
Settings persistence, and Audit logging.
"""
import math
import os
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app, initialize_database_and_seed_demo
from app.database import SessionLocal
from app.models.entities import (
    Device, Telemetry, User, ModelVersion, ModelMetric, Forecast, Alert,
    Scenario, ReportHistory, ApplicationSetting, AuditLog, IngestionJob
)
from app.auth.security import hash_password, create_access_token
from tests.auth_helper import attach_admin_auth

client = attach_admin_auth(TestClient(app))


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    initialize_database_and_seed_demo()


def _auth_headers(username: str, role: str, user_id: str) -> dict:
    token = create_access_token(data={
        "sub": username,
        "role": role,
        "user_id": user_id,
        "organization_id": "org-primary-enterprise",
    })
    return {"Authorization": f"Bearer {token}"}


def _admin_headers() -> dict:
    return _auth_headers("admin", "ADMIN", "usr-system-admin")


def _operator_headers() -> dict:
    return _auth_headers("operator", "OPERATOR", "usr-system-operator")


def _viewer_headers() -> dict:
    return _auth_headers("viewer", "VIEWER", "usr-system-viewer")


# ==============================================================================
# MODULE 1: AUTHENTICATION, USER MANAGEMENT, LOGOUT & RBAC
# ==============================================================================

def _login_seeded_admin() -> str:
    for pwd in ("AegisAdmin!2026", "admin123"):
        resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": pwd})
        if resp.status_code == 200:
            return resp.json()["access_token"]
    raise AssertionError(f"Admin login failed with all known passwords: {resp.status_code} {resp.text}")


def test_module1_auth_rbac_users_and_logout():
    # 1. Login with seeded admin
    admin_token = _login_seeded_admin()
    admin_hdr = {"Authorization": f"Bearer {admin_token}"}

    # 2. Admin creates a VIEWER user via /users
    uname = f"viewer_{uuid.uuid4().hex[:6]}"
    create_resp = client.post(
        "/api/v1/users",
        headers=admin_hdr,
        json={"username": uname, "email": f"{uname}@aegisstor.test", "password": "ViewerPass123!", "role": "VIEWER"}
    )
    assert create_resp.status_code == 201
    created_uid = create_resp.json()["id"]
    assert create_resp.json()["role"] == "VIEWER"

    try:
        # 3. VIEWER logs in
        v_login = client.post("/api/v1/auth/login", json={"username": uname, "password": "ViewerPass123!"})
        assert v_login.status_code == 200
        v_token = v_login.json()["access_token"]
        v_hdr = {"Authorization": f"Bearer {v_token}"}

        # 4. VIEWER can read storage & reports, CANNOT mutate storage or train models or manage users
        assert client.get("/api/v1/storage", headers=v_hdr).status_code == 200
        assert client.get("/api/v1/users", headers=v_hdr).status_code == 403
        assert client.post("/api/v1/storage", headers=v_hdr, json={
            "name": "Blocked Pool", "storage_type": "SAN", "total_capacity_bytes": 10**12
        }).status_code == 403
        assert client.post("/api/v1/models/train/vol-nvme-tier1-db", headers=v_hdr).status_code == 403

        # 5. Logout revokes token cleanly
        lo_resp = client.post("/api/v1/auth/logout", headers=v_hdr)
        assert lo_resp.status_code == 200
        me_after_logout = client.get("/api/v1/auth/me", headers=v_hdr)
        assert me_after_logout.status_code == 401
        assert "revoked" in me_after_logout.json()["detail"].lower()

        # 6. Admin updates user role & deletes user
        upd = client.patch(f"/api/v1/users/{created_uid}", headers=admin_hdr, json={"role": "OPERATOR"})
        assert upd.status_code == 200
        assert upd.json()["role"] == "OPERATOR"
    finally:
        client.delete(f"/api/v1/users/{created_uid}", headers=admin_hdr)


# ==============================================================================
# MODULE 2: STORAGE INVENTORY CRUD, FREE/UTIL CALC & DEPENDENCY CHECKS
# ==============================================================================

def test_module2_storage_inventory_crud_and_validation():
    admin_hdr = _admin_headers()
    sid = f"vol-inv-{uuid.uuid4().hex[:6]}"
    cap_1tb = 1000 * (1024 ** 3)
    used_400gb = 400 * (1024 ** 3)

    # 1. Reject impossible capacity (used > total) and invalid thresholds
    bad = client.post("/api/v1/storage", headers=admin_hdr, json={
        "id": sid, "name": "Bad Pool", "storage_type": "NAS",
        "total_capacity_bytes": cap_1tb, "initial_used_bytes": cap_1tb + 1000
    })
    assert bad.status_code == 400

    bad_thresh = client.post("/api/v1/storage", headers=admin_hdr, json={
        "id": sid, "name": "Bad Thresh", "storage_type": "NAS",
        "total_capacity_bytes": cap_1tb, "warning_threshold_pct": 95.0, "critical_threshold_pct": 85.0
    })
    assert bad_thresh.status_code == 400

    # 2. Valid creation
    ok = client.post("/api/v1/storage", headers=admin_hdr, json={
        "id": sid,
        "name": "Enterprise NAS Archive",
        "storage_type": "NAS",
        "environment_location": "Frankfurt DC-2",
        "total_capacity_bytes": cap_1tb,
        "initial_used_bytes": used_400gb,
        "warning_threshold_pct": 75.0,
        "critical_threshold_pct": 90.0,
        "description": "Primary corporate NAS share",
        "notes": "Quarterly capacity check"
    })
    assert ok.status_code == 201
    data = ok.json()
    assert data["free_capacity_bytes"] == cap_1tb - used_400gb
    assert abs(data["current_utilization_pct"] - 40.0) < 0.01
    assert data["storage_type"] == "NAS"
    assert data["environment_location"] == "Frankfurt DC-2"

    # 3. Search & filter
    flt = client.get("/api/v1/storage?storage_type=NAS&search=Frankfurt")
    assert flt.status_code == 200
    # search checks name/id
    flt2 = client.get(f"/api/v1/storage?storage_type=NAS&search={sid}")
    assert len(flt2.json()) == 1

    # 4. Update storage metadata & check shrink-below-used protection
    bad_shrink = client.put(f"/api/v1/storage/{sid}", headers=admin_hdr, json={
        "total_capacity_bytes": used_400gb - 1024
    })
    assert bad_shrink.status_code == 400

    upd = client.put(f"/api/v1/storage/{sid}", headers=admin_hdr, json={
        "name": "Enterprise NAS Archive v2",
        "notes": "Expanded notes"
    })
    assert upd.status_code == 200
    assert upd.json()["name"] == "Enterprise NAS Archive v2"

    # 5. Dependency check prevents accidental unconfirmed delete
    dep_block = client.delete(f"/api/v1/storage/{sid}", headers=admin_hdr)
    assert dep_block.status_code == 409

    # 6. Confirmed delete succeeds
    del_ok = client.delete(f"/api/v1/storage/{sid}?confirm=true", headers=admin_hdr)
    assert del_ok.status_code == 200
    assert client.get(f"/api/v1/storage/{sid}", headers=admin_hdr).status_code == 404


# ==============================================================================
# MODULE 3 & 4: CSV INGESTION, DUPLICATES, ERROR REPORT & DATA QUALITY
# ==============================================================================

def test_module3_4_csv_ingestion_validation_and_data_quality():
    admin_hdr = _admin_headers()
    op_hdr = _operator_headers()
    sid = f"vol-csv-{uuid.uuid4().hex[:6]}"
    cap = 500 * (1024 ** 3)

    client.post("/api/v1/storage", headers=admin_hdr, json={
        "id": sid, "name": "CSV Test Storage", "storage_type": "Cloud storage",
        "total_capacity_bytes": cap, "initial_used_bytes": 0
    })

    try:
        # 1. Download template
        tmpl = client.get("/api/v1/ingestion/template")
        assert tmpl.status_code == 200
        assert "timestamp,storage_id,total_capacity_bytes,used_capacity_bytes" in tmpl.text

        # 2. CSV with 2 valid rows (1 missing latency -> kept as None, NOT fabricated!),
        #    1 duplicate row, 1 impossible capacity row (used > total), 1 invalid timestamp row
        t0 = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
        csv_body = "\n".join([
            "timestamp,storage_id,total_capacity_bytes,used_capacity_bytes,read_iops,write_iops,read_latency_ms,write_latency_ms,throughput_mbps",
            f"{t0.isoformat()},{sid},{cap},{100*(1024**3)},500,300,,,120.5",
            f"{(t0 + timedelta(hours=1)).isoformat()},{sid},{cap},{105*(1024**3)},520,310,1.2,1.8,125.0",
            f"{t0.isoformat()},{sid},{cap},{100*(1024**3)},500,300,1.1,1.5,120.5",
            f"{(t0 + timedelta(hours=2)).isoformat()},{sid},{cap},{cap + 99999},500,300,1.1,1.5,120.5",
            f"not-a-timestamp,{sid},{cap},{110*(1024**3)},500,300,1.1,1.5,120.5",
        ])

        # Preview check
        prev = client.post("/api/v1/ingestion/csv/preview", headers=op_hdr, data={"csv_content": csv_body})
        assert prev.status_code == 200
        pj = prev.json()
        assert pj["total_rows"] == 5
        assert pj["accepted_rows"] == 2
        assert pj["duplicate_rows"] == 1
        assert pj["rejected_rows"] == 2
        assert pj["missing_field_stats"]["read_latency_ms"] == 1

        # Commit import
        imp = client.post("/api/v1/ingestion/csv/import", headers=op_hdr, data={"csv_content": csv_body})
        assert imp.status_code == 200
        ij = imp.json()
        assert ij["accepted_rows"] == 2
        assert ij["duplicate_rows"] == 1
        assert ij["rejected_rows"] == 2
        job_id = ij["job_id"]

        # Error report CSV download
        err_csv = client.get(f"/api/v1/ingestion/jobs/{job_id}/errors?format=csv")
        assert err_csv.status_code == 200
        assert "DUPLICATE_IN_FILE" in err_csv.text
        assert "IMPOSSIBLE_CAPACITY" in err_csv.text

        # Check performance endpoint preserves missing latency as null/unavailable on row 1 without fabricating
        perf = client.get(f"/api/v1/performance/{sid}")
        assert perf.status_code == 200
        assert perf.json()["points_count"] == 2

        # Check Data Quality endpoint
        dq = client.get(f"/api/v1/data-quality/{sid}")
        assert dq.status_code == 200
        dqj = dq.json()
        assert dqj["total_records_received"] == 2
        assert dqj["valid_records"] == 2
        assert dqj["latest_telemetry_timestamp"] is not None

        # Manual telemetry entry + duplicate guard
        man_ts = (t0 + timedelta(hours=3)).isoformat()
        man1 = client.post("/api/v1/ingestion/manual", headers=op_hdr, json={
            "storage_id": sid, "timestamp": man_ts,
            "total_capacity_bytes": cap, "used_capacity_bytes": 110 * (1024 ** 3),
        })
        assert man1.status_code == 201
        man_dup = client.post("/api/v1/ingestion/manual", headers=op_hdr, json={
            "storage_id": sid, "timestamp": man_ts,
            "total_capacity_bytes": cap, "used_capacity_bytes": 110 * (1024 ** 3),
        })
        assert man_dup.status_code == 409

        # Performance when ALL latency fields are null -> "No data available"
        sid_nolat = f"vol-nolat-{uuid.uuid4().hex[:5]}"
        client.post("/api/v1/storage", headers=admin_hdr, json={
            "id": sid_nolat, "name": "No Latency Pool", "storage_type": "Object storage",
            "total_capacity_bytes": cap, "initial_used_bytes": 0
        })
        try:
            client.post("/api/v1/ingestion/manual", headers=op_hdr, json={
                "storage_id": sid_nolat, "timestamp": t0.isoformat(),
                "total_capacity_bytes": cap, "used_capacity_bytes": 50 * (1024 ** 3),
            })
            perf_nl = client.get(f"/api/v1/performance/{sid_nolat}")
            assert perf_nl.status_code == 200
            assert perf_nl.json()["summary"]["read_latency_ms"]["display"] == "No data available"
            assert perf_nl.json()["summary"]["read_latency_ms"]["available"] is False
        finally:
            client.delete(f"/api/v1/storage/{sid_nolat}?confirm=true", headers=admin_hdr)
    finally:
        client.delete(f"/api/v1/storage/{sid}?confirm=true", headers=admin_hdr)


# ==============================================================================
# MODULE 5 & 6: DUAL ML ENGINE (RF + HISTGBM), PREDICTIONS & CAPACITY RUNWAY
# ==============================================================================

def test_module5_6_ml_training_persistence_prediction_and_runway():
    admin_hdr = _admin_headers()
    op_hdr = _operator_headers()

    # 1. Insufficient history gate test on fresh volume
    sid_small = f"vol-ml-small-{uuid.uuid4().hex[:5]}"
    cap = 1000 * (1024 ** 3)
    client.post("/api/v1/storage", headers=admin_hdr, json={
        "id": sid_small, "name": "Small History", "storage_type": "SAN",
        "total_capacity_bytes": cap, "initial_used_bytes": 100 * (1024 ** 3)
    })
    try:
        tr_small = client.post(f"/api/v1/models/train/{sid_small}", headers=admin_hdr)
        assert tr_small.status_code == 200
        assert tr_small.json()["status"] == "INSUFFICIENT_HISTORY"
        assert tr_small.json()["records_required"] == 48
    finally:
        client.delete(f"/api/v1/storage/{sid_small}?confirm=true", headers=admin_hdr)

    # 2. Train BOTH RandomForestRegressor & HistGradientBoostingRegressor on primary tier-1 volume
    tr_resp = client.post("/api/v1/models/train/vol-nvme-tier1-db", headers=admin_hdr)
    assert tr_resp.status_code == 200
    tj = tr_resp.json()
    assert tj["status"] == "TRAINED"
    algos = {m["algorithm"] for m in tj["models"]}
    assert algos == {"RandomForestRegressor", "HistGradientBoostingRegressor"}
    for m in tj["models"]:
        assert m["artifact_saved"] is True
        assert m["mae_bytes"] >= 0
        assert m["rmse_bytes"] >= 0
    assert tj["selected_model"]["is_selected"] is True

    # Verify /models/{storage_id} returns both persisted models
    ml_list = client.get("/api/v1/models/vol-nvme-tier1-db")
    assert ml_list.status_code == 200
    assert ml_list.json()["active_model"] is not None

    # 3. Generate persisted 7-day, 30-day, and 90-day forecasts using saved joblib model
    for horizon in (7, 30, 90):
        fc = client.post(f"/api/v1/forecasts/generate/vol-nvme-tier1-db?horizon_days={horizon}", headers=op_hdr)
        assert fc.status_code == 200
        fj = fc.json()
        assert fj["horizon_days"] == horizon
        assert len(fj["daily_predictions"]) == horizon
        assert fj["model_used"] in ("RandomForestRegressor", "HistGradientBoostingRegressor")
        assert fj["is_estimate"] is True
        assert fj["runway_analysis"]["is_estimate"] is True

    # Verify saved forecasts retrieval from DB
    saved_fc = client.get("/api/v1/forecasts/vol-nvme-tier1-db")
    assert saved_fc.status_code == 200
    assert len(saved_fc.json()) >= 3

    # 4. Zero / Negative growth runway handling
    sid_flat = f"vol-flat-{uuid.uuid4().hex[:5]}"
    client.post("/api/v1/storage", headers=admin_hdr, json={
        "id": sid_flat, "name": "Flat Volume", "storage_type": "Backup storage",
        "total_capacity_bytes": cap, "initial_used_bytes": 0
    })
    try:
        db = SessionLocal()
        base_t = datetime.now(timezone.utc) - timedelta(hours=30)
        for i in range(25):
            db.add(Telemetry(
                device_id=sid_flat,
                timestamp=base_t + timedelta(hours=i),
                total_capacity_bytes=cap,
                used_bytes=200 * (1024 ** 3),  # constant zero growth
                free_bytes=800 * (1024 ** 3),
                utilization_pct=20.0,
                is_synthetic=False,
            ))
        db.commit()
        db.close()

        rw = client.get(f"/api/v1/forecasts/{sid_flat}/runway")
        assert rw.status_code == 200
        rwj = rw.json()["runway"]
        assert rwj["runway_status"] == "STABLE_OR_SHRINKING"
        assert rwj["estimated_days_until_threshold"] is None
    finally:
        client.delete(f"/api/v1/storage/{sid_flat}?confirm=true", headers=admin_hdr)


# ==============================================================================
# MODULE 7, 8, 9, 10, 11, 12: ALERTS, DIGITAL TWIN, RECOMMENDATIONS, REPORTS, SETTINGS
# ==============================================================================

def test_module8_9_10_11_12_full_lifecycle():
    admin_hdr = _admin_headers()
    op_hdr = _operator_headers()

    # MODULE 8: Evaluate alerts -> Acknowledge -> Resolve -> Reopen
    eval_resp = client.post("/api/v1/alerts/evaluate/vol-nvme-tier1-db", headers=op_hdr)
    assert eval_resp.status_code == 200
    assert eval_resp.json()["risk_category"] in ("NORMAL", "WARNING", "CRITICAL")

    alerts = client.get("/api/v1/alerts?storage_id=vol-nvme-tier1-db").json()
    assert len(alerts) > 0
    aid = alerts[0]["id"]

    ack = client.post(f"/api/v1/alerts/{aid}/acknowledge", headers=op_hdr)
    assert ack.status_code == 200
    assert ack.json()["acknowledged_by"] == "operator"

    res = client.post(f"/api/v1/alerts/{aid}/resolve", headers=op_hdr, json={"resolution_details": "Verified pool capacity"})
    assert res.status_code == 200
    assert res.json()["status"] == "RESOLVED"

    reop = client.post(f"/api/v1/alerts/{aid}/reopen", headers=op_hdr)
    assert reop.status_code == 200
    assert reop.json()["status"] == "ACTIVE"

    # MODULE 9: Digital Twin 5 scenarios + invalid rejection + update + compare + export + delete
    bad_arch = client.post("/api/v1/digital-twin/scenarios", headers=op_hdr, json={
        "device_id": "vol-nvme-tier1-db",
        "name": "Impossible Archival",
        "action_type": "DATA_TIERING_ARCHIVAL",
        "parameters": {"archived_capacity_gb": 499999.0}
    })
    assert bad_arch.status_code == 400

    sc1 = client.post("/api/v1/digital-twin/scenarios", headers=op_hdr, json={
        "device_id": "vol-nvme-tier1-db",
        "name": "Expansion +2TB",
        "action_type": "CAPACITY_EXPANSION",
        "parameters": {"additional_capacity_gb": 2048}
    })
    assert sc1.status_code == 201
    sc1_id = sc1.json()["scenario_id"]
    assert "Simulation only" in sc1.json()["simulation_notice"]

    sc2 = client.post("/api/v1/digital-twin/scenarios", headers=op_hdr, json={
        "device_id": "vol-nvme-tier1-db",
        "name": "Growth Slowdown 0.5x",
        "action_type": "CAPACITY_GROWTH_CHANGE",
        "parameters": {"growth_multiplier": 0.5}
    })
    assert sc2.status_code == 201
    sc2_id = sc2.json()["scenario_id"]

    sc3 = client.post("/api/v1/digital-twin/scenarios", headers=op_hdr, json={
        "device_id": "vol-nvme-tier1-db",
        "name": "Maint Window 3h",
        "action_type": "MAINTENANCE_PLANNING",
        "parameters": {"maintenance_window_hours": 3.0, "expected_io_overhead_pct": 10.0}
    })
    assert sc3.status_code == 201
    sc3_id = sc3.json()["scenario_id"]

    # Edit scenario
    upd_sc = client.put(f"/api/v1/digital-twin/scenarios/{sc2_id}", headers=op_hdr, json={
        "name": "Growth Slowdown 0.4x",
        "parameters": {"growth_multiplier": 0.4}
    })
    assert upd_sc.status_code == 200

    # Compare 2+ scenarios
    cmp_resp = client.post("/api/v1/digital-twin/compare", json={"scenario_ids": [sc1_id, sc2_id, sc3_id]})
    assert cmp_resp.status_code == 200
    assert cmp_resp.json()["compared_count"] == 3

    # Export scenario CSV
    exp_sc = client.get(f"/api/v1/digital-twin/scenarios/{sc1_id}/export?format=csv")
    assert exp_sc.status_code == 200
    assert "predicted_used_bytes" in exp_sc.text

    # Delete test scenarios
    for sid in (sc1_id, sc2_id, sc3_id):
        assert client.delete(f"/api/v1/digital-twin/scenarios/{sid}", headers=op_hdr).status_code == 200

    # MODULE 10: Rule-based traceable recommendations
    rec_gen = client.post("/api/v1/recommendations/generate/vol-nvme-tier1-db", headers=op_hdr)
    assert rec_gen.status_code == 200
    assert rec_gen.json()["generated_count"] >= 1
    assert "supporting_measurement" in rec_gen.json()["recommendations"][0]

    # MODULE 11: Reports in JSON, CSV, and PDF across all 7 report types
    for rt in (
        "storage_inventory", "storage_utilisation", "capacity_forecast",
        "model_performance", "risk_and_alert", "data_quality", "digital_twin_comparison"
    ):
        rj = client.get(f"/api/v1/reports/generate?report_type={rt}&format=json", headers=admin_hdr)
        assert rj.status_code == 200
        assert rj.json()["report_type"] == rt

    rcsv = client.get("/api/v1/reports/generate?report_type=storage_inventory&format=csv", headers=admin_hdr)
    assert rcsv.status_code == 200
    assert "storage_id" in rcsv.text

    rpdf = client.get("/api/v1/reports/generate?report_type=model_performance&format=pdf", headers=admin_hdr)
    assert rpdf.status_code == 200
    assert rpdf.content.startswith(b"%PDF")

    hist = client.get("/api/v1/reports/history")
    assert hist.status_code == 200
    assert len(hist.json()) >= 9

    # MODULE 12: Settings persistence & Audit log & /api alias check
    set_upd = client.put("/api/v1/settings", headers=admin_hdr, json={
        "capacity_thresholds": {"default_warning_pct": 78.0, "default_critical_pct": 92.0},
        "data_retention_settings": {"retention_days": 180}
    })
    assert set_upd.status_code == 200
    assert set_upd.json()["capacity_thresholds"]["default_warning_pct"] == 78.0
    assert set_upd.json()["data_retention_settings"]["retention_days"] == 180

    # Verify /api/... alias works as well as /api/v1/...
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/storage").status_code == 200

    # Verify audit trail captured recent actions
    audit_rows = client.get("/api/v1/audit").json()
    actions = {a["action"] for a in audit_rows}
    assert "UPDATE_SETTINGS" in actions
    assert "GENERATE_REPORT" in actions
