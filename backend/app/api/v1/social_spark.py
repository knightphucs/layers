"""
LAYERS - Social Spark API Router
================================================
Endpoints for the boost / wave / synchronicity trio.

  POST /spark/artifacts/{id}/boost      — boost an artifact (24h, wider radius)
  GET  /spark/boosts/quota              — how many boosts left today
  GET  /spark/boosted-nearby            — boosted artifacts (merge w/ map)

  POST /spark/wave                      — drop an anonymous wave
  GET  /spark/waves/nearby              — anonymous count of nearby waves

  POST /spark/artifacts/{id}/discover   — record discovery → maybe synchronicity ✨
  GET  /spark/synchronicities           — my synchronicity history
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.schemas.social_spark import (
    BoostResponse,
    BoostQuotaResponse,
    BoostedArtifactItem,
    BoostedNearbyResponse,
    WaveCreateRequest,
    WaveCreateResponse,
    WaveNearbyResponse,
    DiscoverRequest,
    DiscoverResponse,
    SynchronicityListItem,
    SynchronicityListResponse,
)
from app.services.social_spark_service import (
    SocialSparkService,
    WAVE_NEARBY_RADIUS_M,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spark", tags=["Social Spark"])


# ============================================================
# 📡 SIGNAL BOOST
# ============================================================

@router.post(
    "/artifacts/{artifact_id}/boost",
    response_model=BoostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Boost an artifact so it reaches a wider radius (24h)",
)
async def boost_artifact(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    boost = await SocialSparkService.boost_artifact(
        db, artifact_id, current_user.id
    )
    return BoostResponse.model_validate(boost)


@router.get(
    "/boosts/quota",
    response_model=BoostQuotaResponse,
    summary="How many boosts you have left today",
)
async def get_boost_quota(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quota = await SocialSparkService.get_boost_quota(db, current_user.id)
    return BoostQuotaResponse(**quota)


@router.get(
    "/boosted-nearby",
    response_model=BoostedNearbyResponse,
    summary="Boosted artifacts near you (merge with /artifacts/nearby on the client)",
)
async def get_boosted_nearby(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = await SocialSparkService.get_boosted_nearby(db, lat, lng)
    return BoostedNearbyResponse(
        items=[BoostedArtifactItem(**r) for r in rows]
    )


# ============================================================
# 👋 ANONYMOUS WAVE
# ============================================================

@router.post(
    "/wave",
    response_model=WaveCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Drop an anonymous 'I'm here too' wave",
)
async def create_wave(
    data: WaveCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await SocialSparkService.create_wave(
        db, current_user.id, data.latitude, data.longitude
    )
    return WaveCreateResponse(**result)


@router.get(
    "/waves/nearby",
    response_model=WaveNearbyResponse,
    summary="Anonymous count of active waves near you",
)
async def get_waves_nearby(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_meters: int = Query(WAVE_NEARBY_RADIUS_M, ge=10, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await SocialSparkService.get_waves_nearby(
        db, current_user.id, lat, lng, radius_meters
    )
    return WaveNearbyResponse(**result)


# ============================================================
# ✨ SYNCHRONICITY
# ============================================================

@router.post(
    "/artifacts/{artifact_id}/discover",
    response_model=DiscoverResponse,
    summary="Record that you unlocked an artifact — may spark synchronicity ✨",
    description=(
        "Call this from the client the moment an artifact unlocks (within 50m, "
        "content revealed). Idempotent per user — repeat calls are no-ops. "
        "If another explorer unlocked the same artifact within the last 30 "
        "minutes, both of you get a Synchronicity ping and your connection grows."
    ),
)
async def discover_artifact(
    artifact_id: UUID,
    data: DiscoverRequest = DiscoverRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await SocialSparkService.record_discovery(
        db, artifact_id, current_user.id
    )
    return DiscoverResponse(**result)


@router.get(
    "/synchronicities",
    response_model=SynchronicityListResponse,
    summary="Your synchronicity history ✨",
)
async def list_synchronicities(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await SocialSparkService.list_synchronicities(
        db, current_user.id, limit=limit, offset=offset
    )
    return SynchronicityListResponse(
        items=[SynchronicityListItem(**i) for i in result["items"]],
        total=result["total"],
    )
