import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np
from scipy import stats
from sqlalchemy.orm import Session

from app.models.entities import Device, Telemetry, WorkloadRegimeEvent


class WorkloadRegimeEngine:
    """
    Statistical Workload Regime, Changepoint Burst, Periodicity, and Drift Engine.
    Operates strictly on real persisted telemetry; returns INSUFFICIENT_HISTORY when < 24 samples.
    """

    @staticmethod
    def _lag_autocorr(series: np.ndarray, lag: int) -> float:
        if len(series) <= lag + 4:
            return 0.0
        a = series[:-lag]
        b = series[lag:]
        if np.std(a) < 1e-9 or np.std(b) < 1e-9:
            return 0.0
        corr = float(np.corrcoef(a, b)[0, 1])
        return 0.0 if np.isnan(corr) else corr

    @staticmethod
    def _compute_psi(expected: np.ndarray, actual: np.ndarray, bins: int = 8) -> float:
        if len(expected) < 5 or len(actual) < 5:
            return 0.0
        lo = float(min(np.min(expected), np.min(actual)))
        hi = float(max(np.max(expected), np.max(actual)))
        if abs(hi - lo) < 1e-9:
            return 0.0
        edges = np.linspace(lo, hi, bins + 1)
        exp_cnt, _ = np.histogram(expected, bins=edges)
        act_cnt, _ = np.histogram(actual, bins=edges)
        exp_pct = np.clip(exp_cnt / max(1, len(expected)), 1e-4, 1.0)
        act_pct = np.clip(act_cnt / max(1, len(actual)), 1e-4, 1.0)
        psi = float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))
        return round(max(0.0, psi), 4)

    @classmethod
    def analyze(cls, db: Session, storage_id: str, persist: bool = True) -> Dict[str, Any]:
        device = db.query(Device).filter(Device.id == storage_id).first()
        if not device:
            raise ValueError(f"Storage volume '{storage_id}' not found")

        rows = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == storage_id)
            .order_by(Telemetry.timestamp.asc())
            .all()
        )
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        if len(rows) < 24:
            explanation = (
                f"Only {len(rows)} telemetry records found (minimum 24 required for statistical "
                "trend, periodicity, changepoint, and drift inference)."
            )
            evt_id = f"wreg-{uuid.uuid4().hex[:10]}"
            if persist:
                db.add(WorkloadRegimeEvent(
                    id=evt_id,
                    storage_id=storage_id,
                    regime_label="INSUFFICIENT_HISTORY",
                    event_type="REGIME_CLASSIFICATION",
                    severity="WARNING",
                    confidence=1.0,
                    supporting_metrics_json=json.dumps({"sample_count": len(rows)}),
                    explanation=explanation,
                ))
                db.commit()
            return {
                "storage_id": storage_id,
                "regime_label": "INSUFFICIENT_HISTORY",
                "confidence": 1.0,
                "sample_count": len(rows),
                "explanation": explanation,
                "events": [{"id": evt_id, "event_type": "REGIME_CLASSIFICATION", "severity": "WARNING", "explanation": explanation}],
                "metrics": {"sample_count": len(rows)},
                "analyzed_at": now_utc.isoformat(),
            }

        ts_hours = np.array(
            [(r.timestamp.replace(tzinfo=None) - rows[0].timestamp.replace(tzinfo=None)).total_seconds() / 3600.0 for r in rows],
            dtype=float,
        )
        util = np.array([float(r.utilization_pct) for r in rows], dtype=float)
        used_gb = np.array([float(r.used_bytes) / (1024.0 ** 3) for r in rows], dtype=float)

        # OLS overall slope (% utilization per day) & first/second half slopes
        span_days = max(1e-3, (ts_hours[-1] - ts_hours[0]) / 24.0)
        x_days = ts_hours / 24.0
        overall_slope_day = float(np.polyfit(x_days, util, 1)[0]) if np.std(x_days) > 1e-6 else 0.0

        mid = len(rows) // 2
        early_slope_day = float(np.polyfit(x_days[:mid], util[:mid], 1)[0]) if np.std(x_days[:mid]) > 1e-6 else overall_slope_day
        recent_slope_day = float(np.polyfit(x_days[mid:], util[mid:], 1)[0]) if np.std(x_days[mid:]) > 1e-6 else overall_slope_day

        # First-difference deltas for burst & periodicity
        diffs = np.diff(util)
        diff_mean = float(np.mean(diffs))
        diff_std = float(np.std(diffs))
        max_abs_z = float(np.max(np.abs((diffs - diff_mean) / max(diff_std, 1e-6)))) if len(diffs) > 3 else 0.0
        recent_diffs = diffs[-min(12, len(diffs)):]
        recent_max_jump = float(np.max(np.abs(recent_diffs))) if len(recent_diffs) else 0.0
        recent_max_z = float(np.max(np.abs((recent_diffs - diff_mean) / max(diff_std, 1e-6)))) if len(recent_diffs) else 0.0

        # Lag-24h / lag-24 index periodicity on detrended diffs
        ac_24 = cls._lag_autocorr(diffs, 24)
        ac_12 = cls._lag_autocorr(diffs, 12)
        periodicity_corr = round(max(ac_24, ac_12), 4)

        # Drift test (KS 2-sample + PSI on utilization deltas between baseline half & recent half)
        early_diffs = diffs[: max(1, len(diffs) // 2)]
        late_diffs = diffs[max(1, len(diffs) // 2):]
        ks_stat, ks_p = stats.ks_2samp(early_diffs, late_diffs) if len(early_diffs) >= 5 and len(late_diffs) >= 5 else (0.0, 1.0)
        psi_val = cls._compute_psi(early_diffs, late_diffs)

        # Interruption detection
        dt_hours = np.diff(ts_hours)
        med_dt = float(np.median(dt_hours)) if len(dt_hours) else 1.0
        interruptions = int(np.sum(dt_hours > max(4.0, med_dt * 3.0)))

        # Residual amplitude after linear detrending prevents tiny oscillations on strong ramps from triggering PERIODIC_SEASONAL
        detrended = util - (overall_slope_day * x_days + np.mean(util - overall_slope_day * x_days))
        seasonal_std_pct = float(np.std(detrended))
        net_window_shift_pct = float(np.mean(util[-min(24, len(util)):]) - np.mean(util[:min(24, len(util))]))

        # Deterministic regime classification priority
        events_to_record: List[Dict[str, Any]] = []
        if recent_max_z >= 3.2 or recent_max_jump >= 6.0:
            regime_label = "SUDDEN_BURST"
            confidence = round(min(0.98, 0.72 + recent_max_z * 0.05), 3)
            explanation = (
                f"Detected abrupt storage burst in recent telemetry (max Z-score={recent_max_z:.2f}, "
                f"max step jump={recent_max_jump:.2f}% over median step)."
            )
            events_to_record.append({
                "event_type": "CHANGEPOINT_BURST",
                "severity": "CRITICAL" if recent_max_jump >= 10.0 else "WARNING",
                "explanation": explanation,
            })
        elif ks_p < 0.01 and psi_val >= 0.35:
            regime_label = "UNUSUAL_CONSUMPTION_CHANGE"
            confidence = round(min(0.95, 0.70 + min(0.25, psi_val * 0.25)), 3)
            explanation = (
                f"Statistical distribution shift detected between baseline and recent consumption rates "
                f"(KS={ks_stat:.3f}, p={ks_p:.4f}, PSI={psi_val:.3f})."
            )
            events_to_record.append({
                "event_type": "DISTRIBUTION_DRIFT",
                "severity": "WARNING",
                "explanation": explanation,
            })
        elif periodicity_corr >= 0.60 and seasonal_std_pct >= 0.30 and abs(net_window_shift_pct) < 1.5:
            regime_label = "PERIODIC_SEASONAL"
            confidence = round(min(0.95, 0.55 + periodicity_corr * 0.4), 3)
            explanation = (
                f"Recurring periodic/diurnal workload pattern detected (autocorrelation={periodicity_corr:.3f}, "
                f"detrended_std={seasonal_std_pct:.2f}%, baseline drift slope={overall_slope_day:.3f}%/day)."
            )
        elif overall_slope_day <= -0.15 or (recent_slope_day <= -0.25 and overall_slope_day < 0.0 and periodicity_corr < 0.42):
            regime_label = "DECLINING_CONSUMPTION"
            confidence = round(min(0.95, 0.70 + min(0.25, abs(recent_slope_day) * 0.15)), 3)
            explanation = (
                f"Storage utilization exhibits net reclamation / declining consumption trend "
                f"(overall={overall_slope_day:.3f}%/day, recent={recent_slope_day:.3f}%/day)."
            )
        elif recent_slope_day >= 0.20 and (recent_slope_day > max(0.05, early_slope_day) * 1.55):
            regime_label = "ACCELERATING_GROWTH"
            confidence = round(min(0.94, 0.70 + min(0.24, (recent_slope_day - early_slope_day) * 0.2)), 3)
            explanation = (
                f"Storage growth rate has accelerated from {early_slope_day:.3f}%/day to {recent_slope_day:.3f}%/day "
                f"over {span_days:.1f} days."
            )
        elif periodicity_corr >= 0.42:
            regime_label = "PERIODIC_SEASONAL"
            confidence = round(min(0.95, 0.55 + periodicity_corr * 0.4), 3)
            explanation = (
                f"Recurring periodic/diurnal workload pattern detected (autocorrelation={periodicity_corr:.3f}, "
                f"baseline drift slope={overall_slope_day:.3f}%/day)."
            )
        else:
            regime_label = "STABLE_GROWTH"
            confidence = 0.85
            explanation = (
                f"Steady workload trajectory over {span_days:.1f} days "
                f"(slope={overall_slope_day:.3f}%/day, no critical changepoints)."
            )

        if interruptions > 0:
            events_to_record.append({
                "event_type": "INTERRUPTION",
                "severity": "WARNING",
                "explanation": f"Detected {interruptions} telemetry collection interruption gap(s) exceeding 3x median sampling interval ({med_dt:.1f}h).",
            })

        metrics = {
            "sample_count": len(rows),
            "span_days": round(span_days, 2),
            "overall_slope_pct_per_day": round(overall_slope_day, 4),
            "early_slope_pct_per_day": round(early_slope_day, 4),
            "recent_slope_pct_per_day": round(recent_slope_day, 4),
            "current_used_gb": round(float(used_gb[-1]), 3),
            "periodicity_autocorr": periodicity_corr,
            "max_step_zscore": round(max_abs_z, 3),
            "recent_max_zscore": round(recent_max_z, 3),
            "ks_statistic": round(float(ks_stat), 4),
            "ks_pvalue": round(float(ks_p), 5),
            "psi_drift": psi_val,
            "interruptions_detected": interruptions,
        }

        persisted_events = []
        primary_evt_id = f"wreg-{uuid.uuid4().hex[:10]}"
        if persist:
            db.add(WorkloadRegimeEvent(
                id=primary_evt_id,
                storage_id=storage_id,
                regime_label=regime_label,
                event_type="REGIME_CLASSIFICATION",
                severity="INFO" if regime_label in {"STABLE_GROWTH", "PERIODIC_SEASONAL"} else "WARNING",
                confidence=confidence,
                supporting_metrics_json=json.dumps(metrics),
                explanation=explanation,
            ))
            for extra in events_to_record:
                eid = f"wreg-{uuid.uuid4().hex[:10]}"
                db.add(WorkloadRegimeEvent(
                    id=eid,
                    storage_id=storage_id,
                    regime_label=regime_label,
                    event_type=extra["event_type"],
                    severity=extra["severity"],
                    confidence=confidence,
                    supporting_metrics_json=json.dumps(metrics),
                    explanation=extra["explanation"],
                ))
                persisted_events.append({"id": eid, **extra})
            db.commit()

        return {
            "id": primary_evt_id,
            "storage_id": storage_id,
            "regime_label": regime_label,
            "confidence": confidence,
            "explanation": explanation,
            "metrics": metrics,
            "events": [{"id": primary_evt_id, "event_type": "REGIME_CLASSIFICATION", "severity": "INFO", "explanation": explanation}] + persisted_events,
            "analyzed_at": now_utc.isoformat(),
        }
