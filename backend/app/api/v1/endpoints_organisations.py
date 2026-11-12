import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.auth.security import get_current_user
from app.auth.tenant import assert_org_resource, resolve_organization_id
from app.database import get_db
from app.models.entities import Device, User
from app.models.enterprise_entities import (
    BusinessUnit,
    Environment,
    Organisation,
    OrganisationMember,
    Region,
    ResourceAssignment,
    Site,
    StorageCluster,
    StorageHost,
    StoragePoolEntity,
    StorageVolume,
)
from app.realtime.event_bus import OutboxService
from app.services.audit_service import AuditService

router = APIRouter()


class OrgCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    slug: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    plan: str = "ENTERPRISE"
    default_currency: str = "USD"


class MemberAddRequest(BaseModel):
    user_id: str
    role: str = "OPERATOR"
    department: str = "Platform Engineering"
    cost_centre: str = "CC-INFRA-01"


class MemberUpdateRequest(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None
    department: Optional[str] = None
    cost_centre: Optional[str] = None


class BusinessUnitRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    code: str = Field(..., min_length=2, max_length=32)
    cost_centre: str = "CC-DEFAULT"
    owner_user_id: Optional[str] = None


class RegionRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    code: str = Field(..., min_length=2, max_length=32)
    residency_zone: str = "GLOBAL"


class SiteRequest(BaseModel):
    business_unit_id: Optional[str] = None
    region_id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=128)
    site_code: str = Field(..., min_length=2, max_length=32)
    address: str = ""
    tier_class: str = "PRIMARY"


class EnvironmentRequest(BaseModel):
    site_id: str
    name: str = Field(..., min_length=2, max_length=64)
    env_type: str = "PRODUCTION"


class ClusterRequest(BaseModel):
    site_id: str
    environment_id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=128)
    vendor: str = "Enterprise SAN"
    cluster_type: str = "BLOCK"


class HostRequest(BaseModel):
    cluster_id: str
    hostname: str = Field(..., min_length=2, max_length=128)
    os_family: str = "Linux"


class PoolRequest(BaseModel):
    cluster_id: str
    host_id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=128)
    tier: str = "NVME_TIER1"
    total_capacity_bytes: int = 0
    used_bytes: int = 0


class VolumeRequest(BaseModel):
    pool_id: str
    device_id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=128)
    total_capacity_bytes: int = 0
    used_bytes: int = 0
    department: str = "Core Infrastructure"
    cost_centre: str = "CC-STORAGE"


class ResourceAssignmentRequest(BaseModel):
    resource_type: str = Field(..., min_length=2, max_length=32)
    resource_id: str = Field(..., min_length=1, max_length=64)
    assigned_to_user_id: str
    department: str = "Operations"
    cost_centre: str = "CC-OPS"


def _serialize_org(o: Organisation) -> dict:
    return {
        "id": o.id,
        "name": o.name,
        "slug": o.slug,
        "plan": o.plan,
        "default_currency": o.default_currency,
        "status": o.status,
        "version": o.version,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


@router.get("/organisations")
def list_organisations(
    current_user: User = Depends(require_permission("org.read")),
    db: Session = Depends(get_db),
):
    if current_user.role == "ADMIN":
        orgs = db.query(Organisation).order_by(Organisation.created_at.asc()).all()
    else:
        memberships = (
            db.query(OrganisationMember)
            .filter(
                OrganisationMember.user_id == current_user.id,
                OrganisationMember.status == "ACTIVE",
            )
            .all()
        )
        org_ids = {m.organization_id for m in memberships}
        if current_user.organization_id:
            org_ids.add(current_user.organization_id)
        orgs = (
            db.query(Organisation)
            .filter(Organisation.id.in_(list(org_ids)))
            .order_by(Organisation.created_at.asc())
            .all()
        )
    return {
        "active_organization_id": current_user.organization_id or "org-primary-enterprise",
        "organisations": [_serialize_org(o) for o in orgs],
    }


@router.post("/organisations", status_code=status.HTTP_201_CREATED)
def create_organisation(
    payload: OrgCreateRequest,
    current_user: User = Depends(require_permission("org.manage")),
    db: Session = Depends(get_db),
):
    existing = db.query(Organisation).filter(Organisation.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Organisation slug '{payload.slug}' already exists.")
    org = Organisation(
        id=f"org-{uuid.uuid4().hex[:10]}",
        name=payload.name.strip(),
        slug=payload.slug.strip(),
        plan=payload.plan.strip().upper(),
        default_currency=payload.default_currency.strip().upper(),
        status="ACTIVE",
    )
    db.add(org)
    db.add(
        OrganisationMember(
            id=f"mem-{uuid.uuid4().hex[:10]}",
            organization_id=org.id,
            user_id=current_user.id,
            role="ADMIN",
            status="ACTIVE",
            invited_by=current_user.username,
        )
    )
    AuditService.log_event(
        db=db,
        action="ORG_CREATED",
        target_type="Organisation",
        target_id=org.id,
        user=current_user.username,
        details={"message": f"Created organisation {org.name} ({org.slug})"},
        organization_id=org.id,
    )
    OutboxService.emit_and_commit(
        db=db,
        event_type="organisation.created",
        resource_type="Organisation",
        resource_id=org.id,
        actor_user=current_user,
        organization_id=org.id,
        payload=_serialize_org(org),
        required_permission="org.read",
    )
    return _serialize_org(org)


@router.post("/organisations/{org_id}/switch")
def switch_active_organisation(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    if current_user.role != "ADMIN":
        member = (
            db.query(OrganisationMember)
            .filter(
                OrganisationMember.organization_id == org_id,
                OrganisationMember.user_id == current_user.id,
                OrganisationMember.status == "ACTIVE",
            )
            .first()
        )
        if not member:
            raise HTTPException(status_code=403, detail="Not an active member of target organisation.")
    current_user.organization_id = org.id
    AuditService.log_event(
        db=db,
        action="ORG_SWITCHED",
        target_type="User",
        target_id=current_user.id,
        user=current_user.username,
        details={"message": f"Switched active organisation to {org.id}"},
        organization_id=org.id,
    )
    db.commit()
    return {"active_organization_id": org.id, "organisation": _serialize_org(org)}


@router.get("/organisations/{org_id}/members")
def list_org_members(
    org_id: str,
    current_user: User = Depends(require_permission("org.read")),
    active_org: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    if current_user.role != "ADMIN" and org_id != active_org:
        raise HTTPException(status_code=403, detail="Cross-tenant member inspection denied.")
    rows = (
        db.query(OrganisationMember, User)
        .join(User, User.id == OrganisationMember.user_id)
        .filter(OrganisationMember.organization_id == org_id)
        .all()
    )
    return {
        "organization_id": org_id,
        "members": [
            {
                "id": m.id,
                "user_id": u.id,
                "username": u.username,
                "email": u.email,
                "role": m.role,
                "department": m.department,
                "cost_centre": m.cost_centre,
                "status": m.status,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            }
            for m, u in rows
        ],
    }


@router.post("/organisations/{org_id}/members", status_code=status.HTTP_201_CREATED)
def add_org_member(
    org_id: str,
    payload: MemberAddRequest,
    current_user: User = Depends(require_permission("org.manage")),
    db: Session = Depends(get_db),
):
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    existing = (
        db.query(OrganisationMember)
        .filter(
            OrganisationMember.organization_id == org_id,
            OrganisationMember.user_id == payload.user_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member of this organisation.")
    member = OrganisationMember(
        id=f"mem-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        user_id=payload.user_id,
        role=payload.role.upper(),
        department=payload.department,
        cost_centre=payload.cost_centre,
        status="ACTIVE",
        invited_by=current_user.username,
    )
    db.add(member)
    AuditService.log_event(
        db=db,
        action="ORG_MEMBER_ADDED",
        target_type="OrganisationMember",
        target_id=member.id,
        user=current_user.username,
        details={"message": f"Added user {user.username} to {org_id} as {member.role}"},
        organization_id=org_id,
    )
    db.commit()
    return {
        "id": member.id,
        "organization_id": member.organization_id,
        "user_id": member.user_id,
        "role": member.role,
        "status": member.status,
    }


@router.patch("/organisations/{org_id}/members/{member_id}")
def update_org_member(
    org_id: str,
    member_id: str,
    payload: MemberUpdateRequest,
    current_user: User = Depends(require_permission("org.manage")),
    db: Session = Depends(get_db),
):
    member = (
        db.query(OrganisationMember)
        .filter(
            OrganisationMember.id == member_id,
            OrganisationMember.organization_id == org_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Organisation member not found.")
    if payload.role is not None:
        member.role = payload.role.upper()
    if payload.status is not None:
        member.status = payload.status.upper()
    if payload.department is not None:
        member.department = payload.department
    if payload.cost_centre is not None:
        member.cost_centre = payload.cost_centre
    AuditService.log_event(
        db=db,
        action="ORG_MEMBER_UPDATED",
        target_type="OrganisationMember",
        target_id=member.id,
        user=current_user.username,
        details={"message": f"Updated member {member.id} ({member.role}/{member.status})"},
        organization_id=org_id,
    )
    db.commit()
    return {
        "id": member.id,
        "organization_id": member.organization_id,
        "user_id": member.user_id,
        "role": member.role,
        "status": member.status,
        "department": member.department,
        "cost_centre": member.cost_centre,
    }


@router.get("/hierarchy/overview")
def get_hierarchy_overview(
    current_user: User = Depends(require_permission("org.read")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    return {
        "organization_id": org_id,
        "business_units": [
            {"id": x.id, "name": x.name, "code": x.code, "cost_centre": x.cost_centre, "owner_user_id": x.owner_user_id}
            for x in db.query(BusinessUnit).filter(BusinessUnit.organization_id == org_id).all()
        ],
        "regions": [
            {"id": x.id, "name": x.name, "code": x.code, "residency_zone": x.residency_zone}
            for x in db.query(Region).filter(Region.organization_id == org_id).all()
        ],
        "sites": [
            {"id": x.id, "region_id": x.region_id, "business_unit_id": x.business_unit_id, "name": x.name, "site_code": x.site_code, "tier_class": x.tier_class}
            for x in db.query(Site).filter(Site.organization_id == org_id).all()
        ],
        "environments": [
            {"id": x.id, "site_id": x.site_id, "name": x.name, "env_type": x.env_type}
            for x in db.query(Environment).filter(Environment.organization_id == org_id).all()
        ],
        "clusters": [
            {
                "id": x.id, "site_id": x.site_id, "environment_id": x.environment_id, "name": x.name,
                "vendor": x.vendor, "cluster_type": x.cluster_type, "status": x.status,
            }
            for x in db.query(StorageCluster).filter(StorageCluster.organization_id == org_id).all()
        ],
        "hosts": [
            {"id": x.id, "cluster_id": x.cluster_id, "hostname": x.hostname, "os_family": x.os_family, "status": x.status}
            for x in db.query(StorageHost).filter(StorageHost.organization_id == org_id).all()
        ],
        "pools": [
            {
                "id": x.id, "cluster_id": x.cluster_id, "host_id": x.host_id, "name": x.name, "tier": x.tier,
                "total_capacity_bytes": x.total_capacity_bytes, "used_bytes": x.used_bytes, "status": x.status,
            }
            for x in db.query(StoragePoolEntity).filter(StoragePoolEntity.organization_id == org_id).all()
        ],
        "volumes": [
            {
                "id": x.id, "pool_id": x.pool_id, "device_id": x.device_id, "name": x.name,
                "total_capacity_bytes": x.total_capacity_bytes, "used_bytes": x.used_bytes, "status": x.status,
                "department": x.department, "cost_centre": x.cost_centre,
            }
            for x in db.query(StorageVolume).filter(StorageVolume.organization_id == org_id).all()
        ],
        "assignments": [
            {
                "id": x.id, "resource_type": x.resource_type, "resource_id": x.resource_id,
                "assigned_to_user_id": x.assigned_to_user_id, "department": x.department, "cost_centre": x.cost_centre,
            }
            for x in db.query(ResourceAssignment).filter(ResourceAssignment.organization_id == org_id).all()
        ],
    }


@router.post("/hierarchy/business-units", status_code=status.HTTP_201_CREATED)
def create_business_unit(
    payload: BusinessUnitRequest,
    current_user: User = Depends(require_permission("org.manage")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    bu = BusinessUnit(
        id=f"bu-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        name=payload.name.strip(),
        code=payload.code.strip().upper(),
        cost_centre=payload.cost_centre.strip(),
        owner_user_id=payload.owner_user_id,
    )
    db.add(bu)
    OutboxService.emit_and_commit(
        db=db,
        event_type="hierarchy.updated",
        resource_type="BusinessUnit",
        resource_id=bu.id,
        actor_user=current_user,
        organization_id=org_id,
        payload={"entity": "business_unit", "id": bu.id, "name": bu.name},
        required_permission="org.read",
    )
    return {"id": bu.id, "organization_id": org_id, "name": bu.name, "code": bu.code, "cost_centre": bu.cost_centre}


@router.post("/hierarchy/regions", status_code=status.HTTP_201_CREATED)
def create_region(
    payload: RegionRequest,
    current_user: User = Depends(require_permission("org.manage")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    r = Region(
        id=f"reg-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        name=payload.name.strip(),
        code=payload.code.strip().upper(),
        residency_zone=payload.residency_zone.strip().upper(),
    )
    db.add(r)
    OutboxService.emit_and_commit(
        db=db, event_type="hierarchy.updated", resource_type="Region", resource_id=r.id,
        actor_user=current_user, organization_id=org_id, payload={"entity": "region", "id": r.id, "name": r.name},
        required_permission="org.read",
    )
    return {"id": r.id, "organization_id": org_id, "name": r.name, "code": r.code, "residency_zone": r.residency_zone}


@router.post("/hierarchy/sites", status_code=status.HTTP_201_CREATED)
def create_site(
    payload: SiteRequest,
    current_user: User = Depends(require_permission("org.manage")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    if payload.region_id:
        assert_org_resource(db.query(Region).filter(Region.id == payload.region_id).first(), org_id, "Region")
    if payload.business_unit_id:
        assert_org_resource(db.query(BusinessUnit).filter(BusinessUnit.id == payload.business_unit_id).first(), org_id, "BusinessUnit")
    s = Site(
        id=f"site-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        business_unit_id=payload.business_unit_id,
        region_id=payload.region_id,
        name=payload.name.strip(),
        site_code=payload.site_code.strip().upper(),
        address=payload.address,
        tier_class=payload.tier_class.upper(),
    )
    db.add(s)
    OutboxService.emit_and_commit(
        db=db, event_type="hierarchy.updated", resource_type="Site", resource_id=s.id,
        actor_user=current_user, organization_id=org_id, payload={"entity": "site", "id": s.id, "name": s.name},
        required_permission="org.read",
    )
    return {"id": s.id, "organization_id": org_id, "name": s.name, "site_code": s.site_code, "region_id": s.region_id}


@router.post("/hierarchy/environments", status_code=status.HTTP_201_CREATED)
def create_environment(
    payload: EnvironmentRequest,
    current_user: User = Depends(require_permission("org.manage")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    assert_org_resource(db.query(Site).filter(Site.id == payload.site_id).first(), org_id, "Site")
    e = Environment(
        id=f"env-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        site_id=payload.site_id,
        name=payload.name.strip(),
        env_type=payload.env_type.upper(),
    )
    db.add(e)
    OutboxService.emit_and_commit(
        db=db, event_type="hierarchy.updated", resource_type="Environment", resource_id=e.id,
        actor_user=current_user, organization_id=org_id, payload={"entity": "environment", "id": e.id, "name": e.name},
        required_permission="org.read",
    )
    return {"id": e.id, "organization_id": org_id, "site_id": e.site_id, "name": e.name, "env_type": e.env_type}


@router.post("/hierarchy/clusters", status_code=status.HTTP_201_CREATED)
def create_cluster(
    payload: ClusterRequest,
    current_user: User = Depends(require_permission("storage.create")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    assert_org_resource(db.query(Site).filter(Site.id == payload.site_id).first(), org_id, "Site")
    if payload.environment_id:
        assert_org_resource(db.query(Environment).filter(Environment.id == payload.environment_id).first(), org_id, "Environment")
    c = StorageCluster(
        id=f"clu-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        site_id=payload.site_id,
        environment_id=payload.environment_id,
        name=payload.name.strip(),
        vendor=payload.vendor,
        cluster_type=payload.cluster_type,
    )
    db.add(c)
    OutboxService.emit_and_commit(
        db=db, event_type="hierarchy.updated", resource_type="StorageCluster", resource_id=c.id,
        actor_user=current_user, organization_id=org_id, payload={"entity": "cluster", "id": c.id, "name": c.name},
        required_permission="org.read",
    )
    return {"id": c.id, "organization_id": org_id, "name": c.name, "cluster_type": c.cluster_type}


@router.post("/hierarchy/hosts", status_code=status.HTTP_201_CREATED)
def create_host(
    payload: HostRequest,
    current_user: User = Depends(require_permission("storage.create")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    assert_org_resource(db.query(StorageCluster).filter(StorageCluster.id == payload.cluster_id).first(), org_id, "StorageCluster")
    h = StorageHost(
        id=f"host-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        cluster_id=payload.cluster_id,
        hostname=payload.hostname.strip(),
        os_family=payload.os_family,
    )
    db.add(h)
    OutboxService.emit_and_commit(
        db=db, event_type="hierarchy.updated", resource_type="StorageHost", resource_id=h.id,
        actor_user=current_user, organization_id=org_id, payload={"entity": "host", "id": h.id, "hostname": h.hostname},
        required_permission="org.read",
    )
    return {"id": h.id, "organization_id": org_id, "hostname": h.hostname, "cluster_id": h.cluster_id}


@router.post("/hierarchy/pools", status_code=status.HTTP_201_CREATED)
def create_pool(
    payload: PoolRequest,
    current_user: User = Depends(require_permission("storage.create")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    assert_org_resource(db.query(StorageCluster).filter(StorageCluster.id == payload.cluster_id).first(), org_id, "StorageCluster")
    if payload.host_id:
        assert_org_resource(db.query(StorageHost).filter(StorageHost.id == payload.host_id).first(), org_id, "StorageHost")
    p = StoragePoolEntity(
        id=f"pool-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        cluster_id=payload.cluster_id,
        host_id=payload.host_id,
        name=payload.name.strip(),
        tier=payload.tier.upper(),
        total_capacity_bytes=payload.total_capacity_bytes,
        used_bytes=payload.used_bytes,
    )
    db.add(p)
    OutboxService.emit_and_commit(
        db=db, event_type="hierarchy.updated", resource_type="StoragePool", resource_id=p.id,
        actor_user=current_user, organization_id=org_id, payload={"entity": "pool", "id": p.id, "name": p.name},
        required_permission="org.read",
    )
    return {"id": p.id, "organization_id": org_id, "name": p.name, "tier": p.tier}


@router.post("/hierarchy/volumes", status_code=status.HTTP_201_CREATED)
def create_volume(
    payload: VolumeRequest,
    current_user: User = Depends(require_permission("storage.create")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    assert_org_resource(db.query(StoragePoolEntity).filter(StoragePoolEntity.id == payload.pool_id).first(), org_id, "StoragePool")
    if payload.device_id:
        assert_org_resource(db.query(Device).filter(Device.id == payload.device_id).first(), org_id, "Device")
    v = StorageVolume(
        id=f"vol-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        pool_id=payload.pool_id,
        device_id=payload.device_id,
        name=payload.name.strip(),
        total_capacity_bytes=payload.total_capacity_bytes,
        used_bytes=payload.used_bytes,
        department=payload.department,
        cost_centre=payload.cost_centre,
        owner_user_id=current_user.id,
    )
    db.add(v)
    OutboxService.emit_and_commit(
        db=db, event_type="hierarchy.updated", resource_type="StorageVolume", resource_id=v.id,
        actor_user=current_user, organization_id=org_id, payload={"entity": "volume", "id": v.id, "name": v.name},
        required_permission="org.read",
    )
    return {"id": v.id, "organization_id": org_id, "name": v.name, "pool_id": v.pool_id, "device_id": v.device_id}


@router.post("/hierarchy/assignments", status_code=status.HTTP_201_CREATED)
def create_resource_assignment(
    payload: ResourceAssignmentRequest,
    current_user: User = Depends(require_permission("org.manage")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    a = ResourceAssignment(
        id=f"asg-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        resource_type=payload.resource_type.upper(),
        resource_id=payload.resource_id,
        assigned_to_user_id=payload.assigned_to_user_id,
        department=payload.department,
        cost_centre=payload.cost_centre,
        assigned_by=current_user.username,
    )
    db.add(a)
    OutboxService.emit_and_commit(
        db=db, event_type="hierarchy.updated", resource_type="ResourceAssignment", resource_id=a.id,
        actor_user=current_user, organization_id=org_id, payload={"entity": "assignment", "id": a.id, "resource_id": a.resource_id},
        required_permission="org.read",
    )
    return {"id": a.id, "organization_id": org_id, "resource_type": a.resource_type, "resource_id": a.resource_id}
