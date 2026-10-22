import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.entities import User

security_scheme = HTTPBearer(auto_error=False)

ROLE_ADMIN = "ADMIN"
ROLE_OPERATOR = "OPERATOR"
ROLE_AUDITOR = "AUDITOR"

ALL_ROLES = [ROLE_ADMIN, ROLE_OPERATOR, ROLE_AUDITOR]

ROLE_PERMISSIONS: Dict[str, list[str]] = {
    ROLE_ADMIN: [
        "users:manage", "thresholds:configure", "interventions:approve",
        "interventions:reject", "models:retrain", "telemetry:read",
        "telemetry:ingest", "simulations:execute", "audits:verify",
        "tenants:manage"
    ],
    ROLE_OPERATOR: [
        "telemetry:read", "telemetry:ingest", "simulations:execute",
        "interventions:preview", "forecasts:generate", "audits:read"
    ],
    ROLE_AUDITOR: [
        "telemetry:read", "forecasts:read", "audits:read", "audits:verify",
        "benchmarks:export"
    ]
}

def enforce_tenant_access(current_user: User, resource_organization_id: Optional[str]):
    """
    Guarantees strict multi-tenant boundary isolation against Insecure Direct Object Reference (IDOR).
    Cross-organization access without global ADMIN privileges is forbidden.
    """
    if not resource_organization_id:
        return

    user_org = getattr(current_user, "organization_id", "org-primary-enterprise") or "org-primary-enterprise"
    if current_user.role != ROLE_ADMIN and user_org != resource_organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant boundary violation: access to external organization '{resource_organization_id}' denied"
        )


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generates a cryptographically signed JWT token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT token signature and expiration."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency that authenticates the user via JWT Bearer token.
    Falls back to a default system admin for development/demo ease if no token provided.
    """
    if not credentials:
        # Check if default admin exists in db or return demo admin
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            user = User(
                id="usr-system-admin",
                username="admin",
                email="admin@aegisstor.internal",
                hashed_password=hash_password("admin123"),
                role="ADMIN",
                organization_id="org-primary-enterprise",
                is_active=True

            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username: str = payload.get("sub")
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
            detail="User account is deactivated"
        )
    return user

def require_role(allowed_roles: list[str]):
    """Role-based authorization dependency factory."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: required role in {allowed_roles}, current role is {current_user.role}"
            )
        return current_user
    return role_checker
