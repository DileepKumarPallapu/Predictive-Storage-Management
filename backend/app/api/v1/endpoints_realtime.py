import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.permissions import get_effective_permissions, require_permission
from app.auth.security import (
    decode_access_token,
    get_current_user,
    hash_token,
    is_token_revoked,
)
from app.database import SessionLocal, get_db
from app.models.entities import (
    Device,
    OperationalTask,
    OutboxEvent,
    TaskComment,
    User,
    UserNotification,
    UserPresence,
    UserSession,
)
from app.services.audit_service import AuditService
from app.realtime.event_bus import (
    ConnectedClient,
    OutboxService,
    raise_if_version_conflict,
    realtime_manager,
)

router = APIRouter()

VALID_TASK_STATUSES = {
    "ASSIGNED",
    "ACKNOWLEDGED",
    "IN_PROGRESS",
    "WAITING",
    "COMPLETED",
    "CANCELLED",
}
VALID_TASK_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _serialize_task(db: Session, task: OperationalTask) -> Dict[str, Any]:
    assignee = db.query(User).filter(User.id == task.assigned_to_user_id).first()
    creator = db.query(User).filter(User.id == task.created_by_user_id).first()
    device = db.query(Device).filter(Device.id == task.linked_device_id).first() if task.linked_device_id else None
    comments = (
        db.query(TaskComment)
        .filter(TaskComment.task_id == task.id)
        .order_by(TaskComment.created_at.asc())
        .all()
    )
    return {
        "id": task.id,
        "organization_id": task.organization_id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "status": task.status,
        "assigned_to_user_id": task.assigned_to_user_id,
        "assigned_to_username": assignee.username if assignee else task.assigned_to_user_id,
        "assigned_to_role": assignee.role if assignee else None,
        "created_by_user_id": task.created_by_user_id,
        "created_by_username": creator.username if creator else task.created_by,
        "linked_device_id": task.linked_device_id,
        "linked_device_name": device.name if device else None,
        "linked_alert_id": task.linked_alert_id,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "version": task.version,
        "created_by": task.created_by,
        "updated_by": task.updated_by,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "comments": [
            {
                "id": c.id,
                "task_id": c.task_id,
                "author_user_id": c.author_user_id,
                "author_username": c.author_username,
                "author_role": c.author_role,
                "body": c.body,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in comments
        ],
    }


def _can_receive_event(user: User, perms: set, evt: OutboxEvent) -> bool:
    if evt.target_user_id and evt.target_user_id != user.id:
        return False
    if evt.organization_id and user.organization_id and evt.organization_id != user.organization_id and user.role != "ADMIN":
        return False
    if evt.required_permission and user.role != "ADMIN":
        if evt.required_permission not in perms:
            return False
    return True


def _authenticate_ws_token(db: Session, raw_token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw_token:
        return None
    if is_token_revoked(db, raw_token):
        return None
    payload = decode_access_token(raw_token)
    if not payload or "sub" not in payload:
        return None
    user = db.query(User).filter(User.username == payload["sub"], User.is_active == True).first()
    if not user:
        return None

    token_role = str(payload.get("role", "")).upper()
    if token_role and token_role != user.role:
        return None

    sid = payload.get("sid")
    sess = None
    if sid:
        sess = db.query(UserSession).filter(UserSession.id == sid).first()
    if not sess:
        token_hash = hash_token(raw_token)
        sess = db.query(UserSession).filter(UserSession.token_hash == token_hash).first()
    if sess:
        if sess.is_revoked or (sess.expires_at and sess.expires_at.replace(tzinfo=None) < _utc_now()):
            return None
        session_id = sess.id
    elif sid:
        return None
    else:
        session_id = f"ws-{uuid.uuid4().hex[:12]}"

    perms = set(get_effective_permissions(db, user.role))
    return {"user": user, "session_id": session_id, "permissions": perms}


@router.websocket("/realtime/ws")
async def realtime_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
    since_seq: Optional[int] = Query(default=None),
    route: Optional[str] = Query(default="/"),
):
    raw_token = token or websocket.cookies.get("aegisstor_session")
    if not raw_token:
        auth_hdr = websocket.headers.get("authorization", "")
        if auth_hdr.lower().startswith("bearer "):
            raw_token = auth_hdr[7:].strip()

    db = SessionLocal()
    auth_info = None
    try:
        auth_info = _authenticate_ws_token(db, raw_token)
    finally:
        db.close()

    if not auth_info:
        await websocket.close(code=4001, reason="Unauthorized or expired session")
        return

    user: User = auth_info["user"]
    session_id: str = auth_info["session_id"]
    perms: set = auth_info["permissions"]

    await websocket.accept()
    conn_id = f"conn-{uuid.uuid4().hex[:12]}"
    loop = asyncio.get_running_loop()

    client = ConnectedClient(
        connection_id=conn_id,
        websocket=websocket,
        user_id=user.id,
        username=user.username,
        role=user.role,
        organization_id=user.organization_id,
        session_id=session_id,
        permissions=perms,
        loop=loop,
    )
    realtime_manager.register(client)

    # Record authenticated presence + send initial handshake & missed events
    db = SessionLocal()
    try:
        presence = db.query(UserPresence).filter(UserPresence.session_id == session_id).first()
        now = _utc_now()
        if presence:
            presence.is_online = True
            presence.last_heartbeat_at = now
            presence.disconnected_at = None
            presence.current_route = (route or "/")[:128]
            presence.role = user.role
        else:
            db.add(
                UserPresence(
                    session_id=session_id,
                    user_id=user.id,
                    username=user.username,
                    role=user.role,
                    current_route=(route or "/")[:128],
                    is_online=True,
                    connected_at=now,
                    last_heartbeat_at=now,
                )
            )
        latest_evt = db.query(OutboxEvent).order_by(OutboxEvent.seq_id.desc()).first()
        current_seq = latest_evt.seq_id if latest_evt else 0

        evt = OutboxService.stage_event(
            db,
            event_type="presence.connected",
            resource_type="presence",
            resource_id=user.id,
            actor_user=user,
            payload={"username": user.username, "role": user.role, "route": (route or "/")[:128]},
            required_permission="system.health.view",
        )
        db.commit()
        db.refresh(evt)
        OutboxService.publish_after_commit(db, evt)

        await websocket.send_json(
            {
                "event_type": "system.connected",
                "connection_id": conn_id,
                "user_id": user.id,
                "username": user.username,
                "role": user.role,
                "current_seq": current_seq,
                "event_timestamp": now.isoformat(),
            }
        )

        if since_seq is not None and since_seq >= 0:
            missed = (
                db.query(OutboxEvent)
                .filter(OutboxEvent.seq_id > since_seq)
                .order_by(OutboxEvent.seq_id.asc())
                .limit(200)
                .all()
            )
            for m in missed:
                if _can_receive_event(user, perms, m):
                    await websocket.send_json(OutboxService.build_envelope(m))
    finally:
        db.close()

    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                msg = json.loads(raw_msg) if raw_msg else {}
            except Exception:
                msg = {"type": "ping"}
            msg_type = msg.get("type", "ping")
            if msg_type in {"ping", "heartbeat", "presence_route"}:
                hb_db = SessionLocal()
                try:
                    # Verify user & session are still active on heartbeat
                    fresh_user = hb_db.query(User).filter(User.id == user.id).first()
                    if not fresh_user or not fresh_user.is_active or fresh_user.role != user.role:
                        await websocket.close(code=4003, reason="User deactivated or role changed")
                        break
                    fresh_sess = hb_db.query(UserSession).filter(UserSession.id == session_id).first()
                    if fresh_sess and fresh_sess.is_revoked:
                        await websocket.close(code=4001, reason="Session revoked")
                        break
                    p = hb_db.query(UserPresence).filter(UserPresence.session_id == session_id).first()
                    if p:
                        p.last_heartbeat_at = _utc_now()
                        if msg.get("route"):
                            p.current_route = str(msg["route"])[:128]
                        hb_db.commit()
                finally:
                    hb_db.close()

                await websocket.send_json(
                    {
                        "event_type": "system.pong",
                        "event_timestamp": _utc_now().isoformat(),
                    }
                )
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        realtime_manager.unregister(conn_id)
        disc_db = SessionLocal()
        try:
            p = disc_db.query(UserPresence).filter(UserPresence.session_id == session_id).first()
            if p:
                p.is_online = False
                p.disconnected_at = _utc_now()
            evt = OutboxService.stage_event(
                disc_db,
                event_type="presence.disconnected",
                resource_type="presence",
                resource_id=user.id,
                actor_user=user,
                payload={"username": user.username, "role": user.role},
                required_permission="system.health.view",
            )
            disc_db.commit()
            disc_db.refresh(evt)
            OutboxService.publish_after_commit(disc_db, evt)
        except Exception:
            disc_db.rollback()
        finally:
            disc_db.close()


@router.get("/realtime/events")
def replay_realtime_events(
    since_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cursor-based recovery endpoint returning committed outbox events after since_seq."""
    perms = set(get_effective_permissions(db, current_user.role))
    events = (
        db.query(OutboxEvent)
        .filter(OutboxEvent.seq_id > since_seq)
        .order_by(OutboxEvent.seq_id.asc())
        .limit(limit)
        .all()
    )
    authorized = [OutboxService.build_envelope(e) for e in events if _can_receive_event(current_user, perms, e)]
    latest = db.query(OutboxEvent).order_by(OutboxEvent.seq_id.desc()).first()
    return {
        "since_seq": since_seq,
        "latest_seq": latest.seq_id if latest else since_seq,
        "events": authorized,
    }


@router.get("/realtime/presence")
def get_live_presence(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns currently authenticated online users based on live WS sessions and recent heartbeats."""
    cutoff = _utc_now() - timedelta(seconds=90)
    stale = (
        db.query(UserPresence)
        .filter(UserPresence.is_online == True, UserPresence.last_heartbeat_at < cutoff)
        .all()
    )
    if stale:
        for s in stale:
            s.is_online = False
            s.disconnected_at = _utc_now()
        db.commit()

    online_rows = (
        db.query(UserPresence)
        .filter(UserPresence.is_online == True)
        .order_by(UserPresence.last_heartbeat_at.desc())
        .all()
    )
    # Deduplicate by user_id while preserving session count
    by_user: Dict[str, Dict[str, Any]] = {}
    for row in online_rows:
        if row.user_id not in by_user:
            by_user[row.user_id] = {
                "user_id": row.user_id,
                "username": row.username,
                "role": row.role,
                "current_route": row.current_route,
                "connected_at": row.connected_at.isoformat() if row.connected_at else None,
                "last_heartbeat_at": row.last_heartbeat_at.isoformat() if row.last_heartbeat_at else None,
                "active_sessions": 1,
            }
        else:
            by_user[row.user_id]["active_sessions"] += 1

    return {
        "online_count": len(by_user),
        "active_connections": realtime_manager.active_count(),
        "users": list(by_user.values()),
    }


@router.get("/realtime/activity")
def get_shared_activity_timeline(
    limit: int = Query(default=40, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns shared persistent activity timeline derived from committed outbox events."""
    perms = set(get_effective_permissions(db, current_user.role))
    rows = (
        db.query(OutboxEvent)
        .filter(~OutboxEvent.event_type.in_(["presence.connected", "presence.disconnected"]))
        .order_by(OutboxEvent.seq_id.desc())
        .limit(limit * 2)
        .all()
    )
    items = []
    for row in rows:
        if _can_receive_event(current_user, perms, row):
            items.append(OutboxService.build_envelope(row))
            if len(items) >= limit:
                break
    return {"items": items, "count": len(items)}


# --- Persistent User Notifications ---


@router.get("/notifications")
def list_my_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(UserNotification).filter(UserNotification.user_id == current_user.id)
    if unread_only:
        q = q.filter(UserNotification.is_read == False)
    rows = q.order_by(UserNotification.created_at.desc()).limit(limit).all()
    unread_count = (
        db.query(UserNotification)
        .filter(UserNotification.user_id == current_user.id, UserNotification.is_read == False)
        .count()
    )
    return {
        "unread_count": unread_count,
        "notifications": [
            {
                "id": n.id,
                "event_id": n.event_id,
                "event_type": n.event_type,
                "title": n.title,
                "message": n.message,
                "resource_type": n.resource_type,
                "resource_id": n.resource_id,
                "severity": n.severity,
                "is_read": n.is_read,
                "read_at": n.read_at.isoformat() if n.read_at else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in rows
        ],
    }


@router.post("/notifications/{notif_id}/read")
def mark_notification_read(
    notif_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(UserNotification)
        .filter(UserNotification.id == notif_id, UserNotification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if not notif.is_read:
        notif.is_read = True
        notif.read_at = _utc_now()
        OutboxService.emit_and_commit(
            db,
            event_type="notification.read",
            resource_type="notification",
            resource_id=notif.id,
            actor_user=current_user,
            target_user_id=current_user.id,
            payload={"notification_id": notif.id, "is_read": True},
        )
    return {"status": "read", "id": notif.id}


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = _utc_now()
    updated = (
        db.query(UserNotification)
        .filter(UserNotification.user_id == current_user.id, UserNotification.is_read == False)
        .update({"is_read": True, "read_at": now})
    )
    OutboxService.emit_and_commit(
        db,
        event_type="notification.read_all",
        resource_type="notification",
        resource_id="all",
        actor_user=current_user,
        target_user_id=current_user.id,
        payload={"marked_count": updated},
    )
    return {"status": "read_all", "marked_count": updated}


# --- Persistent Collaborative Operational Tasks ---


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=160)
    description: str = Field(default="")
    priority: str = Field(default="MEDIUM")
    assigned_to_user_id: str
    linked_device_id: Optional[str] = None
    linked_alert_id: Optional[str] = None
    due_date: Optional[datetime] = None


class TaskUpdateRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to_user_id: Optional[str] = None
    description: Optional[str] = None
    expected_version: Optional[int] = None


class TaskCommentCreateRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


@router.get("/tasks")
def list_operational_tasks(
    status_filter: Optional[str] = Query(default=None),
    assigned_to_me: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(OperationalTask)
    if current_user.role not in {"ADMIN", "AUDITOR"} and assigned_to_me:
        q = q.filter(OperationalTask.assigned_to_user_id == current_user.id)
    elif current_user.role == "VIEWER":
        q = q.filter(OperationalTask.assigned_to_user_id == current_user.id)
    elif assigned_to_me:
        q = q.filter(OperationalTask.assigned_to_user_id == current_user.id)

    if status_filter:
        q = q.filter(OperationalTask.status == status_filter.upper())

    tasks = q.order_by(OperationalTask.created_at.desc()).limit(200).all()
    return {"tasks": [_serialize_task(db, t) for t in tasks], "count": len(tasks)}


@router.post("/tasks", status_code=201)
def create_operational_task(
    req: TaskCreateRequest,
    current_user: User = Depends(require_permission("alerts.acknowledge")),
    db: Session = Depends(get_db),
):
    priority = req.priority.upper()
    if priority not in VALID_TASK_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Invalid priority. Must be one of {sorted(VALID_TASK_PRIORITIES)}")

    assignee = db.query(User).filter(User.id == req.assigned_to_user_id, User.is_active == True).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assigned user not found or inactive")

    if req.linked_device_id:
        dev = db.query(Device).filter(Device.id == req.linked_device_id).first()
        if not dev:
            raise HTTPException(status_code=404, detail="Linked storage volume not found")

    task = OperationalTask(
        id=f"task-{uuid.uuid4().hex[:10]}",
        organization_id=current_user.organization_id,
        title=req.title.strip(),
        description=req.description.strip(),
        priority=priority,
        status="ASSIGNED",
        assigned_to_user_id=assignee.id,
        created_by_user_id=current_user.id,
        linked_device_id=req.linked_device_id,
        linked_alert_id=req.linked_alert_id,
        due_date=req.due_date,
        version=1,
        created_by=current_user.username,
        updated_by=current_user.username,
    )
    db.add(task)
    db.flush()
    serialized = _serialize_task(db, task)
    evt = OutboxService.stage_event(
        db,
        event_type="task.assigned",
        resource_type="task",
        resource_id=task.id,
        actor_user=current_user,
        entity_version=task.version,
        changed_fields=["title", "status", "assigned_to_user_id", "priority"],
        payload=serialized,
        notify_user_ids=[assignee.id],
        notification_title=f"New Task Assigned: {task.title}",
        notification_message=f"{current_user.username} assigned you a {priority} priority task: {task.title}",
        notification_severity=("CRITICAL" if priority == "CRITICAL" else "WARNING" if priority == "HIGH" else "INFO"),
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)
    AuditService.log_event(
        db=db,
        action="TASK_ASSIGNED",
        target_type="TASK",
        target_id=task.id,
        user=current_user.username,
        user_id=current_user.id,
        user_role=current_user.role,
        organization_id=current_user.organization_id,
        details={"title": task.title, "assigned_to": assignee.username, "priority": priority},
    )
    return serialized


@router.patch("/tasks/{task_id}")
def update_operational_task(
    task_id: str,
    req: TaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(OperationalTask).filter(OperationalTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role != "ADMIN" and task.assigned_to_user_id != current_user.id and task.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only assigned operator or administrator can update this task")

    raise_if_version_conflict(
        req.expected_version,
        task.version,
        "OperationalTask",
        task.id,
        _serialize_task(db, task),
    )

    changed: List[str] = []
    if req.status is not None:
        new_status = req.status.upper()
        if new_status not in VALID_TASK_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {sorted(VALID_TASK_STATUSES)}")
        if new_status != task.status:
            task.status = new_status
            changed.append("status")
            if new_status == "COMPLETED":
                task.completed_at = _utc_now()
    if req.priority is not None:
        new_prio = req.priority.upper()
        if new_prio not in VALID_TASK_PRIORITIES:
            raise HTTPException(status_code=400, detail="Invalid priority")
        if new_prio != task.priority:
            task.priority = new_prio
            changed.append("priority")
    if req.assigned_to_user_id is not None and req.assigned_to_user_id != task.assigned_to_user_id:
        if current_user.role != "ADMIN":
            raise HTTPException(status_code=403, detail="Only administrators can reassign tasks")
        assignee = db.query(User).filter(User.id == req.assigned_to_user_id, User.is_active == True).first()
        if not assignee:
            raise HTTPException(status_code=404, detail="Target assignee not found or inactive")
        task.assigned_to_user_id = assignee.id
        changed.append("assigned_to_user_id")
    if req.description is not None and req.description != task.description:
        task.description = req.description
        changed.append("description")

    task.version += 1
    task.updated_by = current_user.username
    task.updated_at = _utc_now()
    db.flush()
    serialized = _serialize_task(db, task)
    notify_targets = {task.assigned_to_user_id, task.created_by_user_id}
    notify_targets.discard(current_user.id)
    evt = OutboxService.stage_event(
        db,
        event_type="task.updated",
        resource_type="task",
        resource_id=task.id,
        actor_user=current_user,
        entity_version=task.version,
        changed_fields=changed,
        payload=serialized,
        notify_user_ids=notify_targets,
        notification_title=f"Task Updated: {task.title}",
        notification_message=f"{current_user.username} changed status to {task.status}",
        notification_severity=("SUCCESS" if task.status == "COMPLETED" else "INFO"),
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)
    AuditService.log_event(
        db=db,
        action="TASK_UPDATED",
        target_type="TASK",
        target_id=task.id,
        user=current_user.username,
        user_id=current_user.id,
        user_role=current_user.role,
        organization_id=current_user.organization_id,
        details={"status": task.status, "changed": changed, "version": task.version},
    )
    return serialized


@router.post("/tasks/{task_id}/comments", status_code=201)
def add_task_comment(
    task_id: str,
    req: TaskCommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(OperationalTask).filter(OperationalTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current_user.role != "ADMIN" and task.assigned_to_user_id != current_user.id and task.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to comment on this task")

    comment = TaskComment(
        id=f"tcmt-{uuid.uuid4().hex[:10]}",
        task_id=task.id,
        author_user_id=current_user.id,
        author_username=current_user.username,
        author_role=current_user.role,
        body=req.body.strip(),
        created_at=_utc_now(),
    )
    db.add(comment)
    task.version += 1
    task.updated_by = current_user.username
    task.updated_at = _utc_now()
    db.flush()

    serialized = _serialize_task(db, task)
    notify_targets = {task.assigned_to_user_id, task.created_by_user_id}
    notify_targets.discard(current_user.id)
    evt = OutboxService.stage_event(
        db,
        event_type="task.comment_added",
        resource_type="task",
        resource_id=task.id,
        actor_user=current_user,
        entity_version=task.version,
        changed_fields=["comments"],
        payload={
            "task": serialized,
            "comment": {
                "id": comment.id,
                "author_username": comment.author_username,
                "author_role": comment.author_role,
                "body": comment.body,
                "created_at": comment.created_at.isoformat(),
            },
        },
        notify_user_ids=notify_targets,
        notification_title=f"Comment on Task: {task.title}",
        notification_message=f"{current_user.username}: {comment.body[:100]}",
        notification_severity="INFO",
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)
    return serialized
