"""
LAYERS - Chat Service
=====================================
Business logic for chat rooms and messages.

PATTERN: Static methods on ChatService class — same as
AuthService, LocationService, ArtifactService, ConnectionService.

DAY 1 SCOPE:
  - get_or_create_direct_room (DIRECT only; CONNECTED-status check is in Day 2 endpoint)
  - send_message (persist + bump message_count + bump last_activity_at)
  - get_room_messages (cursor pagination, descending by created_at)
  - get_room_by_id
  - get_user_rooms (list view)
  - close_room

DAY 2-5 will add:
  - Day 2: REST endpoint wrappers, "is CONNECTED?" gate
  - Day 3: Campfire creation (geo lookup), member tracking, expiry job
  - Day 4: Signal Boost / Wave / Synchronicity hooks
  - Day 5: Read receipts, typing events
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatRoom, Message, ChatRoomType, ChatRoomStatus

logger = logging.getLogger(__name__)


# ============================================================
# HELPERS
# ============================================================

def _canonical_pair(user_a: uuid.UUID, user_b: uuid.UUID) -> Tuple[uuid.UUID, uuid.UUID]:
    """
    Sort a user pair into canonical order (smaller UUID first).
    Same convention as ConnectionService — guarantees one row per pair.
    """
    if user_a == user_b:
        raise ValueError("Cannot create a chat room with yourself")
    if str(user_a) < str(user_b):
        return user_a, user_b
    return user_b, user_a


# ============================================================
# CHAT SERVICE
# ============================================================

class ChatService:
    """Chat room and message business logic."""

    # ========================================================
    # ROOM LOOKUP / CREATION
    # ========================================================

    @staticmethod
    async def get_room_by_id(
        db: AsyncSession,
        room_id: uuid.UUID,
    ) -> Optional[ChatRoom]:
        """Fetch a single room by ID. Returns None if not found."""
        result = await db.execute(
            select(ChatRoom).where(ChatRoom.id == room_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_direct_room(
        db: AsyncSession,
        user_a: uuid.UUID,
        user_b: uuid.UUID,
    ) -> Optional[ChatRoom]:
        """Find an existing DIRECT room between two users (any status)."""
        a, b = _canonical_pair(user_a, user_b)
        result = await db.execute(
            select(ChatRoom).where(
                and_(
                    ChatRoom.room_type == ChatRoomType.DIRECT,
                    ChatRoom.user_a_id == a,
                    ChatRoom.user_b_id == b,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_or_create_direct_room(
        db: AsyncSession,
        user_a: uuid.UUID,
        user_b: uuid.UUID,
    ) -> ChatRoom:
        """
        Get an existing DIRECT room between two users, or create one.

        IMPORTANT: this method does NOT check CONNECTED status — that gate
        lives in the Day 2 REST endpoint so that internal code (tests, hooks)
        can create rooms without going through the user-facing flow.
        """
        existing = await ChatService.get_direct_room(db, user_a, user_b)
        if existing:
            # If previously CLOSED, reopen
            if existing.status == ChatRoomStatus.CLOSED:
                existing.status = ChatRoomStatus.ACTIVE
                existing.closed_at = None
                existing.last_activity_at = datetime.utcnow()
                await db.commit()
                await db.refresh(existing)
            return existing

        a, b = _canonical_pair(user_a, user_b)
        now = datetime.utcnow()
        room = ChatRoom(
            room_type=ChatRoomType.DIRECT,
            status=ChatRoomStatus.ACTIVE,
            user_a_id=a,
            user_b_id=b,
            message_count=0,
            last_activity_at=now,
            created_at=now,
        )
        db.add(room)
        await db.commit()
        await db.refresh(room)

        logger.info(f"Created DIRECT room {room.id} for {a} ↔ {b}")
        return room

    # ========================================================
    # MESSAGE PERSISTENCE
    # ========================================================

    @staticmethod
    async def send_message(
        db: AsyncSession,
        room_id: uuid.UUID,
        sender_id: uuid.UUID,
        content: str,
    ) -> Message:
        """
        Persist a message and bump the room's counters.

        Caller is responsible for:
          - Validating that sender_id is a member of the room
          - Validating that the room is ACTIVE
          - Broadcasting via the WebSocket manager
        """
        # Validate content (defense in depth — Pydantic validates at the boundary too)
        content = (content or "").strip()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message content cannot be empty",
            )
        if len(content) > 2000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message exceeds 2000 character limit",
            )

        # Load room (and verify it exists / is active)
        room = await ChatService.get_room_by_id(db, room_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat room not found",
            )
        if room.status != ChatRoomStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chat room is closed",
            )

        # Create message
        now = datetime.utcnow()
        message = Message(
            room_id=room_id,
            sender_id=sender_id,
            content=content,
            created_at=now,
        )
        db.add(message)

        # Bump counters on the room
        room.message_count += 1
        room.last_activity_at = now

        await db.commit()
        await db.refresh(message)

        return message

    # ========================================================
    # MESSAGE PAGINATION
    # ========================================================

    @staticmethod
    async def get_room_messages(
        db: AsyncSession,
        room_id: uuid.UUID,
        limit: int = 50,
        before: Optional[datetime] = None,
    ) -> List[Message]:
        """
        Return messages in DESCENDING order by created_at (newest first).

        Cursor pagination via `before`: pass the oldest message's created_at
        from the previous page to load older messages. Same pattern as the
        Memory Inbox cursor pagination

        Mobile clients should reverse client-side for inverted FlatList rendering.
        """
        if limit < 1 or limit > 100:
            limit = 50

        query = select(Message).where(Message.room_id == room_id)
        if before is not None:
            query = query.where(Message.created_at < before)
        query = query.order_by(desc(Message.created_at)).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_recent_messages(
        db: AsyncSession,
        room_id: uuid.UUID,
        limit: int = 20,
    ) -> List[Message]:
        """Convenience: latest N messages, descending. Used in ChatRoomDetail."""
        return await ChatService.get_room_messages(db, room_id, limit=limit)

    # ========================================================
    # USER'S ROOMS
    # ========================================================

    @staticmethod
    async def get_user_rooms(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
    ) -> List[ChatRoom]:
        """
        List all DIRECT rooms a user is a member of, ordered by recent activity.

        Day 3 will extend this to include CAMPFIRE rooms the user is currently in.
        """
        query = (
            select(ChatRoom)
            .where(
                and_(
                    ChatRoom.room_type == ChatRoomType.DIRECT,
                    or_(
                        ChatRoom.user_a_id == user_id,
                        ChatRoom.user_b_id == user_id,
                    ),
                )
            )
            .order_by(desc(ChatRoom.last_activity_at))
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    # ========================================================
    # ROOM LIFECYCLE
    # ========================================================

    @staticmethod
    async def close_room(
        db: AsyncSession,
        room_id: uuid.UUID,
    ) -> ChatRoom:
        """Mark a room as CLOSED. Idempotent."""
        room = await ChatService.get_room_by_id(db, room_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat room not found",
            )
        if room.status == ChatRoomStatus.CLOSED:
            return room

        room.status = ChatRoomStatus.CLOSED
        room.closed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(room)
        return room

    # ========================================================
    # MEMBERSHIP
    # ========================================================

    @staticmethod
    def is_member_of_room(room: ChatRoom, user_id: uuid.UUID) -> bool:
        """
        Synchronous membership check — assumes room is already loaded.

        For DIRECT: user must be user_a_id or user_b_id.
        For CAMPFIRE (Day 3): will check the campfire_members table instead.
        """
        if room.room_type == ChatRoomType.DIRECT:
            return user_id == room.user_a_id or user_id == room.user_b_id
        # Day 3 will replace this with a real check
        return True
