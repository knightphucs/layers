"""
================================
V1 API - MAP
LAYERS - Map/Location Endpoints
================================
"""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.services.location_service import LocationService
from app.utils.anti_cheat import validate_location
from app.schemas.location import (
    LocationCreate, LocationUpdate, NearbyQuery,
    LocationResponse, LocationListResponse,
    LocationDetailResponse, NearbyCountResponse,
    LayerType, LocationCategory, SortBy,
)

router = APIRouter(prefix="/map", tags=["Map & Locations"])


# ============================================================
# POST /api/v1/map/locations — Create a new location
# ============================================================

@router.post(
    "/locations",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new location",
)
async def create_location(
    data: LocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(validate_location),
):
    try:
        location = await LocationService.create_location(
            db=db, data=data, user_id=current_user.id,
        )
        return LocationResponse(
            id=location.id, latitude=location.latitude, longitude=location.longitude,
            layer=location.layer, category=location.category, name=location.name,
            description=location.description, address=location.address,
            metadata=location.location_meta, is_verified=location.is_verified,
            visit_count=location.visit_count, artifact_count=location.artifact_count,
            created_by=location.created_by, created_at=location.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# GET /api/v1/map/nearby — THE CORE GEO-QUERY ⭐
# ============================================================

@router.get(
    "/nearby",
    response_model=LocationListResponse,
    summary="Find locations near you",
)
async def get_nearby_locations(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: float = Query(1000, ge=10, le=10000, description="Radius in meters"),
    layer: Optional[LayerType] = Query(None),
    category: Optional[LocationCategory] = Query(None),
    sort_by: SortBy = Query(SortBy.DISTANCE),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = NearbyQuery(
        lat=lat, lng=lng, radius=radius, layer=layer,
        category=category, sort_by=sort_by, limit=limit, offset=offset,
    )
    return await LocationService.get_nearby(db=db, query=query)


# ============================================================
# GET /api/v1/map/nearby/count — Quick count for map badge
# ============================================================

@router.get("/nearby/count", response_model=NearbyCountResponse)
async def get_nearby_count(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: float = Query(1000, ge=10, le=10000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await LocationService.get_nearby_count(db=db, lat=lat, lng=lng, radius=radius)


# ============================================================
# GET /api/v1/map/locations/mine — My created locations
# ============================================================

@router.get("/locations/mine", response_model=LocationListResponse)
async def get_my_locations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await LocationService.get_user_locations(
        db=db, user_id=current_user.id, limit=limit, offset=offset,
    )


# ============================================================
# GET /api/v1/map/locations/{id} — Single location detail
# ============================================================

@router.get("/locations/{location_id}", response_model=LocationDetailResponse)
async def get_location(
    location_id: UUID,
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lng: Optional[float] = Query(None, ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    location = await LocationService.get_by_id(
        db=db, location_id=location_id, user_lat=lat, user_lng=lng,
    )
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


# ============================================================
# PATCH /api/v1/map/locations/{id} — Update
# ============================================================

@router.patch("/locations/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: UUID,
    data: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    location = await LocationService.update_location(
        db=db, location_id=location_id, data=data, user_id=current_user.id,
    )
    if not location:
        raise HTTPException(status_code=404, detail="Location not found or no permission")
    return LocationResponse(
        id=location.id, latitude=location.latitude, longitude=location.longitude,
        layer=location.layer, category=location.category, name=location.name,
        description=location.description, address=location.address,
        metadata=location.location_meta, is_verified=location.is_verified,
        visit_count=location.visit_count, artifact_count=location.artifact_count,
        created_by=location.created_by, created_at=location.created_at,
    )


# ============================================================
# DELETE /api/v1/map/locations/{id} — Soft delete
# ============================================================

@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await LocationService.delete_location(
        db=db, location_id=location_id, user_id=current_user.id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Location not found or no permission")
