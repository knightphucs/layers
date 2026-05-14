"""
LAYERS - WebSocket Connection Manager
=====================================================
In-process registry of active WebSocket connections, indexed by room.

KEY RESPONSIBILITIES:
  - Track WebSocket → (room_id, user_id) bindings
  - Broadcast to all members of a room
  - Clean up on disconnect

DESIGN:
  - Singleton: import `manager` directly from this module
  - In-process only: works for single-worker deploys (development)
  - For multi-worker production: swap in a Redis pub/sub backend (deferred to Week 10)
  - Following the pattern of AntiCheatService's `_location_history` module-level dict

FAILURE HANDLING:
  - send_personal: best-effort; failed sends are logged + connection removed
  - broadcast: iterates a snapshot to avoid mutation-during-iteration errors
  - All public methods are safe to call after connect() / before disconnect()
"""

from typing import Dict, Set, Optional, Any
from uuid import UUID
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Tracks active WebSocket connections per chat room.

    Two indexes for O(1) lookups in both directions:
      - active[room_id] -> set of WebSocket
      - ws_meta[WebSocket] -> {"room_id": UUID, "user_id": UUID}
    """

    def __init__(self) -> None:
        self.active: Dict[UUID, Set[WebSocket]] = {}
        self.ws_meta: Dict[WebSocket, Dict[str, UUID]] = {}

    # ============================================================
    # CONNECT / DISCONNECT
    # ============================================================

    async def connect(
        self,
        websocket: WebSocket,
        room_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Accept the WebSocket and register it under the room.

        IMPORTANT: caller is responsible for awaiting websocket.accept()
        BEFORE calling connect(). We do NOT accept here so the caller can
        send a custom close code if pre-accept validation fails.
        """
        if room_id not in self.active:
            self.active[room_id] = set()
        self.active[room_id].add(websocket)
        self.ws_meta[websocket] = {"room_id": room_id, "user_id": user_id}

        logger.info(
            f"WS CONNECT user={user_id} room={room_id} "
            f"(room now has {len(self.active[room_id])} clients)"
        )

    def disconnect(self, websocket: WebSocket) -> Optional[Dict[str, UUID]]:
        """
        Remove the WebSocket from all indexes.
        Returns the meta dict {"room_id", "user_id"} if registered, else None.
        Safe to call multiple times.
        """
        meta = self.ws_meta.pop(websocket, None)
        if not meta:
            return None

        room_id = meta["room_id"]
        if room_id in self.active:
            self.active[room_id].discard(websocket)
            if not self.active[room_id]:
                # No more clients in this room — drop the empty set
                del self.active[room_id]

        logger.info(
            f"WS DISCONNECT user={meta['user_id']} room={room_id} "
            f"(room now has {len(self.active.get(room_id, set()))} clients)"
        )
        return meta

    # ============================================================
    # SEND
    # ============================================================

    async def send_personal(self, websocket: WebSocket, payload: Dict[str, Any]) -> bool:
        """
        Send a JSON payload to a single WebSocket.
        Returns True on success, False on failure (and removes the connection).
        """
        try:
            await websocket.send_json(payload)
            return True
        except Exception as e:
            logger.warning(f"WS send_personal failed: {e}")
            self.disconnect(websocket)
            return False

    async def broadcast(
        self,
        room_id: UUID,
        payload: Dict[str, Any],
        *,
        exclude: Optional[WebSocket] = None,
    ) -> int:
        """
        Broadcast a payload to every WebSocket in a room.

        Args:
            room_id: target room
            payload: JSON-serializable dict
            exclude: optionally skip the original sender's socket

        Returns:
            Number of successful sends.
        """
        if room_id not in self.active:
            return 0

        # Snapshot so we can modify self.active during iteration
        targets = [ws for ws in self.active[room_id] if ws is not exclude]
        success_count = 0

        for ws in targets:
            ok = await self.send_personal(ws, payload)
            if ok:
                success_count += 1

        return success_count

    # ============================================================
    # INTROSPECTION
    # ============================================================

    def room_size(self, room_id: UUID) -> int:
        """How many active WebSockets are in this room."""
        return len(self.active.get(room_id, set()))
    
    def users_in_room(self, room_id: UUID) -> Set[UUID]:
        """Unqnie user IDs currently connected to this room."""
        user_ids: Set[UUID] = set()
        for ws in self.active.get(room_id, set()):
            meta = self.ws_meta.get(ws)
            if meta:
                user_ids.add(meta["user_id"])
        return user_ids

    def total_connections(self) -> int:
        """Total active WebSockets across all rooms."""
        return len(self.ws_meta)

    def total_rooms(self) -> int:
        """Total rooms with at least one active WebSocket."""
        return len(self.active)

    def stats(self) -> Dict[str, Any]:
        """Snapshot of manager state — useful for /health or admin endpoints."""
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
