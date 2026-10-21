"""
AEGISSTOR PHOENIX — Policy-as-Code Safety Gateway
Enforces non-negotiable hard storage safety constraints.
Safety Invariant: High recommendation scores NEVER override hard safety rules.
"""
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

from app.models.entities import Device, Telemetry, PhoenixPolicy
from app.utils.datetime_utils import utc_now


class PolicyGateway:
    """
    Evaluates action proposals against non-bypassable enterprise storage safety policies.
    """

    @classmethod
    def get_active_policy(cls, db: Session) -> PhoenixPolicy:
        policy = db.query(PhoenixPolicy).filter(PhoenixPolicy.is_active == True).first()
        if not policy:
            # Seed default active policy
            policy = PhoenixPolicy(
                id="pol-default-enterprise",
                name="Enterprise Zero-Outage Storage Safety Invariants",
                version="1.0.0",
                min_free_reserve_pct=10.0,
                max_latency_ms=20.0,
                max_bandwidth_mb_s=6400.0,
                max_telemetry_age_seconds=3600,
                allowed_action_types_json=json.dumps([
                    "TIER_THROTTLE_ADJUSTMENT",
                    "WORKLOAD_RATE_LIMIT",
                    "COMPACT_SHADOW_SNAPSHOTS",
                    "READ_CACHE_PREFETCH_REBALANCE",
                    "POOL_WEIGHT_REBALANCE",
                    "SIMULATED_DRAIN_REPLICA",
                    "NOOP_DIAGNOSTIC_SAMPLE"
                ]),
                require_human_approval=True,
                allow_shadow_mode_only=True,
                is_active=True
            )
            db.add(policy)
            db.commit()
            db.refresh(policy)
        return policy

    @classmethod
    def evaluate_proposal(
        cls,
        db: Session,
        action_type: str,
        target_resource_id: str,
        parameters: Dict[str, Any],
        simulated_outcome: Dict[str, Any],
        recommendation_score: float = 0.85
    ) -> Tuple[str, List[str]]:
        """
        Evaluates the action proposal.
        Returns: (verdict, list_of_violations)
        Verdict is one of:
          - ALLOWED_FOR_SIMULATION
          - REQUIRES_HUMAN_REVIEW
          - REJECTED_BY_POLICY
          - INSUFFICIENT_EVIDENCE
        """
        policy = cls.get_active_policy(db)
        violations: List[str] = []

        # 1. Action Type Whitelist Check
        allowed_actions = json.loads(policy.allowed_action_types_json)
        if action_type not in allowed_actions:
            violations.append(f"Action '{action_type}' is not in the allowlist of safe storage actions.")

        # 2. Target Device & Evidence Freshness Check
        device = db.query(Device).filter(Device.id == target_resource_id).first()
        if not device:
            violations.append(f"Target resource '{target_resource_id}' does not exist in inventory.")
            return "REJECTED_BY_POLICY", violations

        latest_telemetry = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == target_resource_id)
            .order_by(Telemetry.timestamp.desc())
            .first()
        )

        if not latest_telemetry:
            return "INSUFFICIENT_EVIDENCE", ["No telemetry history available for target resource."]

        # 3. Hard Safety Constraint: Minimum Free Reserve Capacity
        # Check projected or simulated post-action utilization
        simulated_util = simulated_outcome.get("projected_utilization_pct", latest_telemetry.utilization_pct if latest_telemetry else 80.0)
        simulated_free_pct = 100.0 - simulated_util
        required_reserve = device.min_free_reserve_pct or policy.min_free_reserve_pct

        if simulated_free_pct < required_reserve:
            violations.append(
                f"Action violates minimum free capacity reserve invariant: projected free capacity {simulated_free_pct:.2f}% is below required reserve {required_reserve:.1f}%."
            )

        # 4. Hard Safety Constraint: Maximum Latency Ceiling
        simulated_latency = simulated_outcome.get("projected_latency_ms", latest_telemetry.latency_p95_ms if latest_telemetry else 15.0)
        allowed_latency = device.max_acceptable_latency_ms or policy.max_latency_ms

        if simulated_latency > allowed_latency:
            violations.append(
                f"Action violates latency ceiling invariant: projected latency {simulated_latency:.2f}ms exceeds maximum acceptable {allowed_latency:.1f}ms."
            )

        # 5. Hard Safety Constraint: Bus / Interconnect Bandwidth Ceiling
        simulated_bandwidth = simulated_outcome.get("projected_bandwidth_mb_s", latest_telemetry.throughput_mb_s if latest_telemetry else 1000.0)
        if simulated_bandwidth > policy.max_bandwidth_mb_s:
            violations.append(
                f"Action violates bus bandwidth ceiling: projected throughput {simulated_bandwidth:.1f} MB/s exceeds fabric limit {policy.max_bandwidth_mb_s} MB/s."
            )

        # Strict Rule: Regardless of how high recommendation_score is, ANY safety violation causes REJECTED_BY_POLICY.
        if violations:
            return "REJECTED_BY_POLICY", violations

        # 6. Telemetry Freshness Check (Only for live non-synthetic telemetry)
        if latest_telemetry and not latest_telemetry.is_synthetic:
            now = utc_now()
            telemetry_age = (now - latest_telemetry.timestamp.replace(tzinfo=timezone.utc if latest_telemetry.timestamp.tzinfo is None else None)).total_seconds()
            if telemetry_age > policy.max_telemetry_age_seconds:
                return "INSUFFICIENT_EVIDENCE", [
                    f"Telemetry age ({telemetry_age:.0f}s) exceeds maximum allowed age ({policy.max_telemetry_age_seconds}s)."
                ]

        if not latest_telemetry:
            return "INSUFFICIENT_EVIDENCE", ["No telemetry history available for target resource."]

        if policy.require_human_approval:
            return "REQUIRES_HUMAN_REVIEW", []

        return "ALLOWED_FOR_SIMULATION", []

