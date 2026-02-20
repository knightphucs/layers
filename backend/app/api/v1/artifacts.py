"""
LAYERS - Artifact Endpoints
==============================
API routes for the artifact system — the HEART of LAYERS.

Endpoints:
  POST   /api/v1/artifacts                  — Create artifact (Letter, Voice, Photo...)
  GET    /api/v1/artifacts/nearby            — Find artifacts on map
  GET    /api/v1/artifacts/mine              — My created artifacts
  GET    /api/v1/artifacts/{id}              — Detail with lock/unlock logic
  POST   /api/v1/artifacts/{id}/unlock       — Unlock PASSCODE artifact
  POST   /api/v1/artifacts/{id}/reply        — Reply via Slow Mail
  POST   /api/v1/artifacts/{id}/report       — Report artifact
  DELETE /api/v1/artifacts/{id}              — Soft delete (owner only)
  POST   /api/v1/artifacts/paper-plane       — Throw a paper plane
  POST   /api/v1/artifacts/time-capsule      — Create time capsule
"""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user  # ← Lives in auth.py!
from app.models.user import User
from app.services.artifact_service import ArtifactService
from app.utils.anti_cheat import validate_location, validate_location_update
from app.schemas.artifact import (
    ArtifactCreate,
    ArtifactDetail,
    ArtifactPreview,
    PaperPlaneCreate,
    PaperPlaneResponse,
    TimeCapsuleCreate,
    ArtifactReplyCreate,
    ContentType,
    Visibility,
)

router = APIRouter(prefix="/artifacts", tags=["Artifacts"])


# ============================================================
# POST /artifacts — Create a new artifact
# ============================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new artifact at a location",
    description="""
    Drop a digital memory at your current GPS position.
    
    Content types: LETTER, VOICE, PHOTO, VOUCHER, NOTEBOOK
    Privacy: PUBLIC (everyone), TARGETED (one person), PASSCODE (secret code)
    
    Note: Use /paper-plane and /time-capsule for those specific types.
    """,
)
async def create_artifact(
    data: ArtifactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(validate_location),
):
    try:
        artifact = await ArtifactService.create_artifact(
            db=db, data=data, user_id=current_user.id,
        )
        return {
            "id": str(artifact.id),
            "content_type": artifact.content_type,
            "visibility": artifact.visibility,
            "layer": artifact.layer,
            "status": artifact.status,
            "created_at": artifact.created_at,
            "message": "Artifact created! 🎯",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# GET /artifacts/nearby — Find artifacts on map ⭐
# ============================================================

@router.get(
    "/nearby",
    summary="Find artifacts near your position",
    description="Returns artifact previews (icons) for map markers. Content is locked until within 50m.",
)
async def get_nearby_artifacts(
    lat: float = Query(..., ge=-90, le=90, description="Your latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Your longitude"),
    radius: float = Query(1000, ge=10, le=10000, description="Search radius in meters"),
    layer: Optional[str] = Query(None, description="Filter: LIGHT or SHADOW"),
    content_type: Optional[str] = Query(None, description="Filter: LETTER, VOUCHER, etc."),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await validate_location_update(current_user.id, lat, lng, db)
    return await ArtifactService.get_nearby_artifacts(
        db=db, lat=lat, lng=lng, radius=radius,
        layer=layer, content_type=content_type,
        limit=limit, offset=offset,
        current_user_id=current_user.id,
    )


# ============================================================
# GET /artifacts/mine — My created artifacts
# ============================================================

@router.get("/mine", summary="Get your created artifacts")
async def get_my_artifacts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ArtifactService.get_user_artifacts(
        db=db, user_id=current_user.id, limit=limit, offset=offset,
    )


# ============================================================
# GET /artifacts/{id} — Detail with lock/unlock logic
# ============================================================

@router.get(
    "/{artifact_id}",
    summary="Get artifact detail",
    description="""
    Returns full artifact content IF unlocked.
    
    Lock conditions:
    - **Geo-Lock**: Must be within 50m (Proof of Presence)
    - **Time Lock**: Shadow Layer artifacts may only be visible at night
    - **Passcode**: Use POST /artifacts/{id}/unlock with the code
    - **Targeted**: Only the intended recipient can see content
    """,
)
async def get_artifact_detail(
    artifact_id: UUID,
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Your latitude for distance check"),
    lng: Optional[float] = Query(None, ge=-180, le=180, description="Your longitude for distance check"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if lat is not None and lng is not None:
        await validate_location_update(current_user.id, lat, lng, db)
    result = await ArtifactService.get_artifact_detail(
        db=db,
        artifact_id=artifact_id,
        user_lat=lat,
        user_lng=lng,
        current_user_id=current_user.id,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return result


# ============================================================
# POST /artifacts/{id}/unlock — Unlock PASSCODE artifact
# ============================================================

@router.post(
    "/{artifact_id}/unlock",
    summary="Unlock a passcode-protected artifact",
    description="Must be within 50m AND provide the correct passcode.",
)
async def unlock_artifact(
    artifact_id: UUID,
    passcode: str = Query(..., min_length=1, description="The secret passcode"),
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await validate_location_update(current_user.id, lat, lng, db)
    try:
        result = await ArtifactService.unlock_with_passcode(
            db=db,
            artifact_id=artifact_id,
            passcode=passcode,
            user_lat=lat,
            user_lng=lng,
            current_user_id=current_user.id,
        )
        if not result:
            raise HTTPException(status_code=404, detail="Artifact not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# POST /artifacts/{id}/reply — Slow Mail Reply ✉️
# ============================================================

@router.post(
    "/{artifact_id}/reply",
    status_code=status.HTTP_201_CREATED,
    summary="Reply to an artifact (Slow Mail)",
    description="""
    Reply to someone's memory or letter.
    
    **Slow Mail Protocol**: Your reply won't arrive instantly.
    It's queued with a random delay of 6-12 hours,
    like waiting for a real letter. ✉️
    
    Requirements: Must be within 50m of the artifact.
    """,
)
async def reply_to_artifact(
    artifact_id: UUID,
    data: ArtifactReplyCreate,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await validate_location_update(current_user.id, lat, lng, db)
    try:
        return await ArtifactService.reply_to_artifact(
            db=db,
            artifact_id=artifact_id,
            data=data,
            user_id=current_user.id,
            user_lat=lat,
            user_lng=lng,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# POST /artifacts/{id}/report — Report artifact
# ============================================================

@router.post(
    "/{artifact_id}/report",
    summary="Report inappropriate content",
    description="5 reports = auto-hide. Keeps LAYERS safe.",
)
async def report_artifact(
    artifact_id: UUID,
    reason: str = Query(..., min_length=5, max_length=500, description="Why are you reporting?"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await ArtifactService.report_artifact(
            db=db,
            artifact_id=artifact_id,
            user_id=current_user.id,
            reason=reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# DELETE /artifacts/{id} — Soft delete
# ============================================================

@router.delete(
    "/{artifact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete your artifact",
)
async def delete_artifact(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await ArtifactService.delete_artifact(
        db=db, artifact_id=artifact_id, user_id=current_user.id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Artifact not found or no permission")


# ============================================================
# POST /artifacts/paper-plane — Throw a paper plane 🛩️
# ============================================================

@router.post(
    "/paper-plane",
    status_code=status.HTTP_201_CREATED,
    summary="Throw a paper plane",
    description="""
    Write a short message (max 280 chars) and throw it!
    It lands at a random spot 200m-1km away.
    Someone else can find it when they walk by. 🛩️
    """,
)
async def create_paper_plane(
    data: PaperPlaneCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(validate_location),
):
    try:
        return await ArtifactService.create_paper_plane(
            db=db, data=data, user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# POST /artifacts/time-capsule — Create time capsule ⏰
# ============================================================

@router.post(
    "/time-capsule",
    status_code=status.HTTP_201_CREATED,
    summary="Create a time capsule",
    description="Send a message to the future! Choose when it unlocks (e.g., 1 year from now).",
)
async def create_time_capsule(
    data: TimeCapsuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(validate_location),
):
    try:
        artifact_data = ArtifactCreate(
            latitude=data.latitude,
            longitude=data.longitude,
            content_type=ContentType.TIME_CAPSULE,
            payload={
                "text": data.text,
                "media_url": data.media_url,
            },
            visibility=Visibility.PUBLIC,
            layer="LIGHT",
            unlock_conditions={"unlock_date": data.unlock_date.isoformat()},
        )
        artifact = await ArtifactService.create_artifact(
            db=db, data=artifact_data, user_id=current_user.id,
        )
        return {
            "id": str(artifact.id),
            "content_type": "TIME_CAPSULE",
            "unlock_at": data.unlock_date,
            "created_at": artifact.created_at,
            "message": f"Time capsule sealed! Opens on {data.unlock_date.strftime('%B %d, %Y')} ⏰",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
