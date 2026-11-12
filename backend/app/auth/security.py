import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import bcrypt
import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.permissions import (
    ALL_ROLES,
    ROLE_ADMIN,
    ROLE_AUDITOR,
    ROLE_OPERATOR,
    ROLE_VIEWER,
    DEFAULT_ROLE_PERMISSIONS,
    get_effective_permissions,
)
from app.config import settings
from app.database import get_db
from app.models.entities import ApiKey, RevokedToken, User, UserSession

security_scheme = HTTPBearer(auto_error=False)
_argon2_hasher = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2, hash_len=32, type=Type.ID)

# Backward-compatible export expected by legacy modules
ROLE_PERMISSIONS: Dict[str, list[str]] = DEFAULT_ROLE_PERMISSIONS


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """Hashes a plaintext password using modern Argon2id."""
    return _argon2_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plaintext password against stored Argon2id (or legacy bcrypt) hash."""
    if not hashed_password or not plain_password:
        return False
    if hashed_password.startswith("$argon2"):
        try:
            return _argon2_hasher.verify(hashed_password, plain_password)
        except (VerifyMismatchError, InvalidHashError, Exception):
            return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def is_token_revoked(db: Session, token: str) -> bool:
    t_hash = hash_token(token)
    return db.query(RevokedToken).filter(RevokedToken.token_hash == t_hash).first() is not None


def revoke_token(db: Session, token: str, user_id: Optional[str] = None, expires_at: Optional[datetime] = None) -> None:
    t_hash = hash_token(token)
    existing = db.query(RevokedToken).filter(RevokedToken.token_hash == t_hash).first()
    if not existing:
        db.add(RevokedToken(
            id=f"rev-{uuid.uuid4().hex[:12]}",
            token_hash=t_hash,
            user_id=user_id,
            expires_at=expires_at,
        ))
        db.commit()


def revoke_all_user_sessions(db: Session, user_id: str, reason: str = "security_revocation") -> int:
    """Immediately revokes every active session belonging to user_id."""
    active = (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id, UserSession.is_revoked == False)
        .all()
    )
    for sess in active:
        sess.is_revoked = True
        sess.revoked_reason = reason
    db.commit()
    return len(active)


def enforce_tenant_access(current_user: User, resource_organization_id: Optional[str]):
    """Guarantees multi-tenant boundary isolation against cross-organization access."""
    if not resource_organization_id:
        return
    user_org = getattr(current_user, "organization_id", "org-primary-enterprise") or "org-primary-enterprise"
    if current_user.role != ROLE_ADMIN and user_org != resource_organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant boundary violation: access to external organization '{resource_organization_id}' denied",
        )


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generates a cryptographically signed JWT token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now, "jti": to_encode.get("jti") or uuid.uuid4().hex})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT token signature and expiration."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    """
    Strictly authenticates via JWT Bearer token, HttpOnly cookie session (+ CSRF header on state-changing requests),
    or valid X-API-Key. Never silently falls back to an unauthenticated admin account.
    """
    # 1. Machine collector authentication via X-API-Key
    if x_api_key:
        k_hash = hash_token(x_api_key.strip())
        api_key = db.query(ApiKey).filter(ApiKey.key_hash == k_hash).first()
        if not api_key or not api_key.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked X-API-Key",
            )
        api_key.last_used_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        return User(
            id=f"apikey-{api_key.id}",
            username=f"collector:{api_key.name}",
            email="collector@aegisstor.internal",
            hashed_password="",
            role=api_key.role,
            organization_id=api_key.organization_id,
            is_active=True,
        )

    # 2. Extract Bearer JWT or HttpOnly Session Cookie
    raw_token: Optional[str] = None
    via_cookie = False
    if credentials and credentials.credentials:
        raw_token = credentials.credentials
    elif request.cookies.get("aegisstor_session"):
        raw_token = request.cookies.get("aegisstor_session")
        via_cookie = True

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Double-submit CSRF enforcement whenever cookie-based auth mutates state
    if via_cookie and request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        csrf_cookie = request.cookies.get("aegisstor_csrf")
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF verification failed for cookie session",
            )

    if is_token_revoked(db, raw_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been logged out or revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(raw_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate persistent DB UserSession if sid claim is present
    sid = payload.get("sid")
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    if sid:
        sess = db.query(UserSession).filter(UserSession.id == sid).first()
        if not sess or sess.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session revoked or terminated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if sess.expires_at and sess.expires_at.replace(tzinfo=None) < now_naive:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired; please log in again",
                headers={"WWW-Authenticate": "Bearer"},
            )
        sess.last_seen_at = now_naive
        db.commit()

    username: str = payload["sub"]
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Invalidate standalone tokens issued before password reset/change
    pw_changed = getattr(user, "password_changed_at", None)
    iat = payload.get("iat")
    if pw_changed and iat:
        iat_dt = datetime.fromtimestamp(float(iat), tz=timezone.utc).replace(tzinfo=None)
        if iat_dt < pw_changed.replace(tzinfo=None) - timedelta(seconds=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credentials were reset; please sign in again",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return user


def require_role(allowed_roles: List[str]):
    """Role-based authorization dependency factory."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: required role in {allowed_roles}, current role is {current_user.role}",
            )
        return current_user
    return role_checker
