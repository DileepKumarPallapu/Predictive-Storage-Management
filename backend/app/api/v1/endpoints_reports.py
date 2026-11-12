import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import ReportHistory, User
from app.auth.security import get_current_user, require_role
from app.auth.permissions import require_permission, get_effective_permissions
from app.services.audit_service import AuditService
from app.services.reporting_service import ReportingService, SUPPORTED_REPORT_TYPES

router = APIRouter(prefix="/reports", tags=["Reporting & Export"])


class ReportGenerateRequest(BaseModel):
    report_type: str
    format: str = "json"
    storage_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.get("/types")
def list_report_types(current_user: User = Depends(require_permission("reports.read"))):
    """Lists supported operational, ML, data-quality, and Digital Twin report types."""
    return {
        "supported_report_types": SUPPORTED_REPORT_TYPES,
        "supported_formats": ["json", "csv", "pdf"],
    }


@router.get("/history")
def list_report_history(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_permission("reports.read")),
    db: Session = Depends(get_db),
):
    """Returns audit log of previously generated reports."""
    rows = db.query(ReportHistory).order_by(ReportHistory.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "report_type": r.report_type,
            "format": r.format,
            "storage_id": r.storage_id,
            "filters": json.loads(r.filters_json or "{}"),
            "generated_by": r.generated_by,
            "row_count": r.row_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/generate")
def generate_report_get(
    report_type: str = Query(..., description=f"One of: {', '.join(SUPPORTED_REPORT_TYPES)}"),
    format: str = Query("json", description="json, csv, or pdf"),
    storage_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("reports.read")),
    db: Session = Depends(get_db)
):
    fmt_l = format.lower()
    perms = get_effective_permissions(db, current_user.role)
    if fmt_l in {"csv", "pdf"} and "reports.export" not in perms:
        raise HTTPException(status_code=403, detail="Missing permission: reports.export")
    """Generates a report from actual persisted application data in JSON, CSV, or PDF format."""
    try:
        res = ReportingService.generate_report(
            db=db,
            report_type=report_type,
            fmt=format,
            storage_id=storage_id,
            start_date=start_date,
            end_date=end_date,
            generated_by=current_user.username,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    AuditService.log_event(
        db=db,
        action="GENERATE_REPORT",
        target_type="REPORT",
        target_id=res["report_id"],
        user=current_user.username,
        details={"report_type": report_type, "format": format, "row_count": res["row_count"]}
    )

    fmt_l = format.lower()
    if fmt_l == "csv":
        return Response(
            content=res["csv_content"],
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={report_type}_{res['report_id']}.csv"}
        )
    if fmt_l == "pdf":
        return Response(
            content=res["pdf_bytes"],
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={report_type}_{res['report_id']}.pdf"}
        )
    return res


@router.post("/generate")
def generate_report_post(
    payload: ReportGenerateRequest,
    current_user: User = Depends(require_permission("reports.generate")),
    db: Session = Depends(get_db)
):
    return generate_report_get(
        report_type=payload.report_type,
        format=payload.format,
        storage_id=payload.storage_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        current_user=current_user,
        db=db,
    )
