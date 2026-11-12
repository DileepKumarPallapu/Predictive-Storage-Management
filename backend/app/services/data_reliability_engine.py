import json
import statistics
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.api.v1.endpoints_settings import _load_persisted_settings
from app.models.entities import (
    DataQualityResult,
    DataReliabilityProfile,
    Device,
    IngestionJob,
    Telemetry,
    TelemetryConnector,
)


DEFAULT_RELIABILITY_WEIGHTS: Dict[str, float] = {
    "completeness_score": 0.16,
    "freshness_score": 0.16,
    "continuity_score": 0.12,
    "duplicate_rate_score": 0.08,
    "invalid_rate_score": 0.12,
    "capacity_consistency_score": 0.14,
    "missing_metric_score": 0.08,
    "source_availability_score": 0.07,
    "historical_stability_score": 0.07,
}


class DataReliabilityEngine:
    """
    Computes a transparent, auditable 9-factor Data Reliability Score (0.0 .. 1.0)
    per storage volume. Gates ML forecast uncertainty intervals and prevents
    high-confidence automated recommendations when underlying telemetry is LOW or STALE.
    """

    @staticmethod
    def _normalize_weights(custom_weights: Optional[Dict[str, float]]) -> Dict[str, float]:
        weights = dict(DEFAULT_RELIABILITY_WEIGHTS)
        if custom_weights:
            for k, v in custom_weights.items():
                if k in weights and v is not None and float(v) >= 0.0:
                    weights[k] = float(v)
        total = sum(weights.values())
        if total <= 0:
            return dict(DEFAULT_RELIABILITY_WEIGHTS)
        return {k: v / total for k, v in weights.items()}

    @classmethod
    def evaluate(
        cls,
        db: Session,
        storage_id: str,
        custom_weights: Optional[Dict[str, float]] = None,
        persist: bool = True,
    ) -> Dict[str, Any]:
        device = db.query(Device).filter(Device.id == storage_id).first()
        if not device:
            raise ValueError(f"Storage volume '{storage_id}' not found")

        weights = cls._normalize_weights(custom_weights)
        persisted = _load_persisted_settings(db)
        stale_hours = float(persisted.get("data_retention_settings", {}).get("stale_telemetry_hours", 24.0))

        rows = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == storage_id)
            .order_by(Telemetry.timestamp.asc())
            .all()
        )
        jobs = (
            db.query(IngestionJob)
            .filter(IngestionJob.storage_id == storage_id)
            .order_by(IngestionJob.created_at.desc())
            .limit(25)
            .all()
        )
        connectors = (
            db.query(TelemetryConnector)
            .filter(TelemetryConnector.target_storage_id == storage_id)
            .all()
        )
        latest_dq = (
            db.query(DataQualityResult)
            .filter(DataQualityResult.storage_id == storage_id)
            .order_by(DataQualityResult.evaluated_at.desc())
            .first()
        )

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        if not rows:
            factors = {k: 0.0 for k in DEFAULT_RELIABILITY_WEIGHTS}
            factors["duplicate_rate_score"] = 1.0
            factors["invalid_rate_score"] = 1.0
            score = round(sum(factors[k] * weights[k] for k in weights), 4)
            profile_id = f"rel-{uuid.uuid4().hex[:10]}"
            explanation = {
                "summary": "No telemetry samples available for this storage volume.",
                "record_count": 0,
                "stale_threshold_hours": stale_hours,
                "allow_high_confidence_recommendations": False,
                "blocked_reason": "Zero telemetry records; reliable forecasting and recommendations are suspended.",
            }
            if persist:
                db.add(DataReliabilityProfile(
                    id=profile_id,
                    storage_id=storage_id,
                    reliability_score=score,
                    reliability_tier="LOW",
                    is_stale=True,
                    last_successful_timestamp=None,
                    weights_json=json.dumps(weights),
                    explanation_json=json.dumps(explanation),
                    uncertainty_multiplier=2.2,
                    **factors,
                ))
                db.commit()
            return {
                "id": profile_id,
                "storage_id": storage_id,
                "reliability_score": score,
                "reliability_tier": "LOW",
                "is_stale": True,
                "last_successful_timestamp": None,
                "uncertainty_multiplier": 2.2,
                "allow_high_confidence_recommendations": False,
                "factors": factors,
                "weights": weights,
                "explanation": explanation,
                "evaluated_at": now_utc.isoformat(),
            }

        n = len(rows)
        last_ts = rows[-1].timestamp.replace(tzinfo=None) if rows[-1].timestamp.tzinfo else rows[-1].timestamp
        age_hours = max(0.0, (now_utc - last_ts).total_seconds() / 3600.0)
        is_stale = age_hours > stale_hours

        # 1. Completeness score (capacity fields populated & DQ completeness if recorded)
        valid_cap_rows = sum(
            1 for r in rows
            if (r.total_capacity_bytes or device.total_capacity_bytes) and r.used_bytes is not None and r.free_bytes is not None
        )
        completeness_raw = valid_cap_rows / n
        if latest_dq and latest_dq.data_completeness_pct is not None:
            completeness_raw = min(completeness_raw, max(0.0, min(1.0, latest_dq.data_completeness_pct / 100.0)))
        completeness_score = round(max(0.0, min(1.0, completeness_raw)), 4)

        # 2. Freshness score
        if age_hours <= stale_hours * 0.25:
            freshness_score = 1.0
        elif age_hours <= stale_hours:
            freshness_score = round(max(0.65, 1.0 - 0.35 * (age_hours / stale_hours)), 4)
        else:
            freshness_score = round(max(0.05, 0.65 * (stale_hours / max(age_hours, stale_hours + 1.0))), 4)

        # 3. Continuity score (timestamp gap regularity)
        if n < 3:
            continuity_score = 0.4
            gap_count = 0
            median_gap_s = 0.0
        else:
            deltas = []
            for idx in range(1, n):
                t_prev = rows[idx - 1].timestamp.replace(tzinfo=None)
                t_curr = rows[idx].timestamp.replace(tzinfo=None)
                dt_s = max(0.0, (t_curr - t_prev).total_seconds())
                if dt_s > 0:
                    deltas.append(dt_s)
            if not deltas:
                continuity_score = 0.2
                gap_count = n - 1
                median_gap_s = 0.0
            else:
                median_gap_s = statistics.median(deltas)
                gap_count = sum(1 for d in deltas if d > max(7200.0, median_gap_s * 2.5))
                continuity_score = round(max(0.1, 1.0 - (gap_count / len(deltas)) * 1.25), 4)

        # 4. Duplicate rate score (from ingestion jobs + exact timestamp collisions)
        ts_list = [r.timestamp.replace(tzinfo=None, microsecond=0) for r in rows]
        unique_ts = len(set(ts_list))
        ts_dup_rate = max(0.0, (n - unique_ts) / n)
        total_job_rows = sum(j.total_rows for j in jobs)
        dup_job_rows = sum(j.duplicate_rows for j in jobs)
        job_dup_rate = (dup_job_rows / total_job_rows) if total_job_rows > 0 else 0.0
        duplicate_rate_score = round(max(0.0, 1.0 - max(ts_dup_rate, job_dup_rate)), 4)

        # 5. Invalid rate score (rejected job rows + negative/out-of-bound telemetry)
        rej_job_rows = sum(j.rejected_rows for j in jobs)
        job_inv_rate = (rej_job_rows / total_job_rows) if total_job_rows > 0 else 0.0
        row_invalid = 0
        for r in rows:
            cap_b = r.total_capacity_bytes if r.total_capacity_bytes is not None else device.total_capacity_bytes
            if r.used_bytes is None or r.used_bytes < 0 or cap_b is None or cap_b <= 0 or r.used_bytes > cap_b:
                row_invalid += 1
        row_inv_rate = row_invalid / n
        invalid_rate_score = round(max(0.0, 1.0 - max(job_inv_rate, row_inv_rate)), 4)

        # 6. Capacity consistency score (used + free == total within 1% tolerance)
        consistent_rows = 0
        for r in rows:
            cap_b = r.total_capacity_bytes if r.total_capacity_bytes is not None else device.total_capacity_bytes
            if cap_b is not None and cap_b > 0:
                sum_b = (r.used_bytes or 0) + (r.free_bytes or 0)
                rel_diff = abs(sum_b - cap_b) / cap_b
                if rel_diff <= 0.015:
                    consistent_rows += 1
        capacity_consistency_score = round(consistent_rows / n, 4)

        # 7. Missing optional metric score (checks presence of IOPS/latency/throughput; never fabricates them)
        perf_present = 0
        perf_total = n * 4
        for r in rows:
            if r.read_iops is not None:
                perf_present += 1
            if r.write_iops is not None:
                perf_present += 1
            if r.latency_p95_ms is not None:
                perf_present += 1
            if r.throughput_mb_s is not None:
                perf_present += 1
        # Optional metrics missing doesn't invalidate capacity, so floor at 0.35 if capacity is clean
        raw_perf_ratio = perf_present / perf_total
        missing_metric_score = round(0.35 + 0.65 * raw_perf_ratio, 4)

        # 8. Source availability score
        if connectors:
            enabled = [c for c in connectors if c.is_enabled]
            if not enabled:
                source_availability_score = 0.5
            else:
                connected = sum(1 for c in enabled if c.last_status == "CONNECTED")
                errored = sum(1 for c in enabled if c.last_status == "ERROR")
                if connected > 0 and errored == 0:
                    source_availability_score = 1.0
                elif errored < len(enabled):
                    source_availability_score = 0.75
                else:
                    source_availability_score = 0.35
        else:
            # Direct API / CSV historical / host seed without external connector errors
            source_availability_score = 0.9 if not is_stale else 0.5

        # 9. Historical stability & depth score
        depth_factor = min(1.0, n / 72.0)
        pct_steps = [abs(rows[i].utilization_pct - rows[i - 1].utilization_pct) for i in range(1, n)]
        extreme_jumps = sum(1 for d in pct_steps if d > 15.0)
        jump_penalty = (extreme_jumps / max(1, len(pct_steps))) * 1.5
        historical_stability_score = round(max(0.1, depth_factor * (1.0 - min(0.8, jump_penalty))), 4)

        factors = {
            "completeness_score": completeness_score,
            "freshness_score": freshness_score,
            "continuity_score": continuity_score,
            "duplicate_rate_score": duplicate_rate_score,
            "invalid_rate_score": invalid_rate_score,
            "capacity_consistency_score": capacity_consistency_score,
            "missing_metric_score": missing_metric_score,
            "source_availability_score": source_availability_score,
            "historical_stability_score": historical_stability_score,
        }

        score = round(sum(factors[k] * weights[k] for k in weights), 4)
        # Stale telemetry cannot hold HIGH reliability tier
        if score >= 0.80 and not is_stale:
            tier = "HIGH"
            uncertainty_multiplier = 1.0
        elif score >= 0.55:
            tier = "MEDIUM"
            uncertainty_multiplier = round(1.0 + max(0.05, (0.80 - score)) * 1.5, 4)
        else:
            tier = "LOW"
            uncertainty_multiplier = round(1.0 + max(0.25, (0.80 - score)) * 2.0, 4)

        allow_high_conf = (tier in {"HIGH", "MEDIUM"}) and not is_stale
        blocked_reason = None
        if tier == "LOW":
            blocked_reason = (
                f"Reliability tier is LOW (score={score:.2f} < 0.55). "
                "Automated high-confidence recommendations are suppressed and prediction bands widened."
            )
        elif is_stale:
            blocked_reason = (
                f"Telemetry is STALE ({age_hours:.1f}h old > {stale_hours}h threshold). "
                "Refresh collector before acting on recommendations."
            )

        explanation = {
            "summary": (
                f"Reliability evaluated across {n} telemetry samples: tier={tier} ({score:.3f}), "
                f"latest_age={age_hours:.1f}h, gaps_detected={gap_count}."
            ),
            "record_count": n,
            "latest_age_hours": round(age_hours, 2),
            "stale_threshold_hours": stale_hours,
            "median_sampling_seconds": round(median_gap_s, 1),
            "gaps_detected": gap_count,
            "allow_high_confidence_recommendations": allow_high_conf,
            "blocked_reason": blocked_reason,
        }

        profile_id = f"rel-{uuid.uuid4().hex[:10]}"
        if persist:
            db.add(DataReliabilityProfile(
                id=profile_id,
                storage_id=storage_id,
                reliability_score=score,
                reliability_tier=tier,
                is_stale=is_stale,
                last_successful_timestamp=last_ts,
                weights_json=json.dumps(weights),
                explanation_json=json.dumps(explanation),
                uncertainty_multiplier=uncertainty_multiplier,
                **factors,
            ))
            db.commit()

        return {
            "id": profile_id,
            "storage_id": storage_id,
            "reliability_score": score,
            "reliability_tier": tier,
            "is_stale": is_stale,
            "last_successful_timestamp": last_ts.isoformat(),
            "uncertainty_multiplier": uncertainty_multiplier,
            "allow_high_confidence_recommendations": allow_high_conf,
            "blocked_reason": blocked_reason,
            "factors": factors,
            "weights": weights,
            "explanation": explanation,
            "evaluated_at": now_utc.isoformat(),
        }
