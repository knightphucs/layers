"""
LAYERS - Quests API
  GET /api/v1/quests/today  — today's quests + progress + streak
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.schemas.quest import QuestTodayResponse
from app.services.quest_service import QuestService

router = APIRouter(prefix="/quests", tags=["Quests"])


@router.get("/today", response_model=QuestTodayResponse, summary="Today's quests + streak")
async def quests_today(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await QuestService.get_today(db, current_user.id)
    return QuestTodayResponse(**data)
