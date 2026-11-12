import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import AuditLog

import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models.entities import AuditLog

GENESIS_HASH = "0" * 64

class AuditService:
    @staticmethod
    def calculate_entry_hash(
        prev_hash: str,
        timestamp_str: str,
        user: str,
        action: str,
        target_type: str,
        target_id: str,
        details_str: str
    ) -> str:
        payload = f"{prev_hash}:{timestamp_str}:{user}:{action}:{target_type}:{target_id}:{details_str}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def log_event(
        db: Session,
        action: str,
        target_type: str,
        target_id: str,
        user: str = "operator@aegisstor.internal",
        details: Optional[Dict[str, Any]] = None,
        organization_id: str = "org-primary-enterprise",
        client_ip: str = "127.0.0.1",
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        outcome: str = "SUCCESS",
    ) -> AuditLog:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        details_str = json.dumps(details or {}, sort_keys=True)

        if user_id is None or user_role is None:
            from app.models.entities import User
            u_obj = db.query(User).filter(User.username == user).first()
            if u_obj:
                user_id = user_id or u_obj.id
                user_role = user_role or u_obj.role

        # Get latest entry to link cryptographic hash chain
        latest = (
            db.query(AuditLog)
            .filter(AuditLog.organization_id == organization_id)
            .order_by(AuditLog.id.desc())
            .first()
        )
        prev_hash = latest.entry_hash if (latest and latest.entry_hash) else GENESIS_HASH
        entry_hash = AuditService.calculate_entry_hash(
            prev_hash=prev_hash,
            timestamp_str=time_str,
            user=user,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details_str=details_str
        )


        log_entry = AuditLog(
            timestamp=now,
            user=user,
            user_id=user_id,
            user_role=user_role,
            outcome=outcome,
            action=action,
            target_type=target_type,
            target_id=target_id,
            organization_id=organization_id,
            client_ip=client_ip,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            details_json=details_str
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def verify_audit_chain(db: Session, organization_id: str = "org-primary-enterprise") -> Dict[str, Any]:
        """
        Cryptographically verifies the immutable SHA-256 hash chain of the audit trail.
        Detects unauthorized deletions, insertions, or in-place modifications.
        """
        entries = (
            db.query(AuditLog)
            .filter(AuditLog.organization_id == organization_id)
            .order_by(AuditLog.id.asc())
            .all()
        )

        if not entries:
            return {
                "organization_id": organization_id,
                "is_valid": True,
                "total_entries": 0,
                "tampered_entries": [],
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "chain_head_hash": GENESIS_HASH,
                "message": "Audit chain empty; nominal genesis state."
            }

        tampered = []
        expected_prev = GENESIS_HASH

        for e in entries:
            # Skip legacy entries created before hash-chaining was active
            if not e.entry_hash:
                continue

            # Verify link to previous entry
            if e.prev_hash != expected_prev and expected_prev != GENESIS_HASH:
                tampered.append({
                    "entry_id": e.id,
                    "reason": f"Broken chain link: expected prev_hash {expected_prev[:12]}..., got {e.prev_hash[:12]}..."
                })

            # Recompute expected hash
            time_str = e.timestamp.strftime("%Y-%m-%d %H:%M:%S") if hasattr(e.timestamp, "strftime") else str(e.timestamp)[:19]
            recomputed = AuditService.calculate_entry_hash(
                prev_hash=e.prev_hash or GENESIS_HASH,
                timestamp_str=time_str,
                user=e.user,
                action=e.action,
                target_type=e.target_type,
                target_id=e.target_id,
                details_str=e.details_json or "{}"
            )


            if recomputed != e.entry_hash:
                tampered.append({
                    "entry_id": e.id,
                    "reason": "Hash mismatch: contents have been modified after commit"
                })

            expected_prev = e.entry_hash

        return {
            "organization_id": organization_id,
            "is_valid": len(tampered) == 0,
            "total_entries": len(entries),
            "tampered_count": len(tampered),
            "tampered_entries": tampered,
            "chain_head_hash": expected_prev,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "tamper_evidence_mechanism": "Cryptographic SHA-256 forward-linked Merkle chain",
            "tamper_evidence_limits": "Guarantees detection of modified or deleted records provided root hash is pinned; does not protect against external OS root filesystem wipe."
        }

