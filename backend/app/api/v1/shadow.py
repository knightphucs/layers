"""
LAYERS - Shadow API
  GET  /api/v1/shadow/status?lat&lng        — full Shadow state (glitch zones + midnight)
  GET  /api/v1/shadow/midnight              — is the 23:00–03:00 window open now?
  GET  /api/v1/shadow/glitch-zones?lat&lng  — zones near you for the map overlay
  POST /api/v1/shadow/glitch-zones          — [ADMIN] create a zone
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.api.v1.anti_cheat import require_admin
from app.models.user import User
from app.schemas.shadow import GlitchZoneCreate, GlitchZoneResponse
from app.services.shadow_service import ShadowService
from app.utils.shadow_time import (
    is_midnight_window_open, night_lock_status,
    MIDNIGHT_LOCK_START, MIDNIGHT_LOCK_END,
)

router = APIRouter(prefix="/shadow", tags=["Shadow Layer"])


@router.get("/status", summary="Your Shadow Layer state right now")
async def shadow_status(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Are you in a glitch zone? What effects apply? Is the midnight window open?"""
    return await ShadowService.shadow_status(db, lat, lng)


@router.get("/midnight", summary="Is the Midnight Lock window open?")
async def midnight_status(
    current_user: User = Depends(get_current_user),
):
    """No location needed — the 23:00–03:00 window is city-wide (HCMC local time)."""
    s = night_lock_status(MIDNIGHT_LOCK_START, MIDNIGHT_LOCK_END)
    return {
        "window": f"{MIDNIGHT_LOCK_START}–{MIDNIGHT_LOCK_END}",
        "open": s["open"],
        "seconds_until_change": s["seconds_until_change"],
        "message": (
            "🌙 The Shadow Layer is awake." if s["open"]
            else "☀️ The Shadow Layer sleeps until 23:00."
        ),
    }


@router.get("/glitch-zones", summary="Glitch zones near you (map overlay)")
async def nearby_glitch_zones(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: float = Query(2000, ge=100, le=10000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    zones = await ShadowService.nearby_zones(db, lat, lng, radius_m=radius)
    return {"zones": zones, "count": len(zones)}


@router.post(
    "/glitch-zones",
    response_model=GlitchZoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[ADMIN] Create a glitch zone",
)
async def create_glitch_zone(
    data: GlitchZoneCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    try:
        zone = await ShadowService.create_zone(
            db,
            name=data.name,
            center_lat=data.center_lat,
            center_lng=data.center_lng,
            radius_m=data.radius_m,
            glitch_type=data.glitch_type,
            intensity=data.intensity,
            active_start=data.active_start,
            active_end=data.active_end,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))

    return GlitchZoneResponse(
        id=str(zone.id), name=zone.name,
        center_lat=zone.center_lat, center_lng=zone.center_lng,
        radius_m=zone.radius_m, glitch_type=zone.glitch_type,
        intensity=zone.intensity, active_start=zone.active_start,
        active_end=zone.active_end, is_active=zone.is_active,
    )
