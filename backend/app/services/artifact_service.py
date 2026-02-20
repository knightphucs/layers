"""
LAYERS - Artifact Service
===========================
The HEART of LAYERS! Business logic for all artifact operations.

KEY CONCEPTS:
- Artifacts are digital memories anchored to physical locations
- Proof of Presence: Must be within 50m to read content
- Privacy: PUBLIC (anyone) / TARGETED (one person) / PASSCODE (secret code)
- Geo-Lock: See icon on map but content locked until you walk there
- Slow Mail: Replies delayed 6-12 hours for emotional weight

"""

import uuid
import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_SetSRID, ST_MakePoint

from app.models.artifact import Artifact, ContentType, Visibility, ArtifactStatus
from app.models.location import Location
from app.models.user import User
from app.schemas.artifact import (
    ArtifactCreate, ArtifactResponse, ArtifactDetail, ArtifactPreview,
    PaperPlaneCreate, PaperPlaneResponse,
    TimeCapsuleCreate,
    ArtifactReplyCreate, ArtifactReplyResponse,
)
from app.utils.geo import random_point_in_ring, haversine_distance

# ============================================================
# CONSTANTS (From Masterplan)
# ============================================================
PROOF_OF_PRESENCE_RADIUS = 50       # meters — must walk here to unlock
SLOW_MAIL_MIN_DELAY_HOURS = 6       # minimum reply delay
SLOW_MAIL_MAX_DELAY_HOURS = 12      # maximum reply delay
PAPER_PLANE_MIN_DISTANCE = 200      # meters
PAPER_PLANE_MAX_DISTANCE = 1000     # meters
MAX_ARTIFACTS_PER_DAY = 5           # rate limit
AUTO_HIDE_REPORT_THRESHOLD = 5      # 5 reports = auto-hide


def _hash_passcode(code: str) -> str:
    """Hash a passcode for storage. Same code always produces same hash."""
    return hashlib.sha256(code.strip().lower().encode()).hexdigest()


def _check_time_lock(unlock_conditions: Optional[dict]) -> tuple[bool, Optional[str]]:
    """
    Check if artifact is time-locked.
    Returns (is_locked, lock_reason)
    """
    if not unlock_conditions:
        return False, None

    now = datetime.utcnow()

    # Time window lock (Shadow Layer: 23:00-03:00)
    if "time_start" in unlock_conditions and "time_end" in unlock_conditions:
        start_hour = int(unlock_conditions["time_start"].split(":")[0])
        end_hour = int(unlock_conditions["time_end"].split(":")[0])
        current_hour = now.hour

        # Handle overnight ranges (23:00-03:00)
        if start_hour > end_hour:
            in_window = current_hour >= start_hour or current_hour < end_hour
        else:
            in_window = start_hour <= current_hour < end_hour

        if not in_window:
            return True, f"Only available {unlock_conditions['time_start']}-{unlock_conditions['time_end']}"

    # Future date lock (Time Capsule)
    if "unlock_date" in unlock_conditions:
        unlock_date = datetime.fromisoformat(unlock_conditions["unlock_date"])
        if now < unlock_date:
            days_left = (unlock_date - now).days
            return True, f"Opens in {days_left} days"

    return False, None


def _build_artifact_response(
    artifact: Artifact,
    distance: Optional[float] = None,
    current_user_id: Optional[uuid.UUID] = None,
    include_payload: bool = False,
    passcode_verified: bool = False,
) -> dict:
    """Build response dict from Artifact model, handling lock/privacy logic."""

    # --- Determine lock status ---
    is_locked = False
    lock_reason = None

    # 1. Geo-lock: is user within 50m?
    if distance is not None and distance > PROOF_OF_PRESENCE_RADIUS:
        is_locked = True
        lock_reason = "distance"

    # 2. Time lock
    time_locked, time_reason = _check_time_lock(artifact.unlock_conditions)
    if time_locked:
        is_locked = True
        lock_reason = time_reason

    # 3. Time Capsule lock
    if artifact.unlock_at and datetime.now(timezone.utc) < artifact.unlock_at:
        is_locked = True
        days_left = (artifact.unlock_at - datetime.now(timezone.utc)).days
        lock_reason = f"Time capsule opens in {days_left} days"

    # 4. Passcode lock
    if artifact.visibility == Visibility.PASSCODE and not passcode_verified:
        is_locked = True
        lock_reason = lock_reason or "passcode"

    # 5. Targeted — only target user can see content
    if artifact.visibility == Visibility.TARGETED:
        if current_user_id and str(artifact.target_user_id) == str(current_user_id):
            pass  # Target user → NOT locked
        elif current_user_id and str(artifact.user_id) == str(current_user_id):
            pass  # Creator → NOT locked
        else:
            is_locked = True
            lock_reason = "This message is for someone else"

    # --- Preview text (first 50 chars for LETTER type) ---
    preview_text = None
    if artifact.content_type == ContentType.LETTER and not is_locked:
        text = artifact.payload.get("text", "")
        preview_text = text[:50] + "..." if len(text) > 50 else text

    # --- Build base response ---
    resp = {
        "id": str(artifact.id),
        "content_type": artifact.content_type,
        "layer": artifact.layer,
        "visibility": artifact.visibility,
        "status": artifact.status,
        "latitude": 0.0,   # Will be set from location join
        "longitude": 0.0,
        "distance_meters": round(distance, 1) if distance else None,
        "view_count": artifact.view_count,
        "reply_count": artifact.reply_count,
        "save_count": artifact.save_count,
        "created_at": artifact.created_at,
        "is_locked": is_locked,
        "lock_reason": lock_reason,
    }

    # Include payload only if unlocked and requested
    if include_payload and not is_locked:
        resp["payload"] = artifact.payload
        resp["unlock_conditions"] = artifact.unlock_conditions
        resp["is_for_me"] = (
            artifact.visibility == Visibility.TARGETED
            and current_user_id
            and str(artifact.target_user_id) == str(current_user_id)
        )

    return resp


class ArtifactService:

    # ========================================================
    # CREATE ARTIFACT
    # ========================================================

    @staticmethod
    async def create_artifact(
        db: AsyncSession,
        data: ArtifactCreate,
        user_id: uuid.UUID,
    ) -> Artifact:
        """
        Create a new artifact at a location.

        Steps:
        1. Rate limit check (max 5/day)
        2. Find or create Location from lat/lng
        3. Handle privacy (hash passcode, resolve target user)
        4. Create artifact with JSONB payload
        5. Update location artifact_count
        """

        # --- Rate limit ---
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_count = (await db.execute(
            select(func.count(Artifact.id)).where(
                and_(Artifact.user_id == user_id, Artifact.created_at >= today_start)
            )
        )).scalar() or 0

        if daily_count >= MAX_ARTIFACTS_PER_DAY:
            raise ValueError(f"Max {MAX_ARTIFACTS_PER_DAY} artifacts per day. Come back tomorrow!")

        # --- Find nearby Location or create new one ---
        user_point = ST_SetSRID(ST_MakePoint(data.longitude, data.latitude), 4326)

        # Look for existing location within 20m
        existing_loc = await db.execute(
            select(Location).where(
                and_(
                    Location.is_active == True,
                    ST_DWithin(Location.geom, user_point, 20)
                )
            ).limit(1)
        )
        location = existing_loc.scalar_one_or_none()

        if not location:
            # Create new location
            geom_wkt = f"SRID=4326;POINT({data.longitude} {data.latitude})"
            location = Location(
                geom=geom_wkt,
                latitude=data.latitude,
                longitude=data.longitude,
                layer=data.layer,
                category="GENERAL",
                created_by=user_id,
            )
            db.add(location)
            await db.flush()  # Get location.id without committing

        # --- Handle privacy ---
        target_user_id = None
        secret_code_hash = None

        if data.visibility == Visibility.TARGETED and data.target_username:
            # Find target user by username
            target_result = await db.execute(
                select(User).where(User.username == data.target_username.lower())
            )
            target_user = target_result.scalar_one_or_none()
            if not target_user:
                raise ValueError(f"User '{data.target_username}' not found")
            target_user_id = target_user.id

        if data.visibility == Visibility.PASSCODE and data.passcode:
            secret_code_hash = _hash_passcode(data.passcode)

        # --- Handle unlock conditions ---
        unlock_at = None
        expires_at = None

        if data.content_type == ContentType.TIME_CAPSULE:
            if data.unlock_conditions and "unlock_date" in data.unlock_conditions:
                unlock_at = datetime.fromisoformat(data.unlock_conditions["unlock_date"])

        if data.content_type == ContentType.VOUCHER:
            if data.payload.get("expiry"):
                expires_at = datetime.fromisoformat(data.payload["expiry"])

        # --- Validate payload per content_type ---
        ArtifactService._validate_payload(data.content_type, data.payload)

        # --- Create artifact ---
        artifact = Artifact(
            location_id=location.id,
            user_id=user_id,
            content_type=data.content_type,
            payload=data.payload,
            visibility=data.visibility,
            target_user_id=target_user_id,
            secret_code_hash=secret_code_hash,
            unlock_conditions=data.unlock_conditions,
            layer=data.layer,
            unlock_at=unlock_at,
            expires_at=expires_at,
        )
        db.add(artifact)

        # Update location stats
        location.artifact_count = (location.artifact_count or 0) + 1

        await db.commit()
        await db.refresh(artifact)
        return artifact

    # ========================================================
    # GET NEARBY ARTIFACTS (Map view)
    # ========================================================

    @staticmethod
    async def get_nearby_artifacts(
        db: AsyncSession,
        lat: float,
        lng: float,
        radius: float = 1000,
        layer: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """
        Find artifacts near user's position.
        Returns previews (not full content) for map markers.
        """
        user_point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
        distance_col = ST_Distance(Location.geom, user_point).label("distance")

        # Build filters
        filters = [
            Artifact.status == ArtifactStatus.ACTIVE,
            Location.is_active == True,
            ST_DWithin(Location.geom, user_point, radius),
        ]
        if layer:
            filters.append(Artifact.layer == layer)
        if content_type:
            filters.append(Artifact.content_type == content_type)

        # Exclude expired vouchers
        filters.append(
            or_(
                Artifact.expires_at == None,
                Artifact.expires_at > datetime.utcnow()
            )
        )

        combined = and_(*filters)

        # Count
        total = (await db.execute(
            select(func.count(Artifact.id))
            .join(Location, Artifact.location_id == Location.id)
            .where(combined)
        )).scalar() or 0

        # Query with location join
        result = await db.execute(
            select(Artifact, Location, distance_col)
            .join(Location, Artifact.location_id == Location.id)
            .where(combined)
            .order_by(distance_col.asc())
            .limit(limit)
            .offset(offset)
        )

        items = []
        for artifact, location, distance in result.all():
            resp = _build_artifact_response(
                artifact, distance=distance, current_user_id=current_user_id,
            )
            resp["latitude"] = location.latitude
            resp["longitude"] = location.longitude
            items.append(ArtifactPreview(
                id=str(artifact.id),
                content_type=artifact.content_type,
                layer=artifact.layer,
                latitude=location.latitude,
                longitude=location.longitude,
                is_locked=resp["is_locked"],
                preview_text=None,  # Preview hidden on map
            ))

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        }

    # ========================================================
    # GET ARTIFACT DETAIL (with unlock logic)
    # ========================================================

    @staticmethod
    async def get_artifact_detail(
        db: AsyncSession,
        artifact_id: uuid.UUID,
        user_lat: Optional[float] = None,
        user_lng: Optional[float] = None,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> Optional[dict]:
        """
        Get full artifact detail with lock/unlock logic.
        
        Proof of Presence: Content only revealed if within 50m.
        Privacy: Targeted artifacts only visible to target user.
        """
        result = await db.execute(
            select(Artifact, Location)
            .join(Location, Artifact.location_id == Location.id)
            .where(
                and_(
                    Artifact.id == artifact_id,
                    Artifact.status == ArtifactStatus.ACTIVE,
                )
            )
        )
        row = result.one_or_none()
        if not row:
            return None

        artifact, location = row

        # Calculate distance
        distance = None
        if user_lat is not None and user_lng is not None:
            distance = haversine_distance(
                user_lat, user_lng, location.latitude, location.longitude
            )

        # Build response (include_payload=True to show content if unlocked)
        resp = _build_artifact_response(
            artifact,
            distance=distance,
            current_user_id=current_user_id,
            include_payload=True,
        )
        resp["latitude"] = location.latitude
        resp["longitude"] = location.longitude

        # Increment view count if unlocked
        if not resp.get("is_locked"):
            artifact.view_count += 1
            await db.commit()

        return resp

    # ========================================================
    # UNLOCK WITH PASSCODE
    # ========================================================

    @staticmethod
    async def unlock_with_passcode(
        db: AsyncSession,
        artifact_id: uuid.UUID,
        passcode: str,
        user_lat: float,
        user_lng: float,
        current_user_id: uuid.UUID,
    ) -> Optional[dict]:
        """
        Attempt to unlock a PASSCODE artifact.
        Requires: correct code + within 50m.
        """
        result = await db.execute(
            select(Artifact, Location)
            .join(Location, Artifact.location_id == Location.id)
            .where(and_(
                Artifact.id == artifact_id,
                Artifact.visibility == Visibility.PASSCODE,
                Artifact.status == ArtifactStatus.ACTIVE,
            ))
        )
        row = result.one_or_none()
        if not row:
            return None

        artifact, location = row

        # Check geo-lock first
        distance = haversine_distance(user_lat, user_lng, location.latitude, location.longitude)
        if distance > PROOF_OF_PRESENCE_RADIUS:
            raise ValueError(f"Too far! You're {int(distance)}m away. Get within {PROOF_OF_PRESENCE_RADIUS}m.")

        # Check passcode
        if _hash_passcode(passcode) != artifact.secret_code_hash:
            raise ValueError("Wrong passcode! Try again.")

        # Success — return full content
        artifact.view_count += 1
        await db.commit()

        resp = _build_artifact_response(
            artifact, distance=distance, current_user_id=current_user_id,
            include_payload=True, passcode_verified=True,
        )
        resp["latitude"] = location.latitude
        resp["longitude"] = location.longitude
        return resp

    # ========================================================
    # CREATE PAPER PLANE 🛩️
    # ========================================================

    @staticmethod
    async def create_paper_plane(
        db: AsyncSession,
        data: PaperPlaneCreate,
        user_id: uuid.UUID,
    ) -> dict:
        """
        Paper Planes: Write a note, throw it, it lands at a random spot.
        From Masterplan Section 5B: Random Drop Algorithm.
        """
        # Calculate random landing spot
        land_lat, land_lng = random_point_in_ring(
            data.latitude, data.longitude,
            min_radius_m=PAPER_PLANE_MIN_DISTANCE,
            max_radius_m=PAPER_PLANE_MAX_DISTANCE,
        )
        flight_distance = haversine_distance(
            data.latitude, data.longitude, land_lat, land_lng
        )

        # Create location at landing spot
        geom_wkt = f"SRID=4326;POINT({land_lng} {land_lat})"
        location = Location(
            geom=geom_wkt,
            latitude=land_lat,
            longitude=land_lng,
            layer="LIGHT",
            category="GENERAL",
            created_by=user_id,
        )
        db.add(location)
        await db.flush()

        # Create artifact
        artifact = Artifact(
            location_id=location.id,
            user_id=user_id,
            content_type=ContentType.PAPER_PLANE,
            payload={
                "text": data.text,
                "flight_distance": round(flight_distance, 1),
                "origin": {"latitude": data.latitude, "longitude": data.longitude},
            },
            visibility=Visibility.PUBLIC,
            layer="LIGHT",
        )
        db.add(artifact)
        location.artifact_count = 1
        await db.commit()
        await db.refresh(artifact)

        return {
            "id": str(artifact.id),
            "text": data.text,
            "landed_at": {"latitude": land_lat, "longitude": land_lng},
            "flight_distance_meters": round(flight_distance, 1),
            "created_at": artifact.created_at,
        }

    # ========================================================
    # REPLY TO ARTIFACT (Slow Mail Protocol)
    # ========================================================

    @staticmethod
    async def reply_to_artifact(
        db: AsyncSession,
        artifact_id: uuid.UUID,
        data: ArtifactReplyCreate,
        user_id: uuid.UUID,
        user_lat: float,
        user_lng: float,
    ) -> dict:
        """
        Reply to an artifact using Slow Mail Protocol.
        From Masterplan: Reply delayed 6-12 hours randomly.
        """
        # Find artifact + location
        result = await db.execute(
            select(Artifact, Location)
            .join(Location, Artifact.location_id == Location.id)
            .where(and_(
                Artifact.id == artifact_id,
                Artifact.status == ArtifactStatus.ACTIVE,
            ))
        )
        row = result.one_or_none()
        if not row:
            raise ValueError("Artifact not found")

        artifact, location = row

        # Proof of Presence check
        distance = haversine_distance(user_lat, user_lng, location.latitude, location.longitude)
        if distance > PROOF_OF_PRESENCE_RADIUS:
            raise ValueError(
                f"You're {int(distance)}m away. Walk within {PROOF_OF_PRESENCE_RADIUS}m to reply."
            )

        # Can't reply to own artifact
        if str(artifact.user_id) == str(user_id):
            raise ValueError("You can't reply to your own artifact!")

        # Calculate random delivery time (Slow Mail: 6-12 hours)
        delay_hours = random.uniform(SLOW_MAIL_MIN_DELAY_HOURS, SLOW_MAIL_MAX_DELAY_HOURS)
        deliver_at = datetime.utcnow() + timedelta(hours=delay_hours)

        # Import reply model (avoid circular import)
        from app.models.artifact import ArtifactReply
        reply = ArtifactReply(
            artifact_id=artifact.id,
            user_id=user_id,
            content=data.content,
            deliver_at=deliver_at,
            is_delivered=False,
        )
        db.add(reply)

        # Update artifact stats
        artifact.reply_count += 1
        await db.commit()
        await db.refresh(reply)

        return {
            "id": str(reply.id),
            "content": data.content,
            "is_delivered": False,
            "deliver_at": deliver_at,
            "created_at": reply.created_at,
            "message": f"Reply will be delivered in ~{int(delay_hours)} hours ✉️",
        }

    # ========================================================
    # REPORT ARTIFACT
    # ========================================================

    @staticmethod
    async def report_artifact(
        db: AsyncSession,
        artifact_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
    ) -> dict:
        """
        Report an artifact. From Masterplan: 5 reports = auto-hide.
        """
        result = await db.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        artifact = result.scalar_one_or_none()
        if not artifact:
            raise ValueError("Artifact not found")

        artifact.report_count += 1

        # Auto-hide at threshold
        if artifact.report_count >= AUTO_HIDE_REPORT_THRESHOLD:
            artifact.status = ArtifactStatus.HIDDEN

        await db.commit()

        return {
            "message": "Report submitted. Thank you for keeping LAYERS safe!",
            "artifact_hidden": artifact.status == ArtifactStatus.HIDDEN,
        }

    # ========================================================
    # MY ARTIFACTS
    # ========================================================

    @staticmethod
    async def get_user_artifacts(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Get all artifacts created by user."""
        base_filter = and_(
            Artifact.user_id == user_id,
            Artifact.status != ArtifactStatus.DELETED,
        )
        total = (await db.execute(
            select(func.count(Artifact.id)).where(base_filter)
        )).scalar() or 0

        result = await db.execute(
            select(Artifact, Location)
            .join(Location, Artifact.location_id == Location.id)
            .where(base_filter)
            .order_by(Artifact.created_at.desc())
            .limit(limit).offset(offset)
        )

        items = []
        for artifact, location in result.all():
            items.append({
                "id": str(artifact.id),
                "content_type": artifact.content_type,
                "layer": artifact.layer,
                "visibility": artifact.visibility,
                "status": artifact.status,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "view_count": artifact.view_count,
                "reply_count": artifact.reply_count,
                "save_count": artifact.save_count,
                "created_at": artifact.created_at,
                "is_locked": False,  # Own artifacts never locked
                "preview_text": artifact.payload.get("text", "")[:50] if artifact.payload else None,
            })

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        }

    # ========================================================
    # DELETE ARTIFACT (Soft delete)
    # ========================================================

    @staticmethod
    async def delete_artifact(
        db: AsyncSession,
        artifact_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Soft-delete. Only creator can delete."""
        result = await db.execute(
            select(Artifact).where(and_(
                Artifact.id == artifact_id,
                Artifact.user_id == user_id,
                Artifact.status != ArtifactStatus.DELETED,
            ))
        )
        artifact = result.scalar_one_or_none()
        if not artifact:
            return False

        artifact.status = ArtifactStatus.DELETED
        await db.commit()
        return True

    # ========================================================
    # PAYLOAD VALIDATION
    # ========================================================

    @staticmethod
    def _validate_payload(content_type: ContentType, payload: dict):
        """Validate payload has required fields for content type."""
        if content_type == ContentType.LETTER:
            if "text" not in payload or not payload["text"].strip():
                raise ValueError("LETTER requires 'text' in payload")

        elif content_type == ContentType.VOICE:
            if "url" not in payload:
                raise ValueError("VOICE requires 'url' in payload")

        elif content_type == ContentType.PHOTO:
            if "url" not in payload:
                raise ValueError("PHOTO requires 'url' in payload")

        elif content_type == ContentType.PAPER_PLANE:
            if "text" not in payload or not payload["text"].strip():
                raise ValueError("PAPER_PLANE requires 'text' in payload")

        elif content_type == ContentType.VOUCHER:
            if "code" not in payload:
                raise ValueError("VOUCHER requires 'code' in payload")

        elif content_type == ContentType.TIME_CAPSULE:
            if "text" not in payload:
                raise ValueError("TIME_CAPSULE requires 'text' in payload")

        elif content_type == ContentType.NOTEBOOK:
            if "pages" not in payload:
                payload["pages"] = []  # Initialize empty notebook
