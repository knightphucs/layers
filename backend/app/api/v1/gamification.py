"""
LAYERS - Badges & Leaderboard API
  GET  /api/v1/badges/me        — all badges with unlocked state
  POST /api/v1/badges/sync      — re-evaluate; returns newly unlocked
  GET  /api/v1/leaderboard      — ranked board (scope=global|weekly)
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.schemas.gamification import (
    BadgeItem, BadgesResponse, BadgeUnlockedItem,
    LeaderboardEntry, LeaderboardResponse,
)
from app.services.badge_service import BadgeService, BADGE_CATALOG
from app.services.leaderboard_service import LeaderboardService

router = APIRouter(tags=["Badges & Leaderboard"])


# ---------------- Badges ----------------

@router.get("/badges/me", response_model=BadgesResponse, summary="My badges")
async def my_badges(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    unlocked = await BadgeService.existing_with_dates(db, current_user.id)
    items = [
        BadgeItem(
            id=b["id"], title=b["title"], description=b["description"], icon=b["icon"],
            unlocked=b["id"] in unlocked, unlocked_at=unlocked.get(b["id"]),
        )
        for b in BADGE_CATALOG
    ]
    return BadgesResponse(
        badges=items, unlocked_count=len(unlocked), total=len(BADGE_CATALOG)
    )


@router.post("/badges/sync", summary="Re-evaluate badges")
async def sync_badges(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    newly = await BadgeService.evaluate(db, current_user.id)
    return {
        "unlocked": [
            BadgeUnlockedItem(id=b["id"], title=b["title"], icon=b["icon"])
            for b in newly
        ]
    }


# ---------------- Leaderboard ----------------

@router.get("/leaderboard", response_model=LeaderboardResponse, summary="Leaderboard")
async def leaderboard(
    scope: str = Query("global", pattern="^(global|weekly)$"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pairs = await LeaderboardService.top(scope, limit)
    ids = [uid for uid, _ in pairs]

    users = {}
    if ids:
        rows = (
            await db.execute(
                select(User.id, User.username, User.avatar_url)
                .where(User.id.in_([UUID(i) for i in ids]))
            )
        ).all()
        users = {str(r.id): r for r in rows}

    me = str(current_user.id)
    entries = [
        LeaderboardEntry(
            rank=rank,
            user_id=uid,
            username=(users[uid].username if uid in users else "Unknown"),
            avatar_url=(users[uid].avatar_url if uid in users else None),
            score=score,
            is_me=(uid == me),
        )
        for rank, (uid, score) in enumerate(pairs, start=1)
    ]

    my_rank, my_score = await LeaderboardService.rank_of(scope, current_user.id)
    return LeaderboardResponse(
        scope=scope, entries=entries, my_rank=my_rank, my_score=my_score
    )
