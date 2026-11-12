"""
Test helper to attach a real persisted test Administrator UserSession JWT
ONLY for legacy domain test suites that exercise operational APIs rather than 401 boundaries.
Never weakens production `get_current_user` 401 enforcement.
"""
import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.database import SessionLocal, Base, engine
from app.models.entities import User, UserSession
from app.auth.security import hash_password, hash_token, create_access_token
from app.auth.permissions import seed_roles_and_permissions


def make_authenticated_headers(username: str = "suite_admin", role: str = "ADMIN") -> dict:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_roles_and_permissions(db)
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                id=f"usr-suite-{username}",
                username=username,
                email=f"{username}@test.internal",
                hashed_password=hash_password("SuiteAdmin!2026"),
                role=role,
                organization_id="org-primary-enterprise",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        sid = f"sess-suite-{uuid.uuid4().hex[:10]}"
        exp = datetime.now(timezone.utc) + timedelta(hours=12)
        csrf_tok = f"csrf-{uuid.uuid4().hex}"
        jwt_tok = create_access_token(
            data={
                "sub": user.username,
                "role": user.role,
                "user_id": user.id,
                "organization_id": user.organization_id,
                "sid": sid,
            },
            expires_delta=timedelta(hours=12),
        )
        db.add(UserSession(
            id=sid,
            user_id=user.id,
            session_token_hash=hash_token(jwt_tok),
            csrf_token_hash=hash_token(csrf_tok),
            role_at_issue=user.role,
            expires_at=exp.replace(tzinfo=None),
            is_revoked=False,
        ))
        db.commit()
        return {"Authorization": f"Bearer {jwt_tok}", "X-CSRF-Token": csrf_tok}
    finally:
        db.close()


def attach_admin_auth(client: TestClient) -> TestClient:
    client.headers.update(make_authenticated_headers())
    return client
