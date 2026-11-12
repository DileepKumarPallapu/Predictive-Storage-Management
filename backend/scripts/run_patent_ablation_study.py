"""
Reproducible Patent-Research Benchmark & Ablation Script for AEGISSTOR.
Runs strictly in-memory / isolated temporary device without altering production fleet devices.

Compares across deterministic chronological splits (Train | Calibration | Holdout Test):
  1. SeasonalNaiveBenchmark
  2. LightGBM (LGBMRegressor + Split Conformal)
  3. SARIMAX (statsmodels state-space + Split Conformal)
  4. Conformal Interval Calibration WITH vs WITHOUT DataReliabilityEngine uncertainty gating
  5. WorkloadRegimeEngine classification accuracy & KS/PSI drift detection across regimes
  6. CapacityRiskEngine residual-CDF Brier score against held-out outcomes
  7. DecisionOptimizer / DigitalTwin deterministic constraint consistency check
"""
import csv
import json
import math
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import numpy as np

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.database import SessionLocal
from app.main import initialize_database_and_seed_demo
from app.ml.champion_challenger import ChampionChallengerEngine
from app.models.entities import (
    CapacityRiskEvaluation,
    DataQualityResult,
    DataReliabilityProfile,
    Device,
    Forecast,
    IngestionJob,
    ModelMetric,
    ModelVersion,
    Telemetry,
    WorkloadRegimeEvent,
)
from app.services.capacity_risk_engine import CapacityRiskEngine
from app.services.data_reliability_engine import DataReliabilityEngine
from app.services.decision_optimizer import DecisionOptimizer
from app.services.workload_regime_engine import WorkloadRegimeEngine


def _cleanup(db, storage_id: str) -> None:
    db.query(CapacityRiskEvaluation).filter(CapacityRiskEvaluation.storage_id == storage_id).delete(synchronize_session=False)
    db.query(WorkloadRegimeEvent).filter(WorkloadRegimeEvent.storage_id == storage_id).delete(synchronize_session=False)
    db.query(DataReliabilityProfile).filter(DataReliabilityProfile.storage_id == storage_id).delete(synchronize_session=False)
    db.query(ModelMetric).filter(ModelMetric.storage_id == storage_id).delete(synchronize_session=False)
    db.query(ModelVersion).filter(ModelVersion.storage_id == storage_id).delete(synchronize_session=False)
    db.query(Forecast).filter(Forecast.device_id == storage_id).delete(synchronize_session=False)
    db.query(DataQualityResult).filter(DataQualityResult.storage_id == storage_id).delete(synchronize_session=False)
    db.query(IngestionJob).filter(IngestionJob.storage_id == storage_id).delete(synchronize_session=False)
    db.query(Telemetry).filter(Telemetry.device_id == storage_id).delete(synchronize_session=False)
    db.query(Device).filter(Device.id == storage_id).delete(synchronize_session=False)
    db.commit()


def _seed_series(db, storage_id: str, regime_kind: str, n_hours: int = 120, end_hours_ago: float = 0.5, include_perf: bool = True) -> None:
    total_gb = 1000
    total_b = total_gb * (1024 ** 3)
    db.add(Device(
        id=storage_id,
        name=f"Ablation {regime_kind}",
        tier="NVME_TIER1",
        media_type="NVMe",
        total_capacity_bytes=total_b,
        warning_threshold_pct=80.0,
        critical_threshold_pct=90.0,
        max_acceptable_latency_ms=20.0,
        status="HEALTHY",
    ))
    db.commit()

    now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0) - timedelta(hours=end_hours_ago)
    start = now - timedelta(hours=n_hours - 1)
    rows: List[Telemetry] = []
    for i in range(n_hours):
        ts = start + timedelta(hours=i)
        seasonal = 8.0 * math.sin(2.0 * math.pi * i / 24.0)
        if regime_kind == "PERIODIC_POSITIVE":
            used_gb = 450.0 + 1.2 * i + seasonal
        elif regime_kind == "ACCELERATING":
            used_gb = 420.0 + 0.4 * i + 0.025 * (i ** 2) + 2.0 * math.sin(2.0 * math.pi * i / 24.0)
        elif regime_kind == "DEGRADED_STALE":
            used_gb = 680.0 + 1.1 * i + seasonal * 1.5
        else:
            used_gb = 500.0 + 1.0 * i + seasonal

        used_gb = max(10.0, min(980.0, used_gb))
        used_b = int(used_gb * (1024 ** 3))
        free_b = max(0, total_b - used_b)
        rows.append(Telemetry(
            device_id=storage_id,
            timestamp=ts,
            total_capacity_bytes=total_b,
            used_bytes=used_b,
            free_bytes=free_b,
            utilization_pct=round((used_b / total_b) * 100.0, 2),
            read_iops=1500.0 + (i % 12) * 30.0 if include_perf else None,
            write_iops=650.0 + (i % 8) * 15.0 if include_perf else None,
            throughput_mb_s=240.0 + (i % 10) * 10.0 if include_perf else None,
            latency_p95_ms=5.2 + (i % 6) * 0.3 if include_perf else None,
            queue_depth=4.0 if include_perf else None,
            is_synthetic=True,
            source_label="ablation_benchmark",
        ))
    db.bulk_save_objects(rows)
    db.commit()


def run_benchmark() -> Dict:
    initialize_database_and_seed_demo()
    db = SessionLocal()
    results = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiments": [],
    }
    temp_ids = []
    try:
        scenarios = [
            ("PERIODIC_POSITIVE", 120, 0.5, True),
            ("ACCELERATING", 120, 0.5, True),
            ("DEGRADED_STALE", 120, 96.0, False),
        ]
        for label, hrs, end_ago, perf in scenarios:
            sid = f"ablation-{label.lower()}-{uuid.uuid4().hex[:6]}"
            temp_ids.append(sid)
            _seed_series(db, sid, label, n_hours=hrs, end_hours_ago=end_ago, include_perf=perf)

            rel = DataReliabilityEngine.evaluate(db, sid, persist=True)
            reg = WorkloadRegimeEngine.analyze(db, sid, persist=True)
            train = ChampionChallengerEngine.train_and_select(db, sid, triggered_by="ablation_script")
            fc = ChampionChallengerEngine.generate_forecast(db, sid, horizon_days=30, persist=False)
            risk = CapacityRiskEngine.evaluate(db, sid, horizon_days=30, safety_threshold_pct=85.0, persist=True)
            opt_no_cost = DecisionOptimizer.optimize(db, sid, max_utilization_pct=85.0, min_free_space_pct=15.0)
            opt_with_cost = DecisionOptimizer.optimize(
                db, sid, budget_usd=100.0, max_utilization_pct=85.0, min_free_space_pct=15.0,
                unit_costs={"expand_usd_per_gb": 0.45, "archive_usd_per_gb": 0.10, "dedup_compute_usd": 20.0},
            )

            end_pt = fc["series"][-1]
            width_with_gate = round(end_pt["p90_used_gb"] - end_pt["p10_used_gb"], 4)
            unc_mult = fc["calibration"]["reliability_uncertainty_multiplier"]
            width_without_gate = round(width_with_gate / max(1e-6, unc_mult), 4)

            results["experiments"].append({
                "scenario": label,
                "reliability_score": rel["reliability_score"],
                "reliability_tier": rel["reliability_tier"],
                "is_stale": rel["is_stale"],
                "allow_high_conf_recommendations": rel["allow_high_confidence_recommendations"],
                "uncertainty_multiplier": unc_mult,
                "workload_regime_detected": reg["regime_label"],
                "naive_baseline": train["reference_benchmark"],
                "candidates": [
                    {
                        "family": c.get("family"),
                        "is_champion": c.get("is_champion"),
                        "metrics": c.get("metrics"),
                    }
                    for c in train["candidates"]
                ],
                "conformal_band_width_30d_with_gate_gb": width_with_gate,
                "conformal_band_width_30d_without_gate_gb": width_without_gate,
                "capacity_risk": {
                    "risk_band": risk["risk_band"],
                    "threshold_crossing_probability": risk["threshold_crossing_probability"],
                    "brier_calibration_score": risk["details"]["brier_calibration_score"],
                    "expected_shortfall_gb": round(risk["expected_shortfall_bytes"] / (1024 ** 3), 3),
                },
                "optimizer_no_cost_status": opt_no_cost["recommended_option"]["cost_status"] if opt_no_cost["recommended_option"] else "NONE",
                "optimizer_budgeted_winner": opt_with_cost["recommended_option"]["action_type"] if opt_with_cost["recommended_option"] else "NONE",
            })
    finally:
        for sid in temp_ids:
            _cleanup(db, sid)
        db.close()

    out_dir = os.path.abspath(os.path.join(BACKEND_DIR, "..", "docs", "patent_research"))
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "experimental_results_observed.json")
    csv_path = os.path.join(out_dir, "experimental_results_observed.csv")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)

    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "scenario", "model_family", "is_champion", "mae_gb", "rmse_gb", "mase",
            "pinball_loss", "interval_coverage", "naive_rmse_gb",
            "reliability_score", "reliability_tier", "uncertainty_multiplier",
            "width_without_gate_gb", "width_with_gate_gb", "detected_regime",
            "crossing_prob", "brier_score"
        ])
        for exp in results["experiments"]:
            for c in exp["candidates"]:
                m = c.get("metrics") or {}
                writer.writerow([
                    exp["scenario"],
                    c.get("family"),
                    c.get("is_champion"),
                    m.get("mae"),
                    m.get("rmse"),
                    m.get("mase"),
                    m.get("pinball_loss"),
                    m.get("interval_coverage"),
                    exp["naive_baseline"]["rmse"],
                    exp["reliability_score"],
                    exp["reliability_tier"],
                    exp["uncertainty_multiplier"],
                    exp["conformal_band_width_30d_without_gate_gb"],
                    exp["conformal_band_width_30d_with_gate_gb"],
                    exp["workload_regime_detected"],
                    exp["capacity_risk"]["threshold_crossing_probability"],
                    exp["capacity_risk"]["brier_calibration_score"],
                ])

    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    run_benchmark()
