"""
LAYERS - XP Service
==================================
THE single source of truth for experience points, levels, and ranks.

Before today this logic was scattered: User.add_xp() on the backend and a
separate copy of the level formula + rank ladder in the mobile profileService.
Everything now lives here.

What it does:
- Defines XP_VALUES (how much each action is worth) — canonical.
- Defines the level formula (level = 1 + xp // 1000) and the rank ladder
  (Wanderer → Mythic), matching the mobile masterplan exactly.
- award(): atomically adds XP to a user, writes an XPEvent log row, detects
  level-ups, and (best-effort) pushes a `level_up` frame over WebSocket.
- Idempotency: pass an idempotency_key so retries don't double-award.

IMPORTANT — no double counting:
  When you hook award() into an action, REMOVE any old `user.add_xp(...)` call
  for that action. Grep for `add_xp` and `XP_REWARDS` and migrate them here.

Transaction model:
  award() does db.flush() (not commit), so the XP change is part of the
  caller's transaction and is atomic with the action. The request's normal
  commit (get_db, or your service's own db.commit()) persists it.
  The HTTP response carrying XPAwardResult is the authoritative signal to the
  client; the WS level_up push is a best-effort real-time nicety.
"""

import logging
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.xp_event import XPEvent
from app.schemas.xp import (
    RankInfo,
    LevelProgress,
    XPAwardResult,
)

logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTS — the canonical numbers
# ============================================================

XP_PER_LEVEL = 1000
MAX_RANK_TIER = 10


class XPEventType(str, Enum):
    ARTIFACT_CREATE = "ARTIFACT_CREATE"
    ARTIFACT_UNLOCK = "ARTIFACT_UNLOCK"
    REPLY_SENT = "REPLY_SENT"
    REPLY_RECEIVED = "REPLY_RECEIVED"
    EXPLORE_NEW_CHUNK = "EXPLORE_NEW_CHUNK"
    CONNECTION_UPGRADE = "CONNECTION_UPGRADE"
    CAMPFIRE_GAME_WIN = "CAMPFIRE_GAME_WIN"
    DAILY_QUEST = "DAILY_QUEST"
    FIRST_CHECK_IN = "FIRST_CHECK_IN"


# Canonical XP values per action.
XP_VALUES = {
    XPEventType.ARTIFACT_CREATE: 50,
    XPEventType.ARTIFACT_UNLOCK: 25,
    XPEventType.REPLY_SENT: 20,
    XPEventType.REPLY_RECEIVED: 30,
    XPEventType.EXPLORE_NEW_CHUNK: 15,
    XPEventType.CONNECTION_UPGRADE: 75,
    XPEventType.CAMPFIRE_GAME_WIN: 40,
    XPEventType.DAILY_QUEST: 100,
    XPEventType.FIRST_CHECK_IN: 25,
}

# Human-friendly labels for the /xp/rewards endpoint.
XP_LABELS = {
    XPEventType.ARTIFACT_CREATE: "Leave a memory",
    XPEventType.ARTIFACT_UNLOCK: "Unlock an artifact",
    XPEventType.REPLY_SENT: "Reply to a memory",
    XPEventType.REPLY_RECEIVED: "Get a reply",
    XPEventType.EXPLORE_NEW_CHUNK: "Explore new ground",
    XPEventType.CONNECTION_UPGRADE: "Make a connection",
    XPEventType.CAMPFIRE_GAME_WIN: "Win a campfire game",
    XPEventType.DAILY_QUEST: "Complete a daily quest",
    XPEventType.FIRST_CHECK_IN: "First check-in",
}

# Rank ladder — MUST match mobile RANK_TITLES (profileService).
RANKS = {
    1: ("Wanderer", "🚶"),
    2: ("Explorer", "🧭"),
    3: ("Pathfinder", "🗺️"),
    4: ("Wayfinder", "⭐"),
    5: ("Trailblazer", "🔥"),
    6: ("Navigator", "🌟"),
    7: ("Cartographer", "📜"),
    8: ("Sage", "🏛️"),
    9: ("Legend", "👑"),
    10: ("Mythic", "💎"),
}


class XPService:
    """Business logic for XP, levels, and ranks."""

    # ========================================================
    # PURE FORMULAS (no DB) — safe to call anywhere
    # ========================================================

    @staticmethod
    def level_for_xp(xp: int) -> int:
        return 1 + max(0, xp) // XP_PER_LEVEL

    @staticmethod
    def xp_floor_for_level(level: int) -> int:
        return (max(1, level) - 1) * XP_PER_LEVEL

    @staticmethod
    def rank_for_level(level: int) -> RankInfo:
        tier = min(max(1, level), MAX_RANK_TIER)
        title, icon = RANKS[tier]
        return RankInfo(tier=tier, title=title, icon=icon)

    @staticmethod
    def progress(xp: int) -> LevelProgress:
        xp = max(0, xp)
        level = XPService.level_for_xp(xp)
        floor = XPService.xp_floor_for_level(level)
        xp_into_level = xp - floor
        xp_to_next = XP_PER_LEVEL - xp_into_level
        pct = round(xp_into_level / XP_PER_LEVEL * 100, 1)
        return LevelProgress(
            xp=xp,
            level=level,
            rank=XPService.rank_for_level(level),
            xp_into_level=xp_into_level,
            xp_needed=XP_PER_LEVEL,
            xp_to_next=xp_to_next,
            pct=pct,
        )

    @staticmethod
    def amount_for(event_type: "XPEventType") -> int:
        return XP_VALUES.get(event_type, 0)

    # ========================================================
    # AWARD (DB) — the main entry point
    # ========================================================

    @staticmethod
    async def award(
        db: AsyncSession,
        user_id: UUID,
        event_type: XPEventType,
        *,
        amount: Optional[int] = None,
        ref_id: Optional[UUID] = None,
        idempotency_key: Optional[str] = None,
        notify: bool = True,
    ) -> XPAwardResult:
        """
        Award XP to a user. Returns an XPAwardResult (embed it in your
        action's response). Does NOT commit — participates in the caller's
        transaction.
        """
        amount = XPService.amount_for(event_type) if amount is None else amount

        # --- Idempotency: already processed? return a no-op result ---
        if idempotency_key:
            existing = (
                await db.execute(
                    select(XPEvent).where(XPEvent.idempotency_key == idempotency_key)
                )
            ).scalar_one_or_none()
            if existing is not None:
                return XPService._result(
                    event_type=event_type,
                    amount=0,
                    duplicate=True,
                    xp_before=existing.xp_before,
                    xp_after=existing.xp_after,
                    level_before=existing.level_before,
                    level_after=existing.level_after,
                )

        user = await db.get(User, user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        xp_before = user.experience_points
        level_before = user.level

        user.experience_points = xp_before + amount
        new_level = XPService.level_for_xp(user.experience_points)
        leveled_up = new_level > level_before
        user.level = new_level

        xp_after = user.experience_points

        event = XPEvent(
            user_id=user_id,
            event_type=event_type.value,
            amount=amount,
            ref_id=ref_id,
            idempotency_key=idempotency_key,
            xp_before=xp_before,
            xp_after=xp_after,
            level_before=level_before,
            level_after=new_level,
        )
        db.add(event)
        await db.flush()  # make it queryable / catch unique violations early

        result = XPService._result(
            event_type=event_type,
            amount=amount,
            duplicate=False,
            xp_before=xp_before,
            xp_after=xp_after,
            level_before=level_before,
            level_after=new_level,
        )

        if leveled_up and notify:
            await XPService._notify_level_up(user_id, result)

        return result

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _result(
        *,
        event_type: XPEventType,
        amount: int,
        duplicate: bool,
        xp_before: int,
        xp_after: int,
        level_before: int,
        level_after: int,
    ) -> XPAwardResult:
        return XPAwardResult(
            event_type=event_type.value if isinstance(event_type, XPEventType) else str(event_type),
            amount=amount,
            duplicate=duplicate,
            xp_before=xp_before,
            xp_after=xp_after,
            level_before=level_before,
            level_after=level_after,
            leveled_up=level_after > level_before,
            rank=XPService.rank_for_level(level_after),
            progress=XPService.progress(xp_after),
        )

    @staticmethod
    async def _notify_level_up(user_id: UUID, result: XPAwardResult) -> None:
        """Best-effort real-time level-up push (HTTP response is the truth)."""
        try:
            from app.core.ws_manager import manager
            await manager.send_to_user(
                user_id,
                {
                    "type": "level_up",
                    "old_level": result.level_before,
                    "new_level": result.level_after,
                    "rank": result.rank.model_dump(),
                    "xp": result.xp_after,
                },
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("level_up notify failed for %s: %s", user_id, e)
