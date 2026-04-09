"""
LAYERS — Connection Service
==========================================
Business logic for the Progressive Connection System.

HOW IT WORKS:
  1. User A replies to User B's letter (Slow Mail)
     → ConnectionService.record_interaction(A, B)
       → Create connection if missing (status=PENDING, count=0)
       → Increment interaction_count
       → If count >= 5 → upgrade available (Level 1 Signal)

  2. Level 1: Username & avatar revealed to each other.

  3. Either user can tap "Request Connection" button
     → ConnectionService.request_upgrade(A, B)
       → Set upgrade_requested_by_a = True
       → Notify B: "Someone wants to connect"

  4. B taps Accept
     → ConnectionService.accept_upgrade(B, connection_id)
       → If both requested → status = CONNECTED
       → connected_at = now()
       → Realtime chat unlocked (Week 6)

NOTE: This assumes the connection model has these extra columns
(New migration for connection adds them):
  upgrade_requested_by_a (Boolean)
  upgrade_requested_by_b (Boolean)
  last_interaction_at (DateTime)
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection, ConnectionStatus
from app.models.user import User

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTS
# ============================================================

SIGNAL_THRESHOLD = 5  # Interactions needed to reach Level 1


class ConnectionService:
    """Progressive connection system business logic."""

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _ordered_pair(
        user_a_id: uuid.UUID,
        user_b_id: uuid.UUID,
    ) -> Tuple[uuid.UUID, uuid.UUID]:
        """
        Normalize user IDs so connections are canonical.
        Always store smaller UUID as user_a_id.
        """
        if str(user_a_id) < str(user_b_id):
            return user_a_id, user_b_id
        return user_b_id, user_a_id

    @staticmethod
    def _compute_level(
        status: ConnectionStatus,
        interaction_count: int,
    ) -> str:
        """Determine connection level from status + count."""
        if status == ConnectionStatus.CONNECTED:
            return "CONNECTED"
        if interaction_count >= SIGNAL_THRESHOLD:
            return "SIGNAL"
        return "STRANGER"

    @staticmethod
    async def _get_or_create_connection(
        db: AsyncSession,
        user_a_id: uuid.UUID,
        user_b_id: uuid.UUID,
    ) -> Connection:
        """Get existing connection or create new PENDING one."""
        a_id, b_id = ConnectionService._ordered_pair(user_a_id, user_b_id)

        result = await db.execute(
            select(Connection).where(
                and_(
                    Connection.user_a_id == a_id,
                    Connection.user_b_id == b_id,
                )
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            connection = Connection(
                user_a_id=a_id,
                user_b_id=b_id,
                interaction_count=0,
                status=ConnectionStatus.PENDING,
            )
            db.add(connection)
            await db.flush()

        return connection

    # ========================================================
    # RECORD INTERACTION
    # Called whenever two users exchange a letter/reply.
    # ========================================================

    @staticmethod
    async def record_interaction(
        db: AsyncSession,
        user_a_id: uuid.UUID,
        user_b_id: uuid.UUID,
    ) -> dict:
        """
        Record an interaction between two users.
        Returns { connection_id, interaction_count, level, level_up }

        Called by ArtifactService.reply_to_artifact() — when A replies to B.
        """
        if user_a_id == user_b_id:
            raise ValueError("Cannot create connection with yourself")

        connection = await ConnectionService._get_or_create_connection(
            db, user_a_id, user_b_id
        )

        # Track previous level for "level up" detection
        prev_level = ConnectionService._compute_level(
            connection.status, connection.interaction_count
        )

        connection.interaction_count += 1
        connection.last_interaction_at = datetime.now(timezone.utc)

        new_level = ConnectionService._compute_level(
            connection.status, connection.interaction_count
        )

        await db.commit()
        await db.refresh(connection)

        level_up = prev_level != new_level

        if level_up:
            logger.info(
                f"🎉 Connection level up: {user_a_id} <-> {user_b_id} "
                f"({prev_level} → {new_level})"
            )

        return {
            "connection_id": str(connection.id),
            "interaction_count": connection.interaction_count,
            "level": new_level,
            "level_up": level_up,
            "prev_level": prev_level,
        }

    # ========================================================
    # LIST CONNECTIONS
    # ========================================================

    @staticmethod
    async def list_connections(
        db: AsyncSession,
        user_id: uuid.UUID,
        level_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """
        List all connections for a user, with other user's info joined.
        Anonymous for Level 0 (Stranger) — no username/avatar returned.
        """
        # Get all connections where user is involved
        query = select(Connection).where(
            or_(
                Connection.user_a_id == user_id,
                Connection.user_b_id == user_id,
            )
        )

        # Count total + per-level buckets
        total_result = await db.execute(
            select(func.count(Connection.id)).where(
                or_(
                    Connection.user_a_id == user_id,
                    Connection.user_b_id == user_id,
                )
            )
        )
        total = total_result.scalar() or 0

        # Per-level counts
        strangers_count = 0
        signals_count = 0
        connected_count = 0

        all_result = await db.execute(query)
        all_connections = all_result.scalars().all()

        for c in all_connections:
            level = ConnectionService._compute_level(c.status, c.interaction_count)
            if level == "STRANGER":
                strangers_count += 1
            elif level == "SIGNAL":
                signals_count += 1
            else:
                connected_count += 1

        # Fetch paginated connections
        page_result = await db.execute(
            query.order_by(Connection.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        page_connections = page_result.scalars().all()

        # For each connection, fetch the other user's info
        items = []
        for c in page_connections:
            other_id = (
                c.user_b_id if c.user_a_id == user_id else c.user_a_id
            )

            level = ConnectionService._compute_level(
                c.status, c.interaction_count
            )

            # Apply level filter
            if level_filter and level != level_filter.upper():
                continue

            # Fetch other user
            other_result = await db.execute(
                select(User).where(User.id == other_id)
            )
            other_user = other_result.scalar_one_or_none()

            # Anonymous for Level 0
            if level == "STRANGER":
                other_user_data = {
                    "id": str(other_id),
                    "username": None,
                    "avatar_url": None,
                    "level": None,
                }
            else:
                other_user_data = {
                    "id": str(other_id),
                    "username": other_user.username if other_user else None,
                    "avatar_url": other_user.avatar_url if other_user else None,
                    "level": other_user.level if other_user else None,
                }

            # Determine who requested upgrade
            upgrade_by_me = False
            upgrade_by_them = False
            if hasattr(c, "upgrade_requested_by_a"):
                if c.user_a_id == user_id:
                    upgrade_by_me = c.upgrade_requested_by_a or False
                    upgrade_by_them = c.upgrade_requested_by_b or False
                else:
                    upgrade_by_me = c.upgrade_requested_by_b or False
                    upgrade_by_them = c.upgrade_requested_by_a or False

            items.append({
                "id": str(c.id),
                "other_user": other_user_data,
                "interaction_count": c.interaction_count,
                "level": level,
                "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                "can_upgrade": (
                    level == "SIGNAL"
                    and c.status == ConnectionStatus.PENDING
                ),
                "upgrade_requested_by_me": upgrade_by_me,
                "upgrade_requested_by_them": upgrade_by_them,
                "created_at": c.created_at,
                "connected_at": c.connected_at,
                "last_interaction_at": getattr(c, "last_interaction_at", None),
            })

        return {
            "connections": items,
            "total": total,
            "strangers_count": strangers_count,
            "signals_count": signals_count,
            "connected_count": connected_count,
        }

    # ========================================================
    # REQUEST UPGRADE (Level 1 → Level 2)
    # ========================================================

    @staticmethod
    async def request_upgrade(
        db: AsyncSession,
        user_id: uuid.UUID,
        connection_id: uuid.UUID,
    ) -> dict:
        """
        Request to upgrade a SIGNAL connection to CONNECTED.
        If both users have requested, auto-upgrade.
        """
        result = await db.execute(
            select(Connection).where(Connection.id == connection_id)
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise ValueError("Connection not found")

        # Check user is part of this connection
        if user_id not in (connection.user_a_id, connection.user_b_id):
            raise ValueError("You are not part of this connection")

        # Must be at Signal level
        level = ConnectionService._compute_level(
            connection.status, connection.interaction_count
        )
        if level != "SIGNAL":
            raise ValueError(
                f"Cannot upgrade connection at {level} level. "
                f"Need at least {SIGNAL_THRESHOLD} interactions."
            )

        # Mark who requested
        if connection.user_a_id == user_id:
            connection.upgrade_requested_by_a = True
        else:
            connection.upgrade_requested_by_b = True

        # Check if both have requested → auto-upgrade
        both_requested = (
            getattr(connection, "upgrade_requested_by_a", False)
            and getattr(connection, "upgrade_requested_by_b", False)
        )

        if both_requested:
            connection.status = ConnectionStatus.CONNECTED
            connection.connected_at = datetime.now(timezone.utc)
            logger.info(f"✨ Connection CONNECTED: {connection.id}")

        await db.commit()
        await db.refresh(connection)

        return {
            "connection_id": str(connection.id),
            "status": connection.status.value if hasattr(connection.status, "value") else str(connection.status),
            "upgraded": both_requested,
            "message": (
                "Connection unlocked! Realtime chat now available. ✨"
                if both_requested
                else "Request sent. Waiting for the other user to accept."
            ),
        }

    # ========================================================
    # REJECT UPGRADE
    # ========================================================

    @staticmethod
    async def reject_upgrade(
        db: AsyncSession,
        user_id: uuid.UUID,
        connection_id: uuid.UUID,
    ) -> dict:
        """Reject an incoming connection upgrade request."""
        result = await db.execute(
            select(Connection).where(Connection.id == connection_id)
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise ValueError("Connection not found")

        if user_id not in (connection.user_a_id, connection.user_b_id):
            raise ValueError("You are not part of this connection")

        # Reset upgrade flags
        connection.upgrade_requested_by_a = False
        connection.upgrade_requested_by_b = False

        await db.commit()

        return {
            "connection_id": str(connection.id),
            "status": "rejected",
            "message": "Connection request declined.",
        }

    # ========================================================
    # STATS
    # ========================================================

    @staticmethod
    async def get_stats(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> dict:
        """Get connection statistics for profile screen."""
        data = await ConnectionService.list_connections(
            db, user_id, limit=1000, offset=0
        )

        # Count pending upgrade requests
        pending_received = 0
        pending_sent = 0
        for c in data["connections"]:
            if c["upgrade_requested_by_them"] and not c["upgrade_requested_by_me"]:
                pending_received += 1
            if c["upgrade_requested_by_me"] and not c["upgrade_requested_by_them"]:
                pending_sent += 1

        return {
            "total_connections": data["total"],
            "strangers": data["strangers_count"],
            "signals": data["signals_count"],
            "connected": data["connected_count"],
            "pending_requests_received": pending_received,
            "pending_requests_sent": pending_sent,
        }
