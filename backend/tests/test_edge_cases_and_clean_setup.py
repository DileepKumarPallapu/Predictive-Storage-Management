import pytest
import os
import tempfile
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.entities import Device, Telemetry, Alert, Recommendation
from app.collector.synthetic import SyntheticGenerator
from app.ml.models import run_forecast, PersistenceForecaster, LightGBMQuantileForecaster
from app.ml.calibration import ModelCalibrator
from app.simulator.digital_twin import DigitalTwinSimulator
from app.services.risk_engine import RiskEngine
from app.services.recommendation_engine import RecommendationEngine
from app.experiments.ablation_runner import AblationStudyRunner

def test_clean_database_initialization():
    """Verify that a pristine database initializes tables and relations cleanly."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Insert test device
        dev = Device(
            id="test-vol-01",
            name="Test NVMe",
            tier="NVME_TIER1",
            media_type="NVMe SSD",
            total_capacity_bytes=10**12,
            warning_threshold_pct=80.0,
            critical_threshold_pct=90.0,
            status="HEALTHY"
        )
        db.add(dev)
        db.commit()

        queried = db.query(Device).filter(Device.id == "test-vol-01").first()
        assert queried is not None
        assert queried.name == "Test NVMe"
    finally:
        db.close()
        engine.dispose()

def test_edge_case_zero_or_negative_growth():
    """Telemetry with zero or negative growth should not crash or produce negative runway."""
    now = datetime.now(timezone.utc)
    flat_records = [
        {
            "timestamp": now - timedelta(hours=i),
            "device_id": "test-vol-01",
            "used_bytes": 500000000000,  # Exactly constant
            "free_bytes": 500000000000,
            "read_iops": 5000.0,
            "write_iops": 4000.0,
            "throughput_mb_s": 200.0,
            "latency_p95_ms": 2.0,
            "queue_depth": 1.0,
            "is_synthetic": True
        }
        for i in range(48, -1, -1)
    ]

    total_cap = 10**12
    fc = run_forecast(flat_records, target_metric="used_bytes", model_type="lightgbm_quantile", horizon_hours=24, total_capacity=total_cap)
    assert len(fc["q50"]) == 24
    assert all(v >= 0.0 for v in fc["q10"])

    dev_meta = {
        "id": "test-vol-01",
        "total_capacity_bytes": total_cap,
        "warning_threshold_pct": 80.0,
        "critical_threshold_pct": 90.0,
        "max_acceptable_latency_ms": 20.0,
        "current_used_bytes": 500000000000,
        "current_latency_p95_ms": 2.0
    }
    risk = RiskEngine.assess_device_risk("test-vol-01", dev_meta, fc)
    assert risk["runway_hours_estimate"] >= 72.0
    assert risk["risk_level"] in ["NOMINAL", "WARNING"]

def test_edge_case_sudden_capacity_burst():
    """Sudden 300GB spike in last 3 hours should properly trigger elevated risk."""
    now = datetime.now(timezone.utc)
    records = []
    base_val = 750000000000
    for i in range(48, -1, -1):
        val = base_val + (300000000000 if i < 3 else 0)  # Sudden burst
        records.append({
            "timestamp": now - timedelta(hours=i),
            "device_id": "test-vol-01",
            "used_bytes": val,
            "free_bytes": 10**12 - val,
            "read_iops": 8000.0,
            "write_iops": 15000.0,
            "throughput_mb_s": 450.0,
            "latency_p95_ms": 12.0 if i < 3 else 2.5,
            "queue_depth": 4.5 if i < 3 else 1.2,
            "is_synthetic": True
        })

    total_cap = 10**12
    fc = run_forecast(records, target_metric="used_bytes", model_type="lightgbm_quantile", horizon_hours=24, total_capacity=total_cap)
    dev_meta = {
        "id": "test-vol-01",
        "total_capacity_bytes": total_cap,
        "warning_threshold_pct": 80.0,
        "critical_threshold_pct": 90.0,
        "max_acceptable_latency_ms": 20.0,
        "current_used_bytes": records[-1]["used_bytes"],
        "current_latency_p95_ms": 12.0
    }
    risk = RiskEngine.assess_device_risk("test-vol-01", dev_meta, fc)
    # Since usage is at 105% (or breached 90%), risk must be CRITICAL
    assert risk["risk_level"] == "CRITICAL"

def test_edge_case_hard_safety_envelope_all_violating():
    """When a device is at 98% capacity and SLA latency limit is 2ms, any heavy action must be disqualified."""
    dev_meta = {
        "id": "fragile-vol",
        "total_capacity_bytes": 10**12,
        "warning_threshold_pct": 80.0,
        "critical_threshold_pct": 90.0,
        "max_acceptable_latency_ms": 3.0,
        "current_used_bytes": 980000000000,
        "current_latency_p95_ms": 2.9
    }
    base_forecast = {
        "timestamps": [datetime.now(timezone.utc) + timedelta(hours=i) for i in range(24)],
        "q50": [980000000000 for _ in range(24)]
    }

    sim = DigitalTwinSimulator.simulate_scenario(
        device_id="fragile-vol",
        device_metadata=dev_meta,
        base_forecast=base_forecast,
        action_type="TIER_COLD_DATA",
        parameters={"data_volume_gb": 100.0, "migration_rate_mb_s": 400.0}
    )
    assert sim["safety_envelope_passed"] is False
    assert len(sim["violation_reasons"]) > 0

def test_ablation_study_runner_execution():
    """Verify that AblationStudyRunner executes and returns complete empirical metrics."""
    res = AblationStudyRunner.run_all_ablations()
    assert "ablation_1_forecast_calibration" in res
    assert "ablation_2_lead_time_planning" in res
    assert "ablation_3_intervention_overhead" in res
    
    cal = res["ablation_1_forecast_calibration"]
    assert len(cal) == 4
    for model_res in cal:
        assert "mae_gb" in model_res
        assert "empirical_coverage" in model_res
        assert "mean_interval_width_gb" in model_res

def test_seeding_idempotency():
    """Verify that calling database seeder repeatedly creates zero duplicates."""
    from app.main import initialize_database_and_seed_demo
    from app.database import SessionLocal
    
    # Run seeder twice
    initialize_database_and_seed_demo()
    initialize_database_and_seed_demo()

    db = SessionLocal()
    try:
        dev_count = db.query(Device).filter(Device.tier != "HOST_LOCAL").count()
        assert dev_count == 4  # Exactly the 4 configured demo pools
        alert_count = db.query(Alert).count()
        assert alert_count >= 3
    finally:
        db.close()

def test_edge_case_missing_telemetry_intervals():
    """Generator under MISSING_TELEMETRY scenario must omit samples without fabricating points."""
    gen = SyntheticGenerator(seed=99)
    dev_cfg = SyntheticGenerator.DEVICES_CONFIG[0]
    records = gen.generate_device_telemetry(dev_cfg, hours_history=720, scenario_type="MISSING_TELEMETRY")
    
    # Should have fewer than 721 records due to dropped dropout intervals
    assert len(records) < 721
    assert all(r["is_synthetic"] is True for r in records)
    assert all(r["source_label"] == "synthetic_generator_v1" for r in records)

def test_time_to_breach_status_edge_cases():
    """Check that RiskEngine returns clear breach_status for zero growth and already breached."""
    dev_meta = {
        "id": "breached-vol",
        "total_capacity_bytes": 10**12,
        "warning_threshold_pct": 80.0,
        "critical_threshold_pct": 90.0,
        "max_acceptable_latency_ms": 20.0,
        "current_used_bytes": 950000000000,
        "current_latency_p95_ms": 2.0
    }
    forecast_result = {
        "timestamps": [datetime.now(timezone.utc) + timedelta(hours=i) for i in range(24)],
        "q10": [950000000000 for _ in range(24)],
        "q50": [950000000000 for _ in range(24)],
        "q90": [950000000000 for _ in range(24)]
    }
    res = RiskEngine.assess_device_risk("breached-vol", dev_meta, forecast_result)
    assert res["breach_status"] == "ALREADY_BREACHED"
    assert res["risk_level"] == "CRITICAL"

