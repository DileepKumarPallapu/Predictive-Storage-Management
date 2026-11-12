import json
import uuid
from collections import deque
from typing import Dict, List, Optional, Set, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.auth.tenant import assert_org_resource, resolve_organization_id
from app.database import get_db
from app.models.entities import User
from app.models.enterprise_entities import (
    ApplicationDependency,
    ApplicationEntity,
    AssetRelationship,
    BusinessService,
    EnterpriseIncident,
    IncidentTimelineEvent,
    RelationshipHistory,
    ServiceResourceRelationship,
)
from app.realtime.event_bus import OutboxService

router = APIRouter()


class RelationshipCreateRequest(BaseModel):
    source_type: str = Field(..., min_length=2, max_length=48)
    source_id: str = Field(..., min_length=1, max_length=64)
    target_type: str = Field(..., min_length=2, max_length=48)
    target_id: str = Field(..., min_length=1, max_length=64)
    relationship_type: str = Field(..., min_length=2, max_length=48)
    discovery_source: str = "MANUAL"  # MANUAL | DISCOVERED
    verified: bool = True


class ApplicationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    criticality: str = "TIER_1"
    department: str = "Engineering"
    environment: str = "PRODUCTION"
    description: str = ""
    availability_objective_pct: float = 99.9


class BusinessServiceCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    department: str = "Business Operations"
    criticality: str = "MISSION_CRITICAL"  # MISSION_CRITICAL, HIGH, MEDIUM, LOW
    description: str = ""
    sla_target_pct: Optional[float] = None
    contractual_sla_supplied: bool = False


class ApplicationDependencyRequest(BaseModel):
    application_id: str
    depends_on_type: str  # DEVICE, VOLUME, CLUSTER, APPLICATION
    depends_on_id: str
    dependency_role: str = "PRIMARY_STORAGE"
    discovery_source: str = "MANUAL"


class ServiceResourceMapRequest(BaseModel):
    service_id: str
    resource_type: str  # APPLICATION, DEVICE, VOLUME, CLUSTER
    resource_id: str
    impact_weight: float = 1.0


class ImpactEvaluateRequest(BaseModel):
    create_incident: bool = False
    trigger_reason: str = "Verified storage capacity/performance risk impacting dependent services"


def _has_directed_path(adjacency: Dict[Tuple[str, str], List[Tuple[str, str]]], start: Tuple[str, str], goal: Tuple[str, str]) -> bool:
    visited: Set[Tuple[str, str]] = set()
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node == goal:
            return True
        if node in visited:
            continue
        visited.add(node)
        for nxt in adjacency.get(node, []):
            if nxt not in visited:
                queue.append(nxt)
    return False


@router.get("/topology/relationships")
def list_topology_relationships(
    current_user: User = Depends(require_permission("topology.read")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    rels = db.query(AssetRelationship).filter(AssetRelationship.organization_id == org_id).all()
    history = (
        db.query(RelationshipHistory)
        .filter(RelationshipHistory.organization_id == org_id)
        .order_by(RelationshipHistory.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "organization_id": org_id,
        "relationships": [
            {
                "id": r.id,
                "source_type": r.source_type,
                "source_id": r.source_id,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "relationship_type": r.relationship_type,
                "discovery_source": r.discovery_source,
                "verified": r.verified,
                "created_by": r.created_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rels
        ],
        "history": [
            {
                "id": h.id,
                "relationship_id": h.relationship_id,
                "action": h.action,
                "actor": h.actor,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in history
        ],
    }


@router.post("/topology/relationships", status_code=status.HTTP_201_CREATED)
def create_topology_relationship(
    payload: RelationshipCreateRequest,
    current_user: User = Depends(require_permission("topology.write")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    src = (payload.source_type.upper(), payload.source_id.strip())
    tgt = (payload.target_type.upper(), payload.target_id.strip())
    rel_type = payload.relationship_type.upper()

    if src == tgt:
        raise HTTPException(status_code=422, detail="Self-referential asset relationship is not allowed.")

    existing_rels = db.query(AssetRelationship).filter(AssetRelationship.organization_id == org_id).all()
    adjacency: Dict[Tuple[str, str], List[Tuple[str, str]]] = {}
    for r in existing_rels:
        if (
            r.source_type == src[0]
            and r.source_id == src[1]
            and r.target_type == tgt[0]
            and r.target_id == tgt[1]
            and r.relationship_type == rel_type
        ):
            raise HTTPException(status_code=409, detail="Duplicate asset relationship already exists.")
        adjacency.setdefault((r.source_type, r.source_id), []).append((r.target_type, r.target_id))

    if _has_directed_path(adjacency, tgt, src):
        raise HTTPException(
            status_code=422,
            detail=f"Cycle detected: adding {src[0]}:{src[1]} -> {tgt[0]}:{tgt[1]} would create a circular topology dependency.",
        )

    rel = AssetRelationship(
        id=f"rel-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        source_type=src[0],
        source_id=src[1],
        target_type=tgt[0],
        target_id=tgt[1],
        relationship_type=rel_type,
        discovery_source=payload.discovery_source.upper(),
        verified=payload.verified,
        created_by=current_user.username,
    )
    db.add(rel)
    db.add(
        RelationshipHistory(
            id=f"rh-{uuid.uuid4().hex[:10]}",
            organization_id=org_id,
            relationship_id=rel.id,
            action="CREATED",
            actor=current_user.username,
            details_json=json.dumps({"source": src, "target": tgt, "type": rel_type}),
        )
    )
    OutboxService.emit_and_commit(
        db=db,
        event_type="topology.updated",
        resource_type="AssetRelationship",
        resource_id=rel.id,
        actor_user=current_user,
        organization_id=org_id,
        payload={"id": rel.id, "source_id": rel.source_id, "target_id": rel.target_id, "relationship_type": rel.relationship_type},
        required_permission="topology.read",
    )
    return {
        "id": rel.id,
        "organization_id": org_id,
        "source_type": rel.source_type,
        "source_id": rel.source_id,
        "target_type": rel.target_type,
        "target_id": rel.target_id,
        "relationship_type": rel.relationship_type,
        "discovery_source": rel.discovery_source,
    }


@router.delete("/topology/relationships/{rel_id}")
def delete_topology_relationship(
    rel_id: str,
    current_user: User = Depends(require_permission("topology.write")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    rel = assert_org_resource(db.query(AssetRelationship).filter(AssetRelationship.id == rel_id).first(), org_id, "AssetRelationship")
    db.add(
        RelationshipHistory(
            id=f"rh-{uuid.uuid4().hex[:10]}",
            organization_id=org_id,
            relationship_id=rel.id,
            action="DELETED",
            actor=current_user.username,
            details_json=json.dumps({"source_id": rel.source_id, "target_id": rel.target_id, "type": rel.relationship_type}),
        )
    )
    db.delete(rel)
    OutboxService.emit_and_commit(
        db=db,
        event_type="topology.updated",
        resource_type="AssetRelationship",
        resource_id=rel_id,
        actor_user=current_user,
        organization_id=org_id,
        payload={"deleted": True, "id": rel_id},
        required_permission="topology.read",
    )
    return {"deleted": True, "id": rel_id}


@router.get("/services/overview")
def list_services_overview(
    current_user: User = Depends(require_permission("services.read")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    apps = db.query(ApplicationEntity).filter(ApplicationEntity.organization_id == org_id).all()
    svcs = db.query(BusinessService).filter(BusinessService.organization_id == org_id).all()
    deps = db.query(ApplicationDependency).filter(ApplicationDependency.organization_id == org_id).all()
    maps = db.query(ServiceResourceRelationship).filter(ServiceResourceRelationship.organization_id == org_id).all()
    return {
        "organization_id": org_id,
        "applications": [
            {
                "id": a.id, "name": a.name, "criticality": a.criticality, "department": a.department,
                "environment": a.environment, "description": a.description, "availability_objective_pct": a.availability_objective_pct,
            }
            for a in apps
        ],
        "business_services": [
            {
                "id": s.id, "name": s.name, "department": s.department, "criticality": s.criticality,
                "sla_target_pct": s.sla_target_pct, "contractual_sla_supplied": s.contractual_sla_supplied,
            }
            for s in svcs
        ],
        "dependencies": [
            {
                "id": d.id, "application_id": d.application_id, "depends_on_type": d.depends_on_type,
                "depends_on_id": d.depends_on_id, "dependency_role": d.dependency_role,
            }
            for d in deps
        ],
        "resource_mappings": [
            {
                "id": m.id, "service_id": m.service_id, "resource_type": m.resource_type,
                "resource_id": m.resource_id, "impact_weight": m.impact_weight,
            }
            for m in maps
        ],
    }


@router.post("/services/applications", status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreateRequest,
    current_user: User = Depends(require_permission("services.write")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    app = ApplicationEntity(
        id=f"app-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        name=payload.name.strip(),
        owner_user_id=current_user.id,
        criticality=payload.criticality.upper(),
        department=payload.department,
        environment=payload.environment.upper(),
        description=payload.description,
        availability_objective_pct=payload.availability_objective_pct,
    )
    db.add(app)
    OutboxService.emit_and_commit(
        db=db, event_type="services.updated", resource_type="Application", resource_id=app.id,
        actor_user=current_user, organization_id=org_id, payload={"id": app.id, "name": app.name},
        required_permission="services.read",
    )
    return {"id": app.id, "organization_id": org_id, "name": app.name, "criticality": app.criticality}


@router.post("/services/business-services", status_code=status.HTTP_201_CREATED)
def create_business_service(
    payload: BusinessServiceCreateRequest,
    current_user: User = Depends(require_permission("services.write")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    svc = BusinessService(
        id=f"svc-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        name=payload.name.strip(),
        owner_user_id=current_user.id,
        department=payload.department,
        criticality=payload.criticality.upper(),
        description=payload.description,
        sla_target_pct=payload.sla_target_pct,
        contractual_sla_supplied=payload.contractual_sla_supplied,
    )
    db.add(svc)
    OutboxService.emit_and_commit(
        db=db, event_type="services.updated", resource_type="BusinessService", resource_id=svc.id,
        actor_user=current_user, organization_id=org_id, payload={"id": svc.id, "name": svc.name, "criticality": svc.criticality},
        required_permission="services.read",
    )
    return {"id": svc.id, "organization_id": org_id, "name": svc.name, "criticality": svc.criticality}


@router.post("/services/dependencies", status_code=status.HTTP_201_CREATED)
def create_application_dependency(
    payload: ApplicationDependencyRequest,
    current_user: User = Depends(require_permission("services.write")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    assert_org_resource(db.query(ApplicationEntity).filter(ApplicationEntity.id == payload.application_id).first(), org_id, "Application")
    if payload.depends_on_type.upper() == "APPLICATION" and payload.application_id == payload.depends_on_id:
        raise HTTPException(status_code=422, detail="Application cannot depend on itself.")

    deps = db.query(ApplicationDependency).filter(ApplicationDependency.organization_id == org_id).all()
    adj: Dict[Tuple[str, str], List[Tuple[str, str]]] = {}
    for d in deps:
        if d.depends_on_type == "APPLICATION":
            adj.setdefault(("APPLICATION", d.application_id), []).append(("APPLICATION", d.depends_on_id))
    if payload.depends_on_type.upper() == "APPLICATION" and _has_directed_path(adj, ("APPLICATION", payload.depends_on_id), ("APPLICATION", payload.application_id)):
        raise HTTPException(status_code=422, detail="Circular application dependency detected.")

    dep = ApplicationDependency(
        id=f"adep-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        application_id=payload.application_id,
        depends_on_type=payload.depends_on_type.upper(),
        depends_on_id=payload.depends_on_id.strip(),
        dependency_role=payload.dependency_role.upper(),
        discovery_source=payload.discovery_source.upper(),
    )
    db.add(dep)
    OutboxService.emit_and_commit(
        db=db, event_type="services.updated", resource_type="ApplicationDependency", resource_id=dep.id,
        actor_user=current_user, organization_id=org_id, payload={"id": dep.id},
        required_permission="services.read",
    )
    return {"id": dep.id, "organization_id": org_id, "application_id": dep.application_id, "depends_on_id": dep.depends_on_id}


@router.post("/services/resource-mappings", status_code=status.HTTP_201_CREATED)
def create_service_resource_mapping(
    payload: ServiceResourceMapRequest,
    current_user: User = Depends(require_permission("services.write")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    assert_org_resource(db.query(BusinessService).filter(BusinessService.id == payload.service_id).first(), org_id, "BusinessService")
    mapping = ServiceResourceRelationship(
        id=f"srm-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        service_id=payload.service_id,
        resource_type=payload.resource_type.upper(),
        resource_id=payload.resource_id.strip(),
        impact_weight=payload.impact_weight,
    )
    db.add(mapping)
    OutboxService.emit_and_commit(
        db=db, event_type="services.updated", resource_type="ServiceResourceRelationship", resource_id=mapping.id,
        actor_user=current_user, organization_id=org_id, payload={"id": mapping.id, "resource_id": mapping.resource_id},
        required_permission="services.read",
    )
    return {"id": mapping.id, "organization_id": org_id, "service_id": mapping.service_id, "resource_id": mapping.resource_id}


def compute_impact_for_resource(db: Session, org_id: str, resource_id: str) -> dict:
    """Deterministic BFS impact traversal across verified AssetRelationship, ApplicationDependency, and ServiceResourceRelationship edges."""
    rels = db.query(AssetRelationship).filter(AssetRelationship.organization_id == org_id).all()
    app_deps = db.query(ApplicationDependency).filter(ApplicationDependency.organization_id == org_id).all()
    mappings = db.query(ServiceResourceRelationship).filter(ServiceResourceRelationship.organization_id == org_id).all()
    apps = {a.id: a for a in db.query(ApplicationEntity).filter(ApplicationEntity.organization_id == org_id).all()}
    svcs = {s.id: s for s in db.query(BusinessService).filter(BusinessService.organization_id == org_id).all()}

    adj: Dict[str, List[Tuple[str, str]]] = {}
    for r in rels:
        adj.setdefault(r.source_id, []).append((r.target_id, r.relationship_type))

    visited_nodes: Set[str] = {resource_id}
    queue = deque([resource_id])
    traversed_edges: List[dict] = []
    while queue:
        curr = queue.popleft()
        for nxt, rel_type in adj.get(curr, []):
            traversed_edges.append({"from": curr, "to": nxt, "relationship": rel_type})
            if nxt not in visited_nodes:
                visited_nodes.add(nxt)
                queue.append(nxt)

    # Reverse-lookup applications depending on any visited infrastructure node, plus transitive app->app dependents
    impacted_app_ids: Set[str] = set()
    changed = True
    while changed:
        changed = False
        for d in app_deps:
            if (d.depends_on_id in visited_nodes or d.depends_on_id in impacted_app_ids) and d.application_id in apps:
                if d.application_id not in impacted_app_ids:
                    impacted_app_ids.add(d.application_id)
                    changed = True

    impacted_svc_ids: Set[str] = set()
    for m in mappings:
        if (m.resource_id in visited_nodes or m.resource_id in impacted_app_ids) and m.service_id in svcs:
            impacted_svc_ids.add(m.service_id)

    crit_rank = {"MISSION_CRITICAL": 4, "TIER_0_CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    highest_crit = "NONE"
    best_rank = 0
    for sid in impacted_svc_ids:
        c = svcs[sid].criticality
        if crit_rank.get(c, 1) > best_rank:
            best_rank = crit_rank.get(c, 1)
            highest_crit = c

    return {
        "organization_id": org_id,
        "root_resource_id": resource_id,
        "reachable_infrastructure_ids": sorted(list(visited_nodes)),
        "traversed_edges": traversed_edges,
        "impacted_applications": [
            {"id": apps[aid].id, "name": apps[aid].name, "criticality": apps[aid].criticality, "department": apps[aid].department}
            for aid in sorted(impacted_app_ids)
        ],
        "impacted_business_services": [
            {"id": svcs[sid].id, "name": svcs[sid].name, "criticality": svcs[sid].criticality}
            for sid in sorted(impacted_svc_ids)
        ],
        "highest_criticality": highest_crit,
        "impact_count": len(impacted_app_ids) + len(impacted_svc_ids),
    }


@router.get("/services/impact/{resource_id}")
def get_resource_impact(
    resource_id: str,
    current_user: User = Depends(require_permission("services.read")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    return compute_impact_for_resource(db, org_id, resource_id)


@router.post("/services/impact/{resource_id}/evaluate")
def evaluate_resource_impact(
    resource_id: str,
    payload: ImpactEvaluateRequest,
    current_user: User = Depends(require_permission("services.write")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    impact = compute_impact_for_resource(db, org_id, resource_id)
    created_incident_id = None
    if payload.create_incident and impact["impact_count"] > 0:
        sev = "SEV-1" if impact["highest_criticality"] in ("MISSION_CRITICAL", "TIER_0_CRITICAL") else ("SEV-2" if impact["highest_criticality"] == "HIGH" else "SEV-3")
        inc = EnterpriseIncident(
            id=f"inc-{uuid.uuid4().hex[:10]}",
            organization_id=org_id,
            title=f"Service Impact Detected on {resource_id} ({impact['highest_criticality']})",
            category="DEPENDENCY_IMPACT",
            severity=sev,
            status="OPEN",
            linked_service_id=impact["impacted_business_services"][0]["id"] if impact["impacted_business_services"] else None,
            severity_policy_reason=payload.trigger_reason,
            evidence_json=json.dumps(impact),
            created_by=current_user.username,
        )
        db.add(inc)
        db.add(
            IncidentTimelineEvent(
                id=f"ite-{uuid.uuid4().hex[:10]}",
                organization_id=org_id,
                incident_id=inc.id,
                event_type="DETECTED",
                actor_username=current_user.username,
                note=payload.trigger_reason,
            )
        )
        created_incident_id = inc.id
        OutboxService.emit_and_commit(
            db=db,
            event_type="incident.created",
            resource_type="EnterpriseIncident",
            resource_id=inc.id,
            actor_user=current_user,
            organization_id=org_id,
            payload={"id": inc.id, "severity": inc.severity, "title": inc.title},
            required_permission="incidents.read",
        )
    impact["created_incident_id"] = created_incident_id
    return impact
