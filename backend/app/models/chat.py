"""
LAYERS - Chat Models
====================================
Real-time chat infrastructure: ChatRoom + Message.

TWO ROOM TYPES:
  - DIRECT:   1:1 chat between CONNECTED users (Day 2 wires up REST endpoints)
  - CAMPFIRE: ephemeral 50m geo-fenced room (Day 3 adds geo columns + members)

DESIGN NOTES (consistent with Week 5 Day 4 Connection model):
  - Canonical pair ordering for DIRECT rooms: smaller UUID = user_a_id
  - One row per pair (unique constraint on user_a_id + user_b_id)
  - Status enum (ACTIVE / CLOSED) — closed rooms are archived, not deleted
  - last_activity_at updated on every send (used for Campfire 2h auto-disband)
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Text,
    Enum as SQLEnum,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


# ============================================================
# ENUMS
# ============================================================

class ChatRoomType(str, Enum):
    """Type of chat room."""
    DIRECT = "DIRECT"        # 1:1 between two CONNECTED users
    CAMPFIRE = "CAMPFIRE"    # Geo-fenced ephemeral room


class ChatRoomStatus(str, Enum):
    """Lifecycle status of a chat room."""
    ACTIVE = "ACTIVE"        # Open for messages
    CLOSED = "CLOSED"        # Archived (DIRECT closed by both, CAMPFIRE expired)


# ============================================================
# CHAT ROOM
# ============================================================

class ChatRoom(Base):
    """
    A chat room — either DIRECT (1:1) or CAMPFIRE (geo-fenced).
    
    For DIRECT rooms:
        - user_a_id and user_b_id store the two members (canonical: smaller UUID first)
        - Unique constraint enforces one room per pair
        - Created lazily by ChatService.get_or_create_direct_room
    
    For CAMPFIRE rooms:
        - user_a_id and user_b_id are NULL
        - center_geom + radius_meters define the area
        - expires_at controls auto-disband
        - Members tracked in a separate campfire_members table
    """
    __tablename__ = "chat_rooms"
    __table_args__ = (
        UniqueConstraint('user_a_id', 'user_b_id', name='uq_chat_rooms_direct_pair'),
    )

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Room type
    room_type: Mapped[ChatRoomType] = mapped_column(
        SQLEnum(ChatRoomType, name="chatroomtype"),
        nullable=False,
        index=True
    )

    # Status
    status: Mapped[ChatRoomStatus] = mapped_column(
        SQLEnum(ChatRoomStatus, name="chatroomstatus"),
        default=ChatRoomStatus.ACTIVE,
        nullable=False,
        index=True
    )

    # ---- DIRECT room fields ----
    # Canonical ordering: user_a_id < user_b_id (UUID comparison)
    # Both NULL for CAMPFIRE rooms.
    user_a_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    user_b_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # ---- Stats / Lifecycle ----
    message_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    def __repr__(self) -> str:
        if self.room_type == ChatRoomType.DIRECT:
            return f"<ChatRoom DIRECT {self.user_a_id} ↔ {self.user_b_id} ({self.status.value})>"
        return f"<ChatRoom CAMPFIRE {self.id} ({self.status.value})>"

    def is_member(self, user_id: uuid.UUID) -> bool:
        """Check if a user is a member of this DIRECT room. (Campfire uses members table)"""
        if self.room_type != ChatRoomType.DIRECT:
            return False
        return user_id == self.user_a_id or user_id == self.user_b_id


# ============================================================
# MESSAGE
# ============================================================

class Message(Base):
    """
    A single chat message inside a ChatRoom.
    
    Append-only — messages are never edited. They can be soft-deleted via status
    (added later for moderation).
    """
    __tablename__ = "messages"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Foreign Keys
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Content (max 2000 chars enforced at schema layer)
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True  # Indexed for cursor pagination
    )

    def __repr__(self) -> str:
        preview = self.content[:30] + "…" if len(self.content) > 30 else self.content
        return f"<Message {self.sender_id} in room {self.room_id}: {preview!r}>"
