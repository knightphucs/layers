"""
LAYERS - Leaderboard Service
===========================================
Redis Sorted Sets for fast, ranked leaderboards.

- Global all-time: `lb:global` — member=user_id, score=total XP (ZADD).
- Weekly: `lb:weekly:{ISOyear}-W{week}` — score=XP earned this week (ZINCRBY),
  expires ~16 days later so old weeks clean themselves up.
- District (optional/generic): `lb:district:{district}` — same shape; populate
  by calling record(..., district=...) once a user's district is known.

Updates are driven from XPService.award() (see the hook there), so the boards
stay fresh automatically. All methods fail open if Redis is down.

Why sorted sets: ZREVRANGE gives top-N and ZREVRANK gives a user's rank in
O(log N) — no `ORDER BY ... LIMIT` scan on Postgres per request.
"""

import logging
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from app.core.redis_client import get_optional_redis
from app.services.quest_service import today_local

logger = logging.getLogger(__name__)

GLOBAL_KEY = "lb:global"
WEEKLY_TTL = 60 * 60 * 24 * 16  # 16 days


def weekly_key(d: Optional[date] = None) -> str:
    d = d or today_local()
    iso = d.isocalendar()  # (year, week, weekday)
    return f"lb:weekly:{iso[0]}-W{iso[1]:02d}"


def district_key(district: str) -> str:
    return f"lb:district:{district}"


def _key_for(scope: str, district: Optional[str] = None) -> str:
    if scope == "weekly":
        return weekly_key()
    if scope == "district" and district:
        return district_key(district)
    return GLOBAL_KEY


class LeaderboardService:

    @staticmethod
    async def record(
        user_id,
        total_xp: int,
        delta: int,
        district: Optional[str] = None,
    ) -> None:
        """Update global (absolute) + weekly (incremental) boards. Fail-open."""
        client = get_optional_redis()
        if client is None:
            return
        try:
            uid = str(user_id)
            pipe = client.pipeline()
            pipe.zadd(GLOBAL_KEY, {uid: total_xp})
            wk = weekly_key()
            if delta:
                pipe.zincrby(wk, delta, uid)
                pipe.expire(wk, WEEKLY_TTL)
            if district and delta:
                dk = district_key(district)
                pipe.zincrby(dk, delta, uid)
            await pipe.execute()
        except Exception as e:  # noqa: BLE001
            logger.debug("leaderboard record failed: %s", e)

    @staticmethod
    async def top(
        scope: str = "global",
        limit: int = 50,
        district: Optional[str] = None,
    ) -> List[Tuple[str, int]]:
        """Return [(user_id, score)] ranked high→low."""
        client = get_optional_redis()
        if client is None:
            return []
        key = _key_for(scope, district)
        try:
            rows = await client.zrevrange(key, 0, max(0, limit - 1), withscores=True)
            return [(member, int(score)) for member, score in rows]
        except Exception as e:  # noqa: BLE001
            logger.debug("leaderboard top failed: %s", e)
            return []

    @staticmethod
    async def rank_of(
        scope: str,
        user_id,
        district: Optional[str] = None,
    ) -> Tuple[Optional[int], int]:
        """Return (rank_1_indexed_or_None, score)."""
        client = get_optional_redis()
        if client is None:
            return None, 0
        key = _key_for(scope, district)
        uid = str(user_id)
        try:
            rank = await client.zrevrank(key, uid)
            score = await client.zscore(key, uid)
            return (
                (rank + 1) if rank is not None else None,
                int(score) if score is not None else 0,
            )
        except Exception as e:  # noqa: BLE001
            logger.debug("leaderboard rank_of failed: %s", e)
            return None, 0
