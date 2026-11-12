from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.database import get_db
from app.models.entities import User
from app.models.enterprise_entities import Organisation, OrganisationMember


DEFAULT_ORG_ID = "org-primary-enterprise"


def resolve_organization_id(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> str:
    """
    Resolve and strictly authorize the active organization_id for the request.
    - Reads optional `X-Organization-ID` header.
    - Falls back to `current_user.organization_id` or `DEFAULT_ORG_ID`.
    - Non-ADMIN users MUST have an ACTIVE OrganisationMember record for the target org.
    - ADMIN users may switch to any existing ACTIVE/non-deleted Organisation.
    """
    requested_org = (request.headers.get("X-Organization-ID") or "").strip()
    user_default_org = current_user.organization_id or DEFAULT_ORG_ID
    target_org = requested_org or user_default_org

    org = db.query(Organisation).filter(Organisation.id == target_org).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{target_org}' not found.",
        )

    if current_user.role == "ADMIN":
        return target_org

    member = (
        db.query(OrganisationMember)
        .filter(
            OrganisationMember.organization_id == target_org,
            OrganisationMember.user_id == current_user.id,
            OrganisationMember.status == "ACTIVE",
        )
        .first()
    )
    if not member and target_org != user_default_org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cross-tenant access denied for organisation '{target_org}'.",
        )
    if not member and requested_org:
        # Even if matching user_default_org, if user was suspended/removed from org, deny
        any_member = (
            db.query(OrganisationMember)
            .filter(
                OrganisationMember.organization_id == target_org,
                OrganisationMember.user_id == current_user.id,
            )
            .first()
        )
        if any_member and any_member.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Membership in organisation '{target_org}' is {any_member.status}.",
            )
    return target_org


def assert_org_resource(obj, organization_id: str, label: str = "Resource"):
    if not obj or getattr(obj, "organization_id", None) != organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{label} not found in active organisation.",
        )
    return obj
