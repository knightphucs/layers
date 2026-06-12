"""
LAYERS - Badge Service
=====================================
Achievements. The catalog lives in code; unlocks are persisted in user_badges.

evaluate(db, user_id) re-checks EVERY criterion against the user's durable
state (level + streak from the users row, action counts from xp_events) and
awards any newly-met badges. It is idempotent — safe to call as often as you
like — which is how we guarantee nothing is ever missed.

Criteria types:
- "count":  count of a given XP event_type >= threshold
- "level":  user.level >= threshold
- "streak": user.current_streak >= threshold
- "event":  awarded directly via award_badge() (e.g. Campfire Star on a win)
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_badge import UserBadge
from app.models.xp_event import XPEvent

logger = logging.getLogger(__name__)


BADGE_CATALOG = [
    {
        "id": "first_memory", 
        "title": "First Memory", 
        "icon": "🌱",
        "description": "Leave your first artifact.",
        "type": "count", 
        "event": "ARTIFACT_CREATE", 
        "threshold": 1
    },
    {
        "id": "storyteller", 
        "title": "Storyteller", 
        "icon": "📚",
        "description": "Leave 10 artifacts.",
        "type": "count", 
        "event": "ARTIFACT_CREATE", 
        "threshold": 10
    },
    {
        "id": "treasure_hunter", 
        "title": "Treasure Hunter", 
        "icon": "🗝️",
        "description": "Unlock 25 artifacts.",
        "type": "count", 
        "event": "ARTIFACT_UNLOCK", 
        "threshold": 25
    },
    {
        "id": "pen_pal", 
        "title": "Pen Pal", 
        "icon": "✍️",
        "description": "Send 25 replies.",
        "type": "count", 
        "event": "REPLY_SENT", 
        "threshold": 25
    },
    {
        "id": "social_creature", 
        "title": "Social Creature", 
        "icon": "🤝",
        "description": "Make 5 connections.",
        "type": "count", 
        "event": "CONNECTION_UPGRADE", 
        "threshold": 5
    },
    {
        "id": "campfire_star", 
        "title": "Campfire Star", 
        "icon": "🔥",
        "description": "Win a round of Truth or Dare.",
        "type": "event"
    },
    {
        "id": "rising_star", 
        "title": "Rising Star", 
        "icon": "⭐",
        "description": "Reach level 5.",
        "type": "level", 
        "threshold": 5
    },
    {
        "id": "mythic", 
        "title": "Mythic", 
        "icon": "💎",
        "description": "Reach level 10.",
        "type": "level", 
        "threshold": 10
    },
    {
        "id": "dedicated", 
        "title": "Dedicated", 
        "icon": "🔁",
        "description": "Hold a 7-day streak.",
        "type": "streak", 
        "threshold": 7
    },
    {
        "id": "unstoppable", 
        "title": "Unstoppable", 
        "icon": "🏔️",
        "description": "Hold a 30-day streak.",
        "type": "streak", 
        "threshold": 30
    }
]
BADGE_BY_ID = {b["id"]: b for b in BADGE_CATALOG}


class BadgeService:

    # ========================================================
    # QUERIES (separated so tests can stub them)
    # ========================================================

    @staticmethod
    async def _existing_badge_ids(db: AsyncSession, user_id: UUID) -> set:
        rows = (
            await db.execute(
                select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
            )
        ).scalars().all()
        return set(rows)

    @staticmethod
    async def _event_counts(db: AsyncSession, user_id: UUID) -> Dict[str, int]:
        rows = (
            await db.execute(
                select(XPEvent.event_type, func.count())
                .where(XPEvent.user_id == user_id)
                .group_by(XPEvent.event_type)
            )
        ).all()
        return {event_type: int(count) for event_type, count in rows}

    # ========================================================
    # AWARD
    # ========================================================

    @staticmethod
    async def award_badge(
        db: AsyncSession, user_id: UUID, badge_id: str
    ) -> Optional[dict]:
        """Award a single badge by id (idempotent). Returns the badge if newly
        unlocked, else None. Used for `event` badges like Campfire Star."""
        badge = BADGE_BY_ID.get(badge_id)
        if badge is None:
            return None
        existing = await BadgeService._existing_badge_ids(db, user_id)
        if badge_id in existing:
            return None
        db.add(UserBadge(user_id=user_id, badge_id=badge_id))
        await db.flush()
        await BadgeService._notify(user_id, badge)
        return badge

    @staticmethod
    async def evaluate(db: AsyncSession, user_id: UUID) -> List[dict]:
        """Re-check all criteria; award newly-met badges. Returns newly unlocked."""
        user = await db.get(User, user_id)
        if user is None:
            return []

        existing = await BadgeService._existing_badge_ids(db, user_id)
        counts = await BadgeService._event_counts(db, user_id)
        streak = getattr(user, "current_streak", 0) or 0
        level = user.level or 1

        newly: List[dict] = []
        for b in BADGE_CATALOG:
            if b["id"] in existing:
                continue
            t = b["type"]
            met = False
            if t == "count":
                met = counts.get(b["event"], 0) >= b["threshold"]
            elif t == "level":
                met = level >= b["threshold"]
            elif t == "streak":
                met = streak >= b["threshold"]
            # "event" badges are only awarded directly via award_badge()

            if met:
                db.add(UserBadge(user_id=user_id, badge_id=b["id"]))
                newly.append(b)

        if newly:
            await db.flush()
            for b in newly:
                await BadgeService._notify(user_id, b)
        return newly

    # ========================================================
    # READ
    # ========================================================

    @staticmethod
    async def existing_with_dates(db: AsyncSession, user_id: UUID) -> Dict[str, object]:
        rows = (
            await db.execute(
                select(UserBadge.badge_id, UserBadge.unlocked_at)
                .where(UserBadge.user_id == user_id)
            )
        ).all()
        return {badge_id: unlocked_at for badge_id, unlocked_at in rows}

    # ========================================================
    # NOTIFY (best-effort)
    # ========================================================

    @staticmethod
    async def _notify(user_id: UUID, badge: dict) -> None:
        try:
            from app.core.ws_manager import manager
            await manager.send_to_user(user_id, {"type": "badge_unlocked", "badge": {
                "id": badge["id"], "title": badge["title"], "icon": badge["icon"],
            }})
        except Exception as e:  # noqa: BLE001
            logger.debug("badge notify failed: %s", e)
