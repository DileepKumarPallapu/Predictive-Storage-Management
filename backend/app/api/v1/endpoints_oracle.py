from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.services.oracle import (
    WorkloadCatalogService,
    AttributionEngine,
    CapacityForensicsService,
    BottleneckForensicsEngine,
    HypothesisManager,
    CounterfactualExperimentService,
    OracleReportGenerator
)
from app.auth.permissions import require_method_permission

router = APIRouter(
    prefix="/oracle",
    tags=["AEGISSTOR Oracle Workload Intelligence"],
    dependencies=[Depends(require_method_permission("workload.read", "workload.analyse"))],
)

# -------------------------------------------------------------
# Request Schemas
# -------------------------------------------------------------
class CreateHypothesisPayload(BaseModel):
    question: str = Field(..., description="The empirical investigation question")
    target_resource: str = Field(..., description="Target storage device or pool ID")
    workload_id: Optional[str] = Field(None, description="Suspected workload ID")
    supporting_evidence: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)
    confounding_variables: List[str] = Field(default_factory=list)
    proposed_evaluation_method: str = Field("CONTROLLED_DIGITAL_TWIN_SIMULATION")
    reviewer: str = Field("lead_sre@aegisstor.internal")
    evidence_references: List[str] = Field(default_factory=list)

class UpdateHypothesisPayload(BaseModel):
    status: str = Field(..., description="New lifecycle status")
    rationale: str = Field(..., description="Audit rationale for status transition")
    reviewer: str = Field("lead_sre@aegisstor.internal")
    conclusion: Optional[str] = Field(None, description="Final scientific conclusion if closing")

class UpdateCasePayload(BaseModel):
    status: str = Field(..., description="Case status: ACTIVE, INVESTIGATING, MITIGATED, DISMISSED, DEFERRED")
    assigned_to: Optional[str] = Field(None, description="Email or user ID of investigator")

class RunCounterfactualPayload(BaseModel):
    target_device_id: str
    workload_id: str
    intervention_type: str = Field("THROTTLE_INTENSITY", description="THROTTLE_INTENSITY, RESCHEDULE_WINDOW, EXPAND_SHARED_LIMIT")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    horizon_hours: int = Field(72, ge=12, le=720)


# -------------------------------------------------------------
# Workload Intelligence & Attribution Endpoints
# -------------------------------------------------------------
@router.get("/workloads")
def list_workloads(device_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    List known workloads, their resource associations, and latest observed telemetry.
    """
    WorkloadCatalogService.seed_workloads_if_missing(db)
    return WorkloadCatalogService.list_workloads(db, device_id=device_id)


@router.get("/attribution/{device_id}")
def get_device_attribution(
    device_id: str,
    hours: int = Query(72, ge=12, le=720),
    db: Session = Depends(get_db)
):
    """
    Calculate workload capacity and IOPS attribution using:
    Method A (Direct Measurement), Method B (Aggregate Reconciliation),
    and Method C (Statistical Feature Attribution with non-causal guardrails).
    """
    WorkloadCatalogService.seed_workloads_if_missing(db)
    try:
        return AttributionEngine.get_attribution_summary(db, device_id=device_id, hours=hours)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/capacity-forensics/{device_id}")
def get_capacity_forensics(
    device_id: str,
    window_hours: int = Query(168, ge=24, le=720),
    db: Session = Depends(get_db)
):
    """
    Historical capacity growth decomposition: velocity, acceleration, changepoint detection,
    and period-over-period comparison.
    """
    try:
        return CapacityForensicsService.analyze_capacity_growth(db, device_id=device_id, window_hours=window_hours)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/bottlenecks/{device_id}")
def get_device_bottlenecks(
    device_id: str,
    hours: int = Query(72, ge=12, le=720),
    db: Session = Depends(get_db)
):
    """
    Performance bottleneck forensics: evaluates tail latency (P95), queue depth,
    throughput saturation, and concurrent background job contention.
    """
    try:
        return BottleneckForensicsEngine.analyze_device_bottlenecks(db, device_id=device_id, hours=hours)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/contention-graph")
def get_resource_contention_graph(
    device_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Resource Contention Graph: returns nodes (Workloads, Devices, Pools, Controllers)
    and edges (Verified dependencies vs Suspected contention).
    """
    WorkloadCatalogService.seed_workloads_if_missing(db)
    return BottleneckForensicsEngine.get_contention_graph(db, device_id=device_id)


# -------------------------------------------------------------
# Bottleneck Investigation Queue Endpoints
# -------------------------------------------------------------
@router.get("/cases")
def list_bottleneck_cases(
    status: Optional[str] = "ALL",
    db: Session = Depends(get_db)
):
    """
    Lists prioritized bottleneck investigation cases with supporting & conflicting evidence.
    """
    BottleneckForensicsEngine.seed_initial_bottleneck_cases_if_missing(db)
    return BottleneckForensicsEngine.list_cases(db, status=status)


@router.patch("/cases/{case_id}")
def update_bottleneck_case(
    case_id: str,
    payload: UpdateCasePayload,
    db: Session = Depends(get_db)
):
    """
    Updates the triage status or assignee for an active bottleneck case.
    """
    try:
        return BottleneckForensicsEngine.update_case_status(
            db, case_id=case_id, new_status=payload.status, assignee=payload.assigned_to
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -------------------------------------------------------------
# Hypothesis Management Endpoints
# -------------------------------------------------------------
@router.get("/hypotheses")
def list_hypotheses(
    target_resource: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lists investigation hypotheses and their lifecycle progression.
    """
    HypothesisManager.seed_initial_hypotheses_if_missing(db)
    return HypothesisManager.list_hypotheses(db, target_resource=target_resource)


@router.post("/hypotheses", status_code=201)
def create_hypothesis(
    payload: CreateHypothesisPayload,
    db: Session = Depends(get_db)
):
    """
    Creates a new investigation hypothesis. Automatically runs evidence contradiction checks.
    """
    return HypothesisManager.create_hypothesis(db, payload.model_dump())


@router.patch("/hypotheses/{hypothesis_id}")
def update_hypothesis(
    hypothesis_id: str,
    payload: UpdateHypothesisPayload,
    db: Session = Depends(get_db)
):
    """
    Transitions hypothesis status with mandatory audit rationale.
    Enforces scientific verification rules (cannot mark supported without evaluation).
    """
    try:
        return HypothesisManager.update_hypothesis_status(
            db,
            hypothesis_id=hypothesis_id,
            new_status=payload.status,
            rationale=payload.rationale,
            reviewer=payload.reviewer,
            conclusion=payload.conclusion
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------------------------------------------
# Counterfactual Workload Experiments
# -------------------------------------------------------------
@router.post("/counterfactual")
def run_counterfactual_simulation(
    payload: RunCounterfactualPayload,
    db: Session = Depends(get_db)
):
    """
    Executes a controlled what-if workload simulation in the Digital Twin.
    Strictly isolated: zero real mutations, explicitly disclaims physical causation.
    """
    try:
        return CounterfactualExperimentService.run_counterfactual_simulation(
            db,
            target_device_id=payload.target_device_id,
            workload_id=payload.workload_id,
            intervention_type=payload.intervention_type,
            parameters=payload.parameters,
            horizon_hours=payload.horizon_hours
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/counterfactual")
def list_counterfactual_experiments(
    target_device_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lists past counterfactual simulations and their audit parameters.
    """
    return CounterfactualExperimentService.list_experiments(db, target_device_id=target_device_id)


# -------------------------------------------------------------
# Investigation Reports & Export
# -------------------------------------------------------------
@router.get("/report/{device_id}")
def get_investigation_report(
    device_id: str,
    hypothesis_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Generates a structured, evidence-backed investigation report.
    """
    try:
        return OracleReportGenerator.generate_investigation_report(
            db, device_id=device_id, hypothesis_id=hypothesis_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/report/{device_id}/export")
def export_investigation_report(
    device_id: str,
    format: str = Query("markdown", pattern="^(markdown|csv)$"),
    hypothesis_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Exports investigation findings in Markdown (.md) or CSV (.csv) format.
    """
    try:
        report = OracleReportGenerator.generate_investigation_report(
            db, device_id=device_id, hypothesis_id=hypothesis_id
        )
        if format == "markdown":
            content = OracleReportGenerator.export_report_markdown(report)
            return Response(
                content=content,
                media_type="text/markdown",
                headers={"Content-Disposition": f"attachment; filename=oracle_report_{device_id}.md"}
            )
        else:
            content = OracleReportGenerator.export_workloads_csv(report)
            return Response(
                content=content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=oracle_workloads_{device_id}.csv"}
            )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
