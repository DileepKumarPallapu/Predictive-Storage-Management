import pytest
from datetime import datetime, timedelta, timezone
import pandas as pd
from app.collector.synthetic import SyntheticGenerator
from app.ml.feature_pipeline import FeaturePipeline
from app.ml.models import PersistenceForecaster, SeasonalNaiveForecaster, LightGBMQuantileForecaster, run_forecast
from app.simulator.digital_twin import DigitalTwinSimulator
from app.services.risk_engine import RiskEngine
from app.services.recommendation_engine import RecommendationEngine

def test_synthetic_generator_deterministic():
    gen1 = SyntheticGenerator(seed=42)
    gen2 = SyntheticGenerator(seed=42)
    dev_cfg = SyntheticGenerator.DEVICES_CONFIG[0]
    
    t1 = gen1.generate_device_telemetry(dev_cfg, hours_history=48)
    t2 = gen2.generate_device_telemetry(dev_cfg, hours_history=48)
    
    assert len(t1) == 49
    assert len(t2) == 49
    assert t1[0]["used_bytes"] == t2[0]["used_bytes"]
    assert t1[10]["latency_p95_ms"] == t2[10]["latency_p95_ms"]
    assert all(r["is_synthetic"] for r in t1)

def test_feature_pipeline_no_future_leakage():
    gen = SyntheticGenerator(seed=42)
    dev_cfg = SyntheticGenerator.DEVICES_CONFIG[0]
    records = gen.generate_device_telemetry(dev_cfg, hours_history=100)
    
    df = FeaturePipeline.prepare_dataframe(records)
    X, y = FeaturePipeline.extract_features(df, target_col="used_bytes")
    
    assert not X.empty
    assert len(X) == len(y)
    # Check that feature columns do not include target_col directly
    assert "used_bytes" not in X.columns

def test_forecasting_models_monotonicity_and_bounds():
    gen = SyntheticGenerator(seed=42)
    dev_cfg = SyntheticGenerator.DEVICES_CONFIG[0]
    records = gen.generate_device_telemetry(dev_cfg, hours_history=72)
    total_cap = float(dev_cfg["total_capacity_bytes"])

    # Test LightGBM Quantile
    res_lgb = run_forecast(records, target_metric="used_bytes", model_type="lightgbm_quantile", horizon_hours=24, total_capacity=total_cap)
    assert len(res_lgb["q50"]) == 24
    assert len(res_lgb["q10"]) == 24
    assert len(res_lgb["q90"]) == 24
    
    for lo, med, hi in zip(res_lgb["q10"], res_lgb["q50"], res_lgb["q90"]):
        assert lo <= med <= hi
        assert 0.0 <= lo
        assert hi <= total_cap

    # Test Seasonal Naive
    res_sn = run_forecast(records, target_metric="used_bytes", model_type="seasonal_naive", horizon_hours=24, total_capacity=total_cap)
    assert len(res_sn["q50"]) == 24
    for lo, med, hi in zip(res_sn["q10"], res_sn["q50"], res_sn["q90"]):
        assert lo <= med <= hi

    # Test Persistence
    res_p = run_forecast(records, target_metric="used_bytes", model_type="persistence", horizon_hours=24, total_capacity=total_cap)
    assert len(res_p["q50"]) == 24
    for lo, med, hi in zip(res_p["q10"], res_p["q50"], res_p["q90"]):
        assert lo <= med <= hi

def test_digital_twin_safety_envelope_enforcement():
    dev_meta = {
        "id": "vol-nvme-tier1-db",
        "total_capacity_bytes": 10 * 1024 * 1024 * 1024 * 1024,
        "critical_threshold_pct": 90.0,
        "warning_threshold_pct": 80.0,
        "max_acceptable_latency_ms": 15.0,
        "current_latency_p95_ms": 1.5
    }
    base_forecast = {
        "timestamps": [datetime.now(timezone.utc) + timedelta(hours=i) for i in range(24)],
        "q50": [8.5e12 + i * 5e10 for i in range(24)]
    }

    # Action 1: Tier Cold Data
    tier_res = DigitalTwinSimulator.simulate_scenario(
        device_id="vol-nvme-tier1-db",
        device_metadata=dev_meta,
        base_forecast=base_forecast,
        action_type="TIER_COLD_DATA",
        parameters={"data_volume_gb": 1000.0, "migration_rate_mb_s": 150.0}
    )
    assert tier_res["is_simulated_estimate"] is True
    assert tier_res["safety_envelope_passed"] is True
    assert tier_res["counterfactual_q50"][-1] < base_forecast["q50"][-1]

    # Action 2: Unsafe action violating latency constraint
    dev_meta_fragile = dict(dev_meta, current_latency_p95_ms=14.5, max_acceptable_latency_ms=15.0)
    unsafe_res = DigitalTwinSimulator.simulate_scenario(
        device_id="vol-nvme-tier1-db",
        device_metadata=dev_meta_fragile,
        base_forecast=base_forecast,
        action_type="TIER_COLD_DATA",
        parameters={"data_volume_gb": 2000.0, "migration_rate_mb_s": 300.0}
    )
    assert unsafe_res["safety_envelope_passed"] is False
    assert len(unsafe_res["violation_reasons"]) > 0

def test_risk_engine_and_runway():
    dev_meta = {
        "id": "vol-nvme-tier1-db",
        "total_capacity_bytes": 10e12,
        "warning_threshold_pct": 80.0,
        "critical_threshold_pct": 90.0,
        "max_acceptable_latency_ms": 20.0,
        "current_latency_p95_ms": 2.1
    }
    forecast_result = {
        "timestamps": [datetime.now(timezone.utc) + timedelta(hours=i) for i in range(72)],
        "q10": [7.0e12 + i * 2e10 for i in range(72)],
        "q50": [7.5e12 + i * 2.5e10 for i in range(72)],
        "q90": [8.0e12 + i * 3e10 for i in range(72)]
    }
    risk_out = RiskEngine.assess_device_risk("vol-nvme-tier1-db", dev_meta, forecast_result)
    assert "runway_hours_estimate" in risk_out
    assert risk_out["runway_hours_lower_bound"] <= risk_out["runway_hours_estimate"]
    assert risk_out["risk_level"] in ["NOMINAL", "WARNING", "ELEVATED", "CRITICAL"]
    assert len(risk_out["risk_contributors"]) > 0
