"""
LAYERS - Shadow Service
======================================
Brings the Shadow Layer alive: Glitch Zone detection + the Midnight Lock view.

Two membership conditions for a zone to affect you RIGHT NOW:
  1. TIME    — the zone's activation window is currently open (tz-aware)
  2. SPACE   — you are physically within radius_m of its center (haversine)

Both must hold. A nocturnal zone you're standing in at noon does nothing; an
active zone across town does nothing. Stand inside one at midnight → glitch.

XP multiplier is exposed (not force-applied) so the XP architecture stays the
single source of truth: the client shows "⚡ 2× XP here", and create/explore
endpoints can OPTIONALLY award a bonus (see SETUP). We never bypass XPService.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.glitch_zone import GlitchZone
from app.utils.geo import haversine_distance
from app.utils.shadow_time import (
    in_window,
    night_lock_status,
    is_midnight_window_open,
    MIDNIGHT_LOCK_START,
    MIDNIGHT_LOCK_END,
)

logger = logging.getLogger(__name__)


class GlitchType(str, Enum):
    XP_SURGE = "XP_SURGE"
    SHADOW_REVEAL = "SHADOW_REVEAL"
    ANONYMOUS = "ANONYMOUS"


# Safety cap so a misconfigured zone can't grant absurd XP.
MAX_XP_MULTIPLIER = 3.0


class ShadowService:

    # ---- pure membership helpers (testable without DB) ----

    @staticmethod
    def zone_is_open(zone: GlitchZone, now_utc: Optional[datetime] = None) -> bool:
        """Time condition: is the zone's window open now? No window = always."""
        if not zone.is_active:
            return False
        if not zone.active_start or not zone.active_end:
            return True
        return in_window(zone.active_start, zone.active_end, now_utc)

    @staticmethod
    def distance_to_center(zone: GlitchZone, lat: float, lng: float) -> float:
        return haversine_distance(lat, lng, zone.center_lat, zone.center_lng)

    @staticmethod
    def is_inside(zone: GlitchZone, lat: float, lng: float) -> bool:
        """Space condition: within the zone's radius."""
        return ShadowService.distance_to_center(zone, lat, lng) <= zone.radius_m

    @staticmethod
    def affects_user(zone: GlitchZone, lat: float, lng: float,
                     now_utc: Optional[datetime] = None) -> bool:
        """Both conditions: open in time AND inside in space."""
        return (ShadowService.zone_is_open(zone, now_utc)
                and ShadowService.is_inside(zone, lat, lng))

    @staticmethod
    def xp_multiplier(zones: List[GlitchZone]) -> float:
        """Highest XP_SURGE intensity among the given zones (capped)."""
        mults = [z.intensity for z in zones if z.glitch_type == GlitchType.XP_SURGE]
        if not mults:
            return 1.0
        return min(max(mults), MAX_XP_MULTIPLIER)

    # ---- DB-aware ----

    @staticmethod
    async def _all_active(db: AsyncSession) -> List[GlitchZone]:
        return list((await db.execute(
            select(GlitchZone).where(GlitchZone.is_active == True)  # noqa: E712
        )).scalars().all())

    @staticmethod
    async def zones_containing_user(
        db: AsyncSession, lat: float, lng: float,
        now_utc: Optional[datetime] = None,
    ) -> List[GlitchZone]:
        """Active zones the user is currently inside (time + space)."""
        now_utc = now_utc or datetime.now(timezone.utc)
        return [z for z in await ShadowService._all_active(db)
                if ShadowService.affects_user(z, lat, lng, now_utc)]

    @staticmethod
    async def nearby_zones(
        db: AsyncSession, lat: float, lng: float, radius_m: float = 2000,
        now_utc: Optional[datetime] = None,
    ) -> List[dict]:
        """Zones near the user for the map overlay. Includes DORMANT zones
        (window closed) so the map can show them sleeping, with when they wake."""
        now_utc = now_utc or datetime.now(timezone.utc)
        out = []
        for z in await ShadowService._all_active(db):
            dist = ShadowService.distance_to_center(z, lat, lng)
            # within search radius OR the user is inside the zone itself
            if dist > radius_m + z.radius_m:
                continue
            open_now = ShadowService.zone_is_open(z, now_utc)
            window = None
            if z.active_start and z.active_end:
                window = night_lock_status(z.active_start, z.active_end, now_utc=now_utc)
            out.append({
                "id": str(z.id),
                "name": z.name,
                "center_lat": z.center_lat,
                "center_lng": z.center_lng,
                "radius_m": z.radius_m,
                "glitch_type": z.glitch_type,
                "intensity": z.intensity,
                "distance_m": round(dist, 1),
                "is_inside": dist <= z.radius_m,
                "is_open_now": open_now,
                "active_start": z.active_start,
                "active_end": z.active_end,
                "seconds_until_change": window["seconds_until_change"] if window else None,
            })
        out.sort(key=lambda d: d["distance_m"])
        return out

    @staticmethod
    async def shadow_status(
        db: AsyncSession, lat: float, lng: float,
        now_utc: Optional[datetime] = None,
    ) -> dict:
        """Everything the client needs about the user's Shadow state right now."""
        now_utc = now_utc or datetime.now(timezone.utc)
        inside = await ShadowService.zones_containing_user(db, lat, lng, now_utc)
        mult = ShadowService.xp_multiplier(inside)
        effects = sorted({z.glitch_type for z in inside})

        midnight = night_lock_status(
            MIDNIGHT_LOCK_START, MIDNIGHT_LOCK_END, now_utc=now_utc
        )
        return {
            "in_glitch_zone": len(inside) > 0,
            "active_zones": [
                {"id": str(z.id), "name": z.name, "glitch_type": z.glitch_type,
                 "intensity": z.intensity}
                for z in inside
            ],
            "xp_multiplier": mult,
            "effects": effects,
            "midnight_window_open": midnight["open"],
            "midnight_seconds_until_change": midnight["seconds_until_change"],
            "shadow_reveal": "SHADOW_REVEAL" in effects,
            "anonymous": "ANONYMOUS" in effects,
        }

    @staticmethod
    async def create_zone(
        db: AsyncSession, name: str, center_lat: float, center_lng: float,
        radius_m: int = 150, glitch_type: str = "XP_SURGE",
        intensity: float = 2.0,
        active_start: Optional[str] = MIDNIGHT_LOCK_START,
        active_end: Optional[str] = MIDNIGHT_LOCK_END,
    ) -> GlitchZone:
        # Validate type
        try:
            GlitchType(glitch_type)
        except ValueError:
            valid = ", ".join(t.value for t in GlitchType)
            raise ValueError(f"Invalid glitch_type. Must be one of: {valid}")

        zone = GlitchZone(
            name=name, center_lat=center_lat, center_lng=center_lng,
            radius_m=radius_m, glitch_type=glitch_type,
            intensity=min(intensity, MAX_XP_MULTIPLIER),
            active_start=active_start, active_end=active_end,
        )
        db.add(zone)
        await db.commit()
        await db.refresh(zone)
        logger.info("Created glitch zone %s (%s)", zone.name, zone.glitch_type)
        return zone
