"""
LAYERS - Chat API Router
========================================
WebSocket endpoint for real-time chat + minimal REST helpers.

WS ENDPOINT:
  WS /api/v1/chat/ws/{room_id}?token={jwt_access_token}

  Auth: JWT passed as a query param (WebSockets cannot send custom headers
  from browsers/React Native cleanly). Token is validated BEFORE accept().

  Close codes (see schemas.chat.WSCloseCode):
    4001 — unauthorized (bad/missing token, banned user)
    4003 — forbidden (not a member of this DIRECT room)
    4004 — room not found
    4005 — room closed
    4400 — invalid payload
    4500 — internal error

REST ENDPOINTS (for client compatibility and WS fallback):
  GET  /api/v1/chat/rooms                     — list current user's rooms
  GET  /api/v1/chat/rooms/{room_id}           — get one room (with recent messages)
  GET  /api/v1/chat/rooms/{room_id}/messages  — paginated history
  GET  /api/v1/chat/ws/stats                  — debug: connection manager state
  POST /api/v1/chat/rooms/direct              — create-or-find room (CONNECTED gate)
  POST /api/v1/chat/rooms/{room_id}/messages  — REST send (fallback for dead WS)

DESIGN NOTE: We do NOT wrap the WebSocket session in a single long-lived DB session.
On every inbound message, we open a fresh AsyncSession via the get_db generator.
This keeps Postgres connections short-lived and avoids the gotcha where a stale
session prevents other coroutines from making progress.
"""

import json
import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import and_, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_access_token
from app.core.ws_manager import manager
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.chat import ChatRoomStatus
from app.models.connection import Connection, ConnectionStatus
from app.schemas.chat import (
    ChatRoomResponse,
    ChatRoomDetail,
    MessageResponse as ChatMessageSchema,
    MessageListResponse,
    SendMessageRequest,
    WSClientMessage,
    WSClientPing,
    WSServerMessage,
    WSServerPresence,
    WSServerError,
    WSServerPong,
    WSCloseCode,
)
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat Module"])

# ============================================================
# Day 2 request schema (local — Day 5 may move to schemas/chat.py)
# ============================================================

class DirectRoomCreate(BaseModel):
    other_user_id: UUID = Field(
        ..., 
        description="The other user's UUID (must be at CONNECTED status)",
    )

# ============================================================
# Day 2 helper — verify CONNECTED status
# ============================================================
    
async def _require_connected(
    db: AsyncSession,
    user_a: UUID,
    user_b: UUID,
) -> Connection:
    """
    Look up the Connection row between two users (canonical pair) and
    verify status == CONNECTED. Raises 403 otherwise.

    Mirrors the pair-ordering convention used by ConnectionService and
    ChatService — smaller UUID first.
    """
    if user_a == user_b:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot open a chat with yourself",
        )

    a, b = (user_a, user_b) if str(user_a) < str(user_b) else (user_b, user_a)

    result = await db.execute(
        select(Connection).where(
            and_(
                Connection.user_a_id == a,
                Connection.user_b_id == b,
            )
        )
    )
    conn = result.scalar_one_or_none()

    if not conn:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You don't have a connection with this user. "
                "Send Slow Mail to start one."
            ),
        )

    if conn.status != ConnectionStatus.CONNECTED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This connection isn't open for real-time chat yet. "
                "You both need to upgrade to CONNECTED first."
            ),
        )

    return conn

# ============================================================
# REST: list user's rooms
# ============================================================

@router.get(
    "/rooms",
    response_model=List[ChatRoomResponse],
    summary="List my chat rooms",
)
async def list_my_rooms(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all DIRECT rooms the current user is a member of, newest activity first."""
    rooms = await ChatService.get_user_rooms(db, current_user.id, limit=limit)
    return [ChatRoomResponse.model_validate(r) for r in rooms]

# ============================================================
# REST: get-or-create DIRECT room
# ============================================================

@router.post(
    "/rooms/direct",
    response_model=ChatRoomDetail,
    summary="Get or create a DIRECT room with another user",
    description=(
        "Returns the existing DIRECT room (with recent messages) or creates a new one. "
        "**Requires** the two users to be at CONNECTED status — STRANGER and SIGNAL "
        "users get 403."
    ),
)
async def create_direct_room(
    data: DirectRoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify CONNECTED status
    await _require_connected(db, current_user.id, data.other_user_id)

    # Get or create room
    room = await ChatService.get_or_create_direct_room(
        db, current_user.id, data.other_user_id,
    )

    # Hydrate detail response
    recent = await ChatService.get_recent_messages(db, room.id, limit=20)
    other_user_id = (
        room.user_b_id if room.user_a_id == current_user.id else room.user_a_id
    )

    logger.info(
        f"DIRECT room {room.id} accessed by {current_user.id} "
        f"(other: {other_user_id})"
    )

    return ChatRoomDetail(
        id=room.id,
        room_type=room.room_type,
        status=room.status,
        user_a_id=room.user_a_id,
        user_b_id=room.user_b_id,
        message_count=room.message_count,
        last_activity_at=room.last_activity_at,
        created_at=room.created_at,
        recent_messages=[ChatMessageSchema.model_validate(m) for m in recent],
        other_user_id=other_user_id,
    )

# ============================================================
# REST: get one room with recent messages
# ============================================================

@router.get(
    "/rooms/{room_id}",
    response_model=ChatRoomDetail,
    summary="Get a chat room with the most recent messages",
)
async def get_room(
    room_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = await ChatService.get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found",
        )
    if not ChatService.is_member_of_room(room, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this room",
        )

    recent = await ChatService.get_recent_messages(db, room_id, limit=20)
    other_user_id = None
    if room.user_a_id and room.user_b_id:
        other_user_id = (
            room.user_b_id if room.user_a_id == current_user.id else room.user_a_id
        )

    return ChatRoomDetail(
        id=room.id,
        room_type=room.room_type,
        status=room.status,
        user_a_id=room.user_a_id,
        user_b_id=room.user_b_id,
        message_count=room.message_count,
        last_activity_at=room.last_activity_at,
        created_at=room.created_at,
        recent_messages=[ChatMessageSchema.model_validate(m) for m in recent],
        other_user_id=other_user_id,
    )


# ============================================================
# REST: paginated message history
# ============================================================

@router.get(
    "/rooms/{room_id}/messages",
    response_model=MessageListResponse,
    summary="Get paginated message history (newest first)",
)
async def get_room_messages(
    room_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[datetime] = Query(
        None,
        description="ISO datetime cursor — return messages older than this",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = await ChatService.get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found",
        )
    if not ChatService.is_member_of_room(room, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this room",
        )

    messages = await ChatService.get_room_messages(
        db, room_id, limit=limit + 1, before=before,
    )
    has_more = len(messages) > limit
    items = messages[:limit]

    next_cursor = None
    if has_more and items:
        # Cursor for next page = oldest returned message's timestamp
        next_cursor = items[-1].created_at.isoformat()

    return MessageListResponse(
        items=[ChatMessageSchema.model_validate(m) for m in items],
        has_more=has_more,
        next_cursor=next_cursor,
    )

# ============================================================
# REST: send a message (fallback for dead WS) (Week 6 Day 2)
# ============================================================

@router.post(
    "/rooms/{room_id}/messages",
    response_model=ChatMessageSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message via REST (fallback when WebSocket is unavailable)",
)
async def send_message_rest(
    room_id: UUID,
    data: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    REST send fallback. Persists the message AND broadcasts it to any
    WebSocket clients currently connected to the room — so a user with
    a dead WS can still post, and others see it instantly.
    """
    # Validate membership
    room = await ChatService.get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found",
        )
    if not ChatService.is_member_of_room(room, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this room",
        )

    # Persist
    message = await ChatService.send_message(
        db=db,
        room_id=room_id,
        sender_id=current_user.id,
        content=data.content,
    )

    # Broadcast to any active WS clients in the room
    response = ChatMessageSchema.model_validate(message)
    try:
        await manager.broadcast(
            room_id,
            WSServerMessage(data=response).model_dump(mode="json"),
        )
    except Exception as e:
        # Broadcast failure shouldn't fail the REST request — message is persisted
        logger.warning(f"REST send → WS broadcast failed: {e}")

    return response

# ============================================================
# REST: connection manager debug stats
# ============================================================

@router.get(
    "/ws/stats",
    summary="WebSocket connection manager stats (debug)",
)
async def get_ws_stats(
    current_user: User = Depends(get_current_user),
):
    """Snapshot of active WebSocket connections — useful for debugging."""
    return manager.stats()


# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================

@router.websocket("/ws/{room_id}")
async def chat_websocket(
    websocket: WebSocket,
    room_id: UUID,
    token: Optional[str] = Query(None, description="JWT access token"),
):
    """
    Real-time chat WebSocket.

    HANDSHAKE:
      1. Client connects: ws://host/api/v1/chat/ws/{room_id}?token=<jwt>
      2. Server validates token (close 4001 on failure)
      3. Server loads room (close 4004 if missing, 4005 if closed)
      4. Server checks membership (close 4003 if not a member)
      5. Server accepts and registers connection
      6. Server broadcasts {"type":"presence","event":"join"} to other members

    MESSAGE LOOP:
      Client sends: {"type": "message", "content": "..."} or {"type": "ping"}
      Server replies / broadcasts accordingly.

    DISCONNECT:
      On any disconnect (client close, network drop, exception),
      server broadcasts {"type":"presence","event":"leave"}.
    """
    # ============================================================
    # 1. AUTH (before accept — invalid tokens get an HTTP 403 close, no upgrade)
    # ============================================================
    if not token:
        await websocket.close(
            code=WSCloseCode.UNAUTHORIZED,
            reason="Missing token",
        )
        return

    token_data = verify_access_token(token)
    if not token_data:
        await websocket.close(
            code=WSCloseCode.UNAUTHORIZED,
            reason="Invalid or expired token",
        )
        return

    # ============================================================
    # 2. LOAD USER + ROOM (one-shot DB session for setup)
    # ============================================================
    user_id: Optional[UUID] = None
    try:
        async for db in get_db():  # Manually iterate the dep generator
            # Load user
            result = await db.execute(
                select(User).where(User.id == token_data.user_id)
            )
            user = result.scalar_one_or_none()
            if not user or user.is_banned or not user.is_active:
                await websocket.close(
                    code=WSCloseCode.UNAUTHORIZED,
                    reason="User not authorized",
                )
                return
            user_id = user.id

            # Load room
            room = await ChatService.get_room_by_id(db, room_id)
            if not room:
                await websocket.close(
                    code=WSCloseCode.ROOM_NOT_FOUND,
                    reason="Room not found",
                )
                return
            if room.status != ChatRoomStatus.ACTIVE:
                await websocket.close(
                    code=WSCloseCode.ROOM_CLOSED,
                    reason="Room is closed",
                )
                return
            if not ChatService.is_member_of_room(room, user_id):
                await websocket.close(
                    code=WSCloseCode.FORBIDDEN,
                    reason="Not a member of this room",
                )
                return

            break  # got everything we need from setup session
    except Exception as e:
        logger.exception(f"WS setup error: {e}")
        await websocket.close(
            code=WSCloseCode.INTERNAL,
            reason="Internal error",
        )
        return

    # ============================================================
    # 3. ACCEPT + REGISTER
    # ============================================================
    await websocket.accept()
    await manager.connect(websocket, room_id, user_id)

    # Broadcast presence: join
    await manager.broadcast(
        room_id,
        WSServerPresence(event="join", user_id=user_id).model_dump(mode="json"),
        exclude=websocket,
    )

    # ============================================================
    # 4. MESSAGE LOOP
    # ============================================================
    try:
        while True:
            raw = await websocket.receive_text()

            # Parse JSON
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_personal(
                    websocket,
                    WSServerError(
                        code="INVALID_JSON",
                        message="Payload must be valid JSON",
                    ).model_dump(mode="json"),
                )
                continue

            payload_type = payload.get("type")

            # ---- ping ----
            if payload_type == "ping":
                try:
                    WSClientPing(**payload)
                except ValidationError:
                    pass  # ping is shape-flexible; ignore extras
                await manager.send_personal(
                    websocket,
                    WSServerPong().model_dump(mode="json"),
                )
                continue

            # ---- message ----
            if payload_type == "message":
                try:
                    parsed = WSClientMessage(**payload)
                except ValidationError as ve:
                    await manager.send_personal(
                        websocket,
                        WSServerError(
                            code="INVALID_PAYLOAD",
                            message=ve.errors()[0].get("msg", "Invalid payload"),
                        ).model_dump(mode="json"),
                    )
                    continue

                # Persist with a FRESH db session
                try:
                    saved_message = None
                    async for db in get_db():
                        saved_message = await ChatService.send_message(
                            db=db,
                            room_id=room_id,
                            sender_id=user_id,
                            content=parsed.content,
                        )
                        break
                except HTTPException as he:
                    await manager.send_personal(
                        websocket,
                        WSServerError(
                            code="SEND_FAILED",
                            message=he.detail,
                        ).model_dump(mode="json"),
                    )
                    continue
                except Exception as e:
                    logger.exception(f"WS send error: {e}")
                    await manager.send_personal(
                        websocket,
                        WSServerError(
                            code="INTERNAL",
                            message="Failed to persist message",
                        ).model_dump(mode="json"),
                    )
                    continue

                # Broadcast (including back to sender so all clients show the
                # canonical persisted version, not an optimistic one)
                if saved_message is not None:
                    out_payload = WSServerMessage(
                        data=ChatMessageSchema.model_validate(saved_message)
                    ).model_dump(mode="json")
                    await manager.broadcast(room_id, out_payload)
                continue

            # ---- unknown type ----
            await manager.send_personal(
                websocket,
                WSServerError(
                    code="UNKNOWN_TYPE",
                    message=f"Unknown payload type: {payload_type!r}",
                ).model_dump(mode="json"),
            )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception(f"WS loop error: {e}")
    finally:
        manager.disconnect(websocket)
        # Broadcast leave (best-effort)
        if user_id is not None:
            try:
                await manager.broadcast(
                    room_id,
                    WSServerPresence(event="leave", user_id=user_id).model_dump(mode="json"),
                )
            except Exception:
                pass
