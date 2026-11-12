"""Strict authentication dependencies for the new Control Plane API.

Legacy API authentication is left unchanged in this sprint to avoid silently
breaking existing routes. Control Plane routes never use the legacy
no-token administrator fallback.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.database import get_db
from app.models.entities import User

bearer_scheme = HTTPBearer(auto_error=False)
CONTROL_PLANE_ROLES = {"ADMIN", "OPERATOR", "AUDITOR", "VIEWER"}


def get_control_plane_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required for Control Plane access.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.username == payload["sub"]).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account no longer exists.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated.")
    if user.role not in CONTROL_PLANE_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role is not enabled for Control Plane access.")

    token_user_id = payload.get("user_id")
    if token_user_id and token_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication subject does not match user record.")

    return user


def require_control_plane_roles(*allowed_roles: str):
    allowed = set(allowed_roles)

    def dependency(user: User = Depends(get_control_plane_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role is not permitted to perform this Control Plane operation.",
            )
        return user

    return dependency


def get_user_organization_id(user: User) -> str:
    organization_id = getattr(user, "organization_id", None)
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no organisation scope configured.",
        )
    return organization_id
