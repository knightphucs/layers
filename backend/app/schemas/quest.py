"""
LAYERS - Quest Schemas
"""

from typing import List
from pydantic import BaseModel


class QuestItem(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    layer: str          # LIGHT | SHADOW | BOTH
    target: int
    progress: int
    completed: bool
    xp_reward: int


class QuestStreak(BaseModel):
    current: int
    longest: int
    active_today: bool   # has the user completed a quest today?


class QuestTodayResponse(BaseModel):
    date: str
    streak: QuestStreak
    quests: List[QuestItem]
    completed_count: int
    total_count: int


class QuestCompletedItem(BaseModel):
    """Returned inline by actions when a quest completes as a side effect."""
    id: str
    title: str
    xp: int
