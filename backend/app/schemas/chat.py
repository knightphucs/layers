"""
LAYERS - Chat Schemas
=====================================
Pydantic models for chat REST endpoints + WebSocket message payloads.

WEBSOCKET PROTOCOL:

  CLIENT → SERVER:
    {"type": "message",  "content": "hello"}
    {"type": "ping"}

  SERVER → CLIENT:
    {"type": "message",  "data": MessageResponse}
    {"type": "presence", "event": "join" | "leave", "user_id": "..."}
    {"type": "error",    "code": "...", "message": "..."}
    {"type": "pong"}
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# ENUMS (mirror app.models.chat)
# ============================================================

class ChatRoomType(str, Enum):
    DIRECT = "DIRECT"
    CAMPFIRE = "CAMPFIRE"


class ChatRoomStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


# ============================================================
# REST RESPONSES
# ============================================================

class MessageResponse(BaseModel):
    """A single chat message."""
    id: UUID
    room_id: UUID
    sender_id: UUID
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRoomResponse(BaseModel):
    """Chat room summary (list view)."""
    id: UUID
    room_type: ChatRoomType
    status: ChatRoomStatus
    user_a_id: Optional[UUID] = None
    user_b_id: Optional[UUID] = None
    message_count: int
    last_activity_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRoomDetail(ChatRoomResponse):
    """Chat room with the most recent messages embedded."""
    recent_messages: List[MessageResponse] = Field(default_factory=list)
    other_user_id: Optional[UUID] = None  # For DIRECT — convenience field


class MessageListResponse(BaseModel):
    """Cursor-paginated message list."""
    items: List[MessageResponse]
    has_more: bool
    next_cursor: Optional[str] = None  # ISO datetime of oldest returned message


# ============================================================
# REST REQUESTS (Day 1 has only test/dev request shapes; Day 2 adds room creation)
# ============================================================

class SendMessageRequest(BaseModel):
    """REST send (used in tests + by mobile fallback when WS is dead)."""
    content: str = Field(..., min_length=1, max_length=2000)


# ============================================================
# WEBSOCKET PAYLOADS — CLIENT → SERVER
# ============================================================

class WSClientMessage(BaseModel):
    """{"type": "message", "content": "..."}"""
    type: Literal["message"] = "message"
    content: str = Field(..., min_length=1, max_length=2000)


class WSClientPing(BaseModel):
    """{"type": "ping"} — keepalive."""
    type: Literal["ping"] = "ping"


# Discriminated union for inbound parsing
WSClientPayload = Union[WSClientMessage, WSClientPing]


# ============================================================
# WEBSOCKET PAYLOADS — SERVER → CLIENT
# ============================================================

class WSServerMessage(BaseModel):
    """A new chat message broadcast to all room members."""
    type: Literal["message"] = "message"
    data: MessageResponse


class WSServerPresence(BaseModel):
    """A user joined or left the room."""
    type: Literal["presence"] = "presence"
    event: Literal["join", "leave"]
    user_id: UUID


class WSServerError(BaseModel):
    """Server-side error sent before/instead of close."""
    type: Literal["error"] = "error"
    code: str
    message: str


class WSServerPong(BaseModel):
    """Reply to a ping."""
    type: Literal["pong"] = "pong"


# ============================================================
# WEBSOCKET CLOSE CODES (4xxx = application-defined)
# ============================================================

class WSCloseCode:
    """Custom WebSocket close codes used by the chat endpoint."""
    UNAUTHORIZED = 4001       # Bad / missing token
    FORBIDDEN = 4003          # Not a member of this room
    ROOM_NOT_FOUND = 4004     # Room does not exist
    ROOM_CLOSED = 4005        # Room is CLOSED
    INVALID_PAYLOAD = 4400    # Malformed JSON or wrong shape
    INTERNAL = 4500           # Server error
