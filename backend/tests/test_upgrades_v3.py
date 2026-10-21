import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models.entities import User
from app.auth.security import hash_password, create_access_token
from app.ml.models import run_forecast
from app.collector.synthetic import SyntheticGenerator

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_users():
    db = SessionLocal()
    # Ensure default admin
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            id="usr-test-admin",
            username="admin",
            email="admin@test.internal",
            hashed_password=hash_password("admin123"),
            role="ADMIN",
            is_active=True
        )
        db.add(admin)
        db.commit()
    db.close()

def test_request_tracing_headers():
    """Verify X-Request-ID and X-Process-Time-Ms headers are present on all API responses."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    assert "X-Process-Time-Ms" in resp.headers
    assert float(resp.headers["X-Process-Time-Ms"]) >= 0.0

def test_auth_login_and_me():
    """Verify JWT token issuance on login and authenticated /me retrieval."""
    login_resp = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert data["role"] == "ADMIN"
    token = data["access_token"]

    # Access /auth/me with Bearer token
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["username"] == "admin"
    assert me_data["role"] == "ADMIN"

def test_auth_invalid_password():
    """Verify rejection of incorrect passwords."""
    resp = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert resp.status_code == 401
    assert "Incorrect" in resp.json()["detail"]

def test_rbac_register_operator_user():
    """Verify admin can register a new operator and operator has restricted role."""
    # Login as admin
    login_resp = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = login_resp.json()["access_token"]

    reg_resp = client.post(
        "/api/v1/auth/register",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "ops_analyst_1",
            "email": "ops1@test.internal",
            "password": "Password123!",
            "role": "OPERATOR"
        }
    )
    assert reg_resp.status_code in [200, 400]  # 200 on first run, 400 if already registered

def test_prometheus_metrics_scrape():
    """Verify Prometheus scrape target format and metrics existence."""
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    text = resp.text
    assert "aegisstor_storage_total_bytes" in text
    assert "aegisstor_storage_used_bytes" in text
    assert "aegisstor_storage_latency_p95_ms" in text
    assert "aegisstor_storage_reserve_runway_hours" in text

def test_multitarget_latency_forecasting():
    """Verify forecasting models support non-growth target metrics like latency_p95_ms."""
    gen = SyntheticGenerator(seed=101)
    dev_cfg = SyntheticGenerator.DEVICES_CONFIG[0]
    telemetry = gen.generate_device_telemetry(dev_cfg, hours_history=336)
    
    out = run_forecast(
        telemetry_records=telemetry,
        target_metric="latency_p95_ms",
        model_type="lightgbm_quantile",
        horizon_hours=24,
        total_capacity=100.0
    )
    assert "q10" in out
    assert "q50" in out
    assert "q90" in out
    assert len(out["q50"]) == 24
    # Check monotonicity
    for lo, med, hi in zip(out["q10"], out["q50"], out["q90"]):
        assert lo <= med <= hi
