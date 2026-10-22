from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid

from app.database import get_db
from app.models.entities import User
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_role
)

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str
    organization_id: str = "org-primary-enterprise"

class UserProfileResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    organization_id: str = "org-primary-enterprise"
    is_active: bool

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[str] = "OPERATOR"
    organization_id: Optional[str] = "org-primary-enterprise"

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates credentials and returns a cryptographic JWT bearer token with tenant context."""
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is currently inactive"
        )
    
    org_id = getattr(user, "organization_id", "org-primary-enterprise") or "org-primary-enterprise"
    token = create_access_token(data={
        "sub": user.username,
        "role": user.role,
        "user_id": user.id,
        "organization_id": org_id
    })
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        role=user.role,
        organization_id=org_id
    )

@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user profile, organization ID, and assigned resilience role."""
    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        organization_id=getattr(current_user, "organization_id", "org-primary-enterprise") or "org-primary-enterprise",
        is_active=current_user.is_active
    )


@router.post("/register", response_model=UserProfileResponse)
def register_user(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role(["ADMIN"]))
):
    """Registers a new administrative or operator user (Admin role required)."""
    existing = db.query(User).filter(
        (User.username == payload.username) | (User.email == payload.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is already registered"
        )
    
    role = payload.role if payload.role in ["ADMIN", "OPERATOR", "AUDITOR"] else "OPERATOR"
    org_id = payload.organization_id or getattr(admin_user, "organization_id", "org-primary-enterprise") or "org-primary-enterprise"
    new_user = User(
        id=f"usr-{uuid.uuid4().hex[:10]}",
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=role,
        organization_id=org_id,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserProfileResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        role=new_user.role,
        organization_id=new_user.organization_id,
        is_active=new_user.is_active
    )

@router.get("/permissions")
def get_current_user_permissions(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user's assigned role and active server-enforced permissions."""
    from app.auth.security import ROLE_PERMISSIONS
    permissions = ROLE_PERMISSIONS.get(current_user.role, [])
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "organization_id": getattr(current_user, "organization_id", "org-primary-enterprise") or "org-primary-enterprise",
        "permissions_count": len(permissions),
        "permissions": permissions,
        "enforcement_mode": "SERVER_ENFORCED_RBAC"
    }

@router.get("/audit/verify-chain")
def verify_audit_trail_tamper_chain(
    organization_id: Optional[str] = None,
    current_user: User = Depends(require_role(["ADMIN", "AUDITOR"])),
    db: Session = Depends(get_db)
):
    """
    Cryptographically verifies the immutable SHA-256 forward-linked Merkle chain of the audit trail.
    Enforces multi-tenant isolation and checks for unauthorized deletions or modifications.
    """
    from app.services.audit_service import AuditService
    target_org = organization_id if (current_user.role == "ADMIN" and organization_id) else getattr(current_user, "organization_id", "org-primary-enterprise")
    res = AuditService.verify_audit_chain(db, organization_id=target_org)
    return res

