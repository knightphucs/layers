"""
LAYERS - Badge & Leaderboard Schemas
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# ---- Badges ----

class BadgeItem(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    unlocked: bool
    unlocked_at: Optional[datetime] = None


class BadgesResponse(BaseModel):
    badges: List[BadgeItem]
    unlocked_count: int
    total: int


class BadgeUnlockedItem(BaseModel):
    id: str
    title: str
    icon: str


# ---- Leaderboard ----

class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: str
    avatar_url: Optional[str] = None
    score: int
    is_me: bool = False


class LeaderboardResponse(BaseModel):
    scope: str
    entries: List[LeaderboardEntry]
    my_rank: Optional[int] = None
    my_score: int = 0
