"""
LAYERS - XP Schemas
==================================
Response shapes for XP/level/rank. XPAwardResult is returned by
XPService.award() and is meant to be embedded in the response of whatever
action granted the XP, so the client gets immediate, authoritative feedback.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class RankInfo(BaseModel):
    tier: int          # 1..10
    title: str         # "Wanderer" ... "Mythic"
    icon: str          # emoji


class LevelProgress(BaseModel):
    xp: int
    level: int
    rank: RankInfo
    xp_into_level: int    # xp earned within the current level
    xp_needed: int        # total xp span of the current level (1000)
    xp_to_next: int       # remaining xp to reach the next level
    pct: float            # 0..100 progress within the level


class XPAwardResult(BaseModel):
    event_type: str
    amount: int           # xp granted by THIS award (0 if duplicate)
    duplicate: bool        # True if idempotency_key already existed
    xp_before: int
    xp_after: int
    level_before: int
    level_after: int
    leveled_up: bool
    rank: RankInfo
    progress: LevelProgress


class XPHistoryItem(BaseModel):
    id: UUID
    event_type: str
    amount: int
    ref_id: Optional[UUID] = None
    xp_after: int
    level_after: int
    created_at: datetime

    model_config = {"from_attributes": True}


class XPHistoryResponse(BaseModel):
    items: List[XPHistoryItem]
    next_cursor: Optional[str] = None


class XPRewardEntry(BaseModel):
    event_type: str
    amount: int
    label: str


class XPRewardsResponse(BaseModel):
    rewards: List[XPRewardEntry]
    xp_per_level: int
