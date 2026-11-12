import asyncio
import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set

from fastapi import HTTPException, WebSocket
from sqlalchemy.orm import Session

from app.models.entities import OutboxEvent, User, UserNotification

logger = logging.getLogger("aegisstor.realtime")

_SENSITIVE_KEY_SUBSTRINGS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "credential",
    "private_key",
    "auth_header",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def sanitize_payload(data: Any) -> Any:
    """Recursively redact sensitive fields so credentials/secrets never traverse WebSockets."""
    if isinstance(data, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in data.items():
            lower_k = str(k).lower()
            if any(sub in lower_k for sub in _SENSITIVE_KEY_SUBSTRINGS):
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = sanitize_payload(v)
        return cleaned
    if isinstance(data, list):
        return [sanitize_payload(item) for item in data]
    if isinstance(data, datetime):
        return data.isoformat()
    return data


def raise_if_version_conflict(
    expected_version: Optional[int],
    actual_version: int,
    resource_type: str,
    resource_id: str,
    server_state: Dict[str, Any],
) -> None:
    """Enforce optimistic concurrency control; raises HTTP 409 with authoritative server state."""
    if expected_version is not None and int(expected_version) != int(actual_version):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "VERSION_CONFLICT",
                "message": (
                    f"{resource_type} '{resource_id}' was modified by another user "
                    f"(expected version {expected_version}, current server version {actual_version})."
                ),
                "expected_version": expected_version,
                "server_version": actual_version,
                "server_state": sanitize_payload(server_state),
            },
        )


@dataclass
class ConnectedClient:
    connection_id: str
    websocket: WebSocket
    user_id: str
    username: str
    role: str
    organization_id: str
    session_id: str
    permissions: Set[str] = field(default_factory=set)
    loop: Optional[asyncio.AbstractEventLoop] = None


class RealtimeConnectionManager:
    """Thread-safe registry of authenticated WebSocket clients with permission-filtered dispatch."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._clients: Dict[str, ConnectedClient] = {}
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None

    def register(self, client: ConnectedClient) -> None:
        with self._lock:
            self._clients[client.connection_id] = client
            if client.loop is not None:
                self._main_loop = client.loop

    def unregister(self, connection_id: str) -> None:
        with self._lock:
            self._clients.pop(connection_id, None)

    def connection_count(self) -> int:
        with self._lock:
            return len(self._clients)

    async def shutdown(self) -> None:
        with self._lock:
            targets = list(self._clients.values())
            self._clients.clear()
        for t in targets:
            await self._close_safe(t, 1001, "server_shutdown")

    def update_user_permissions(self, user_id: str, role: str, permissions: Set[str]) -> None:
        with self._lock:
            for c in self._clients.values():
                if c.user_id == user_id:
                    c.role = role
                    c.permissions = set(permissions)

    def _is_authorized(self, client: ConnectedClient, envelope: Dict[str, Any], required_permission: Optional[str], target_user_id: Optional[str]) -> bool:
        if target_user_id and client.user_id != target_user_id:
            return False
        org_id = envelope.get("organization_id")
        if org_id and client.organization_id and org_id != client.organization_id and client.role != "ADMIN":
            return False
        if required_permission:
            if client.role == "ADMIN":
                return True
            if required_permission not in client.permissions:
                return False
        return True

    async def _send_json_safe(self, client: ConnectedClient, envelope: Dict[str, Any]) -> bool:
        try:
            await client.websocket.send_json(envelope)
            return True
        except Exception:
            return False

    async def _close_safe(self, client: ConnectedClient, code: int, reason: str) -> None:
        try:
            await client.websocket.close(code=code, reason=reason)
        except Exception:
            pass

    async def dispatch_async(
        self,
        envelope: Dict[str, Any],
        required_permission: Optional[str] = None,
        target_user_id: Optional[str] = None,
    ) -> int:
        with self._lock:
            clients = list(self._clients.values())

        delivered = 0
        dead_ids: List[str] = []
        for client in clients:
            if not self._is_authorized(client, envelope, required_permission, target_user_id):
                continue
            ok = await self._send_json_safe(client, envelope)
            if ok:
                delivered += 1
            else:
                dead_ids.append(client.connection_id)

        if dead_ids:
            with self._lock:
                for cid in dead_ids:
                    self._clients.pop(cid, None)
        return delivered

    def dispatch_sync(
        self,
        envelope: Dict[str, Any],
        required_permission: Optional[str] = None,
        target_user_id: Optional[str] = None,
    ) -> None:
        with self._lock:
            has_clients = bool(self._clients)
            loop = self._main_loop
        if not has_clients or loop is None or loop.is_closed():
            return

        try:
            running = asyncio.get_running_loop()
            if running is loop:
                running.create_task(self.dispatch_async(envelope, required_permission, target_user_id))
                return
        except RuntimeError:
            pass

        try:
            asyncio.run_coroutine_threadsafe(
                self.dispatch_async(envelope, required_permission, target_user_id),
                loop,
            )
        except Exception as exc:
            logger.debug("WebSocket cross-thread dispatch skipped: %s", exc)

    def terminate_user_connections(self, user_id: str, reason: str = "access_revoked", code: int = 4003) -> int:
        with self._lock:
            targets = [c for c in self._clients.values() if c.user_id == user_id]
            for t in targets:
                self._clients.pop(t.connection_id, None)
            loop = self._main_loop

        if not targets or loop is None or loop.is_closed():
            return len(targets)

        async def _close_all():
            for t in targets:
                await self._send_json_safe(
                    t,
                    {
                        "event_type": "auth.connection_terminated",
                        "reason": reason,
                        "event_timestamp": _utc_now().isoformat(),
                    },
                )
                await self._close_safe(t, code, reason)

        try:
            running = asyncio.get_running_loop()
            if running is loop:
                running.create_task(_close_all())
                return len(targets)
        except RuntimeError:
            pass

        try:
            asyncio.run_coroutine_threadsafe(_close_all(), loop)
        except Exception:
            pass
        return len(targets)

    def terminate_session_connections(self, session_id: str, reason: str = "session_revoked", code: int = 4001) -> int:
        with self._lock:
            targets = [c for c in self._clients.values() if c.session_id == session_id]
            for t in targets:
                self._clients.pop(t.connection_id, None)
            loop = self._main_loop

        if not targets or loop is None or loop.is_closed():
            return len(targets)

        async def _close_all():
            for t in targets:
                await self._send_json_safe(
                    t,
                    {
                        "event_type": "auth.session_revoked",
                        "reason": reason,
                        "event_timestamp": _utc_now().isoformat(),
                    },
                )
                await self._close_safe(t, code, reason)

        try:
            running = asyncio.get_running_loop()
            if running is loop:
                running.create_task(_close_all())
                return len(targets)
        except RuntimeError:
            pass

        try:
            asyncio.run_coroutine_threadsafe(_close_all(), loop)
        except Exception:
            pass
        return len(targets)

    def active_count(self) -> int:
        with self._lock:
            return len(self._clients)


realtime_manager = RealtimeConnectionManager()


class OutboxService:
    """Transactional outbox writer + post-commit WebSocket / optional Redis Pub/Sub publisher."""

    @staticmethod
    def build_envelope(evt: OutboxEvent) -> Dict[str, Any]:
        try:
            changed_fields = json.loads(evt.changed_fields_json or "[]")
        except Exception:
            changed_fields = []
        try:
            safe_payload = json.loads(evt.payload_json or "{}")
        except Exception:
            safe_payload = {}

        return {
            "event_id": evt.id,
            "seq_id": evt.seq_id,
            "event_type": evt.event_type,
            "event_version": evt.event_version,
            "organization_id": evt.organization_id,
            "actor_user_id": evt.actor_user_id,
            "actor_username": evt.actor_username,
            "actor_role": evt.actor_role,
            "resource_type": evt.resource_type,
            "resource_id": evt.resource_id,
            "event_timestamp": (evt.created_at.isoformat() if evt.created_at else _utc_now().isoformat()),
            "entity_version": evt.entity_version,
            "changed_fields": changed_fields,
            "relevant_safe_payload": safe_payload,
        }

    @staticmethod
    def stage_event(
        db: Session,
        *,
        event_type: str,
        resource_type: str,
        resource_id: str,
        actor_user: Optional[User] = None,
        actor_username: Optional[str] = None,
        actor_role: Optional[str] = None,
        organization_id: str = "org-primary-enterprise",
        entity_version: Optional[int] = None,
        changed_fields: Optional[List[str]] = None,
        payload: Optional[Dict[str, Any]] = None,
        required_permission: Optional[str] = None,
        target_user_id: Optional[str] = None,
        notify_user_ids: Optional[Iterable[str]] = None,
        notify_roles: Optional[Iterable[str]] = None,
        notification_title: Optional[str] = None,
        notification_message: Optional[str] = None,
        notification_severity: str = "INFO",
    ) -> OutboxEvent:
        """Stage an OutboxEvent (and optional UserNotifications) inside the open DB transaction."""
        event_id = f"evt-{uuid.uuid4().hex[:14]}"
        safe_payload = sanitize_payload(payload or {})
        evt = OutboxEvent(
            id=event_id,
            event_type=event_type,
            event_version=1,
            organization_id=(actor_user.organization_id if actor_user else organization_id),
            actor_user_id=(actor_user.id if actor_user else None),
            actor_username=(actor_user.username if actor_user else (actor_username or "system")),
            actor_role=(actor_user.role if actor_user else (actor_role or "SYSTEM")),
            resource_type=resource_type,
            resource_id=str(resource_id),
            entity_version=entity_version,
            changed_fields_json=json.dumps(changed_fields or []),
            payload_json=json.dumps(safe_payload),
            required_permission=required_permission,
            target_user_id=target_user_id,
            created_at=_utc_now(),
        )
        db.add(evt)

        recipient_ids: Set[str] = set(notify_user_ids or [])
        if notify_roles:
            role_set = {str(r).upper() for r in notify_roles}
            matched_users = db.query(User.id).filter(User.is_active == True, User.role.in_(role_set)).all()
            for (uid,) in matched_users:
                recipient_ids.add(uid)

        if actor_user and len(recipient_ids) > 1:
            # Keep notifications relevant: avoid notifying actor about their own routine write unless direct target
            if target_user_id != actor_user.id:
                recipient_ids.discard(actor_user.id)

        if recipient_ids and notification_title and notification_message:
            for uid in recipient_ids:
                db.add(
                    UserNotification(
                        id=f"notif-{uuid.uuid4().hex[:12]}",
                        user_id=uid,
                        event_id=event_id,
                        event_type=event_type,
                        title=notification_title[:160],
                        message=notification_message,
                        resource_type=resource_type,
                        resource_id=str(resource_id),
                        severity=notification_severity,
                        is_read=False,
                        created_at=_utc_now(),
                    )
                )

        return evt

    @staticmethod
    def _publish_redis_if_configured(envelope: Dict[str, Any]) -> None:
        redis_url = os.getenv("REDIS_URL", "").strip()
        if not redis_url:
            return
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(redis_url, socket_connect_timeout=0.5, socket_timeout=0.5)
            client.publish("aegisstor:realtime_events", json.dumps(envelope))
        except Exception as exc:
            logger.debug("Redis pub/sub publish skipped: %s", exc)

    @classmethod
    def publish_after_commit(cls, db: Session, evt: OutboxEvent) -> Dict[str, Any]:
        """Publish an already-committed OutboxEvent to connected WebSocket clients."""
        envelope = cls.build_envelope(evt)
        try:
            realtime_manager.dispatch_sync(
                envelope,
                required_permission=evt.required_permission,
                target_user_id=evt.target_user_id,
            )
            cls._publish_redis_if_configured(envelope)
            evt.published_at = _utc_now()
            db.commit()
        except Exception as exc:
            evt.delivery_error = str(exc)[:500]
            try:
                db.commit()
            except Exception:
                db.rollback()
        return envelope

    @classmethod
    def emit_and_commit(
        cls,
        db: Session,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Convenience helper: stage outbox + notifications, commit transaction, then publish."""
        evt = cls.stage_event(db, **kwargs)
        db.commit()
        db.refresh(evt)
        return cls.publish_after_commit(db, evt)
