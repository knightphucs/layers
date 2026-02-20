"""
LAYERS - Exploration Endpoints (Fog of War)
=============================================
API routes for the Fog of War system.

The map starts covered in fog. As users walk around in real life,
the fog clears, revealing the hidden world beneath.

Endpoints:
  POST  /api/v1/explore              — Mark current position as explored
  POST  /api/v1/explore/batch        — Process GPS trail (buffered updates)
  GET   /api/v1/explore/chunks       — Get explored chunks in viewport
  GET   /api/v1/explore/stats        — My exploration stats (gamification)
  GET   /api/v1/explore/heatmap      — Community heatmap (popular areas)
  GET   /api/v1/explore/leaderboard  — Top explorers
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.services.exploration_service import ExplorationService
from app.utils.anti_cheat import validate_location, validate_location_update


router = APIRouter(prefix="/explore", tags=["Exploration (Fog of War)"])


# ============================================================
# Request schemas (local to this router)
# ============================================================

class ExploreRequest(BaseModel):
    """Single point exploration"""
    latitude: float = Field(..., ge=-90, le=90, examples=[10.7725])
    longitude: float = Field(..., ge=-180, le=180, examples=[106.6980])


class BatchExploreRequest(BaseModel):
    """Multiple points from GPS trail"""
    coordinates: List[dict] = Field(
        ...,
        min_length=1,
        max_length=50,
        description='List of {"lat": float, "lng": float} points',
        examples=[[
            {"lat": 10.7725, "lng": 106.6980},
            {"lat": 10.7730, "lng": 106.6985},
            {"lat": 10.7735, "lng": 106.6990},
        ]],
    )


# ============================================================
# POST /explore — Mark single position as explored
# ============================================================

@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Explore your current position",
    description="""
    Call this when user's GPS updates. Marks the ~100m chunk as explored.
    
    If already explored, returns is_new=false (idempotent).
    If new chunk, returns is_new=true + 'New area discovered! 🗺️'
    
    **Tip**: Call this every time the user moves to a new location.
    The client should buffer updates and use /batch for efficiency.
    """,
)
async def explore_position(
    data: ExploreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(validate_location),
):
    return await ExplorationService.explore_at(
        db=db,
        user_id=current_user.id,
        latitude=data.latitude,
        longitude=data.longitude,
    )


# ============================================================
# POST /explore/batch — Process GPS trail
# ============================================================

@router.post(
    "/batch",
    summary="Batch explore from GPS trail",
    description="""
    Process multiple GPS points at once. Ideal for:
    - Buffered location updates (send every 30 seconds)
    - Replaying a walking route
    - Catching up after offline period
    
    Max 50 points per request. Automatically deduplicates chunks.
    """,
)
async def batch_explore(
    data: BatchExploreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    first = data.coordinates[0]
    await validate_location_update(current_user.id, first["lat"], first["lng"], db)
    try:
        return await ExplorationService.batch_explore(
            db=db,
            user_id=current_user.id,
            coordinates=data.coordinates,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# GET /explore/chunks — Get explored chunks in viewport
# ============================================================

@router.get(
    "/chunks",
    summary="Get explored chunks for map rendering",
    description="""
    Returns which chunks the user has explored within a viewport.
    
    The client uses this to render the fog overlay:
    - Explored chunks → clear (visible)
    - Unexplored chunks → fog (dark overlay)
    
    Each chunk includes GPS bounds for rectangle rendering.
    Also returns fog_percentage for the current viewport.
    """,
)
async def get_explored_chunks(
    lat: float = Query(..., ge=-90, le=90, description="Viewport center latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Viewport center longitude"),
    radius: float = Query(1000, ge=100, le=5000, description="Viewport radius in meters"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ExplorationService.get_explored_chunks(
        db=db,
        user_id=current_user.id,
        lat=lat,
        lng=lng,
        radius=radius,
    )


# ============================================================
# GET /explore/stats — My exploration statistics
# ============================================================

@router.get(
    "/stats",
    summary="Get your exploration statistics",
    description="""
    Returns gamification data:
    - Total chunks explored
    - Total area in square meters
    - Percentage of city explored
    - Recent 20 explored chunks
    
    Use this for profile screen, achievements, progress bar.
    """,
)
async def get_exploration_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stats = await ExplorationService.get_stats(db=db, user_id=current_user.id)
    return {
        "total_chunks_explored": stats.total_chunks_explored,
        "total_area_sqm": stats.total_area_sqm,
        "total_area_km2": round(stats.total_area_sqm / 1_000_000, 2),
        "percentage_of_city": stats.percentage_of_city,
        "recent_chunks": [
            {"chunk_x": c.chunk_x, "chunk_y": c.chunk_y, "explored_at": c.explored_at}
            for c in stats.recent_chunks
        ],
    }


# ============================================================
# GET /explore/heatmap — Community exploration heatmap
# ============================================================

@router.get(
    "/heatmap",
    summary="Community exploration heatmap",
    description="""
    Shows which areas are explored by many users (hot) vs few (cold).
    
    Heat levels:
    - 🔴 hot: 50+ explorers
    - 🟠 warm: 10-49 explorers
    - 🟡 cool: 3-9 explorers
    - 🔵 cold: 1-2 explorers
    
    Great for discovering popular areas or finding untouched territory!
    """,
)
async def get_heatmap(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: float = Query(2000, ge=100, le=5000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ExplorationService.get_community_heatmap(
        db=db, lat=lat, lng=lng, radius=radius,
    )


# ============================================================
# GET /explore/leaderboard — Top explorers
# ============================================================

@router.get(
    "/leaderboard",
    summary="Top explorers leaderboard",
    description="Who has explored the most? Walk more to climb the ranks! 🏆",
)
async def get_leaderboard(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ExplorationService.get_leaderboard(db=db, limit=limit)
