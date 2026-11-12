import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.permissions import (
    ALL_ROLES,
    PERMISSION_CATALOG,
    ROLE_ADMIN,
    ROLE_DESCRIPTIONS,
    ROLE_OPERATOR,
    ROLE_VIEWER,
    get_effective_permissions,
    require_permission,
    seed_roles_and_permissions,
)
from app.auth.security import (
    create_access_token,
    decode_access_token,
    get_current_user,
    hash_password,
    hash_token,
    revoke_all_user_sessions,
    revoke_token,
    security_scheme,
    verify_password,
)
from app.config import settings
from app.database import get_db
from app.models.entities import (
    AuditLog,
    LoginAttempt,
    PasswordResetToken,
    RolePermission,
    User,
    UserSession,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])
users_router = APIRouter(prefix="/users", tags=["User Management"])
permissions_router = APIRouter(prefix="/permissions", tags=["Permissions Engine"])

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15


def _landing_route_for_role(role: str) -> str:
    r = (role or "").upper()
    if r == ROLE_ADMIN:
        return "/admin"
    if r == ROLE_OPERATOR:
        return "/operator"
    return "/viewer"


class SetupAdminRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=5, max_length=128)
    password: str = Field(..., min_length=8, max_length=128)
    setup_token: Optional[str] = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Username or email address")
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    csrf_token: str
    session_id: str
    expires_at: str
    user_id: str
    username: str
    email: str
    role: str
    landing_route: str
    permissions: List[str] = []
    organization_id: str = "org-primary-enterprise"


class UserProfileResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    organization_id: str = "org-primary-enterprise"
    is_active: bool
    failed_login_attempts: int = 0
    locked_until: Optional[str] = None
    last_login_at: Optional[str] = None
    active_sessions_count: int = 0
    landing_route: str = "/overview"
    permissions: List[str] = []


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=5, max_length=128)
    password: str = Field(..., min_length=6, max_length=128)
    role: Optional[str] = "OPERATOR"
    organization_id: Optional[str] = "org-primary-enterprise"


class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(..., min_length=2, description="Username or email")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserUpdateRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    email: Optional[str] = None


class RolePermissionsUpdateRequest(BaseModel):
    permissions: List[str]


def _serialize_user_profile(db: Session, u: User, include_perms: bool = False) -> UserProfileResponse:
    active_sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == u.id, UserSession.is_revoked == False)
        .count()
    )
    return UserProfileResponse(
        id=u.id,
        username=u.username,
        email=u.email,
        role=u.role,
        organization_id=getattr(u, "organization_id", "org-primary-enterprise") or "org-primary-enterprise",
        is_active=bool(u.is_active),
        failed_login_attempts=int(getattr(u, "failed_login_attempts", 0) or 0),
        locked_until=u.locked_until.isoformat() if getattr(u, "locked_until", None) else None,
        last_login_at=u.last_login_at.isoformat() if getattr(u, "last_login_at", None) else None,
        active_sessions_count=active_sessions,
        landing_route=_landing_route_for_role(u.role),
        permissions=get_effective_permissions(db, u.role) if include_perms else [],
    )


# ------------------------------------------------------------------------------
# FIRST-RUN SYSTEM BOOTSTRAP (/auth/setup-status & /auth/setup)
# ------------------------------------------------------------------------------

@router.get("/setup-status")
def get_setup_status(db: Session = Depends(get_db)):
    admin_count = db.query(User).filter(User.role == ROLE_ADMIN).count()
    return {
        "needs_setup": admin_count == 0,
        "setup_required": admin_count == 0,
        "setup_token_required": bool(os.getenv("AEGISSTOR_SETUP_TOKEN", "").strip()),
    }


@router.post("/setup", response_model=UserProfileResponse, status_code=201)
def bootstrap_first_administrator(
    payload: SetupAdminRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Creates the initial Administrator account only when zero Administrators exist in the system."""
    admin_count = db.query(User).filter(User.role == ROLE_ADMIN).count()
    if admin_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System bootstrap is already completed.",
        )

    expected_setup_token = os.getenv("AEGISSTOR_SETUP_TOKEN", "").strip()
    if expected_setup_token and (payload.setup_token or "").strip() != expected_setup_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid setup authorization token.")

    existing = db.query(User).filter(
        or_(User.username == payload.username.strip(), User.email == payload.email.strip())
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists.")

    seed_roles_and_permissions(db)
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    admin_user = User(
        id=f"usr-admin-{uuid.uuid4().hex[:8]}",
        username=payload.username.strip(),
        email=payload.email.strip(),
        hashed_password=hash_password(payload.password),
        role=ROLE_ADMIN,
        organization_id="org-primary-enterprise",
        is_active=True,
        password_changed_at=now_naive,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    AuditService.log_event(
        db=db,
        action="BOOTSTRAP_ADMIN_CREATED",
        target_type="USER",
        target_id=admin_user.id,
        user=admin_user.username,
        user_id=admin_user.id,
        user_role=ROLE_ADMIN,
        client_ip=request.client.host if request.client else "127.0.0.1",
        details={"username": admin_user.username},
    )
    return _serialize_user_profile(db, admin_user, include_perms=True)


# ------------------------------------------------------------------------------
# LOGIN, LOGOUT, SESSION LIFECYCLE & PASSWORD RECOVERY
# ------------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Authenticates by username or email, enforces lockout & active status,
    creates a persistent DB session + HttpOnly cookie + CSRF token, and logs attempts.
    """
    seed_roles_and_permissions(db)
    identifier = payload.username.strip()
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = (request.headers.get("user-agent") or "")[:250]
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)

    user = db.query(User).filter(or_(User.username == identifier, User.email == identifier)).first()
    if not user:
        db.add(LoginAttempt(
            id=f"att-{uuid.uuid4().hex[:10]}",
            identifier=identifier,
            user_id=None,
            success=False,
            failure_reason="UNKNOWN_USER",
            client_ip=client_ip,
            user_agent=user_agent,
        ))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check active brute-force lockout window
    if getattr(user, "locked_until", None) and user.locked_until.replace(tzinfo=None) > now_naive:
        db.add(LoginAttempt(
            id=f"att-{uuid.uuid4().hex[:10]}",
            identifier=identifier,
            user_id=user.id,
            success=False,
            failure_reason="ACCOUNT_LOCKED",
            client_ip=client_ip,
            user_agent=user_agent,
        ))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to repeated failed login attempts. Try again later or reset password.",
        )

    if not verify_password(payload.password, user.hashed_password):
        attempts = int(getattr(user, "failed_login_attempts", 0) or 0) + 1
        user.failed_login_attempts = attempts
        if attempts >= MAX_FAILED_LOGINS:
            user.locked_until = now_naive + timedelta(minutes=LOCKOUT_MINUTES)
        db.add(LoginAttempt(
            id=f"att-{uuid.uuid4().hex[:10]}",
            identifier=identifier,
            user_id=user.id,
            success=False,
            failure_reason="INVALID_PASSWORD",
            client_ip=client_ip,
            user_agent=user_agent,
        ))
        db.commit()
        AuditService.log_event(
            db=db,
            action="LOGIN_FAILED",
            target_type="USER",
            target_id=user.id,
            user=user.username,
            user_id=user.id,
            user_role=user.role,
            outcome="FAILED",
            client_ip=client_ip,
            details={"attempts": attempts},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        db.add(LoginAttempt(
            id=f"att-{uuid.uuid4().hex[:10]}",
            identifier=identifier,
            user_id=user.id,
            success=False,
            failure_reason="INACTIVE_ACCOUNT",
            client_ip=client_ip,
            user_agent=user_agent,
        ))
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")

    # Successful authentication: reset lockout counters & issue persistent UserSession
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now_naive

    org_id = getattr(user, "organization_id", "org-primary-enterprise") or "org-primary-enterprise"
    session_id = f"sess-{uuid.uuid4().hex[:12]}"
    csrf_token = secrets.token_urlsafe(24)
    expires_dt = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role,
            "user_id": user.id,
            "organization_id": org_id,
            "sid": session_id,
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    db.add(UserSession(
        id=session_id,
        user_id=user.id,
        session_token_hash=hash_token(token),
        csrf_token_hash=hash_token(csrf_token),
        role_at_issue=user.role,
        client_ip=client_ip,
        user_agent=user_agent,
        is_revoked=False,
        expires_at=expires_dt.replace(tzinfo=None),
        last_seen_at=now_naive,
    ))
    db.add(LoginAttempt(
        id=f"att-{uuid.uuid4().hex[:10]}",
        identifier=identifier,
        user_id=user.id,
        success=True,
        failure_reason=None,
        client_ip=client_ip,
        user_agent=user_agent,
    ))
    db.commit()

    # Set secure HttpOnly session cookie + readable double-submit CSRF cookie
    is_https = request.url.scheme == "https"
    response.set_cookie(
        key="aegisstor_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_https,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="aegisstor_csrf",
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=is_https,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    perms = get_effective_permissions(db, user.role)
    AuditService.log_event(
        db=db,
        action="LOGIN",
        target_type="USER",
        target_id=user.id,
        user=user.username,
        user_id=user.id,
        user_role=user.role,
        organization_id=org_id,
        client_ip=client_ip,
        details={"role": user.role, "session_id": session_id},
    )

    return TokenResponse(
        access_token=token,
        csrf_token=csrf_token,
        session_id=session_id,
        expires_at=expires_dt.isoformat(),
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        landing_route=_landing_route_for_role(user.role),
        permissions=perms,
        organization_id=org_id,
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logs out current session, revokes persistent UserSession & token, and clears session cookies."""
    raw_token = credentials.credentials if (credentials and credentials.credentials) else request.cookies.get("aegisstor_session")
    sid = None
    if raw_token:
        revoke_token(db, raw_token, user_id=current_user.id)
        decoded = decode_access_token(raw_token)
        if decoded:
            sid = decoded.get("sid")
            if sid:
                sess = db.query(UserSession).filter(UserSession.id == sid).first()
                if sess:
                    sess.is_revoked = True
                    sess.revoked_reason = "user_logout"
                    db.commit()

    response.delete_cookie("aegisstor_session")
    response.delete_cookie("aegisstor_csrf")

    AuditService.log_event(
        db=db,
        action="LOGOUT",
        target_type="USER",
        target_id=current_user.id,
        user=current_user.username,
        user_id=current_user.id,
        user_role=current_user.role,
        organization_id=getattr(current_user, "organization_id", "org-primary-enterprise") or "org-primary-enterprise",
        client_ip=request.client.host if request.client else "127.0.0.1",
        details={"session_id": sid, "token_revoked": bool(raw_token)},
    )
    return {"status": "ok", "message": "Session logged out and revoked"}


@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _serialize_user_profile(db, current_user, include_perms=True)


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """Issues an expiring single-use SHA-256 hashed password reset token without leaking user existence."""
    ident = payload.identifier.strip()
    user = db.query(User).filter(or_(User.username == ident, User.email == ident)).first()
    issued_token: Optional[str] = None
    if user and user.is_active:
        raw_reset = secrets.token_urlsafe(24)
        exp = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=15)
        db.add(PasswordResetToken(
            id=f"rst-{uuid.uuid4().hex[:10]}",
            user_id=user.id,
            token_hash=hash_token(raw_reset),
            expires_at=exp,
            created_by="self_service",
        ))
        db.commit()
        AuditService.log_event(
            db=db,
            action="PASSWORD_RESET_REQUESTED",
            target_type="USER",
            target_id=user.id,
            user=user.username,
            user_id=user.id,
            user_role=user.role,
            client_ip=request.client.host if request.client else "127.0.0.1",
            details={"expires_at": exp.isoformat()},
        )
        # Return token in response ONLY in explicit dev/test mode so E2E resets work cleanly without external SMTP
        if os.getenv("AEGISSTOR_ALLOW_DEV_SEED", "false").lower() == "true" or os.getenv("PYTEST_CURRENT_TEST"):
            issued_token = raw_reset

    resp_obj: Dict[str, Any] = {
        "status": "ok",
        "message": "If an active matching account exists, a password reset instruction has been generated (15 min expiry).",
    }
    if issued_token:
        resp_obj["reset_token_dev"] = issued_token
    return resp_obj


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """Validates single-use reset token, updates password via Argon2id, and revokes all active sessions."""
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    t_hash = hash_token(payload.token.strip())
    rec = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == t_hash).first()
    if not rec or rec.used_at is not None or rec.expires_at.replace(tzinfo=None) < now_naive:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token.")

    user = db.query(User).filter(User.id == rec.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Account cannot complete password reset.")

    user.hashed_password = hash_password(payload.new_password)
    user.password_changed_at = now_naive
    user.failed_login_attempts = 0
    user.locked_until = None
    rec.used_at = now_naive
    db.commit()

    revoked_count = revoke_all_user_sessions(db, user.id, reason="password_reset")
    AuditService.log_event(
        db=db,
        action="PASSWORD_RESET_COMPLETED",
        target_type="USER",
        target_id=user.id,
        user=user.username,
        user_id=user.id,
        user_role=user.role,
        client_ip=request.client.host if request.client else "127.0.0.1",
        details={"revoked_sessions": revoked_count},
    )
    return {"status": "ok", "message": "Password reset successfully; existing sessions revoked."}


@router.post("/change-password")
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    current_user.hashed_password = hash_password(payload.new_password)
    current_user.password_changed_at = now_naive
    db.commit()
    revoked_count = revoke_all_user_sessions(db, current_user.id, reason="password_changed")
    AuditService.log_event(
        db=db,
        action="CHANGE_PASSWORD",
        target_type="USER",
        target_id=current_user.id,
        user=current_user.username,
        user_id=current_user.id,
        user_role=current_user.role,
        client_ip=request.client.host if request.client else "127.0.0.1",
        details={"revoked_sessions": revoked_count},
    )
    return {"status": "ok", "message": "Password updated and prior sessions revoked."}


@router.get("/sessions")
def list_sessions(
    user_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_uid = current_user.id
    if user_id and user_id != current_user.id:
        if current_user.role != ROLE_ADMIN:
            raise HTTPException(status_code=403, detail="Only administrators can inspect other users' sessions.")
        target_uid = user_id

    rows = db.query(UserSession).filter(UserSession.user_id == target_uid).order_by(UserSession.created_at.desc()).limit(30).all()
    return {
        "sessions": [
            {
                "id": s.id,
                "user_id": s.user_id,
                "role_at_issue": s.role_at_issue,
                "client_ip": s.client_ip,
                "user_agent": s.user_agent,
                "is_revoked": s.is_revoked,
                "revoked_reason": s.revoked_reason,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                "last_seen_at": s.last_seen_at.isoformat() if s.last_seen_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in rows
        ]
    }


@router.delete("/sessions/{session_id}")
def revoke_specific_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sess = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    if sess.user_id != current_user.id and current_user.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Cannot revoke another user's session")
    sess.is_revoked = True
    sess.revoked_reason = f"revoked_by_{current_user.username}"
    db.commit()
    from app.realtime.event_bus import realtime_manager
    realtime_manager.terminate_session_connections(session_id, reason="session_revoked")
    return {"status": "revoked", "session_id": session_id}


@router.get("/login-history")
def get_login_history(
    user_id: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(LoginAttempt)
    if current_user.role != ROLE_ADMIN:
        q = q.filter(or_(LoginAttempt.user_id == current_user.id, LoginAttempt.identifier == current_user.username, LoginAttempt.identifier == current_user.email))
    elif user_id:
        q = q.filter(LoginAttempt.user_id == user_id)

    rows = q.order_by(LoginAttempt.attempted_at.desc()).limit(limit).all()
    return {
        "login_history": [
            {
                "id": r.id,
                "identifier": r.identifier,
                "user_id": r.user_id,
                "success": r.success,
                "failure_reason": r.failure_reason,
                "client_ip": r.client_ip,
                "attempted_at": r.attempted_at.isoformat() if r.attempted_at else None,
            }
            for r in rows
        ]
    }


@router.get("/permissions")
def get_current_user_permissions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    perms = get_effective_permissions(db, current_user.role)
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "landing_route": _landing_route_for_role(current_user.role),
        "organization_id": getattr(current_user, "organization_id", "org-primary-enterprise") or "org-primary-enterprise",
        "permissions_count": len(perms),
        "permissions": perms,
        "enforcement_mode": "CENTRAL_DB_RBAC",
    }


@router.post("/register", response_model=UserProfileResponse)
def register_user(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_permission("users.create")),
):
    existing = db.query(User).filter(
        or_(User.username == payload.username.strip(), User.email == payload.email.strip())
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email is already registered")

    role = payload.role.upper() if payload.role and payload.role.upper() in ALL_ROLES else ROLE_OPERATOR
    org_id = payload.organization_id or getattr(admin_user, "organization_id", "org-primary-enterprise") or "org-primary-enterprise"
    new_user = User(
        id=f"usr-{uuid.uuid4().hex[:10]}",
        username=payload.username.strip(),
        email=payload.email.strip(),
        hashed_password=hash_password(payload.password),
        role=role,
        organization_id=org_id,
        is_active=True,
        password_changed_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    AuditService.log_event(
        db=db,
        action="REGISTER_USER",
        target_type="USER",
        target_id=new_user.id,
        user=admin_user.username,
        user_id=admin_user.id,
        user_role=admin_user.role,
        organization_id=org_id,
        details={"username": new_user.username, "role": new_user.role},
    )
    return _serialize_user_profile(db, new_user)


@router.get("/audit/verify-chain")
def verify_audit_trail_tamper_chain(
    organization_id: Optional[str] = None,
    current_user: User = Depends(require_permission("audit.export")),
    db: Session = Depends(get_db),
):
    target_org = organization_id if (current_user.role == ROLE_ADMIN and organization_id) else getattr(current_user, "organization_id", "org-primary-enterprise")
    return AuditService.verify_audit_chain(db, organization_id=target_org)


# ------------------------------------------------------------------------------
# CENTRAL PERMISSIONS MATRIX ADMIN (/permissions)
# ------------------------------------------------------------------------------

@permissions_router.get("/catalog")
def get_permission_catalog(
    current_user: User = Depends(require_permission("users.assign_role")),
    db: Session = Depends(get_db),
):
    seed_roles_and_permissions(db)
    role_matrix = {r: get_effective_permissions(db, r) for r in ALL_ROLES}
    return {
        "roles": [{"name": r, "description": ROLE_DESCRIPTIONS.get(r, "")} for r in ALL_ROLES],
        "permissions": PERMISSION_CATALOG,
        "role_matrix": role_matrix,
    }


@permissions_router.put("/roles/{role_name}")
def update_role_permissions(
    role_name: str,
    payload: RolePermissionsUpdateRequest,
    current_user: User = Depends(require_permission("users.assign_role")),
    db: Session = Depends(get_db),
):
    r_up = role_name.upper()
    if r_up not in ALL_ROLES:
        raise HTTPException(status_code=400, detail=f"Unknown role '{role_name}'")
    if r_up == ROLE_ADMIN:
        raise HTTPException(status_code=400, detail="Administrator base safety permissions cannot be stripped")

    seed_roles_and_permissions(db)
    allowed_set = set(payload.permissions)
    rows = db.query(RolePermission).filter(RolePermission.role_name == r_up).all()
    for rp in rows:
        rp.is_allowed = rp.permission_key in allowed_set
    new_perms = get_effective_permissions(db, r_up)
    from app.realtime.event_bus import OutboxService
    evt = OutboxService.stage_event(
        db,
        event_type="permissions.updated",
        resource_type="role",
        resource_id=r_up,
        actor_user=current_user,
        changed_fields=["permissions"],
        payload={"role": r_up, "permissions": new_perms},
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)

    AuditService.log_event(
        db=db,
        action="ROLE_PERMISSIONS_UPDATED",
        target_type="ROLE",
        target_id=r_up,
        user=current_user.username,
        user_id=current_user.id,
        user_role=current_user.role,
        details={"enabled_count": len(allowed_set)},
    )
    return {"status": "updated", "role": r_up, "permissions": new_perms}


# ------------------------------------------------------------------------------
# USER MANAGEMENT CRUD (/users) — ADMINISTRATOR ONLY
# ------------------------------------------------------------------------------

@users_router.get("", response_model=List[UserProfileResponse])
def list_users(
    admin_user: User = Depends(require_permission("users.read")),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [_serialize_user_profile(db, u) for u in users]


@users_router.post("", response_model=UserProfileResponse, status_code=201)
def create_user(
    payload: RegisterRequest,
    admin_user: User = Depends(require_permission("users.create")),
    db: Session = Depends(get_db),
):
    return register_user(payload=payload, db=db, admin_user=admin_user)


@users_router.patch("/{user_id}", response_model=UserProfileResponse)
def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    admin_user: User = Depends(require_permission("users.update")),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    if u.id == admin_user.id:
        if payload.is_active is False:
            raise HTTPException(status_code=400, detail="Administrators cannot deactivate their own active account")
        if payload.role is not None and payload.role.upper() != ROLE_ADMIN:
            raise HTTPException(status_code=400, detail="Administrators cannot demote their own active role")

    changes: Dict[str, Any] = {}
    should_revoke_sessions = False
    if payload.role is not None:
        role_upper = payload.role.upper()
        if role_upper not in ALL_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role. Allowed: {ALL_ROLES}")
        if role_upper != u.role:
            changes["role"] = {"old": u.role, "new": role_upper}
            u.role = role_upper
            should_revoke_sessions = True
    if payload.is_active is not None and payload.is_active != u.is_active:
        changes["is_active"] = {"old": u.is_active, "new": payload.is_active}
        u.is_active = payload.is_active
        if not payload.is_active:
            should_revoke_sessions = True
    if payload.email is not None and payload.email != u.email:
        changes["email"] = {"old": u.email, "new": payload.email}
        u.email = payload.email

    db.commit()
    db.refresh(u)

    if should_revoke_sessions:
        revoke_all_user_sessions(db, u.id, reason="admin_account_change")
        from app.realtime.event_bus import realtime_manager
        realtime_manager.terminate_user_connections(u.id, reason="admin_account_change")

    from app.realtime.event_bus import OutboxService
    OutboxService.emit_and_commit(
        db,
        event_type="user.updated",
        resource_type="user",
        resource_id=u.id,
        actor_user=admin_user,
        changed_fields=list(changes.keys()),
        payload={"user_id": u.id, "username": u.username, "role": u.role, "is_active": u.is_active},
        required_permission="users.read",
    )

    AuditService.log_event(
        db=db,
        action="UPDATE_USER",
        target_type="USER",
        target_id=u.id,
        user=admin_user.username,
        user_id=admin_user.id,
        user_role=admin_user.role,
        organization_id=getattr(u, "organization_id", "org-primary-enterprise") or "org-primary-enterprise",
        details=changes,
    )
    return _serialize_user_profile(db, u)


@users_router.post("/{user_id}/revoke-sessions")
def admin_revoke_user_sessions(
    user_id: str,
    admin_user: User = Depends(require_permission("users.deactivate")),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    revoked = revoke_all_user_sessions(db, u.id, reason=f"revoked_by_admin:{admin_user.username}")
    from app.realtime.event_bus import OutboxService, realtime_manager
    realtime_manager.terminate_user_connections(u.id, reason="sessions_revoked")
    OutboxService.emit_and_commit(
        db,
        event_type="user.sessions_revoked",
        resource_type="user",
        resource_id=u.id,
        actor_user=admin_user,
        payload={"user_id": u.id, "revoked_sessions": revoked},
        required_permission="users.read",
    )
    AuditService.log_event(
        db=db,
        action="REVOKE_USER_SESSIONS",
        target_type="USER",
        target_id=u.id,
        user=admin_user.username,
        user_id=admin_user.id,
        user_role=admin_user.role,
        details={"revoked_sessions_count": revoked},
    )
    return {"status": "ok", "revoked_sessions": revoked}


@users_router.post("/{user_id}/trigger-reset")
def admin_trigger_password_reset(
    user_id: str,
    admin_user: User = Depends(require_permission("users.update")),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    raw_reset = secrets.token_urlsafe(24)
    exp = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)
    db.add(PasswordResetToken(
        id=f"rst-{uuid.uuid4().hex[:10]}",
        user_id=u.id,
        token_hash=hash_token(raw_reset),
        expires_at=exp,
        created_by=admin_user.username,
    ))
    db.commit()
    AuditService.log_event(
        db=db,
        action="ADMIN_TRIGGER_PASSWORD_RESET",
        target_type="USER",
        target_id=u.id,
        user=admin_user.username,
        user_id=admin_user.id,
        user_role=admin_user.role,
        details={"expires_at": exp.isoformat()},
    )
    return {
        "status": "ok",
        "user_id": u.id,
        "reset_token": raw_reset,
        "expires_at": exp.isoformat(),
        "notice": "Deliver this single-use reset token securely out-of-band to the user.",
    }


@users_router.get("/{user_id}/audit")
def get_user_audit_history(
    user_id: str,
    admin_user: User = Depends(require_permission("users.read")),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    logs = (
        db.query(AuditLog)
        .filter(or_(AuditLog.user_id == u.id, AuditLog.user == u.username, AuditLog.target_id == u.id))
        .order_by(AuditLog.timestamp.desc())
        .limit(50)
        .all()
    )
    attempts = (
        db.query(LoginAttempt)
        .filter(or_(LoginAttempt.user_id == u.id, LoginAttempt.identifier == u.username, LoginAttempt.identifier == u.email))
        .order_by(LoginAttempt.attempted_at.desc())
        .limit(30)
        .all()
    )
    return {
        "user_id": u.id,
        "username": u.username,
        "user": _serialize_user_profile(db, u),
        "logs": [
            {
                "id": l.id,
                "timestamp": l.timestamp.isoformat() if l.timestamp else None,
                "action": l.action,
                "user": l.user,
                "user_role": getattr(l, "user_role", None),
                "outcome": getattr(l, "outcome", "SUCCESS"),
                "target_type": l.target_type,
                "target_id": l.target_id,
            }
            for l in logs
        ],
        "login_attempts": [
            {
                "id": a.id,
                "identifier": a.identifier,
                "success": a.success,
                "failure_reason": a.failure_reason,
                "client_ip": a.client_ip,
                "attempted_at": a.attempted_at.isoformat() if a.attempted_at else None,
            }
            for a in attempts
        ],
    }


@users_router.delete("/{user_id}")
def delete_or_deactivate_user(
    user_id: str,
    admin_user: User = Depends(require_permission("users.deactivate")),
    db: Session = Depends(get_db),
):
    if user_id == admin_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete currently active administrator account")
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    username = u.username
    revoke_all_user_sessions(db, u.id, reason="user_deleted")
    from app.realtime.event_bus import OutboxService, realtime_manager
    realtime_manager.terminate_user_connections(u.id, reason="user_deleted")
    db.delete(u)
    evt = OutboxService.stage_event(
        db,
        event_type="user.deleted",
        resource_type="user",
        resource_id=user_id,
        actor_user=admin_user,
        payload={"user_id": user_id, "username": username},
        required_permission="users.read",
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)
    AuditService.log_event(
        db=db,
        action="DELETE_USER",
        target_type="USER",
        target_id=user_id,
        user=admin_user.username,
        user_id=admin_user.id,
        user_role=admin_user.role,
        details={"deleted_username": username},
    )
    return {"status": "ok", "message": f"User {username} deleted"}
