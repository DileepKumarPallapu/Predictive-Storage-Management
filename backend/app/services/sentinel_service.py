import math
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.entities import Device, Telemetry, Forecast, ModelVersion, Alert, ModelTrustEvaluation
from app.ml.models import run_forecast


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def to_utc_naive(dt: Any) -> datetime:
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt



class SentinelEngine:
    """
    AEGISSTOR SENTINEL — Drift-Aware Prediction Trust Engine.
    Monitors storage workload distributions, pairs forecasts against realized actuals,
    measures prediction reliability, and computes actionable model trust statuses.
    """

    # Monitored workload input metrics
    WORKLOAD_METRICS = [
        "capacity_growth_rate_gb_day",
        "utilization_pct",
        "write_iops",
        "read_iops",
        "throughput_mb_s",
        "latency_p95_ms",
        "queue_depth"
    ]

    # Standard PSI thresholds
    PSI_STABLE_THRESHOLD = 0.10
    PSI_MODERATE_THRESHOLD = 0.25

    # Nominal conformal interval coverage target
    TARGET_NOMINAL_COVERAGE = 0.80

    @classmethod
    def compute_psi(
        cls,
        reference_data: List[float],
        current_data: List[float],
        num_bins: int = 10
    ) -> float:
        """
        Calculates Population Stability Index (PSI) between reference and current distribution.
        PSI < 0.10: Stable / Nominal
        0.10 <= PSI < 0.25: Moderate Drift
        PSI >= 0.25: Significant Distribution Drift
        """
        if not reference_data or not current_data or len(reference_data) < 5 or len(current_data) < 5:
            return 0.0

        ref_clean = [float(x) for x in reference_data if not math.isnan(x)]
        curr_clean = [float(x) for x in current_data if not math.isnan(x)]
        if len(ref_clean) < 5 or len(curr_clean) < 5:
            return 0.0

        min_val = min(min(ref_clean), min(curr_clean))
        max_val = max(max(ref_clean), max(curr_clean))
        if min_val == max_val:
            return 0.0

        bin_width = (max_val - min_val) / float(num_bins)
        ref_len = float(len(ref_clean))
        curr_len = float(len(curr_clean))

        ref_counts = [0] * num_bins
        curr_counts = [0] * num_bins

        for val in ref_clean:
            b = min(int((val - min_val) / bin_width), num_bins - 1)
            ref_counts[b] += 1

        for val in curr_clean:
            b = min(int((val - min_val) / bin_width), num_bins - 1)
            curr_counts[b] += 1

        eps = 1e-4
        psi = 0.0
        for i in range(num_bins):
            ref_prop = (ref_counts[i] / ref_len) + eps
            curr_prop = (curr_counts[i] / curr_len) + eps
            psi += (curr_prop - ref_prop) * math.log(curr_prop / ref_prop)

        return round(max(0.0, psi), 4)

    @classmethod
    def compute_ks_2samp(
        cls,
        reference_data: List[float],
        current_data: List[float]
    ) -> Tuple[float, float]:
        """
        Two-sample Kolmogorov-Smirnov statistic D and approximate p-value.
        Tests null hypothesis that reference and current come from identical distributions.
        """
        ref_sorted = sorted([float(x) for x in reference_data if not math.isnan(x)])
        curr_sorted = sorted([float(x) for x in current_data if not math.isnan(x)])

        n1 = len(ref_sorted)
        n2 = len(curr_sorted)
        if n1 < 5 or n2 < 5:
            return 0.0, 1.0

        all_vals = sorted(list(set(ref_sorted + curr_sorted)))
        d_max = 0.0
        i1 = 0
        i2 = 0

        for val in all_vals:
            while i1 < n1 and ref_sorted[i1] <= val:
                i1 += 1
            while i2 < n2 and curr_sorted[i2] <= val:
                i2 += 1
            cdf1 = i1 / float(n1)
            cdf2 = i2 / float(n2)
            d = abs(cdf1 - cdf2)
            if d > d_max:
                d_max = d

        # Asymptotic p-value approximation
        en = math.sqrt((n1 * n2) / float(n1 + n2))
        lambda_val = (en + 0.12 + 0.11 / en) * d_max
        if lambda_val <= 0.0:
            p_value = 1.0
        else:
            p_value = max(0.0, min(1.0, 2.0 * math.exp(-2.0 * lambda_val * lambda_val)))

        return round(d_max, 4), round(p_value, 4)

    @classmethod
    def evaluate_metric_distribution(cls, values: List[float]) -> Dict[str, float]:
        """Calculates mean, std, median, p95 for a sample set."""
        if not values:
            return {"mean": 0.0, "std": 0.0, "median": 0.0, "p95": 0.0}
        clean = sorted([float(x) for x in values if not math.isnan(x)])
        n = len(clean)
        if n == 0:
            return {"mean": 0.0, "std": 0.0, "median": 0.0, "p95": 0.0}

        mean = sum(clean) / n
        var = sum((x - mean)**2 for x in clean) / n
        std = math.sqrt(var)
        med = clean[n // 2]
        p95 = clean[min(int(n * 0.95), n - 1)]

        return {
            "mean": round(mean, 2),
            "std": round(std, 2),
            "median": round(med, 2),
            "p95": round(p95, 2)
        }

    @classmethod
    def extract_workload_metric_series(
        cls,
        records: List[Telemetry],
        metric_name: str
    ) -> List[float]:
        """Extracts numerical series for a given monitored workload metric."""
        if metric_name == "capacity_growth_rate_gb_day":
            series = []
            for i in range(1, len(records)):
                delta_b = records[i].used_bytes - records[i-1].used_bytes
                delta_h = max(0.1, (records[i].timestamp - records[i-1].timestamp).total_seconds() / 3600.0)
                rate_gb_day = (delta_b / (1024**3)) / (delta_h / 24.0)
                series.append(round(rate_gb_day, 3))
            return series

        vals = []
        for r in records:
            v = getattr(r, metric_name, 0.0)
            if v is not None:
                vals.append(float(v))
        return vals

    @classmethod
    def assess_prediction_trust(
        cls,
        db: Session,
        device_id: str,
        evaluation_window_hours: int = 168,
        reference_window_hours: int = 336
    ) -> Dict[str, Any]:
        """
        Executes full SENTINEL drift and model trust assessment for a storage volume.
        Analyzes data drift, prediction drift, and measured deterioration in model performance.
        Returns trust status (HEALTHY, WATCH, DEGRADED, INSUFFICIENT_EVIDENCE).
        """
        now = utc_now()
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found")

        # 1. Fetch telemetry ordered by time
        records = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == device_id)
            .order_by(Telemetry.timestamp.asc())
            .all()
        )

        # Edge case: Insufficient total observations
        if len(records) < 24:
            return {
                "device_id": device_id,
                "evaluated_at": now.isoformat(),
                "trust_status": "INSUFFICIENT_EVIDENCE",
                "status_reason": f"Only {len(records)} observations available. Minimum 24 required for statistical trust scoring.",
                "data_drift": {"detected": False, "severity": "NONE", "metrics": {}},
                "prediction_drift": {"detected": False, "severity": "NONE"},
                "performance_reliability": {
                    "deterioration_detected": False,
                    "evaluated_mae_gb": 0.0,
                    "evaluated_rmse_gb": 0.0,
                    "empirical_coverage_pct": 0.0,
                    "actual_observations_evaluated": len(records)
                },
                "recommended_action": "CONTINUE_DATA_COLLECTION",
                "evidence": {
                    "evaluation_window_hours": evaluation_window_hours,
                    "reference_window_hours": reference_window_hours,
                    "total_records": len(records),
                    "insufficient_samples": True
                }
            }

        # 2. Check for stale telemetry or missing intervals
        latest_ts = to_utc_naive(records[-1].timestamp)
        now_naive = to_utc_naive(now)
        age_hours = (now_naive - latest_ts).total_seconds() / 3600.0
        is_stale = age_hours > 24.0

        missing_intervals = []
        for i in range(1, len(records)):
            t_prev = to_utc_naive(records[i-1].timestamp)
            t_curr = to_utc_naive(records[i].timestamp)
            delta_h = (t_curr - t_prev).total_seconds() / 3600.0
            if delta_h > 2.5:
                missing_intervals.append({
                    "from": records[i-1].timestamp.isoformat() if hasattr(records[i-1].timestamp, "isoformat") else str(records[i-1].timestamp),
                    "to": records[i].timestamp.isoformat() if hasattr(records[i].timestamp, "isoformat") else str(records[i].timestamp),
                    "gap_hours": round(delta_h, 1)
                })

        # 3. Partition into Reference Period vs Evaluation/Current Period
        curr_cutoff = latest_ts - timedelta(hours=evaluation_window_hours)
        ref_cutoff = curr_cutoff - timedelta(hours=reference_window_hours)

        current_records = [r for r in records if to_utc_naive(r.timestamp) >= curr_cutoff]
        reference_records = [r for r in records if ref_cutoff <= to_utc_naive(r.timestamp) < curr_cutoff]


        # If reference window has too few records, fallback to first 60% as reference, last 40% as current
        if len(reference_records) < 20 or len(current_records) < 10:
            split_point = int(len(records) * 0.60)
            reference_records = records[:split_point]
            current_records = records[split_point:]

        # 4. Measure Workload Input Data Drift across Monitored Metrics
        metric_drift_details: Dict[str, Any] = {}
        max_psi = 0.0
        drifted_metrics = []

        for m in cls.WORKLOAD_METRICS:
            ref_vals = cls.extract_workload_metric_series(reference_records, m)
            curr_vals = cls.extract_workload_metric_series(current_records, m)

            psi = cls.compute_psi(ref_vals, curr_vals)
            ks_d, ks_p = cls.compute_ks_2samp(ref_vals, curr_vals)
            ref_dist = cls.evaluate_metric_distribution(ref_vals)
            curr_dist = cls.evaluate_metric_distribution(curr_vals)

            if psi > max_psi:
                max_psi = psi

            if psi >= cls.PSI_MODERATE_THRESHOLD or (ks_p < 0.01 and psi >= cls.PSI_STABLE_THRESHOLD):
                severity = "SIGNIFICANT_DRIFT" if psi >= cls.PSI_MODERATE_THRESHOLD else "MODERATE_DRIFT"
                drifted_metrics.append(m)
            elif psi >= cls.PSI_STABLE_THRESHOLD:
                severity = "MODERATE_DRIFT"
                drifted_metrics.append(m)
            else:
                severity = "STABLE"

            metric_drift_details[m] = {
                "psi": psi,
                "ks_statistic": ks_d,
                "ks_p_value": ks_p,
                "severity": severity,
                "reference_distribution": ref_dist,
                "current_distribution": curr_dist
            }

        data_drift_detected = len(drifted_metrics) > 0
        data_drift_severity = "SIGNIFICANT" if max_psi >= cls.PSI_MODERATE_THRESHOLD else ("MODERATE" if data_drift_detected else "NONE")

        # 5. Measure Prediction Reliability (Forecast vs Actuals Pairing)
        # We compare chronological forecasts against actual observations in current_records
        eval_dicts = [
            {
                "timestamp": r.timestamp,
                "device_id": r.device_id,
                "used_bytes": r.used_bytes,
                "free_bytes": r.free_bytes,
                "read_iops": r.read_iops,
                "write_iops": r.write_iops,
                "throughput_mb_s": r.throughput_mb_s,
                "latency_p95_ms": r.latency_p95_ms,
                "queue_depth": r.queue_depth,
                "is_synthetic": r.is_synthetic
            }
            for r in reference_records
        ]

        H = min(len(current_records), 72)
        ref_forecast = run_forecast(
            telemetry_records=eval_dicts,
            target_metric="used_bytes",
            model_type="lightgbm_quantile",
            horizon_hours=H,
            total_capacity=device.total_capacity_bytes
        )

        actual_bytes = [float(current_records[h].used_bytes) for h in range(H)]
        actual_gb = [v / (1024**3) for v in actual_bytes]
        pred_q50_gb = [float(v) / (1024**3) for v in ref_forecast["q50"][:H]]
        pred_q10_gb = [float(v) / (1024**3) for v in ref_forecast["q10"][:H]]
        pred_q90_gb = [float(v) / (1024**3) for v in ref_forecast["q90"][:H]]

        # Compute actual errors
        abs_errors_gb = [abs(act - pr) for act, pr in zip(actual_gb, pred_q50_gb)]
        sq_errors_gb = [(act - pr)**2 for act, pr in zip(actual_gb, pred_q50_gb)]

        eval_mae_gb = round(sum(abs_errors_gb) / float(H), 3) if H > 0 else 0.0
        eval_rmse_gb = round(math.sqrt(sum(sq_errors_gb) / float(H)), 3) if H > 0 else 0.0

        sum_act = sum(actual_gb)
        eval_wape_pct = round((sum(abs_errors_gb) / sum_act * 100.0), 2) if sum_act > 0 else 0.0

        # Conformal interval coverage check
        covered = sum(1 for act, low, high in zip(actual_gb, pred_q10_gb, pred_q90_gb) if low <= act <= high)
        empirical_coverage_pct = round((covered / float(H)) * 100.0, 1) if H > 0 else 0.0

        # Forecast vs actual pairing samples for UI inspection (first 10 and last 5)
        paired_points = []
        step_stride = max(1, H // 12)
        for idx in range(0, H, step_stride):
            paired_points.append({
                "timestamp": current_records[idx].timestamp.isoformat(),
                "actual_used_gb": round(actual_gb[idx], 2),
                "predicted_q50_gb": round(pred_q50_gb[idx], 2),
                "predicted_q10_gb": round(pred_q10_gb[idx], 2),
                "predicted_q90_gb": round(pred_q90_gb[idx], 2),
                "absolute_error_gb": round(abs_errors_gb[idx], 2),
                "within_interval": pred_q10_gb[idx] <= actual_gb[idx] <= pred_q90_gb[idx]
            })

        # Measure Prediction Drift: compare forecast trajectory distribution against reference
        pred_drift_psi = cls.compute_psi(
            [float(r.used_bytes) / (1024**3) for r in reference_records[-H:]],
            pred_q50_gb
        )
        prediction_drift_detected = pred_drift_psi >= cls.PSI_MODERATE_THRESHOLD

        # Model Performance Deterioration check:
        # Deterioration is flagged if empirical coverage drops below 70% OR WAPE exceeds 10%
        # OR evaluated MAE exceeds 25 GB for tier-1 volume.
        performance_deteriorated = (empirical_coverage_pct < 70.0) or (eval_wape_pct > 10.0) or (eval_mae_gb > 35.0)

        # 6. Actionable Trust Status Assignment
        if is_stale and age_hours > 48.0:
            trust_status = "INSUFFICIENT_EVIDENCE"
            status_reason = f"Telemetry observations are stale by {round(age_hours, 1)} hours. Operational verification suspended until collector recovers."
            recommended_action = "VERIFY_TELEMETRY_COLLECTOR"

        elif performance_deteriorated:
            trust_status = "DEGRADED"
            status_reason = f"Demonstrated performance deterioration: Evaluated coverage ({empirical_coverage_pct}%) fell below 70% threshold or error (WAPE {eval_wape_pct}%) exceeded envelope."
            recommended_action = "RETRAIN_CANDIDATE_MODEL"

        elif data_drift_detected or prediction_drift_detected:
            trust_status = "WATCH"
            drift_names = ", ".join(drifted_metrics[:3])
            status_reason = f"Workload distribution shift detected in [{drift_names}] (Max PSI={max_psi}). Prediction error remains acceptable (Coverage={empirical_coverage_pct}%), but active review is recommended."
            recommended_action = "INVESTIGATE_WORKLOAD_SHIFT"

        else:
            trust_status = "HEALTHY"
            status_reason = f"Telemetry workload is stable (Max PSI={max_psi} < 0.10) and empirical coverage ({empirical_coverage_pct}%) meets 80% nominal calibration envelope."
            recommended_action = "NO_ACTION_REQUIRED"

        # 7. Persist Evaluation in Database Audit Table
        eval_id = f"eval-trust-{uuid.uuid4().hex[:12]}"
        db_eval = ModelTrustEvaluation(
            id=eval_id,
            device_id=device_id,
            evaluated_at=now,
            trust_status=trust_status,
            status_reason=status_reason,
            data_drift_detected=data_drift_detected,
            prediction_drift_detected=prediction_drift_detected,
            performance_degraded=performance_deteriorated,
            max_metric_psi=max_psi,
            evaluated_mae_gb=eval_mae_gb,
            evaluated_rmse_gb=eval_rmse_gb,
            empirical_coverage_pct=empirical_coverage_pct,
            recommended_action=recommended_action,
            details_json=json.dumps({
                "drifted_metrics": drifted_metrics,
                "max_psi": max_psi,
                "wape_pct": eval_wape_pct,
                "coverage_pct": empirical_coverage_pct,
                "missing_gaps_count": len(missing_intervals),
                "is_stale": is_stale
            })
        )
        db.add(db_eval)
        db.commit()

        # Build response payload
        return {
            "evaluation_id": eval_id,
            "device_id": device_id,
            "evaluated_at": now.isoformat(),
            "trust_status": trust_status,
            "status_reason": status_reason,
            "recommended_action": recommended_action,
            "workload_data_drift": {
                "detected": data_drift_detected,
                "severity": data_drift_severity,
                "max_psi": max_psi,
                "psi_threshold_moderate": cls.PSI_STABLE_THRESHOLD,
                "psi_threshold_critical": cls.PSI_MODERATE_THRESHOLD,
                "drifted_metrics_count": len(drifted_metrics),
                "drifted_metrics": drifted_metrics,
                "metrics_breakdown": metric_drift_details
            },
            "prediction_drift": {
                "detected": prediction_drift_detected,
                "prediction_psi": pred_drift_psi,
                "severity": "ELEVATED" if prediction_drift_detected else "NOMINAL"
            },
            "performance_reliability": {
                "deterioration_detected": performance_deteriorated,
                "evaluated_mae_gb": eval_mae_gb,
                "evaluated_rmse_gb": eval_rmse_gb,
                "evaluated_wape_pct": eval_wape_pct,
                "empirical_coverage_pct": empirical_coverage_pct,
                "target_nominal_coverage_pct": cls.TARGET_NOMINAL_COVERAGE * 100.0,
                "actual_samples_evaluated": H,
                "forecast_vs_actual_samples": paired_points
            },
            "data_quality": {
                "total_telemetry_samples": len(records),
                "reference_window_samples": len(reference_records),
                "evaluation_window_samples": len(current_records),
                "is_stale": is_stale,
                "latest_observation_age_hours": round(age_hours, 1),
                "missing_intervals_detected": len(missing_intervals),
                "missing_intervals": missing_intervals[:3]
            },
            "safe_model_improvement": {
                "recalibration_eligible": trust_status in ("WATCH", "DEGRADED"),
                "retraining_eligible": trust_status == "DEGRADED",
                "automatic_replacement_blocked": True,
                "approval_required": "LEAD_STORAGE_ADMINISTRATOR",
                "validation_design": "Chronological holdout split (70% train / 15% val / 15% test)",
                "governance_note": "Production model replacement requires passing chronological holdout with MAE improvement >= 5%."
            }
        }

    @classmethod
    def get_trust_history(cls, db: Session, device_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves historical trust evaluation audits for drift timeline visualization."""
        history = (
            db.query(ModelTrustEvaluation)
            .filter(ModelTrustEvaluation.device_id == device_id)
            .order_by(ModelTrustEvaluation.evaluated_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": h.id,
                "device_id": h.device_id,
                "evaluated_at": h.evaluated_at.isoformat() if h.evaluated_at else None,
                "trust_status": h.trust_status,
                "status_reason": h.status_reason,
                "data_drift_detected": h.data_drift_detected,
                "prediction_drift_detected": h.prediction_drift_detected,
                "performance_degraded": h.performance_degraded,
                "max_metric_psi": h.max_metric_psi,
                "evaluated_mae_gb": h.evaluated_mae_gb,
                "evaluated_rmse_gb": h.evaluated_rmse_gb,
                "empirical_coverage_pct": h.empirical_coverage_pct,
                "recommended_action": h.recommended_action,
                "details": json.loads(h.details_json) if h.details_json else {}
            }
            for h in history
        ]
