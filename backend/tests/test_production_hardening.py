import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.collector.host_collector import HostStorageCollector
from app.config import Settings
from app.database import SessionLocal
from app.main import app
from app.models.entities import BackgroundJob
from app.services.object_storage import DurableObjectStorage, compute_sha256
from scripts.linux_collector_agent import (
    append_to_local_buffer,
    clear_local_buffer,
    load_local_buffer,
)
import worker as bg_worker

client = TestClient(app)


def test_granular_health_endpoints():
    for path in (
        "/health/live",
        "/health/ready",
        "/health/database",
        "/health/worker",
        "/health/realtime",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/health/database",
        "/api/v1/health/worker",
        "/api/v1/health/realtime",
    ):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} failed: {resp.status_code} {resp.text}"
        body = resp.json()
        assert "DATABASE_URL" not in str(body)
        assert "SECRET_KEY" not in str(body)

    ready = client.get("/health/ready").json()
    assert ready["status"] == "ready"
    assert ready["dependencies"]["database"]["connected"] is True
    assert "realtime" in ready["dependencies"]
    assert "worker" in ready["dependencies"]


def test_production_safety_validation_guards():
    bad_secret = Settings(ENVIRONMENT="production", SECRET_KEY="short", CORS_ALLOWED_ORIGINS="https://app.example.com")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        bad_secret.validate_production_safety()

    bad_cors = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 40,
        CORS_ALLOWED_ORIGINS="*",
    )
    with pytest.raises(RuntimeError, match="CORS_ALLOWED_ORIGINS"):
        bad_cors.validate_production_safety()

    good = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 40,
        CORS_ALLOWED_ORIGINS="https://aegisstor.vercel.app",
    )
    good.validate_production_safety()


def test_object_storage_checksum_and_tamper_detection():
    storage = DurableObjectStorage()
    with tempfile.TemporaryDirectory() as tmpdir:
        fp = os.path.join(tmpdir, "test_model.joblib")
        with open(fp, "wb") as f:
            f.write(b"aegisstor-model-bytes-v1")

        uri, sha = storage.put_file(fp, category="models")
        assert uri.startswith("local://")
        assert sha == compute_sha256(fp)
        assert storage.ensure_local_file(fp, remote_uri=uri, expected_sha256=sha) == fp

        with open(fp, "wb") as f:
            f.write(b"tampered-model-bytes")
        with pytest.raises(ValueError, match="checksum mismatch"):
            storage.ensure_local_file(fp, remote_uri=uri, expected_sha256=sha)


def test_worker_stale_job_recovery_marks_failed():
    db = SessionLocal()
    job_id = "job-stale-test-001"
    try:
        db.query(BackgroundJob).filter(BackgroundJob.id == job_id).delete()
        stale_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1200)
        db.add(
            BackgroundJob(
                id=job_id,
                job_type="ML_TRAINING",
                storage_id="vol-test",
                status="RUNNING",
                stage="TRAINING",
                progress_pct=55,
                created_at=stale_time,
                updated_at=stale_time,
            )
        )
        db.commit()

        recovered = bg_worker.recover_stale_jobs(stale_seconds=600)
        assert recovered >= 1

        db.expire_all()
        refreshed = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        assert refreshed is not None
        assert refreshed.status == "FAILED"
        assert refreshed.stage == "FAILED"
        assert "recovery" in (refreshed.error_message or "").lower()
    finally:
        db.query(BackgroundJob).filter(BackgroundJob.id == job_id).delete()
        db.commit()
        db.close()


def test_linux_collector_local_buffer_retention_and_clear():
    with tempfile.TemporaryDirectory() as tmpdir:
        buf = os.path.join(tmpdir, "spool.jsonl")
        for i in range(5):
            count = append_to_local_buffer(buf, {"seq": i, "used_bytes": 1000 + i}, max_records=3)
        assert count == 3
        loaded = load_local_buffer(buf)
        assert [x["seq"] for x in loaded] == [2, 3, 4]
        clear_local_buffer(buf)
        assert load_local_buffer(buf) == []


def test_prometheus_unconfigured_returns_not_configured():
    res = HostStorageCollector.scrape_prometheus_node_exporter(endpoint_url="")
    assert res["status"] == "NOT_CONFIGURED"
    assert res["is_operational"] is False
