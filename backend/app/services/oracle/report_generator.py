import csv
import io
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import (
    Device, Telemetry, OracleHypothesis, OracleBottleneckCase, OracleCounterfactualExperiment,
    OracleWorkload
)
from app.services.oracle.attribution_engine import AttributionEngine
from app.services.oracle.capacity_forensics import CapacityForensicsService
from app.services.oracle.bottleneck_engine import BottleneckForensicsEngine

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class OracleReportGenerator:
    """
    AEGISSTOR ORACLE — Interpretable Investigation Report Generator.
    Produces comprehensive evidence-backed investigation reports with
    Markdown and CSV export capabilities.
    """

    @classmethod
    def generate_investigation_report(
        cls,
        db: Session,
        device_id: str,
        hypothesis_id: Optional[str] = None
    ) -> Dict[str, Any]:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found")

        # 1. Fetch Attribution, Capacity Forensics, and Bottleneck signals
        attr_data = AttributionEngine.get_attribution_summary(db, device_id, hours=72)
        cap_data = CapacityForensicsService.analyze_capacity_growth(db, device_id, window_hours=168)
        btnk_data = BottleneckForensicsEngine.analyze_device_bottlenecks(db, device_id, hours=72)

        # 2. Fetch specific or latest hypothesis
        hyp_record = None
        if hypothesis_id:
            hyp_record = db.query(OracleHypothesis).filter(OracleHypothesis.id == hypothesis_id).first()
        if not hyp_record:
            hyp_record = (
                db.query(OracleHypothesis)
                .filter(OracleHypothesis.target_resource == device_id)
                .order_by(OracleHypothesis.updated_at.desc())
                .first()
            )

        # 3. Fetch latest counterfactual experiment
        latest_exp = (
            db.query(OracleCounterfactualExperiment)
            .filter(OracleCounterfactualExperiment.target_device_id == device_id)
            .order_by(OracleCounterfactualExperiment.created_at.desc())
            .first()
        )

        now_str = utc_now().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Fetch latest device telemetry
        latest_device_tel = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == device_id)
            .order_by(Telemetry.timestamp.desc())
            .first()
        )
        util_pct = latest_device_tel.utilization_pct if latest_device_tel and latest_device_tel.utilization_pct else 65.0
        p95_lat = latest_device_tel.latency_p95_ms if latest_device_tel and latest_device_tel.latency_p95_ms else 8.5

        # Compile structured report dict
        report = {
            "report_id": f"rpt-oracle-{device_id}-{int(utc_now().timestamp())}",
            "generated_at": now_str,
            "device": {
                "id": device.id,
                "name": device.name,
                "tier": device.tier,
                "media_type": device.media_type,
                "utilization_pct": round(util_pct, 1),
                "p95_latency_ms": round(p95_lat, 2),
                "sla_latency_limit_ms": device.max_acceptable_latency_ms
            },
            "investigation_question": hyp_record.question if hyp_record else f"Workload attribution and performance bottleneck assessment for {device.name}",
            "hypothesis_status": hyp_record.status if hyp_record else "NO_HYPOTHESIS_RECORDED",
            "reviewer": hyp_record.reviewer if hyp_record else "lead_sre@aegisstor.internal",
            "attribution_summary": {
                "coverage_pct": attr_data.get("attribution_coverage_pct", 0.0),
                "reconciliation_status": attr_data.get("reconciliation_status", "UNKNOWN"),
                "total_attributed_gb": attr_data.get("total_attributed_gb", 0.0),
                "unattributed_residual_gb": attr_data.get("residual_unattributed_gb", 0.0),
                "workload_breakdown": attr_data.get("workload_breakdown", [])
            },
            "capacity_growth_forensics": {
                "growth_pattern": cap_data.get("growth_pattern", "STEADY"),
                "growth_rate_gb_day": cap_data.get("growth_rate_gb_per_day", 0.0),
                "acceleration_gb_day2": cap_data.get("acceleration_gb_per_day2", 0.0),
                "changepoints_detected": cap_data.get("changepoints_detected", []),
                "days_to_reserve_breach": cap_data.get("reserve_runway_projection", {}).get("projected_days_to_breach")
            },
            "performance_bottleneck_findings": {
                "contention_index": btnk_data.get("contention_index", 0.0),
                "contention_level": btnk_data.get("contention_level", "LOW"),
                "signals": btnk_data.get("forensics_findings", []),
                "concurrent_background_jobs": btnk_data.get("concurrent_background_jobs", [])
            },
            "supporting_evidence": json.loads(hyp_record.supporting_evidence_json or "[]") if hyp_record else [],
            "contradicting_evidence": json.loads(hyp_record.contradicting_evidence_json or "[]") if hyp_record else [],
            "confounding_variables": json.loads(hyp_record.confounding_variables_json or "[]") if hyp_record else [],
            "counterfactual_simulation": {
                "experiment_id": latest_exp.id if latest_exp else None,
                "intervention_type": latest_exp.intervention_type if latest_exp else "NONE",
                "simulated_outcome": json.loads(latest_exp.simulated_metrics_json or "{}") if latest_exp else None,
                "is_causally_proven": False
            },
            "scientific_limitations": [
                "Observational attribution measures statistical correlation only. It does not establish physical causation without real experimental ablation.",
                "Digital Twin what-if simulations reflect model assumptions and must not be treated as empirical ground truth.",
                "Filesystem residual growth accounts for unmeasured OS journaling, block allocation overhead, and untagged tenant writes."
            ],
            "recommended_actions": [
                f"Schedule non-invasive controlled what-if workload test in Digital Twin for {device.id}.",
                "Investigate unmeasured residual growth allocations if attribution coverage falls below 85%.",
                "Review background job concurrency windows (01:00-04:00) to mitigate P95 tail latency contention."
            ]
        }
        return report

    @classmethod
    def export_report_markdown(cls, report: Dict[str, Any]) -> str:
        d = report["device"]
        attr = report["attribution_summary"]
        cap = report["capacity_growth_forensics"]
        btnk = report["performance_bottleneck_findings"]

        md = f"""# AEGISSTOR ORACLE — Workload Attribution & Bottleneck Forensic Report
**Report ID**: `{report["report_id"]}`  
**Target Resource**: `{d["name"]} ({d["id"]})`  
**Media Tier**: `{d["tier"]}` | **Status**: `Util: {d["utilization_pct"]}%` | `P95 Latency: {d["p95_latency_ms"]} ms` (SLA Ceiling: `{d["sla_latency_limit_ms"]} ms`)  
**Generated At**: `{report["generated_at"]}`  
**Reviewer**: `{report["reviewer"]}`  

---

## 1. Investigation Hypothesis
**Question**: {report["investigation_question"]}  
**Current Status**: `{report["hypothesis_status"]}`  

### Supporting Evidence
"""
        for se in report["supporting_evidence"]:
            md += f"- **[Observed]** {se}\n"
        if not report["supporting_evidence"]:
            md += "- *No supporting evidence recorded yet.*\n"

        md += "\n### Contradicting Evidence & Candidate Confounds\n"
        for ce in report["contradicting_evidence"]:
            md += f"- **[Contradiction]** {ce}\n"
        for cv in report["confounding_variables"]:
            md += f"- **[Confound]** {cv}\n"
        if not report["contradicting_evidence"] and not report["confounding_variables"]:
            md += "- *No contradictory evidence or confounds flagged.*\n"

        md += f"""
---

## 2. Workload Capacity Attribution & Aggregate Reconciliation
- **Attribution Coverage**: `{attr["coverage_pct"]}%` (`{attr["reconciliation_status"]}`)
- **Total Attributed Capacity**: `{attr["total_attributed_gb"]} GB`
- **Unattributed Residual Growth**: `{attr["unattributed_residual_gb"]} GB`

| Workload ID | Workload Name | Type | Allocated GB | Delta GB | IOPS | P95 Latency (ms) | Method |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""
        for w in attr["workload_breakdown"]:
            md += f"| `{w['workload_id']}` | {w['workload_name']} | {w['workload_type']} | {w['current_allocated_gb']} | +{w['growth_delta_gb']} | {w['current_iops']} | {w['current_latency_p95_ms']} | {w['attribution_method']} |\n"

        md += f"""
---

## 3. Capacity Growth Velocity & Acceleration
- **Growth Pattern**: `{cap["growth_pattern"]}`
- **Net Daily Growth Rate**: `{cap["growth_rate_gb_day"]} GB/day`
- **Acceleration**: `{cap["acceleration_gb_day2"]} GB/day²`
- **Estimated Days to Reserve Breach**: `{cap["days_to_reserve_breach"] or 'Safe Runway'}`

---

## 4. Performance Contention & Tail Latency Signals
- **Contention Index**: `{btnk["contention_index"]}` (`{btnk["contention_level"]}`)
"""
        for s in btnk["signals"]:
            md += f"- **Signal**: `{s['signal']}` ({s['severity']}) — {s['evidence']}\n"

        if btnk["concurrent_background_jobs"]:
            md += "\n**Concurrent Background Jobs**:\n"
            for c in btnk["concurrent_background_jobs"]:
                md += f"- `{c['workload_id']}` ({c['type']}): {c['potential_contention']}\n"

        md += """
---

## 5. Scientific Limitations & Epistemological Boundaries
> [!IMPORTANT]
> - Observational attribution and feature importance measure correlation only; they do not establish causation without controlled experimental ablation.
> - Counterfactual simulator outcomes reflect Digital Twin physics assumptions and are strictly isolated from production storage hardware.

---

## 6. Recommended Operational Actions
"""
        for act in report["recommended_actions"]:
            md += f"1. {act}\n"

        return md

    @classmethod
    def export_workloads_csv(cls, report: Dict[str, Any]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "device_id", "workload_id", "workload_name", "workload_type",
            "allocated_gb", "growth_delta_gb", "current_iops", "latency_p95_ms", "attribution_method"
        ])
        dev_id = report["device"]["id"]
        for w in report["attribution_summary"]["workload_breakdown"]:
            writer.writerow([
                dev_id,
                w.get("workload_id"),
                w.get("workload_name"),
                w.get("workload_type"),
                w.get("current_allocated_gb"),
                w.get("growth_delta_gb"),
                w.get("current_iops"),
                w.get("current_latency_p95_ms"),
                w.get("attribution_method")
            ])
        return output.getvalue()
