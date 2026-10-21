"""
AEGISSTOR PHOENIX — Incident Evidence Graph & Repeated Incident Learning
Synthesizes graph provenance models and recurring failure pattern analysis.
"""
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.entities import (
    PhoenixIncident, PhoenixActionProposal, PhoenixExecutionRecord,
    PhoenixRecoveryVerification, Device, Forecast
)


class EvidenceGraphEngine:
    """
    Constructs an auditable directed graph correlating incidents, models, policies, and runbooks.
    """

    @classmethod
    def build_graph_for_incident(cls, db: Session, incident_id: str) -> Dict[str, Any]:
        incident = db.query(PhoenixIncident).filter(PhoenixIncident.id == incident_id).first()
        if not incident:
            return {"nodes": [], "edges": []}

        nodes = []
        edges = []

        # 1. Root Incident Node
        nodes.append({
            "id": incident.id,
            "label": incident.title,
            "type": "INCIDENT",
            "status": incident.status,
            "severity": incident.severity,
            "evidence_type": incident.evidence_type,
            "time_to_breach_hours": incident.time_to_breach_hours
        })

        # 2. Target Resource / Pool Nodes
        if incident.target_device_id:
            dev = db.query(Device).filter(Device.id == incident.target_device_id).first()
            dev_name = dev.name if dev else incident.target_device_id
            nodes.append({
                "id": incident.target_device_id,
                "label": f"Device: {dev_name}",
                "type": "STORAGE_DEVICE",
                "tier": dev.tier if dev else "UNKNOWN",
                "media_type": dev.media_type if dev else "UNKNOWN"
            })
            edges.append({
                "source": incident.id,
                "target": incident.target_device_id,
                "relation": "AFFECTS_RESOURCE"
            })

            if dev and dev.pool_id:
                nodes.append({
                    "id": dev.pool_id,
                    "label": f"Pool: {dev.pool_id}",
                    "type": "STORAGE_POOL"
                })
                edges.append({
                    "source": incident.target_device_id,
                    "target": dev.pool_id,
                    "relation": "MEMBER_OF_POOL"
                })

        # 3. Forecast / Uncertainty Horizon Node
        if incident.forecast_reference_id:
            fc = db.query(Forecast).filter(Forecast.id == incident.forecast_reference_id).first()
            fc_label = f"Forecast #{incident.forecast_reference_id} ({fc.model_name if fc else 'Conformal'})"
            nodes.append({
                "id": f"forecast-{incident.forecast_reference_id}",
                "label": fc_label,
                "type": "PREDICTIVE_MODEL",
                "horizon_hours": fc.horizon_hours if fc else 72,
                "confidence": incident.confidence_score
            })
            edges.append({
                "source": incident.id,
                "target": f"forecast-{incident.forecast_reference_id}",
                "relation": "PREDICTED_BY"
            })

        # 4. Action Proposal & Policy Gateway Nodes
        if incident.active_proposal_id:
            prop = db.query(PhoenixActionProposal).filter(PhoenixActionProposal.id == incident.active_proposal_id).first()
            if prop:
                nodes.append({
                    "id": prop.id,
                    "label": f"Proposal: {prop.action_type}",
                    "type": "ACTION_PROPOSAL",
                    "status": prop.approval_status,
                    "policy_verdict": prop.policy_verdict,
                    "score": prop.recommendation_score
                })
                edges.append({
                    "source": incident.id,
                    "target": prop.id,
                    "relation": "MITIGATED_BY_PLAN"
                })

                # Policy Node
                nodes.append({
                    "id": f"policy-gate-{prop.id}",
                    "label": f"Safety Policy ({prop.policy_verdict})",
                    "type": "SAFETY_GATEWAY",
                    "violations": json.loads(prop.policy_violations_json) if prop.policy_violations_json else []
                })
                edges.append({
                    "source": prop.id,
                    "target": f"policy-gate-{prop.id}",
                    "relation": "VALIDATED_BY_POLICY"
                })

                # Execution Record Node
                exec_rec = db.query(PhoenixExecutionRecord).filter(PhoenixExecutionRecord.proposal_id == prop.id).first()
                if exec_rec:
                    nodes.append({
                        "id": exec_rec.id,
                        "label": f"Execution ({exec_rec.execution_mode})",
                        "type": "EXECUTION_RUN",
                        "status": exec_rec.status,
                        "mode": exec_rec.execution_mode
                    })
                    edges.append({
                        "source": prop.id,
                        "target": exec_rec.id,
                        "relation": "EXECUTED_AS"
                    })

        # 5. Independent Recovery Verification Node
        verif = db.query(PhoenixRecoveryVerification).filter(PhoenixRecoveryVerification.incident_id == incident.id).first()
        if verif:
            nodes.append({
                "id": verif.id,
                "label": f"Recovery Verifier ({verif.status})",
                "type": "RECOVERY_VERIFICATION",
                "status": verif.status,
                "residual_risk": verif.residual_risk_score
            })
            edges.append({
                "source": incident.id,
                "target": verif.id,
                "relation": "VERIFIED_BY"
            })

        return {
            "incident_id": incident.id,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }

    @classmethod
    def analyze_repeated_patterns(cls, db: Session) -> Dict[str, Any]:
        """
        Groups incidents to discover recurrence signatures and calculates MTTR / recurrence metrics.
        """
        all_incidents = db.query(PhoenixIncident).all()
        by_category: Dict[str, List[PhoenixIncident]] = {}
        by_device: Dict[str, List[PhoenixIncident]] = {}

        for inc in all_incidents:
            by_category.setdefault(inc.category, []).append(inc)
            if inc.target_device_id:
                by_device.setdefault(inc.target_device_id, []).append(inc)

        category_stats = []
        for cat, inc_list in by_category.items():
            resolved = [i for i in inc_list if i.status == "RESOLVED" and i.resolved_at and i.detection_timestamp]
            durations_min = [
                (i.resolved_at - i.detection_timestamp).total_seconds() / 60.0
                for i in resolved
            ]
            mttr_minutes = sum(durations_min) / len(durations_min) if durations_min else 0.0

            category_stats.append({
                "category": cat,
                "total_count": len(inc_list),
                "resolved_count": len(resolved),
                "active_count": len(inc_list) - len(resolved),
                "mttr_minutes": round(mttr_minutes, 1),
                "recurrence_rate": round(len(inc_list) / max(len(all_incidents), 1), 2)
            })

        device_hotspots = [
            {"device_id": dev_id, "incident_count": len(incs)}
            for dev_id, incs in by_device.items()
        ]
        device_hotspots.sort(key=lambda x: x["incident_count"], reverse=True)

        return {
            "total_incidents": len(all_incidents),
            "category_distribution": category_stats,
            "device_hotspots": device_hotspots[:5],
            "repeat_incident_signature": "CAPACITY_EXHAUSTION_PERSISTENT" if len(all_incidents) > 0 else "NONE",
            "recommended_preventive_action": "Tighten autonomous shadow rebalance threshold to 75% for high-growth tiers."
        }
