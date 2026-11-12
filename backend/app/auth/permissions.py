import uuid
from typing import Dict, List, Set

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import Permission, Role, RolePermission, User
from app.services.audit_service import AuditService

ROLE_ADMIN = "ADMIN"
ROLE_OPERATOR = "OPERATOR"
ROLE_VIEWER = "VIEWER"
ROLE_AUDITOR = "AUDITOR"

ALL_ROLES = [ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER, ROLE_AUDITOR]

PERMISSION_CATALOG: List[Dict[str, str]] = [
    # Storage Infrastructure
    {"key": "storage.read", "module": "Storage", "description": "View storage inventory, capacity, and topology"},
    {"key": "storage.create", "module": "Storage", "description": "Register storage systems and volumes"},
    {"key": "storage.update", "module": "Storage", "description": "Update storage metadata and collector bindings"},
    {"key": "storage.delete", "module": "Storage", "description": "Remove storage resources after dependency check"},
    # Telemetry
    {"key": "telemetry.read", "module": "Telemetry", "description": "Inspect telemetry series and live collector status"},
    {"key": "telemetry.collect", "module": "Telemetry", "description": "Initiate permitted read-only collection and test probes"},
    {"key": "telemetry.ingest", "module": "Telemetry", "description": "Submit manual or API telemetry batches"},
    {"key": "telemetry.configure", "module": "Telemetry", "description": "Configure permitted collector polling parameters"},
    # Data Ingestion
    {"key": "ingestion.preview", "module": "Ingestion", "description": "Preview CSV telemetry imports"},
    {"key": "ingestion.validate", "module": "Ingestion", "description": "Validate telemetry schemas and invariants"},
    {"key": "ingestion.commit", "module": "Ingestion", "description": "Commit validated imports to database"},
    {"key": "ingestion.export", "module": "Ingestion", "description": "Download templates and ingestion error CSVs"},
    # Data Quality
    {"key": "quality.read", "module": "Data Quality", "description": "Inspect missing values, duplicates, reliability profiles"},
    {"key": "quality.process", "module": "Data Quality", "description": "Execute data quality & reliability scoring"},
    # Workload Intelligence
    {"key": "workload.read", "module": "Workload", "description": "Inspect workload regimes, changepoints, and drift"},
    {"key": "workload.analyse", "module": "Workload", "description": "Trigger workload regime and drift analysis"},
    # ML Models
    {"key": "models.read", "module": "ML Models", "description": "Inspect LightGBM/SARIMAX models and validation metrics"},
    {"key": "models.train", "module": "ML Models", "description": "Trigger champion-challenger model training jobs"},
    {"key": "models.retrain", "module": "ML Models", "description": "Trigger authorized model retraining / recalibration"},
    # Forecasting
    {"key": "forecasts.read", "module": "Forecasting", "description": "View generated forecasts and historical comparisons"},
    {"key": "forecasts.generate", "module": "Forecasting", "description": "Generate calibrated multi-horizon forecasts"},
    {"key": "forecasts.export", "module": "Forecasting", "description": "Export forecast datasets"},
    # Capacity Risk
    {"key": "risk.read", "module": "Capacity Risk", "description": "View capacity runway and probabilistic risk"},
    {"key": "risk.evaluate", "module": "Capacity Risk", "description": "Execute capacity threshold-crossing evaluations"},
    {"key": "risk.configure", "module": "Capacity Risk", "description": "Configure delegated warning/critical resource thresholds"},
    # Performance Analytics
    {"key": "performance.read", "module": "Performance", "description": "View IOPS, latency, throughput, and SLA breaches"},
    {"key": "performance.configure", "module": "Performance", "description": "Configure delegated latency SLA thresholds"},
    # Alerts
    {"key": "alerts.read", "module": "Alerts", "description": "View alerts, evidence, and alert history"},
    {"key": "alerts.acknowledge", "module": "Alerts", "description": "Acknowledge active alerts"},
    {"key": "alerts.assign", "module": "Alerts", "description": "Assign alerts to operational owners"},
    {"key": "alerts.resolve", "module": "Alerts", "description": "Resolve alerts with audit resolution notes"},
    {"key": "alerts.reopen", "module": "Alerts", "description": "Reopen resolved alerts"},
    # Digital Twin
    {"key": "digital_twin.read", "module": "Digital Twin", "description": "View saved counterfactual scenarios and outcomes"},
    {"key": "digital_twin.create", "module": "Digital Twin", "description": "Create new Digital Twin scenarios"},
    {"key": "digital_twin.update", "module": "Digital Twin", "description": "Edit permitted Digital Twin scenario parameters"},
    {"key": "digital_twin.delete", "module": "Digital Twin", "description": "Delete permitted Digital Twin scenarios"},
    {"key": "digital_twin.execute", "module": "Digital Twin", "description": "Execute Digital Twin counterfactual simulations"},
    {"key": "digital_twin.export", "module": "Digital Twin", "description": "Export Digital Twin results"},
    # Decision Optimisation
    {"key": "optimisation.read", "module": "Optimisation", "description": "Inspect constrained decision ranking outputs"},
    {"key": "optimisation.execute", "module": "Optimisation", "description": "Run constrained intervention optimisation"},
    # Recommendations & Approvals
    {"key": "recommendations.read", "module": "Recommendations", "description": "Inspect advisory recommendations and evidence"},
    {"key": "recommendations.review", "module": "Recommendations", "description": "Generate and review operational recommendations"},
    {"key": "approvals.read", "module": "Approvals", "description": "View approval queues and decision statuses"},
    {"key": "approvals.submit", "module": "Approvals", "description": "Submit operational recommendations for review"},
    {"key": "approvals.approve", "module": "Approvals", "description": "Approve assigned recommendations within policy"},
    {"key": "approvals.reject", "module": "Approvals", "description": "Reject assigned recommendations with reason"},
    # Reports
    {"key": "reports.read", "module": "Reports", "description": "View and list persisted report history"},
    {"key": "reports.generate", "module": "Reports", "description": "Generate JSON/CSV/PDF reports from database values"},
    {"key": "reports.export", "module": "Reports", "description": "Download CSV/PDF report exports"},
    # Users & IAM (Admin Default Only)
    {"key": "users.read", "module": "IAM", "description": "View all system user accounts and login status"},
    {"key": "users.create", "module": "IAM", "description": "Create Administrator, Operator, or Viewer accounts"},
    {"key": "users.update", "module": "IAM", "description": "Edit user profile fields and active status"},
    {"key": "users.deactivate", "module": "IAM", "description": "Deactivate user accounts and revoke sessions"},
    {"key": "users.assign_role", "module": "IAM", "description": "Assign user roles and configure role permissions"},
    # Settings & Integrations & Audit
    {"key": "settings.read", "module": "Settings", "description": "View global system thresholds and retention policy"},
    {"key": "settings.update", "module": "Settings", "description": "Modify global system thresholds and retention policy"},
    {"key": "integrations.read", "module": "Integrations", "description": "View configured collector integrations (secrets redacted)"},
    {"key": "integrations.configure", "module": "Integrations", "description": "Register or reconfigure global collector integrations"},
    {"key": "integrations.manage_secrets", "module": "Integrations", "description": "Issue/revoke API keys and manage connector secrets"},
    {"key": "audit.read", "module": "Audit", "description": "Inspect operational and authentication audit logs"},
    {"key": "audit.export", "module": "Audit", "description": "Export and cryptographically verify full audit chain"},
    # Enterprise Multi-Organisation & Hierarchy
    {"key": "org.read", "module": "Enterprise", "description": "View organisations, hierarchy, and memberships"},
    {"key": "org.manage", "module": "Enterprise", "description": "Create/update organisations, members, and hierarchy"},
    # Topology & Services
    {"key": "topology.read", "module": "Topology", "description": "View infrastructure asset relationships and lineage"},
    {"key": "topology.write", "module": "Topology", "description": "Create/update infrastructure asset relationships"},
    {"key": "services.read", "module": "Services", "description": "View applications, business services, and impact graphs"},
    {"key": "services.write", "module": "Services", "description": "Manage applications, business services, and dependencies"},
    # Service Reliability (SLI/SLO) & Incidents & ITSM
    {"key": "slo.read", "module": "Reliability", "description": "View SLIs, SLOs, error budgets, and evaluations"},
    {"key": "slo.manage", "module": "Reliability", "description": "Create/update SLIs, SLOs, and trigger evaluations"},
    {"key": "incidents.read", "module": "Incidents", "description": "View enterprise incidents, timelines, and postmortems"},
    {"key": "incidents.write", "module": "Incidents", "description": "Create, triage, resolve incidents and author postmortems"},
    {"key": "itsm.configure", "module": "ITSM", "description": "Configure ServiceNow, Jira SM, and Webhook ITSM connectors"},
    # FinOps & Procurement
    {"key": "finops.read", "module": "FinOps", "description": "View FOCUS billing, cost allocations, and budgets"},
    {"key": "finops.write", "module": "FinOps", "description": "Ingest FOCUS billing, manage allocation rules and budgets"},
    {"key": "procurement.propose", "module": "Procurement", "description": "Prepare capacity procurement proposals"},
    {"key": "procurement.approve", "module": "Procurement", "description": "Approve or reject capacity procurement proposals"},
    # Backup/DR & Governance
    {"key": "backup.read", "module": "Resilience", "description": "View backup/replication events, RPO/RTO, and DR plans"},
    {"key": "backup.manage", "module": "Resilience", "description": "Record backup/replication events, objectives, and DR plans"},
    {"key": "governance.read", "module": "Governance", "description": "View NIST CSF 2.0 governance policies and evaluations"},
    {"key": "governance.manage", "module": "Governance", "description": "Author governance policies and approve policy exceptions"},
    # MLOps & Decision Feedback
    {"key": "mlops.promote", "module": "MLOps", "description": "Promote or rollback champion/challenger ML models"},
    {"key": "decisions.verify", "module": "Decisions", "description": "Record and verify decision implementation outcomes"},
    # Control Plane Foundation (Sprint 1)
    {"key": "control_plane.read", "module": "Control Plane", "description": "View control plane connectors, action requests, preflight, and execution evidence"},
    {"key": "control_plane.connectors.manage", "module": "Control Plane", "description": "Register/manage control plane connectors, capabilities, and action policies"},
    {"key": "control_plane.actions.create", "module": "Control Plane", "description": "Create action requests, run preflight/dry-run, and execute supported read-only actions"},
    {"key": "control_plane.actions.approve", "module": "Control Plane", "description": "Approve or reject pending control plane action requests"},
]

ALL_PERMISSION_KEYS: List[str] = [p["key"] for p in PERMISSION_CATALOG]

DEFAULT_ROLE_PERMISSIONS: Dict[str, List[str]] = {
    ROLE_ADMIN: list(ALL_PERMISSION_KEYS),
    ROLE_OPERATOR: [
        "storage.read", "storage.create", "storage.update", "storage.delete",
        "telemetry.read", "telemetry.collect", "telemetry.ingest", "telemetry.configure",
        "ingestion.preview", "ingestion.validate", "ingestion.commit", "ingestion.export",
        "quality.read", "quality.process",
        "workload.read", "workload.analyse",
        "models.read", "models.train", "models.retrain",
        "forecasts.read", "forecasts.generate", "forecasts.export",
        "risk.read", "risk.evaluate", "risk.configure",
        "performance.read", "performance.configure",
        "alerts.read", "alerts.acknowledge", "alerts.assign", "alerts.resolve", "alerts.reopen",
        "digital_twin.read", "digital_twin.create", "digital_twin.update", "digital_twin.delete",
        "digital_twin.execute", "digital_twin.export",
        "optimisation.read", "optimisation.execute",
        "recommendations.read", "recommendations.review",
        "approvals.read", "approvals.submit", "approvals.approve", "approvals.reject",
        "reports.read", "reports.generate", "reports.export",
        "integrations.read",
        "audit.read",
        "org.read",
        "topology.read", "topology.write",
        "services.read", "services.write",
        "slo.read", "slo.manage",
        "incidents.read", "incidents.write",
        "finops.read", "finops.write",
        "procurement.propose",
        "backup.read", "backup.manage",
        "governance.read",
        "decisions.verify",
        "control_plane.read",
        "control_plane.actions.create",
    ],
    ROLE_VIEWER: [
        "storage.read",
        "telemetry.read",
        "quality.read",
        "workload.read",
        "models.read",
        "forecasts.read",
        "risk.read",
        "performance.read",
        "alerts.read",
        "digital_twin.read",
        "optimisation.read",
        "recommendations.read",
        "approvals.read",
        "reports.read",
        "reports.export",
        "org.read",
        "topology.read",
        "services.read",
        "slo.read",
        "incidents.read",
        "finops.read",
        "backup.read",
        "governance.read",
        "control_plane.read",
    ],
    ROLE_AUDITOR: [
        "storage.read",
        "telemetry.read",
        "quality.read",
        "workload.read",
        "models.read",
        "forecasts.read",
        "risk.read",
        "performance.read",
        "alerts.read",
        "digital_twin.read",
        "recommendations.read",
        "approvals.read",
        "reports.read", "reports.export",
        "audit.read", "audit.export",
        "org.read",
        "topology.read",
        "services.read",
        "slo.read",
        "incidents.read",
        "finops.read",
        "backup.read",
        "governance.read",
        "control_plane.read",
    ],
}

ROLE_DESCRIPTIONS: Dict[str, str] = {
    ROLE_ADMIN: "Full system administration, user & IAM governance, global policies, and all operational modules.",
    ROLE_OPERATOR: "Full day-to-day storage, telemetry, ingestion, ML training, forecasting, risk, Digital Twin, alert, and reporting operations without IAM or security policy authority.",
    ROLE_VIEWER: "Read-only access across dashboards, storage, telemetry, forecasts, alerts, Digital Twin views, and permitted reports.",
    ROLE_AUDITOR: "Read-only compliance & cryptographic audit verification access.",
}


def seed_roles_and_permissions(db: Session) -> None:
    """Idempotently seeds canonical roles, permissions, and default role-permission mappings."""
    for role_name in ALL_ROLES:
        if not db.query(Role).filter(Role.name == role_name).first():
            db.add(Role(name=role_name, description=ROLE_DESCRIPTIONS.get(role_name, ""), is_system=True))

    existing_perms = {p.key for p in db.query(Permission).all()}
    for item in PERMISSION_CATALOG:
        if item["key"] not in existing_perms:
            db.add(Permission(key=item["key"], module=item["module"], description=item["description"]))
    db.flush()

    existing_rp = {(rp.role_name, rp.permission_key) for rp in db.query(RolePermission).all()}
    for role_name, allowed_list in DEFAULT_ROLE_PERMISSIONS.items():
        allowed_set = set(allowed_list)
        for perm_key in ALL_PERMISSION_KEYS:
            if (role_name, perm_key) not in existing_rp:
                db.add(RolePermission(
                    id=f"rp-{role_name.lower()}-{perm_key.replace('.', '_')}",
                    role_name=role_name,
                    permission_key=perm_key,
                    is_allowed=(perm_key in allowed_set),
                ))
    db.commit()


def get_effective_permissions(db: Session, role_name: str) -> List[str]:
    """Resolves active permissions dynamically from DB RolePermission table (with safe fallback if unseeded)."""
    rows = (
        db.query(RolePermission)
        .filter(RolePermission.role_name == role_name, RolePermission.is_allowed == True)
        .all()
    )
    if rows:
        return sorted({r.permission_key for r in rows})
    if db.query(RolePermission).filter(RolePermission.role_name == role_name).count() > 0:
        return []
    return sorted(DEFAULT_ROLE_PERMISSIONS.get(role_name, []))


def has_permission(db: Session, user: User, permission_key: str) -> bool:
    if not user or not getattr(user, "is_active", False):
        return False
    allowed: Set[str] = set(get_effective_permissions(db, user.role))
    return permission_key in allowed


def require_permission(permission_key: str):
    """Central FastAPI dependency enforcing authenticated permission checks from persisted DB mappings."""
    from app.auth.security import get_current_user

    def _checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not has_permission(db, current_user, permission_key):
            try:
                AuditService.log_event(
                    db=db,
                    action="ACCESS_DENIED",
                    target_type="PERMISSION",
                    target_id=permission_key,
                    user=current_user.username,
                    user_id=current_user.id,
                    user_role=current_user.role,
                    outcome="DENIED",
                    client_ip=request.client.host if request.client else "127.0.0.1",
                    details={"path": str(request.url.path), "method": request.method, "required_permission": permission_key},
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires '{permission_key}' (current role: {current_user.role})",
            )
        return current_user

    return _checker


def require_method_permission(read_key: str, write_key: str):
    """Router-level dependency checking read_key for GET/HEAD/OPTIONS and write_key for mutations."""
    from app.auth.security import get_current_user

    def _checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        perm_key = read_key if request.method in ("GET", "HEAD", "OPTIONS") else write_key
        if not has_permission(db, current_user, perm_key):
            try:
                AuditService.log_event(
                    db=db,
                    action="ACCESS_DENIED",
                    target_type="PERMISSION",
                    target_id=perm_key,
                    user=current_user.username,
                    user_id=current_user.id,
                    user_role=current_user.role,
                    outcome="DENIED",
                    client_ip=request.client.host if request.client else "127.0.0.1",
                    details={"path": str(request.url.path), "method": request.method, "required_permission": perm_key},
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires '{perm_key}' (current role: {current_user.role})",
            )
        return current_user

    return _checker
