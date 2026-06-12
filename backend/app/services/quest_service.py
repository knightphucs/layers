"""
LAYERS - Quest Service
=====================================
Daily quests + streaks.

Design:
- CATALOG: a static list of quest templates (no DB needed).
- "Today's quests": a deterministic rotating slice of the catalog seeded by
  the date, so everyone gets the same N quests today (rotates daily). No
  per-user assignment table required.
- PROGRESS: ephemeral Redis counters, keyed per (user, date, quest), with a
  TTL set to the next local midnight (Asia/Ho_Chi_Minh). Resets automatically.
- COMPLETION: durable — a QuestCompletion row is written and XP is awarded via
  XPService.award(DAILY_QUEST, amount=quest.xp). Idempotent per quest/day.
- STREAK: durable on the User (current_streak, longest_streak, last_quest_date),
  bumped once per day when the first quest of the day completes.

Degradation: if Redis is down, progress can't be tracked (quests simply won't
advance) — a soft, non-crashing degradation. Completions/streak that already
happened remain safe in Postgres.

Wiring (see SETUP.md): next to each Day 3 XP hook, add
    await QuestService.report_progress(db, user_id, QuestTrigger.<X>)
"""

import logging
from datetime import datetime, timedelta, date
from enum import Enum
from typing import List, Optional
from uuid import UUID

try:
    from zoneinfo import ZoneInfo
    QUEST_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:  # pragma: no cover - fallback if tz data missing
    QUEST_TZ = None

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_optional_redis
from app.models.user import User
from app.models.quest_completion import QuestCompletion
from app.services.xp_service import XPService, XPEventType

logger = logging.getLogger(__name__)

DAILY_COUNT = 3


class QuestTrigger(str, Enum):
    ARTIFACT_CREATE = "ARTIFACT_CREATE"
    ARTIFACT_UNLOCK = "ARTIFACT_UNLOCK"
    REPLY_SENT = "REPLY_SENT"
    EXPLORE_CHUNK = "EXPLORE_CHUNK"
    PAPER_PLANE = "PAPER_PLANE"
    CONNECTION_UPGRADE = "CONNECTION_UPGRADE"
    GAME_WIN = "GAME_WIN"


# Catalog — keys: id, title, description, icon, trigger, target, xp, layer
QUEST_CATALOG = [
    {
        "id": "leave_memory", 
        "title": "Leave a Memory", 
        "icon": "✍️", 
        "layer": "LIGHT",
        "description": "Drop one artifact for someone to find.",
        "trigger": QuestTrigger.ARTIFACT_CREATE, 
        "target": 1, 
        "xp": 50
    },
    {
        "id": "treasure_hunter", 
        "title": "Treasure Hunter", 
        "icon": "🔓", 
        "layer": "BOTH",
        "description": "Unlock 3 artifacts around the city.",
        "trigger": QuestTrigger.ARTIFACT_UNLOCK, 
        "target": 3, 
        "xp": 40
    },
    {
        "id": "pen_pal", 
        "title": "Pen Pal", 
        "icon": "💌", 
        "layer": "LIGHT",
        "description": "Reply to 2 memories.",
        "trigger": QuestTrigger.REPLY_SENT, 
        "target": 2, 
        "xp": 30
    },
    {
        "id": "wanderer", 
        "title": "Wanderer", 
        "icon": "🧭", 
        "layer": "BOTH",
        "description": "Explore 5 new patches of the map.",
        "trigger": QuestTrigger.EXPLORE_CHUNK, 
        "target": 5, 
        "xp": 40
    },
    {
        "id": "into_the_wind", 
        "title": "Into the Wind", 
        "icon": "✈️", 
        "layer": "LIGHT",
        "description": "Send a paper plane.",
        "trigger": QuestTrigger.PAPER_PLANE, 
        "target": 1, 
        "xp": 30
    },
    {
        "id": "new_connection", 
        "title": "New Connection", 
        "icon": "🔗", "layer": "BOTH",
        "description": "Turn a signal into a connection.",
        "trigger": QuestTrigger.CONNECTION_UPGRADE, 
        "target": 1, 
        "xp": 75
    },
    {
        "id": "campfire_star", "title": "Campfire Star", 
        "icon": "🔥", 
        "layer": "BOTH",
        "description": "Win a round of Truth or Dare.",
        "trigger": QuestTrigger.GAME_WIN, 
        "target": 1, 
        "xp": 40
    },
    {
        "id": "night_owl", 
        "title": "Night Owl", 
        "icon": "🌙", 
        "layer": "SHADOW",
        "description": "Unlock 2 artifacts in the Shadow layer.",
        "trigger": QuestTrigger.ARTIFACT_UNLOCK, 
        "target": 2, 
        "xp": 50
    }
]


# ============================================================
# TIME HELPERS (local midnight)
# ============================================================

def now_local() -> datetime:
    return datetime.now(QUEST_TZ) if QUEST_TZ else datetime.utcnow()


def today_local() -> date:
    return now_local().date()


def seconds_to_midnight() -> int:
    n = now_local()
    tomorrow = (n + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(60, int((tomorrow - n).total_seconds()))


# ============================================================
# REDIS KEYS
# ============================================================

def _prog_key(uid, d, qid) -> str:
    return f"quest:prog:{uid}:{d}:{qid}"


def _done_key(uid, d, qid) -> str:
    return f"quest:done:{uid}:{d}:{qid}"


class QuestService:

    # ========================================================
    # CATALOG / SELECTION
    # ========================================================

    @staticmethod
    def todays_quests(d: Optional[date] = None) -> List[dict]:
        """Deterministic rotating slice of the catalog for a given date."""
        d = d or today_local()
        pool = QUEST_CATALOG
        start = (d.toordinal() * DAILY_COUNT) % len(pool)
        return [pool[(start + i) % len(pool)] for i in range(DAILY_COUNT)]

    # ========================================================
    # STREAK (pure, testable)
    # ========================================================

    @staticmethod
    def compute_streak(last_date: Optional[date], today: date, current: int, longest: int):
        """Return (current, longest, changed)."""
        if last_date == today:
            return current, longest, False  # already counted today
        if last_date == today - timedelta(days=1):
            current = current + 1
        else:
            current = 1  # first ever, or a gap → reset
        longest = max(longest, current)
        return current, longest, True

    @staticmethod
    def _bump_streak(user: User) -> None:
        cur, longest, changed = QuestService.compute_streak(
            user.last_quest_date, today_local(),
            user.current_streak or 0, user.longest_streak or 0,
        )
        if changed:
            user.current_streak = cur
            user.longest_streak = longest
            user.last_quest_date = today_local()

    # ========================================================
    # PROGRESS / COMPLETION
    # ========================================================

    @staticmethod
    async def report_progress(
        db: AsyncSession,
        user_id: UUID,
        trigger: QuestTrigger,
        amount: int = 1,
    ) -> List[dict]:
        """
        Advance any of today's active quests matching `trigger`. Returns a list
        of quests that completed as a result (each: {id, title, xp}).
        """
        client = get_optional_redis()
        if client is None:
            return []  # degraded: no progress tracking without Redis

        d = today_local().isoformat()
        matching = [q for q in QuestService.todays_quests() if q["trigger"] == trigger]
        if not matching:
            return []

        completed: List[dict] = []
        user: Optional[User] = None

        for q in matching:
            qid, target = q["id"], q["target"]
            if await client.exists(_done_key(user_id, d, qid)):
                continue

            prog = await client.incrby(_prog_key(user_id, d, qid), amount)
            await client.expire(_prog_key(user_id, d, qid), seconds_to_midnight())

            if prog >= target:
                await client.set(_done_key(user_id, d, qid), "1", ex=seconds_to_midnight())
                if user is None:
                    user = await db.get(User, user_id)

                db.add(QuestCompletion(
                    user_id=user_id, quest_id=qid,
                    quest_date=today_local(), xp_awarded=q["xp"],
                ))
                await XPService.award(
                    db, user_id, XPEventType.DAILY_QUEST,
                    amount=q["xp"],
                    idempotency_key=f"quest:{user_id}:{d}:{qid}",
                )
                if user is not None:
                    QuestService._bump_streak(user)
                completed.append({"id": qid, "title": q["title"], "xp": q["xp"]})

        if completed:
            await db.flush()
            from app.services.badge_service import BadgeService
            await BadgeService.evaluate(db, user_id)
        return completed

    # ========================================================
    # READ (for the mobile screen)
    # ========================================================

    @staticmethod
    async def get_today(db: AsyncSession, user_id: UUID) -> dict:
        client = get_optional_redis()
        d = today_local().isoformat()
        quests = QuestService.todays_quests()

        items = []
        completed_count = 0
        for q in quests:
            prog = 0
            if client is not None:
                raw = await client.get(_prog_key(user_id, d, q["id"]))
                prog = int(raw) if raw else 0
            done = prog >= q["target"]
            if done:
                completed_count += 1
            items.append({
                "id": q["id"], "title": q["title"], "description": q["description"],
                "icon": q["icon"], "layer": q["layer"], "target": q["target"],
                "progress": min(prog, q["target"]), "completed": done,
                "xp_reward": q["xp"],
            })

        user = await db.get(User, user_id)
        streak = {
            "current": (user.current_streak or 0) if user else 0,
            "longest": (user.longest_streak or 0) if user else 0,
            "active_today": bool(user and user.last_quest_date == today_local()),
        }
        return {
            "date": d, "streak": streak, "quests": items,
            "completed_count": completed_count, "total_count": len(quests),
        }
