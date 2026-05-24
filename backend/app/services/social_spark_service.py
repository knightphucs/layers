"""
LAYERS - Social Spark Service
=============================================
Business logic for the three "social spark" features.

  📡 Signal Boost   — amplify an artifact to a wider discovery radius (24h)
  👋 Anonymous Wave — ephemeral "I'm here too" ping, never reveals identity
  ✨ Synchronicity  — two strangers unlock the same artifact within 30 min,
                      both get pinged AND their connection grows

Synchronicity is intentionally wired into ConnectionService.record_interaction:
a shared moment at a place is exactly the kind of interaction that should make
two strangers a little less strange to each other.

Notifications go through NotificationService.send (W5D2). Calls are wrapped
defensively so a notification failure never breaks the core spark write.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_SetSRID, ST_MakePoint

from app.models.social_spark import (
    ArtifactBoost,
    Wave,
    ArtifactDiscovery,
    SynchronicityEvent,
)
from app.models.artifact import Artifact, ArtifactStatus
from app.models.location import Location

logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTS
# ============================================================

BOOST_DAILY_LIMIT = 3
BOOST_DURATION_HOURS = 24
BOOST_DISCOVERY_RADIUS_M = 2000

WAVE_EXPIRY_MIN = 15
WAVE_COOLDOWN_SEC = 300              # 5 minutes between waves
WAVE_NEARBY_RADIUS_M = 150          # who counts as "waving near you"

SYNC_WINDOW_MIN = 30                # two unlocks within this window → sync
SYNC_NOTIFY_CATEGORY = "social"
BOOST_NOTIFY_CATEGORY = "discovery"


# In-process wave cooldown (ephemeral data — fine to lose on restart).
# Same pattern as AntiCheatService._location_history / campfire limiter.
_wave_cooldown: dict = {}


# ============================================================
# DEFENSIVE NOTIFICATION HELPER
# ============================================================

async def _notify_safe(
    db: AsyncSession,
    user_id: uuid.UUID,
    notification_type: str,
    category: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> None:
    """
    Best-effort notification. Never raises — a notification problem must not
    roll back a synchronicity/boost/wave write.
    """
    try:
        from app.services.notification_service import NotificationService

        await NotificationService.send(
            db=db,
            user_id=user_id,
            notification_type=notification_type,
            category=category,
            title=title,
            body=body,
            data=data or {},
        )
    except Exception as e:  # noqa: BLE001 — intentional broad catch
        logger.warning(f"_notify_safe failed ({notification_type}): {e}")


async def _grow_connection_safe(
    db: AsyncSession,
    user_a_id: uuid.UUID,
    user_b_id: uuid.UUID,
) -> None:
    """
    Best-effort connection growth. Synchronicity is a real interaction —
    feed it into the W5D4 connection system. Never raises.
    """
    try:
        from app.services.connection_service import ConnectionService

        await ConnectionService.record_interaction(
            db=db, user_a_id=user_a_id, user_b_id=user_b_id
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"_grow_connection_safe failed: {e}")


def _canonical_pair(
    a: uuid.UUID, b: uuid.UUID
) -> Tuple[uuid.UUID, uuid.UUID]:
    """Smaller UUID first — matches ConnectionService + ChatService convention."""
    return (a, b) if str(a) < str(b) else (b, a)


# ============================================================
# SOCIAL SPARK SERVICE
# ============================================================

class SocialSparkService:

    # ========================================================
    # 📡 SIGNAL BOOST
    # ========================================================

    @staticmethod
    async def get_boost_quota(
        db: AsyncSession, user_id: uuid.UUID
    ) -> dict:
        """How many boosts the user has spent today (UTC day)."""
        day_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        result = await db.execute(
            select(func.count(ArtifactBoost.id)).where(
                and_(
                    ArtifactBoost.booster_id == user_id,
                    ArtifactBoost.created_at >= day_start,
                )
            )
        )
        used = result.scalar() or 0
        return {
            "used_today": used,
            "daily_limit": BOOST_DAILY_LIMIT,
            "remaining": max(0, BOOST_DAILY_LIMIT - used),
        }

    @staticmethod
    async def boost_artifact(
        db: AsyncSession,
        artifact_id: uuid.UUID,
        booster_id: uuid.UUID,
    ) -> ArtifactBoost:
        """
        Boost an artifact. Validates:
          - artifact exists + ACTIVE
          - user hasn't exceeded BOOST_DAILY_LIMIT
          - no active (non-expired) boost on this artifact by this user already
        """
        # Artifact must exist and be active
        art_result = await db.execute(
            select(Artifact).where(
                and_(
                    Artifact.id == artifact_id,
                    Artifact.status == ArtifactStatus.ACTIVE,
                )
            )
        )
        artifact = art_result.scalar_one_or_none()
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artifact not found or not active",
            )

        # Daily quota
        quota = await SocialSparkService.get_boost_quota(db, booster_id)
        if quota["remaining"] <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"You've used all {BOOST_DAILY_LIMIT} boosts today. "
                    "Boosts refresh at midnight UTC."
                ),
            )

        # No duplicate active boost by same user on same artifact
        now = datetime.utcnow()
        dup_result = await db.execute(
            select(ArtifactBoost.id).where(
                and_(
                    ArtifactBoost.artifact_id == artifact_id,
                    ArtifactBoost.booster_id == booster_id,
                    ArtifactBoost.expires_at > now,
                )
            )
        )
        if dup_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active boost on this artifact",
            )

        boost = ArtifactBoost(
            artifact_id=artifact_id,
            booster_id=booster_id,
            boost_radius_meters=BOOST_DISCOVERY_RADIUS_M,
            created_at=now,
            expires_at=now + timedelta(hours=BOOST_DURATION_HOURS),
        )
        db.add(boost)
        await db.commit()
        await db.refresh(boost)

        logger.info(
            f"📡 Artifact {artifact_id} boosted by {booster_id} "
            f"(radius {BOOST_DISCOVERY_RADIUS_M}m, 24h)"
        )

        # Let the original author know their memory got amplified
        if artifact.user_id and artifact.user_id != booster_id:
            await _notify_safe(
                db,
                user_id=artifact.user_id,
                notification_type="artifact_boosted",
                category=BOOST_NOTIFY_CATEGORY,
                title="Someone boosted your memory 📡",
                body="A memory you left is now reaching more explorers nearby.",
                data={"artifact_id": str(artifact_id)},
            )

        return boost

    @staticmethod
    async def get_boosted_nearby(
        db: AsyncSession,
        latitude: float,
        longitude: float,
    ) -> List[dict]:
        """
        Boosted artifacts whose location is within their boost radius of the
        user. Mobile merges these with the regular /artifacts/nearby results,
        so a boosted memory can appear from much further away than normal.
        """
        user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        distance_col = ST_Distance(Location.geom, user_point).label("dist")
        now = datetime.utcnow()

        stmt = (
            select(
                Artifact.id,
                Location.latitude,
                Location.longitude,
                distance_col,
                ArtifactBoost.expires_at,
            )
            .join(Location, Artifact.location_id == Location.id)
            .join(ArtifactBoost, ArtifactBoost.artifact_id == Artifact.id)
            .where(
                and_(
                    Artifact.status == ArtifactStatus.ACTIVE,
                    ArtifactBoost.expires_at > now,
                    ST_DWithin(
                        Location.geom,
                        user_point,
                        ArtifactBoost.boost_radius_meters,
                    ),
                )
            )
            .order_by(distance_col.asc())
            .limit(50)
        )
        result = await db.execute(stmt)
        items = []
        seen = set()
        for art_id, lat, lng, dist, expires in result.all():
            if art_id in seen:
                continue
            seen.add(art_id)
            items.append(
                {
                    "artifact_id": art_id,
                    "latitude": lat,
                    "longitude": lng,
                    "distance_meters": round(dist, 1),
                    "boost_expires_at": expires,
                }
            )
        return items

    # ========================================================
    # 👋 ANONYMOUS WAVE
    # ========================================================

    @staticmethod
    async def create_wave(
        db: AsyncSession,
        sender_id: uuid.UUID,
        latitude: float,
        longitude: float,
    ) -> dict:
        """
        Drop an anonymous wave. Returns a count of other people who waved
        nearby recently — never any identity.
        """
        # Cooldown (in-process)
        last = _wave_cooldown.get(sender_id)
        now = datetime.utcnow()
        if last is not None:
            elapsed = (now - last).total_seconds()
            if elapsed < WAVE_COOLDOWN_SEC:
                remaining = int(WAVE_COOLDOWN_SEC - elapsed)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Wave again in {remaining // 60}m {remaining % 60}s.",
                )

        user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)

        # Who else has a live wave nearby (excluding me)?
        others_result = await db.execute(
            select(Wave.sender_id).where(
                and_(
                    Wave.expires_at > now,
                    Wave.sender_id != sender_id,
                    ST_DWithin(Wave.geom, user_point, WAVE_NEARBY_RADIUS_M),
                )
            )
        )
        other_sender_ids = {row[0] for row in others_result.all()}
        others_count = len(other_sender_ids)

        # Persist my wave
        geom_wkt = f"SRID=4326;POINT({longitude} {latitude})"
        wave = Wave(
            sender_id=sender_id,
            geom=geom_wkt,
            latitude=latitude,
            longitude=longitude,
            created_at=now,
            expires_at=now + timedelta(minutes=WAVE_EXPIRY_MIN),
        )
        db.add(wave)
        await db.commit()
        await db.refresh(wave)

        _wave_cooldown[sender_id] = now

        # Ping the others — anonymously — that someone waved near them
        for other_id in other_sender_ids:
            await _notify_safe(
                db,
                user_id=other_id,
                notification_type="wave_nearby",
                category=SYNC_NOTIFY_CATEGORY,
                title="Someone waved near you 👋",
                body="An explorer nearby just said hi. The city's not so empty.",
                data={},
            )

        logger.info(
            f"👋 Wave by {sender_id} @ ({latitude:.4f},{longitude:.4f}) "
            f"— {others_count} others nearby"
        )

        return {
            "wave_id": wave.id,
            "expires_at": wave.expires_at,
            "others_waving_nearby": others_count,
            "waved_back": others_count > 0,
        }

    @staticmethod
    async def get_waves_nearby(
        db: AsyncSession,
        user_id: uuid.UUID,
        latitude: float,
        longitude: float,
        radius_meters: int = WAVE_NEARBY_RADIUS_M,
    ) -> dict:
        """Anonymous count of active waves within radius (excluding mine)."""
        user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        now = datetime.utcnow()
        result = await db.execute(
            select(func.count(Wave.id)).where(
                and_(
                    Wave.expires_at > now,
                    Wave.sender_id != user_id,
                    ST_DWithin(Wave.geom, user_point, radius_meters),
                )
            )
        )
        count = result.scalar() or 0
        return {"count": count, "radius_meters": radius_meters}

    # ========================================================
    # ✨ SYNCHRONICITY
    # ========================================================

    @staticmethod
    async def record_discovery(
        db: AsyncSession,
        artifact_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        """
        Record that `user_id` discovered `artifact_id`. Idempotent.

        On a genuinely new discovery, look back SYNC_WINDOW_MIN for another
        person who discovered the same artifact. If found → SynchronicityEvent,
        notify both, and grow their connection.

        Returns a dict matching DiscoverResponse.
        """
        # Artifact must exist + be active
        art_result = await db.execute(
            select(Artifact).where(
                and_(
                    Artifact.id == artifact_id,
                    Artifact.status == ArtifactStatus.ACTIVE,
                )
            )
        )
        artifact = art_result.scalar_one_or_none()
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artifact not found or not active",
            )

        # Already discovered? → idempotent no-op (no re-trigger)
        existing_result = await db.execute(
            select(ArtifactDiscovery).where(
                and_(
                    ArtifactDiscovery.artifact_id == artifact_id,
                    ArtifactDiscovery.user_id == user_id,
                )
            )
        )
        if existing_result.scalar_one_or_none():
            return {
                "is_new_discovery": False,
                "synchronicity": None,
                "message": None,
            }

        now = datetime.utcnow()
        discovery = ArtifactDiscovery(
            artifact_id=artifact_id,
            user_id=user_id,
            discovered_at=now,
        )
        db.add(discovery)
        await db.commit()
        await db.refresh(discovery)

        # Look for another discoverer within the window (not me)
        window_start = now - timedelta(minutes=SYNC_WINDOW_MIN)
        other_result = await db.execute(
            select(ArtifactDiscovery)
            .where(
                and_(
                    ArtifactDiscovery.artifact_id == artifact_id,
                    ArtifactDiscovery.user_id != user_id,
                    ArtifactDiscovery.discovered_at >= window_start,
                )
            )
            .order_by(ArtifactDiscovery.discovered_at.desc())
            .limit(1)
        )
        other = other_result.scalar_one_or_none()

        if not other:
            return {
                "is_new_discovery": True,
                "synchronicity": None,
                "message": None,
            }

        # ✨ Synchronicity! Canonical pair, de-duped per artifact.
        a_id, b_id = _canonical_pair(user_id, other.user_id)

        dup_event = await db.execute(
            select(SynchronicityEvent).where(
                and_(
                    SynchronicityEvent.artifact_id == artifact_id,
                    SynchronicityEvent.user_a_id == a_id,
                    SynchronicityEvent.user_b_id == b_id,
                )
            )
        )
        event = dup_event.scalar_one_or_none()

        if event is None:
            event = SynchronicityEvent(
                artifact_id=artifact_id,
                user_a_id=a_id,
                user_b_id=b_id,
                created_at=now,
            )
            db.add(event)
            await db.commit()
            await db.refresh(event)

            # Notify BOTH — anonymized, no names
            for uid in (user_id, other.user_id):
                await _notify_safe(
                    db,
                    user_id=uid,
                    notification_type="synchronicity",
                    category=SYNC_NOTIFY_CATEGORY,
                    title="Someone else felt this too ✨",
                    body=(
                        "Another explorer unlocked the same memory you just "
                        "did, moments apart. You're not alone here."
                    ),
                    data={
                        "artifact_id": str(artifact_id),
                        "event_id": str(event.id),
                    },
                )

            # Synchronicity is a real interaction — grow the connection
            await _grow_connection_safe(db, user_id, other.user_id)

            logger.info(
                f"✨ Synchronicity: {a_id} ~ {b_id} on artifact {artifact_id}"
            )

        return {
            "is_new_discovery": True,
            "synchronicity": {
                "event_id": event.id,
                "artifact_id": artifact_id,
                "created_at": event.created_at,
            },
            "message": "Someone else felt this too ✨",
        }

    @staticmethod
    async def list_synchronicities(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """All synchronicity events this user is part of (either side)."""
        base_filter = or_(
            SynchronicityEvent.user_a_id == user_id,
            SynchronicityEvent.user_b_id == user_id,
        )

        total_result = await db.execute(
            select(func.count(SynchronicityEvent.id)).where(base_filter)
        )
        total = total_result.scalar() or 0

        result = await db.execute(
            select(SynchronicityEvent)
            .where(base_filter)
            .order_by(SynchronicityEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        events = result.scalars().all()

        items = [
            {
                "event_id": e.id,
                "artifact_id": e.artifact_id,
                "created_at": e.created_at,
            }
            for e in events
        ]
        return {"items": items, "total": total}
