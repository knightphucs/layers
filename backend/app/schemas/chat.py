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
    
    # DIRECT
    user_a_id: Optional[UUID] = None
    user_b_id: Optional[UUID] = None
    
    # CAMPFIRE
    center_latitude: Optional[float] = None
    center_longitude: Optional[float] = None
    radius_meters: Optional[int] = None
    expires_at: Optional[datetime] = None
    name: Optional[str] = None
    creator_id: Optional[UUID] = None
    
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
# REST REQUESTS
# ============================================================

class SendMessageRequest(BaseModel):
    """REST send (used in tests + by mobile fallback when WS is dead)."""
    content: str = Field(..., min_length=1, max_length=2000)

class CampfireFindOrCreateRequest(BaseModel):
    """POST /chat/campfires/find-or-create"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    name: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional title only used when creating a NEW campfire",
    )
class CampfireJoinRequest(BaseModel):
    """POST /chat/campfires/{room_id}/join — verify proximity to center."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    
# ============================================================
# CAMPFIRE RESPONSES (Day 3)
# ============================================================

class CampfireMemberInfo(BaseModel):
    """A single campfire member (for the members panel)."""
    user_id: UUID
    joined_at: datetime
    is_online: bool = False  # Derived from WS connection manager
    username: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}


class CampfireMembersResponse(BaseModel):
    """GET /chat/campfires/{room_id}/members"""
    members: List[CampfireMemberInfo]
    online_count: int
    total_count: int


class CampfireNearbyItem(BaseModel):
    """A single campfire in the 'nearby campfires' list (for map beacons)."""
    id: UUID
    name: Optional[str] = None
    center_latitude: float
    center_longitude: float
    radius_meters: int
    expires_at: datetime
    distance_meters: float  # From the query point
    online_count: int
    creator_id: Optional[UUID] = None
    created_at: datetime


class CampfireNearbyResponse(BaseModel):
    """GET /chat/campfires/nearby?lat=&lng=&radius="""
    items: List[CampfireNearbyItem]

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
