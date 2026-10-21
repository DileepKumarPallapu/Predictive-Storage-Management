import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import AuditLog

class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        action: str,
        target_type: str,
        target_id: str,
        user: str = "operator@aegisstor.internal",
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        log_entry = AuditLog(
            timestamp=datetime.now(timezone.utc),
            user=user,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details_json=json.dumps(details or {})
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
