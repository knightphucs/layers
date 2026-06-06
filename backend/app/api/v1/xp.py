"""
LAYERS - XP API
==============================
  GET /api/v1/xp/me        — current xp / level / rank / progress
  GET /api/v1/xp/history   — paginated XP event log (cursor-based)
  GET /api/v1/xp/rewards   — the canonical XP values table (for client display)
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.xp_event import XPEvent
from app.schemas.xp import (
    LevelProgress,
    XPHistoryItem,
    XPHistoryResponse,
    XPRewardEntry,
    XPRewardsResponse,
)
from app.services.xp_service import XPService, XP_VALUES, XP_LABELS, XP_PER_LEVEL

router = APIRouter(prefix="/xp", tags=["XP & Gamification"])


@router.get("/me", response_model=LevelProgress, summary="My current XP / level / rank")
async def my_progress(current_user: User = Depends(get_current_user)):
    return XPService.progress(current_user.experience_points)


@router.get("/history", response_model=XPHistoryResponse, summary="My XP history")
async def my_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    cursor: Optional[str] = Query(None, description="ISO timestamp of last item"),
    limit: int = Query(20, ge=1, le=50),
):
    stmt = (
        select(XPEvent)
        .where(XPEvent.user_id == current_user.id)
        .order_by(XPEvent.created_at.desc())
    )
    if cursor:
        from datetime import datetime
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            stmt = stmt.where(XPEvent.created_at < cursor_dt)
        except ValueError:
            pass
    stmt = stmt.limit(limit + 1)

    rows = (await db.execute(stmt)).scalars().all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    next_cursor = rows[-1].created_at.isoformat() if (has_more and rows) else None
    return XPHistoryResponse(
        items=[XPHistoryItem.model_validate(r) for r in rows],
        next_cursor=next_cursor,
    )


@router.get("/rewards", response_model=XPRewardsResponse, summary="XP values table")
async def xp_rewards():
    rewards = [
        XPRewardEntry(
            event_type=et.value,
            amount=amount,
            label=XP_LABELS.get(et, et.value),
        )
        for et, amount in XP_VALUES.items()
    ]
    return XPRewardsResponse(rewards=rewards, xp_per_level=XP_PER_LEVEL)
