import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.models.entities import (
    Device, Telemetry, Forecast, ModelVersion, ModelMetric,
    Alert, DataQualityResult, DataReliabilityProfile, WorkloadRegimeEvent,
    CapacityRiskEvaluation, Recommendation, Scenario, SimulatedOutcome, ReportHistory
)
from app.services.data_quality_service import _parse_iso_timestamp

SUPPORTED_REPORT_TYPES = [
    "storage_inventory",
    "storage_utilisation",
    "capacity_forecast",
    "model_performance",
    "performance_trends",
    "risk_and_alert",
    "data_quality",
    "data_reliability",
    "workload_behaviour",
    "capacity_risk",
    "digital_twin_comparison",
    "recommendation_history",
]


class ReportingService:
    """
    AEGISSTOR Module 11 — Actual Data Reporting & Export Service.
    Generates JSON, CSV, and PDF reports strictly from persisted database records.
    """

    @classmethod
    def generate_report(
        cls,
        db: Session,
        report_type: str,
        fmt: str = "json",
        storage_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        generated_by: str = "system",
    ) -> Dict[str, Any]:
        rt = report_type.lower().strip()
        if rt not in SUPPORTED_REPORT_TYPES:
            raise ValueError(f"Unsupported report_type '{report_type}'. Must be one of {SUPPORTED_REPORT_TYPES}")
        fmt_norm = fmt.lower().strip()
        if fmt_norm not in ("json", "csv", "pdf"):
            raise ValueError("Unsupported format. Must be one of: json, csv, pdf")

        dt_start = _parse_iso_timestamp(start_date) if start_date else None
        dt_end = _parse_iso_timestamp(end_date) if end_date else None

        rows: List[Dict[str, Any]] = []
        methodology = ""

        if rt == "storage_inventory":
            methodology = "Snapshot of persisted storage inventory records and latest observed capacity utilization."
            q = db.query(Device)
            if storage_id:
                q = q.filter(Device.id == storage_id)
            for d in q.all():
                tel = db.query(Telemetry).filter(Telemetry.device_id == d.id).order_by(Telemetry.timestamp.desc()).first()
                used = int(tel.used_bytes) if tel else 0
                free = max(0, int(d.total_capacity_bytes) - used)
                util = round((used / d.total_capacity_bytes) * 100.0, 2) if d.total_capacity_bytes > 0 else 0.0
                rows.append({
                    "storage_id": d.id,
                    "name": d.name,
                    "storage_type": getattr(d, "storage_type", "SAN"),
                    "tier": d.tier,
                    "location": getattr(d, "environment_location", "Primary Data Center"),
                    "total_capacity_gb": round(d.total_capacity_bytes / (1024 ** 3), 2),
                    "used_capacity_gb": round(used / (1024 ** 3), 2),
                    "free_capacity_gb": round(free / (1024 ** 3), 2),
                    "utilization_pct": util,
                    "warning_threshold_pct": d.warning_threshold_pct,
                    "critical_threshold_pct": d.critical_threshold_pct,
                    "status": d.status,
                    "last_telemetry_at": tel.timestamp.isoformat() if tel and tel.timestamp else None,
                })

        elif rt == "storage_utilisation":
            methodology = "Chronological persisted telemetry records filtered by storage_id and date window."
            q = db.query(Telemetry)
            if storage_id:
                q = q.filter(Telemetry.device_id == storage_id)
            if dt_start:
                q = q.filter(Telemetry.timestamp >= dt_start)
            if dt_end:
                q = q.filter(Telemetry.timestamp <= dt_end)
            for t in q.order_by(Telemetry.timestamp.desc()).limit(500).all():
                rows.append({
                    "storage_id": t.device_id,
                    "timestamp": t.timestamp.isoformat() if t.timestamp else None,
                    "used_gb": round(t.used_bytes / (1024 ** 3), 2),
                    "free_gb": round(t.free_bytes / (1024 ** 3), 2),
                    "utilization_pct": t.utilization_pct,
                    "read_iops": t.read_iops,
                    "write_iops": t.write_iops,
                    "throughput_mb_s": t.throughput_mb_s,
                    "latency_p95_ms": t.latency_p95_ms,
                    "is_synthetic": t.is_synthetic,
                })

        elif rt == "performance_trends":
            methodology = "Actual IOPS, read/write latency, and throughput telemetry series without fabricated missing points."
            q = db.query(Telemetry)
            if storage_id:
                q = q.filter(Telemetry.device_id == storage_id)
            if dt_start:
                q = q.filter(Telemetry.timestamp >= dt_start)
            if dt_end:
                q = q.filter(Telemetry.timestamp <= dt_end)
            for t in q.order_by(Telemetry.timestamp.desc()).limit(500).all():
                rows.append({
                    "storage_id": t.device_id,
                    "timestamp": t.timestamp.isoformat() if t.timestamp else None,
                    "read_iops": t.read_iops,
                    "write_iops": t.write_iops,
                    "read_latency_ms": getattr(t, "read_latency_ms", None) if getattr(t, "read_latency_ms", None) is not None else t.latency_p95_ms,
                    "write_latency_ms": getattr(t, "write_latency_ms", None) if getattr(t, "write_latency_ms", None) is not None else t.latency_p95_ms,
                    "throughput_mbps": t.throughput_mb_s,
                    "utilization_pct": t.utilization_pct,
                })

        elif rt == "capacity_forecast":
            methodology = "Saved ML capacity forecasts generated by persisted scikit-learn / ensemble artifacts."
            q = db.query(Forecast)
            if storage_id:
                q = q.filter(Forecast.device_id == storage_id)
            if dt_start:
                q = q.filter(Forecast.generated_at >= dt_start)
            if dt_end:
                q = q.filter(Forecast.generated_at <= dt_end)
            for f in q.order_by(Forecast.generated_at.desc()).limit(100).all():
                q50 = json.loads(f.q50_json or "[]")
                rows.append({
                    "forecast_id": f.id,
                    "storage_id": f.device_id,
                    "model_name": f.model_name,
                    "horizon_days": getattr(f, "horizon_days", None) or max(1, f.horizon_hours // 24),
                    "generated_at": f.generated_at.isoformat() if f.generated_at else None,
                    "historical_cutoff": f.historical_cutoff.isoformat() if f.historical_cutoff else None,
                    "end_predicted_used_gb": round(q50[-1] / (1024 ** 3), 2) if q50 else None,
                    "projected_capacity_breach": bool(getattr(f, "projected_capacity_breach", False)),
                    "inference_ms": f.inference_ms,
                })

        elif rt == "model_performance":
            methodology = "Chronological holdout validation metrics (MAE, RMSE, R2, MAPE) for trained ML versions."
            q = db.query(ModelVersion)
            if storage_id:
                q = q.filter(ModelVersion.storage_id == storage_id)
            for mv in q.order_by(ModelVersion.trained_at.desc()).limit(100).all():
                mm = db.query(ModelMetric).filter(ModelMetric.model_version_id == mv.id).first()
                rows.append({
                    "model_version_id": mv.id,
                    "storage_id": mv.storage_id,
                    "algorithm": mv.model_type,
                    "version": mv.version_tag,
                    "training_samples": mv.train_samples_count,
                    "validation_samples": getattr(mv, "validation_samples", 0),
                    "mae_bytes": mm.mae if mm else mv.mae,
                    "rmse_bytes": mm.rmse if mm else mv.rmse,
                    "r2_score": mm.r2_score if mm else None,
                    "mape_pct": mm.mape if mm else None,
                    "is_active": mv.is_active,
                    "selection_reason": mm.selection_reason if mm else "",
                    "trained_at": mv.trained_at.isoformat() if mv.trained_at else None,
                })

        elif rt == "risk_and_alert":
            methodology = "Persisted risk evaluation alerts with severity, acknowledgement, and resolution audit trail."
            q = db.query(Alert)
            if storage_id:
                q = q.filter(Alert.device_id == storage_id)
            if dt_start:
                q = q.filter(Alert.triggered_at >= dt_start)
            if dt_end:
                q = q.filter(Alert.triggered_at <= dt_end)
            for a in q.order_by(Alert.triggered_at.desc()).limit(200).all():
                rows.append({
                    "alert_id": a.id,
                    "storage_id": a.device_id,
                    "category": a.category,
                    "severity": a.severity,
                    "title": a.title,
                    "status": a.status,
                    "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
                    "acknowledged_by": getattr(a, "acknowledged_by", None),
                    "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                    "resolution_details": getattr(a, "resolution_details", None),
                })

        elif rt == "data_quality":
            methodology = "Deterministic preprocessing & completeness audit results recorded without altering source telemetry."
            q = db.query(DataQualityResult)
            if storage_id:
                q = q.filter(DataQualityResult.storage_id == storage_id)
            for dq in q.order_by(DataQualityResult.evaluated_at.desc()).limit(100).all():
                rows.append({
                    "quality_id": dq.id,
                    "storage_id": dq.storage_id,
                    "total_records_received": dq.total_records_received,
                    "valid_records": dq.valid_records,
                    "rejected_records": dq.rejected_records,
                    "duplicate_records": dq.duplicate_records,
                    "outlier_count": dq.outlier_count,
                    "data_completeness_pct": dq.data_completeness_pct,
                    "latest_telemetry_timestamp": dq.latest_telemetry_timestamp.isoformat() if dq.latest_telemetry_timestamp else None,
                    "evaluated_at": dq.evaluated_at.isoformat() if dq.evaluated_at else None,
                })

        elif rt == "digital_twin_comparison":
            methodology = "Saved Digital Twin counterfactual simulations comparing safety envelope pass rate, residual risk, and cost."
            q = db.query(Scenario)
            if storage_id:
                q = q.filter(Scenario.device_id == storage_id)
            for s in q.order_by(Scenario.created_at.desc()).limit(100).all():
                out = db.query(SimulatedOutcome).filter(SimulatedOutcome.scenario_id == s.id).first()
                rows.append({
                    "scenario_id": s.id,
                    "storage_id": s.device_id,
                    "name": s.name,
                    "action_type": s.action_type,
                    "safety_envelope_passed": out.safety_envelope_passed if out else None,
                    "residual_risk_score": out.residual_risk_score if out else None,
                    "estimated_cost_usd": out.estimated_cost_usd if out else None,
                    "overhead_io_penalty_pct": out.overhead_io_penalty_pct if out else None,
                    "duration_minutes": out.duration_minutes if out else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                })

        elif rt == "data_reliability":
            methodology = "9-factor data reliability profiles gating conformal forecast uncertainty & recommendations."
            q = db.query(DataReliabilityProfile)
            if storage_id:
                q = q.filter(DataReliabilityProfile.storage_id == storage_id)
            for p in q.order_by(DataReliabilityProfile.evaluated_at.desc()).limit(100).all():
                rows.append({
                    "profile_id": p.id,
                    "storage_id": p.storage_id,
                    "reliability_score": p.reliability_score,
                    "reliability_tier": p.reliability_tier,
                    "is_stale": p.is_stale,
                    "uncertainty_multiplier": p.uncertainty_multiplier,
                    "completeness_score": p.completeness_score,
                    "freshness_score": p.freshness_score,
                    "evaluated_at": p.evaluated_at.isoformat() if p.evaluated_at else None,
                })

        elif rt == "workload_behaviour":
            methodology = "Statistical workload regime classifications, burst changepoints, and KS/PSI drift events."
            q = db.query(WorkloadRegimeEvent)
            if storage_id:
                q = q.filter(WorkloadRegimeEvent.storage_id == storage_id)
            for w in q.order_by(WorkloadRegimeEvent.detected_at.desc()).limit(150).all():
                rows.append({
                    "event_id": w.id,
                    "storage_id": w.storage_id,
                    "regime_label": w.regime_label,
                    "event_type": w.event_type,
                    "severity": w.severity,
                    "confidence": w.confidence,
                    "explanation": w.explanation,
                    "detected_at": w.detected_at.isoformat() if w.detected_at else None,
                })

        elif rt == "capacity_risk":
            methodology = "Probabilistic capacity risk evaluations from empirical residual CDFs & shortfall bounds."
            q = db.query(CapacityRiskEvaluation)
            if storage_id:
                q = q.filter(CapacityRiskEvaluation.storage_id == storage_id)
            for cr in q.order_by(CapacityRiskEvaluation.evaluated_at.desc()).limit(100).all():
                rows.append({
                    "risk_eval_id": cr.id,
                    "storage_id": cr.storage_id,
                    "horizon_days": cr.horizon_days,
                    "current_utilization_pct": cr.current_utilization_pct,
                    "forecasted_utilization_pct": cr.forecasted_utilization_pct,
                    "adverse_p90_utilization_pct": cr.adverse_p90_utilization_pct,
                    "threshold_crossing_probability": cr.threshold_crossing_probability,
                    "expected_shortfall_gb": round(cr.expected_shortfall_bytes / (1024 ** 3), 2),
                    "safety_threshold_crossing_date": cr.safety_threshold_crossing_date.isoformat() if cr.safety_threshold_crossing_date else None,
                    "exhaustion_date": cr.exhaustion_date.isoformat() if cr.exhaustion_date else None,
                    "evaluated_at": cr.evaluated_at.isoformat() if cr.evaluated_at else None,
                })

        elif rt == "recommendation_history":
            methodology = "Advisory recommendation & human approval lifecycle ledger (non-execution guaranteed)."
            q = db.query(Recommendation)
            if storage_id:
                q = q.filter(Recommendation.device_id == storage_id)
            for rec in q.order_by(Recommendation.created_at.desc()).limit(150).all():
                rows.append({
                    "recommendation_id": rec.id,
                    "storage_id": rec.device_id,
                    "action_type": rec.action_type,
                    "title": rec.title,
                    "approval_status": rec.approval_status,
                    "reviewed_by": rec.reviewed_by,
                    "review_notes": rec.review_notes,
                    "utility_score": rec.utility_score,
                    "created_at": rec.created_at.isoformat() if rec.created_at else None,
                })

        now = datetime.now(timezone.utc)
        report_id = f"rep-{uuid.uuid4().hex[:10]}"
        filters_meta = {"storage_id": storage_id, "start_date": start_date, "end_date": end_date}

        history = ReportHistory(
            id=report_id,
            report_type=rt,
            format=fmt_norm.upper(),
            storage_id=storage_id,
            filters_json=json.dumps(filters_meta),
            generated_by=generated_by,
            row_count=len(rows),
            summary_json=json.dumps({"methodology": methodology}),
            created_at=now,
        )
        db.add(history)
        db.commit()

        payload = {
            "report_id": report_id,
            "report_type": rt,
            "format": fmt_norm.upper(),
            "generated_at": now.isoformat(),
            "generated_by": generated_by,
            "filters": filters_meta,
            "methodology": methodology,
            "row_count": len(rows),
            "rows": rows,
        }

        if fmt_norm == "csv":
            output = io.StringIO()
            if rows:
                writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            else:
                output.write("message\nNo records matched the selected filters.\n")
            payload["csv_content"] = output.getvalue()
        elif fmt_norm == "pdf":
            payload["pdf_bytes"] = cls._render_pdf(payload)

        return payload

    @staticmethod
    def _render_pdf(report_data: Dict[str, Any]) -> bytes:
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        width, height = letter
        y = height - 48

        c.setFont("Helvetica-Bold", 14)
        c.drawString(44, y, f"AEGISSTOR Report: {report_data['report_type'].replace('_', ' ').title()}")
        y -= 20

        c.setFont("Helvetica", 9)
        c.drawString(44, y, f"Report ID: {report_data['report_id']}   Generated: {report_data['generated_at']}")
        y -= 14
        c.drawString(44, y, f"Generated By: {report_data['generated_by']}   Filters: {json.dumps(report_data['filters'])}")
        y -= 14
        c.drawString(44, y, f"Methodology: {report_data['methodology'][:95]}")
        y -= 20

        c.line(44, y, width - 44, y)
        y -= 16

        rows = report_data.get("rows", [])
        if not rows:
            c.drawString(44, y, "No records matched the selected report filters.")
        else:
            for idx, r in enumerate(rows[:40], start=1):
                line = f"{idx}. " + " | ".join(f"{k}={v}" for k, v in list(r.items())[:5])
                if y < 54:
                    c.showPage()
                    c.setFont("Helvetica", 8)
                    y = height - 44
                c.setFont("Helvetica", 8)
                c.drawString(44, y, line[:115])
                y -= 13

        c.save()
        return buf.getvalue()
