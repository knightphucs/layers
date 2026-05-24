"""
LAYERS - Social Spark Schemas
=============================================
Pydantic models for the boost / wave / synchronicity endpoints.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# SIGNAL BOOST  📡
# ============================================================

class BoostCreateRequest(BaseModel):
    """POST /spark/artifacts/{id}/boost — no body fields needed beyond path."""
    # Reserved for future tuning (e.g. custom radius). Empty for now.
    pass


class BoostResponse(BaseModel):
    id: UUID
    artifact_id: UUID
    booster_id: UUID
    boost_radius_meters: int
    created_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class BoostQuotaResponse(BaseModel):
    """How many boosts the user has left today."""
    used_today: int
    daily_limit: int
    remaining: int


class BoostedArtifactItem(BaseModel):
    """A boosted artifact surfaced on the map beyond the normal radius."""
    artifact_id: UUID
    latitude: float
    longitude: float
    distance_meters: float
    boost_expires_at: datetime


class BoostedNearbyResponse(BaseModel):
    items: List[BoostedArtifactItem]


# ============================================================
# WAVE  👋
# ============================================================

class WaveCreateRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class WaveCreateResponse(BaseModel):
    """
    Result of dropping a wave. We never reveal who waved — only how many
    other people waved nearby in the recent window (so it feels reciprocal).
    """
    wave_id: UUID
    expires_at: datetime
    others_waving_nearby: int
    waved_back: bool  # True if someone else had a live wave here when you waved


class WaveNearbyResponse(BaseModel):
    """GET /spark/waves/nearby — fully anonymous."""
    count: int  # Active waves within the radius (excluding your own)
    radius_meters: int


# ============================================================
# SYNCHRONICITY  ✨
# ============================================================

class DiscoverRequest(BaseModel):
    """
    POST /spark/artifacts/{id}/discover — call when an artifact unlocks
    on the client (within 50m, content revealed). Idempotent per user.
    """
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class SynchronicityMatch(BaseModel):
    """A single sync — anonymized: we never name the other person."""
    event_id: UUID
    artifact_id: UUID
    created_at: datetime


class DiscoverResponse(BaseModel):
    """
    Tells the client whether this discovery sparked a synchronicity.
    `is_new_discovery` is False on repeat calls (idempotent no-op).
    """
    is_new_discovery: bool
    synchronicity: Optional[SynchronicityMatch] = None
    message: Optional[str] = None  # e.g. "Someone else felt this too ✨"


class SynchronicityListItem(BaseModel):
    event_id: UUID
    artifact_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class SynchronicityListResponse(BaseModel):
    items: List[SynchronicityListItem]
    total: int
