"""
AEGISSTOR PHOENIX — Incident Correlation & Transparent Triage Engine
Correlates multi-tier storage telemetry, forecast horizons, and topology bottlenecks into auditable incident packages.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import uuid
from sqlalchemy.orm import Session

from app.models.entities import Device, Telemetry, Forecast, RiskAssessment, PhoenixIncident
from app.utils.datetime_utils import utc_now


class IncidentCorrelationEngine:
    """
    Ingests storage telemetry, forecast breach projections, and topology metrics
    to formulate evidence-backed incident candidates with transparent triage.
    """

    @classmethod
    def evaluate_device_for_incidents(cls, db: Session, device_id: str) -> Optional[Dict[str, Any]]:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return None

        # Fetch latest telemetry reading
        latest_telemetry = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == device_id)
            .order_by(Telemetry.timestamp.desc())
            .first()
        )
        if not latest_telemetry:
            return None

        # Fetch latest forecast and risk
        latest_forecast = (
            db.query(Forecast)
            .filter(Forecast.device_id == device_id)
            .order_by(Forecast.generated_at.desc())
            .first()
        )
        latest_risk = (
            db.query(RiskAssessment)
            .filter(RiskAssessment.device_id == device_id)
            .order_by(RiskAssessment.computed_at.desc())
            .first()
        )

        curr_util = latest_telemetry.utilization_pct
        curr_lat = latest_telemetry.latency_p95_ms
        warn_util = device.warning_threshold_pct or 80.0
        crit_util = device.critical_threshold_pct or 90.0
        max_lat = device.max_acceptable_latency_ms or 20.0

        runway_hours = latest_risk.runway_hours_estimate if latest_risk else 168.0
        runway_lower = latest_risk.runway_hours_lower if latest_risk else runway_hours * 0.8
        cap_breach_24h = latest_risk.capacity_breach_prob_24h if latest_risk else 0.0

        symptoms: List[str] = []
        hypotheses: List[Dict[str, Any]] = []
        incident_category = None
        severity = "SEV4_LOW"
        evidence_type = "PREDICTED"

        # Check observed breaches
        if curr_util >= crit_util:
            symptoms.append(f"Storage utilization critical at {curr_util:.1f}% (limit: {crit_util}%)")
            hypotheses.append({
                "hypothesis": "Physical capacity near saturation, imminent I/O rejection risk",
                "status": "CONFIRMED_OBSERVATION",
                "metric": "utilization_pct",
                "value": curr_util,
                "threshold": crit_util
            })
            incident_category = "CAPACITY_EXHAUSTION"
            severity = "SEV1_CRITICAL"
            evidence_type = "OBSERVED"
        elif curr_util >= warn_util:
            symptoms.append(f"Storage utilization elevated at {curr_util:.1f}% (limit: {warn_util}%)")
            hypotheses.append({
                "hypothesis": "Operating above warning capacity threshold; buffer reserve eroding",
                "status": "CONFIRMED_OBSERVATION",
                "metric": "utilization_pct",
                "value": curr_util,
                "threshold": warn_util
            })
            incident_category = "CAPACITY_EXHAUSTION"
            severity = "SEV2_HIGH"
            evidence_type = "OBSERVED"

        # Check observed latency
        if curr_lat > max_lat:
            symptoms.append(f"P95 latency elevated at {curr_lat:.2f}ms (threshold: {max_lat}ms)")
            hypotheses.append({
                "hypothesis": "Storage queue depth or device media saturation producing response time degradation",
                "status": "CONFIRMED_OBSERVATION",
                "metric": "latency_p95_ms",
                "value": curr_lat,
                "threshold": max_lat
            })
            if not incident_category or incident_category == "CAPACITY_EXHAUSTION":
                incident_category = "LATENCY_SATURATION"
            if severity in ("SEV3_MEDIUM", "SEV4_LOW"):
                severity = "SEV2_HIGH"
            evidence_type = "OBSERVED"

        # Check predicted breach horizons (even if observed is not yet broken)
        if runway_hours < 24.0 or cap_breach_24h > 0.5:
            symptoms.append(f"Conformal forecast projects capacity exhaustion in {runway_hours:.1f}h (P={cap_breach_24h:.2f})")
            hypotheses.append({
                "hypothesis": "Predictive quantile horizon indicates runway exhaustion within lead-time window",
                "status": "SUPPORTED_HYPOTHESIS",
                "metric": "runway_hours",
                "value": runway_hours,
                "threshold": 24.0
            })
            if not incident_category:
                incident_category = "CAPACITY_EXHAUSTION"
                severity = "SEV1_CRITICAL" if runway_hours < 12.0 else "SEV2_HIGH"
                evidence_type = "PREDICTED"
        elif runway_hours < 72.0:
            symptoms.append(f"Forecast runway constrained at {runway_hours:.1f}h (confidence interval: {runway_lower:.1f}h)")
            hypotheses.append({
                "hypothesis": "Multi-day trend shows reserve depletion without intervention",
                "status": "SUPPORTED_HYPOTHESIS",
                "metric": "runway_hours",
                "value": runway_hours,
                "threshold": 72.0
            })
            if not incident_category:
                incident_category = "CAPACITY_EXHAUSTION"
                severity = "SEV3_MEDIUM"
                evidence_type = "PREDICTED"

        if not symptoms:
            return None  # No incident warranted

        title = f"{severity} {incident_category.replace('_', ' ').title()} on {device.name}"
        
        evidence_payload = {
            "device_id": device.id,
            "device_name": device.name,
            "tier": device.tier,
            "pool_id": device.pool_id,
            "telemetry_timestamp": latest_telemetry.timestamp.isoformat(),
            "telemetry_sample": {
                "utilization_pct": curr_util,
                "latency_p95_ms": curr_lat,
                "throughput_mb_s": latest_telemetry.throughput_mb_s,
                "queue_depth": latest_telemetry.queue_depth,
                "is_synthetic": latest_telemetry.is_synthetic
            },
            "forecast_summary": {
                "forecast_id": latest_forecast.id if latest_forecast else None,
                "runway_hours": runway_hours,
                "runway_lower": runway_lower,
                "breach_prob_24h": cap_breach_24h
            }
        }

        return {
            "title": title,
            "category": incident_category,
            "severity": severity,
            "target_device_id": device.id,
            "affected_devices": [device.id],
            "pool_id": device.pool_id,
            "evidence_type": evidence_type,
            "time_to_breach_hours": runway_hours,
            "confidence_score": 0.88 if latest_forecast else 0.70,
            "model_version": latest_forecast.model_name if latest_forecast else "Conformal-Quantile-v1.8",
            "symptoms": symptoms,
            "hypotheses": hypotheses,
            "evidence_payload": evidence_payload,
            "forecast_reference_id": latest_forecast.id if latest_forecast else None,
            "risk_reference_id": latest_risk.id if latest_risk else None
        }

    @classmethod
    def scan_and_create_incidents(cls, db: Session) -> List[PhoenixIncident]:
        """
        Scans all registered devices and spawns or updates Phoenix incidents.
        """
        devices = db.query(Device).all()
        created_or_updated: List[PhoenixIncident] = []

        for dev in devices:
            triage = cls.evaluate_device_for_incidents(db, dev.id)
            if not triage:
                continue

            # Look for existing active incident on this device
            existing = (
                db.query(PhoenixIncident)
                .filter(
                    PhoenixIncident.target_device_id == dev.id,
                    PhoenixIncident.status.notin_(["RESOLVED", "CANCELLED"])
                )
                .first()
            )

            if existing:
                # Update symptoms and hypotheses
                existing.severity = triage["severity"]
                existing.symptoms_json = json.dumps(triage["symptoms"])
                existing.hypotheses_json = json.dumps(triage["hypotheses"])
                existing.evidence_payload_json = json.dumps(triage["evidence_payload"])
                existing.time_to_breach_hours = triage["time_to_breach_hours"]
                existing.updated_at = utc_now()
                db.flush()
                created_or_updated.append(existing)
            else:
                inc_id = f"inc-phx-{uuid.uuid4().hex[:8]}"
                new_incident = PhoenixIncident(
                    id=inc_id,
                    title=triage["title"],
                    category=triage["category"],
                    severity=triage["severity"],
                    status="DETECTED",
                    target_device_id=triage["target_device_id"],
                    affected_devices_json=json.dumps(triage["affected_devices"]),
                    pool_id=triage["pool_id"],
                    evidence_type=triage["evidence_type"],
                    detection_timestamp=utc_now(),
                    time_to_breach_hours=triage["time_to_breach_hours"],
                    confidence_score=triage["confidence_score"],
                    model_version=triage["model_version"],
                    symptoms_json=json.dumps(triage["symptoms"]),
                    hypotheses_json=json.dumps(triage["hypotheses"]),
                    evidence_payload_json=json.dumps(triage["evidence_payload"]),
                    forecast_reference_id=triage["forecast_reference_id"],
                    risk_reference_id=triage["risk_reference_id"]
                )
                db.add(new_incident)
                db.flush()
                created_or_updated.append(new_incident)

        db.commit()
        return created_or_updated
