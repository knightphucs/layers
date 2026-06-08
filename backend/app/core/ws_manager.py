"""
LAYERS - WebSocket Connection Manager
=============================================================
In-process registry of active WebSocket connections, indexed by room,
BACKED BY REDIS PUB/SUB so features work across many workers.

THE PROBLEM THIS FIXES
----------------------
The registry (self.active) only knows about sockets connected to THIS
worker process. When a REST endpoint on worker B calls manager.broadcast(),
the recipient's socket may live on worker A → the message is silently lost.

THE FIX
-------
broadcast() now PUBLISHES the message to a Redis channel `ws:room:{room_id}`.
Every worker runs a background listener (start_pubsub) subscribed to
`ws:room:*`; on receipt it delivers to ITS OWN local sockets in that room.
So a broadcast from any worker reaches every connected client everywhere.

PUBLIC API: connect(), disconnect(), send_personal(), broadcast(room_id, message, exclude=ws)
INTROSPECTION: users_in_room(), stats(), room_size(), total_connections(), total_rooms()

GRACEFUL FALLBACK: If Redis is unavailable, broadcast() delivers to local
sockets directly (original single-process behavior from Week 6).
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Set
from uuid import UUID

from fastapi import WebSocket

from app.core.redis_client import get_optional_redis

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "ws:room:"
CHANNEL_PATTERN = "ws:room:*"
USER_CHANNEL_PREFIX = "ws:user:"
USER_CHANNEL_PATTERN = "ws:user:*"

class ConnectionManager:
    """
    Tracks active WebSocket connections per room, bridged via Redis Pub/Sub.
    
    Two indexes for O(1) lookups locally:
      - active[room_id] -> set of WebSocket
      - ws_meta[WebSocket] -> {"room_id": UUID, "user_id": UUID}
    """

    def __init__(self) -> None:
        self.active: Dict[UUID, Set[WebSocket]] = {}
        self.ws_meta: Dict[WebSocket, Dict[str, UUID]] = {}
        self._pubsub_task: Optional[asyncio.Task] = None

    # ============================================================
    # CONNECT / DISCONNECT (local registry)
    # ============================================================

    async def connect(self, websocket: WebSocket, room_id: UUID, user_id: UUID) -> None:
        """
        Accept the WebSocket and register it under the room.

        IMPORTANT: caller is responsible for awaiting websocket.accept()
        BEFORE calling connect(). We do NOT accept here so the caller can
        send a custom close code if pre-accept validation fails.
        """
        self.active.setdefault(room_id, set()).add(websocket)
        self.ws_meta[websocket] = {"room_id": room_id, "user_id": user_id}
        
        logger.info(
            "WS CONNECT user=%s room=%s (room now has %d local clients)",
            user_id, room_id, len(self.active[room_id]),
        )

    def disconnect(self, websocket: WebSocket) -> Optional[Dict[str, UUID]]:
        """
        Remove the WebSocket from all indexes.
        Returns the meta dict {"room_id", "user_id"} if registered, else None.
        Safe to call multiple times.
        """
        meta = self.ws_meta.pop(websocket, None)
        if meta is not None:
            room_id = meta["room_id"]
            conns = self.active.get(room_id)
            if conns:
                conns.discard(websocket)
                if not conns:
                    # No more clients in this room — drop the empty set
                    self.active.pop(room_id, None)
            logger.info("WS DISCONNECT user=%s room=%s", meta["user_id"], room_id)
        return meta
    
    # ============================================================
    # SEND
    # ============================================================

    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """
        Send a JSON payload to a single WebSocket.
        Returns True on success, False on failure (and removes the connection).
        """
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:  # noqa: BLE001
            logger.debug("WS send_personal failed, dropping socket: %s", e)
            self.disconnect(websocket)
            return False

    async def broadcast(
        self,
        room_id: UUID,
        message: Dict[str, Any],
        *,
        exclude: Optional[WebSocket] = None,
    ) -> None:
        """
        Deliver `message` to every client in `room_id` across all workers.
        Publishes to Redis; falls back to local-only if Redis is down.
        `exclude` (a socket) is translated to its user_id for cross-process use.
        """
        exclude_user_id: Optional[UUID] = None
        if exclude is not None:
            meta = self.ws_meta.get(exclude)
            if meta:
                exclude_user_id = meta["user_id"]

        client = get_optional_redis()
        if client is not None:
            envelope = {
                "room_id": str(room_id),
                "exclude_user_id": str(exclude_user_id) if exclude_user_id else None,
                "message": message,
            }
            try:
                await client.publish(CHANNEL_PREFIX + str(room_id), json.dumps(envelope))
                return  # local delivery happens via the pubsub listener
            except Exception as e:  # noqa: BLE001
                logger.warning("Redis publish failed, local fallback: %s", e)

        # Single-process / Redis-down path
        await self._local_broadcast(
            room_id, message, exclude_user_id=exclude_user_id, exclude_ws=exclude
        )
    
    async def send_to_user(self, user_id: UUID, message: Dict[str, Any]) -> None:
        """
        Deliver a message to ALL of a user's sockets, across every room and
        every worker. Used for user-scoped events like `level_up`.
        Publishes to `ws:user:{id}`; falls back to local delivery if Redis down.
        """
        client = get_optional_redis()
        if client is not None:
            envelope = {
                "user_id": str(user_id),
                "message": message,
            }
            try:
                await client.publish(USER_CHANNEL_PREFIX + str(user_id), json.dumps(envelope))
                return
            except Exception as e:  # noqa: BLE001
                logger.warning("Redis publish to user failed, local fallback: %s", e)

        # Single-process / Redis-down path
        await self._local_send_to_user(user_id, message)
    
    async def _local_send_to_user(self, user_id: UUID, message: Dict[str, Any]) -> None:
        uid = str(user_id)
        for ws, meta in list(self.ws_meta.items()):
            if str(meta["user_id"]) == uid:
                try:
                    await ws.send_json(message)
                except Exception as e:  # noqa: BLE001
                    logger.debug("WS send_to_user failed, dropping socket: %s", e)
                    self.disconnect(ws)

    # ============================================================
    # LOCAL DELIVERY (used by fallback AND by the pubsub listener)
    # ============================================================

    async def _local_broadcast(
        self,
        room_id: UUID,
        message: Dict[str, Any],
        exclude_user_id: Optional[Any] = None,
        exclude_ws: Optional[WebSocket] = None,
    ) -> None:
        exclude_user_id = str(exclude_user_id) if exclude_user_id else None
        for ws in list(self.active.get(room_id, set())):
            if exclude_ws is not None and ws is exclude_ws:
                continue
            meta = self.ws_meta.get(ws)
            if exclude_user_id and meta and str(meta["user_id"]) == exclude_user_id:
                continue
            try:
                await ws.send_json(message)
            except Exception as e:  # noqa: BLE001
                logger.debug("broadcast send failed, dropping socket: %s", e)
                self.disconnect(ws)

    async def _deliver_envelope(self, envelope: Dict[str, Any]) -> None:
        """Handle one envelope received from Redis → deliver to local sockets."""
        # User-scoped envelope (e.g. level_up)
        if "user_id" in envelope and "room_id" not in envelope:
            await self._local_send_to_user(
                envelope["user_id"], envelope.get("message", {})
            )
            return
        # Room-scoped envelope
        try:
            room_id = UUID(envelope["room_id"])
        except (KeyError, ValueError):
            return
        await self._local_broadcast(
            room_id,
            envelope.get("message", {}),
            exclude_user_id=envelope.get("exclude_user_id"),
        )

    # ============================================================
    # PUB/SUB LISTENER (one per worker, started in app lifespan)
    # ============================================================

    async def start_pubsub(self) -> None:
        """Start the background listener if Redis is available."""
        client = get_optional_redis()
        if client is None:
            logger.warning("⚠️ WS pub/sub disabled (Redis down) — single-process mode.")
            return
        if self._pubsub_task and not self._pubsub_task.done():
            return
        self._pubsub_task = asyncio.create_task(self._pubsub_listener(client))
        logger.info("✅ WS pub/sub listener started (%s, %s)", CHANNEL_PATTERN, USER_CHANNEL_PATTERN)

    async def _pubsub_listener(self, client) -> None:
        pubsub = client.pubsub()
        await pubsub.psubscribe(CHANNEL_PATTERN, USER_CHANNEL_PATTERN)
        try:
            async for msg in pubsub.listen():
                if msg.get("type") != "pmessage":
                    continue
                try:
                    envelope = json.loads(msg["data"])
                    await self._deliver_envelope(envelope)
                except Exception as e:  # noqa: BLE001
                    logger.warning("WS pubsub deliver error: %s", e)
        except asyncio.CancelledError:
            pass
        finally:
            try:
                await pubsub.punsubscribe(CHANNEL_PATTERN, USER_CHANNEL_PATTERN)
                await pubsub.aclose()
            except Exception:  # noqa: BLE001
                pass

    async def stop_pubsub(self) -> None:
        """Cancel the background listener on shutdown."""
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._pubsub_task = None

    # ============================================================
    # INTROSPECTION (Local Worker Context)
    # ============================================================

    def room_size(self, room_id: UUID) -> int:
        """How many active WebSockets are in this room on THIS worker."""
        return len(self.active.get(room_id, set()))
    
    def users_in_room(self, room_id: UUID) -> Set[UUID]:
        """Unique user IDs currently connected to this room on THIS worker."""
        return {
            self.ws_meta[ws]["user_id"]
            for ws in self.active.get(room_id, set())
            if ws in self.ws_meta
        }

    def total_connections(self) -> int:
        """Total active WebSockets across all rooms on THIS worker."""
        return len(self.ws_meta)

    def total_rooms(self) -> int:
        """Total rooms with at least one active WebSocket on THIS worker."""
        return len(self.active)

    def stats(self) -> Dict[str, Any]:
        """Snapshot of manager state on THIS worker — useful for /health or admin endpoints."""
        return {
            "total_connections": self.total_connections(),
            "total_active_rooms": self.total_rooms(),
            "rooms": {
                str(rid): len(sockets)
                for rid, sockets in self.active.items()
            },
        }


# ============================================================
# SINGLETON
# ============================================================
# Import this directly: `from app.core.ws_manager import manager`
manager = ConnectionManager()