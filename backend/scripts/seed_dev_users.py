"""
Explicit Development User Seeding Script (Local Development ONLY).

Never run this script with default synthetic credentials in production.
Production environments must initialize their first Administrator account via
the first-run `/setup` bootstrap flow or `AEGISSTOR_BOOTSTRAP_ADMIN_*` env vars.

Usage (from `backend/` directory):
    python -m scripts.seed_dev_users
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, Base, engine
from app.models.entities import User
from app.auth.security import hash_password
from app.auth.permissions import seed_roles_and_permissions


def seed_dev_users(force_reset_passwords: bool = False) -> None:
    if os.getenv("AEGISSTOR_ENV", "development").lower() == "production":
        raise RuntimeError("Refusing to seed synthetic development accounts when AEGISSTOR_ENV=production.")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_roles_and_permissions(db)

        accounts = [
            (
                "usr-dev-admin",
                os.getenv("AEGISSTOR_DEV_ADMIN_USER", "admin"),
                os.getenv("AEGISSTOR_DEV_ADMIN_EMAIL", "admin@aegisstor.internal"),
                os.getenv("AEGISSTOR_DEV_ADMIN_PASS", "AegisAdmin!2026"),
                "ADMIN",
            ),
            (
                "usr-dev-operator",
                os.getenv("AEGISSTOR_DEV_OPERATOR_USER", "operator"),
                os.getenv("AEGISSTOR_DEV_OPERATOR_EMAIL", "operator@aegisstor.internal"),
                os.getenv("AEGISSTOR_DEV_OPERATOR_PASS", "AegisOperator!2026"),
                "OPERATOR",
            ),
            (
                "usr-dev-viewer",
                os.getenv("AEGISSTOR_DEV_VIEWER_USER", "viewer"),
                os.getenv("AEGISSTOR_DEV_VIEWER_EMAIL", "viewer@aegisstor.internal"),
                os.getenv("AEGISSTOR_DEV_VIEWER_PASS", "AegisViewer!2026"),
                "VIEWER",
            ),
        ]

        for uid, uname, uemail, upass, urole in accounts:
            existing = db.query(User).filter(User.username == uname).first()
            if not existing:
                db.add(User(
                    id=uid,
                    username=uname,
                    email=uemail,
                    hashed_password=hash_password(upass),
                    role=urole,
                    is_active=True,
                ))
                print(f"[CREATED] {urole:8s} user '{uname}' ({uemail})")
            elif force_reset_passwords:
                existing.hashed_password = hash_password(upass)
                existing.is_active = True
                existing.failed_login_attempts = 0
                existing.locked_until = None
                existing.role = urole
                print(f"[UPDATED] {urole:8s} user '{uname}' ({uemail})")
            else:
                print(f"[EXISTS ] {urole:8s} user '{uname}' (skipped; pass --reset to overwrite)")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic local development users for AEGISSTOR.")
    parser.add_argument("--reset", action="store_true", help="Reset passwords/active state for existing dev accounts.")
    args = parser.parse_args()
    seed_dev_users(force_reset_passwords=args.reset)
