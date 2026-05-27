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
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, and_, or_, desc, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_SetSRID, ST_MakePoint

from app.models.chat import CampfireMember, ChatRoom, Message, ChatRoomType, ChatRoomStatus

logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTS (campfire-specific)
# ============================================================

CAMPFIRE_RADIUS_METERS = 50         # Geo-fence radius
CAMPFIRE_LIFETIME_HOURS = 2          # Auto-disband after this much inactivity
CAMPFIRE_CREATE_COOLDOWN_SEC = 600   # 1 campfire creation per 10 min per user
NEARBY_CAMPFIRE_DEFAULT_RADIUS = 500  # Map beacon discovery radius
CAMPFIRE_NAME_MAX_LEN = 100


# ============================================================
# IN-PROCESS RATE LIMITER (single-worker dev)
# Production (Week 10) will replace this with Redis.
# Same pattern as AntiCheatService._location_history.
# ============================================================
_campfire_create_history: Dict[uuid.UUID, datetime] = {}

# ============================================================
# HELPERS
# ============================================================

def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp for timezone=True columns."""
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_expired(expires_at: Optional[datetime]) -> bool:
    if expires_at is None:
        return False
    return _as_utc(expires_at) <= _utcnow()


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

def _check_campfire_rate_limit(user_id: uuid.UUID) -> None:
    """Raise 429 if the user created a campfire within the cooldown window."""
    last = _campfire_create_history.get(user_id)
    if last is None:
        return
    elapsed = (_utcnow() - _as_utc(last)).total_seconds()
    if elapsed < CAMPFIRE_CREATE_COOLDOWN_SEC:
        remaining = int(CAMPFIRE_CREATE_COOLDOWN_SEC - elapsed)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"You started a campfire recently. "
                f"Try again in {remaining // 60}m {remaining % 60}s."
            ),
        )


def _record_campfire_creation(user_id: uuid.UUID) -> None:
    _campfire_create_history[user_id] = _utcnow()

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
        """
        existing = await ChatService.get_direct_room(db, user_a, user_b)
        if existing:
            # If previously CLOSED, reopen
            if existing.status == ChatRoomStatus.CLOSED:
                existing.status = ChatRoomStatus.ACTIVE
                existing.closed_at = None
                existing.last_activity_at = _utcnow()
                await db.commit()
                await db.refresh(existing)
            return existing

        a, b = _canonical_pair(user_a, user_b)
        now = _utcnow()
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
    
    # ============================================================
    # CAMPFIRE LOOKUP / CREATION
    # ============================================================

    @staticmethod
    async def find_nearest_active_campfire(
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_meters: int = CAMPFIRE_RADIUS_METERS,
    ) -> Optional[ChatRoom]:
        """
        Find the closest ACTIVE, non-expired campfire whose center is within
        `radius_meters` of (latitude, longitude).

        Uses PostGIS ST_DWithin + ST_Distance. Same pattern as LocationService.get_nearby.
        Note: PostGIS expects (longitude, latitude) — NOT (lat, lng)!
        """
        user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        distance_col = ST_Distance(ChatRoom.center_geom, user_point).label("distance_m")
        now = _utcnow()

        stmt = (
            select(ChatRoom, distance_col)
            .where(
                and_(
                    ChatRoom.room_type == ChatRoomType.CAMPFIRE,
                    ChatRoom.status == ChatRoomStatus.ACTIVE,
                    or_(
                        ChatRoom.expires_at.is_(None),
                        ChatRoom.expires_at > now,
                    ),
                    ST_DWithin(ChatRoom.center_geom, user_point, radius_meters),
                )
            )
            .order_by(distance_col.asc())
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.first()
        return row[0] if row else None

    @staticmethod
    async def find_or_create_campfire(
        db: AsyncSession,
        creator_id: uuid.UUID,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
    ) -> Tuple[ChatRoom, bool]:
        """
        Find the closest active campfire within CAMPFIRE_RADIUS_METERS of the user,
        or create a new one centered at the user's position.

        Returns (room, created_bool).

        Side effects (if creating):
          - Inserts a new ChatRoom (room_type=CAMPFIRE)
          - Sets expires_at = now + CAMPFIRE_LIFETIME_HOURS
          - Records rate-limit timestamp

        Caller is responsible for then calling join_campfire() to add the creator
        to campfire_members. We don't do it implicitly here — keeps the API symmetric
        (the endpoint joins the creator after creating).
        """
        # Try to find an existing one
        existing = await ChatService.find_nearest_active_campfire(
            db, latitude, longitude, CAMPFIRE_RADIUS_METERS,
        )
        if existing:
            return existing, False

        # Rate-limit campfire creation
        _check_campfire_rate_limit(creator_id)

        # Create new campfire
        now = _utcnow()
        expires_at = now + timedelta(hours=CAMPFIRE_LIFETIME_HOURS)
        geom_wkt = f"SRID=4326;POINT({longitude} {latitude})"

        # Trim name if provided
        clean_name = None
        if name:
            clean_name = name.strip()[:CAMPFIRE_NAME_MAX_LEN]
            if not clean_name:
                clean_name = None

        room = ChatRoom(
            room_type=ChatRoomType.CAMPFIRE,
            status=ChatRoomStatus.ACTIVE,
            center_geom=geom_wkt,
            center_latitude=latitude,
            center_longitude=longitude,
            radius_meters=CAMPFIRE_RADIUS_METERS,
            expires_at=expires_at,
            name=clean_name,
            creator_id=creator_id,
            message_count=0,
            last_activity_at=now,
            created_at=now,
        )
        db.add(room)
        await db.commit()
        await db.refresh(room)

        _record_campfire_creation(creator_id)
        logger.info(
            f"Created CAMPFIRE {room.id} at ({latitude}, {longitude}) by {creator_id}"
        )
        return room, True

    # ============================================================
    # CAMPFIRE MEMBERSHIP
    # ============================================================

    @staticmethod
    async def join_campfire(
        db: AsyncSession,
        room_id: uuid.UUID,
        user_id: uuid.UUID,
        latitude: float,
        longitude: float,
    ) -> CampfireMember:
        """
        Add a user to a campfire after verifying proximity to its center.

        Raises:
          - 404 if room missing
          - 400 if not CAMPFIRE / not ACTIVE / expired
          - 403 if user is outside the geo-fence
        """
        # Lazy-close if expired
        room = await ChatService._fetch_and_auto_close_if_expired(db, room_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campfire not found",
            )
        if room.room_type != ChatRoomType.CAMPFIRE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Room is not a campfire",
            )
        if room.status != ChatRoomStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This campfire is closed",
            )

        # Proximity check via PostGIS
        user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        distance_result = await db.execute(
            select(ST_Distance(ChatRoom.center_geom, user_point)).where(
                ChatRoom.id == room_id
            )
        )
        distance_m = distance_result.scalar()
        if distance_m is None or distance_m > (room.radius_meters or CAMPFIRE_RADIUS_METERS):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"You're {int(distance_m or 0)}m from this campfire. "
                    f"You need to be within {room.radius_meters or CAMPFIRE_RADIUS_METERS}m to join."
                ),
            )

        # If user already has an active membership, return it (idempotent)
        existing_q = select(CampfireMember).where(
            and_(
                CampfireMember.room_id == room_id,
                CampfireMember.user_id == user_id,
                CampfireMember.left_at.is_(None),
            )
        )
        existing_result = await db.execute(existing_q)
        existing = existing_result.scalar_one_or_none()
        if existing:
            return existing

        # Insert a new active membership
        membership = CampfireMember(
            room_id=room_id,
            user_id=user_id,
            joined_at=_utcnow(),
        )
        db.add(membership)
        # Bump room activity (joining counts as activity)
        await ChatService._extend_expiry_in_session(room)
        await db.commit()
        await db.refresh(membership)

        logger.info(f"User {user_id} joined campfire {room_id}")
        return membership

    @staticmethod
    async def leave_campfire(
        db: AsyncSession,
        room_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Mark the user's active membership as left. Idempotent."""
        stmt = (
            update(CampfireMember)
            .where(
                and_(
                    CampfireMember.room_id == room_id,
                    CampfireMember.user_id == user_id,
                    CampfireMember.left_at.is_(None),
                )
            )
            .values(left_at=_utcnow())
        )
        await db.execute(stmt)
        await db.commit()
        logger.info(f"User {user_id} left campfire {room_id}")

    @staticmethod
    async def get_active_members(
        db: AsyncSession,
        room_id: uuid.UUID,
    ) -> List[CampfireMember]:
        """All users currently joined to the campfire (left_at IS NULL)."""
        result = await db.execute(
            select(CampfireMember)
            .where(
                and_(
                    CampfireMember.room_id == room_id,
                    CampfireMember.left_at.is_(None),
                )
            )
            .order_by(CampfireMember.joined_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def is_campfire_member(
        db: AsyncSession,
        room_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        result = await db.execute(
            select(CampfireMember.id).where(
                and_(
                    CampfireMember.room_id == room_id,
                    CampfireMember.user_id == user_id,
                    CampfireMember.left_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none() is not None

    # ============================================================
    # CAMPFIRE DISCOVERY
    # ============================================================

    @staticmethod
    async def get_campfires_near(
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_meters: int = NEARBY_CAMPFIRE_DEFAULT_RADIUS,
    ) -> List[Tuple[ChatRoom, float]]:
        """
        Return [(room, distance_meters), ...] for active campfires whose
        centers are within `radius_meters` of (lat, lng).
        Used by GET /chat/campfires/nearby for rendering map beacons.
        """
        user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        distance_col = ST_Distance(ChatRoom.center_geom, user_point).label("distance_m")
        now = _utcnow()

        stmt = (
            select(ChatRoom, distance_col)
            .where(
                and_(
                    ChatRoom.room_type == ChatRoomType.CAMPFIRE,
                    ChatRoom.status == ChatRoomStatus.ACTIVE,
                    or_(
                        ChatRoom.expires_at.is_(None),
                        ChatRoom.expires_at > now,
                    ),
                    ST_DWithin(ChatRoom.center_geom, user_point, radius_meters),
                )
            )
            .order_by(distance_col.asc())
            .limit(50)
        )
        result = await db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    # ============================================================
    # EXPIRY MANAGEMENT
    # ============================================================

    @staticmethod
    async def _fetch_and_auto_close_if_expired(
        db: AsyncSession,
        room_id: uuid.UUID,
    ) -> Optional[ChatRoom]:
        """
        Load a room; if it's an expired campfire still marked ACTIVE,
        flip it to CLOSED first. Returns the (possibly updated) room.
        """
        room = await ChatService.get_room_by_id(db, room_id)
        if not room:
            return None
        if (
            room.room_type == ChatRoomType.CAMPFIRE
            and room.status == ChatRoomStatus.ACTIVE
            and room.expires_at is not None
            and _is_expired(room.expires_at)
        ):
            room.status = ChatRoomStatus.CLOSED
            room.closed_at = _utcnow()
            await db.commit()
            await db.refresh(room)
            logger.info(f"Auto-closed expired campfire {room.id}")
        return room

    @staticmethod
    async def _extend_expiry_in_session(room: ChatRoom) -> None:
        """
        Extend a campfire's expires_at to NOW + lifetime.
        Caller must commit. No-op for DIRECT rooms.
        """
        if room.room_type != ChatRoomType.CAMPFIRE:
            return
        now = _utcnow()
        room.expires_at = now + timedelta(hours=CAMPFIRE_LIFETIME_HOURS)
        room.last_activity_at = now

    @staticmethod
    async def close_expired_campfires(db: AsyncSession) -> int:
        """
        Bulk-close all ACTIVE campfires past their expires_at.
        Returns count closed.
        Run on a cron/scheduler in production; can be invoked manually otherwise.
        """
        now = _utcnow()
        stmt = (
            update(ChatRoom)
            .where(
                and_(
                    ChatRoom.room_type == ChatRoomType.CAMPFIRE,
                    ChatRoom.status == ChatRoomStatus.ACTIVE,
                    ChatRoom.expires_at.is_not(None),
                    ChatRoom.expires_at <= now,
                )
            )
            .values(status=ChatRoomStatus.CLOSED, closed_at=now)
        )
        result = await db.execute(stmt)
        await db.commit()
        closed = result.rowcount or 0
        if closed > 0:
            logger.info(f"close_expired_campfires: closed {closed} room(s)")
        return closed

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
        now = _utcnow()
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
        if room.room_type == ChatRoomType.CAMPFIRE:
            room.expires_at = now + timedelta(hours=CAMPFIRE_LIFETIME_HOURS)

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
        All rooms the user is in:
          - DIRECT rooms where they're user_a_id or user_b_id
          - CAMPFIRE rooms where they have an ACTIVE membership (left_at IS NULL)
        """
        # DIRECT rooms
        direct_q = select(ChatRoom).where(
            and_(
                ChatRoom.room_type == ChatRoomType.DIRECT,
                or_(
                    ChatRoom.user_a_id == user_id,
                    ChatRoom.user_b_id == user_id,
                ),
            )
        )
        # CAMPFIRE rooms via active membership
        campfire_q = (
            select(ChatRoom)
            .join(CampfireMember, CampfireMember.room_id == ChatRoom.id)
            .where(
                and_(
                    ChatRoom.room_type == ChatRoomType.CAMPFIRE,
                    CampfireMember.user_id == user_id,
                    CampfireMember.left_at.is_(None),
                )
            )
        )
        union_q = direct_q.union(campfire_q).subquery()

        # Re-select from the union and order
        final_q = (
            select(ChatRoom)
            .join(union_q, ChatRoom.id == union_q.c.id)
            .order_by(desc(ChatRoom.last_activity_at))
            .limit(limit)
        )
        result = await db.execute(final_q)
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
        room.closed_at = _utcnow()
        await db.commit()
        await db.refresh(room)
        return room

    # ========================================================
    # MEMBERSHIP
    # ========================================================

    @staticmethod
    async def is_member_of_room(
        db: AsyncSession, 
        room: ChatRoom, 
        user_id: uuid.UUID
    ) -> bool:
        """
        DIRECT: user must be user_a_id or user_b_id.
        CAMPFIRE: user must have an active campfire_members row.
        """
        if room.room_type == ChatRoomType.DIRECT:
            return user_id == room.user_a_id or user_id == room.user_b_id
        if room.room_type == ChatRoomType.CAMPFIRE:
            return await ChatService.is_campfire_member(db, room.id, user_id)
        return True

    # ============================================================
    # OTHER-USER PROFILE LOOKUP
    # ============================================================
    # DIRECT room responses should carry the other participant's username
    # + avatar_url so the chat list doesn't need follow-up /users/{id} calls.

    @staticmethod
    async def build_other_user_map(
        db: AsyncSession,
        rooms: List[ChatRoom],
        current_user_id: uuid.UUID,
    ) -> dict:
        """
        Given a list of rooms and the current user, return:
            { room.id (UUID) : {"id": uuid, "username": str, "avatar_url": str|None} }
        for every DIRECT room. CAMPFIRE rooms are skipped (they have members,
        not a single 'other_user' — see /chat/campfires/{id}/members instead).

        ONE bulk SELECT, regardless of room count.
        """
        # Lazy import to avoid a circular dep at module-load time
        from app.models.user import User

        target_user_ids = set()
        room_to_other = {}
        for r in rooms:
            if r.room_type != ChatRoomType.DIRECT:
                continue
            if not r.user_a_id or not r.user_b_id:
                continue
            other = r.user_b_id if r.user_a_id == current_user_id else r.user_a_id
            room_to_other[r.id] = other
            target_user_ids.add(other)

        if not target_user_ids:
            return {}

        result = await db.execute(
            select(User).where(User.id.in_(target_user_ids))
        )
        users_by_id = {u.id: u for u in result.scalars().all()}

        out = {}
        for room_id, other_id in room_to_other.items():
            user = users_by_id.get(other_id)
            if user is None:
                continue
            out[room_id] = {
                "id": user.id,
                "username": user.username,
                "avatar_url": getattr(user, "avatar_url", None),
            }
        return out