"""In-process WebSocket fanout for Control Plane events.

Events are persisted in the database outbox before this manager is called.
Clients recover missed events through the authenticated HTTP event cursor.
For multi-instance deployment, replace/extend this fanout with Redis Pub/Sub
while retaining the database outbox as the durable source of truth.
"""
import asyncio
import logging
from collections import defaultdict
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger("aegisstor.control_plane.realtime")


class ControlPlaneConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, organization_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[organization_id].add(websocket)

    async def disconnect(self, organization_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(organization_id)
            if connections is not None:
                connections.discard(websocket)
                if not connections:
                    self._connections.pop(organization_id, None)

    async def broadcast(self, organization_id: str, payload: dict[str, Any]) -> int:
        async with self._lock:
            recipients = list(self._connections.get(organization_id, set()))

        delivered = 0
        stale: list[WebSocket] = []
        for websocket in recipients:
            try:
                await websocket.send_json(payload)
                delivered += 1
            except Exception:
                stale.append(websocket)

        for websocket in stale:
            await self.disconnect(organization_id, websocket)

        if stale:
            logger.warning("Removed %s stale Control Plane WebSocket connection(s).", len(stale))
        return delivered

    async def count(self, organization_id: str) -> int:
        async with self._lock:
            return len(self._connections.get(organization_id, set()))


control_plane_connections = ControlPlaneConnectionManager()
