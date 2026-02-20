"""
LAYERS - Location Schemas
Pydantic models for location-related requests/responses
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class LayerType(str, Enum):
    LIGHT = "LIGHT"
    SHADOW = "SHADOW"


class LocationCategory(str, Enum):
    CAFE = "CAFE"
    PARK = "PARK"
    RESTAURANT = "RESTAURANT"
    LANDMARK = "LANDMARK"
    STREET = "STREET"
    GHOST = "GHOST"
    VOUCHER = "VOUCHER"
    CUSTOM = "CUSTOM"
    MONUMENT = "MONUMENT"
    SCHOOL = "SCHOOL"
    MARKET = "MARKET"
    GENERAL = "GENERAL"
    URBAN_LEGEND = "URBAN_LEGEND"
    MIDNIGHT = "MIDNIGHT"
    CHALLENGE = "CHALLENGE"
    HIDDEN_GEM = "HIDDEN_GEM"


class SortBy(str, Enum):
    DISTANCE = "distance"
    NEWEST = "newest"
    MOST_VISITED = "most_visited"
    MOST_ARTIFACTS = "most_artifacts"


class LocationCreate(BaseModel):
    """Create a new location"""
    latitude: float = Field(..., ge=-90, le=90, examples=[10.7769])
    longitude: float = Field(..., ge=-180, le=180, examples=[106.7009])
    layer: LayerType = Field(default=LayerType.LIGHT)
    category: LocationCategory = Field(default=LocationCategory.GENERAL)
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    address: Optional[str] = Field(None, max_length=500)
    metadata: Optional[dict] = Field(default=None)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v):
        if v is not None:
            import json
            if len(json.dumps(v)) > 10000:
                raise ValueError("Metadata too large (max 10KB)")
        return v


class LocationUpdate(BaseModel):
    """PATCH /api/v1/map/locations/{id}"""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    address: Optional[str] = Field(None, max_length=500)
    category: Optional[LocationCategory] = None
    metadata: Optional[dict] = None
    is_active: Optional[bool] = None


class LocationResponse(BaseModel):
    """Location response"""
    id: UUID
    latitude: float
    longitude: float
    layer: LayerType
    category: LocationCategory
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    metadata: Optional[dict] = None
    is_verified: bool = False
    visit_count: int = 0
    artifact_count: int = 0
    created_by: Optional[UUID] = None
    created_at: datetime
    distance_meters: Optional[float] = None

    model_config = {"from_attributes": True}


class LocationListResponse(BaseModel):
    items: List[LocationResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class LocationStats(BaseModel):
    """Stats for a location detail view"""
    total_artifacts: int = 0
    total_visitors: int = 0
    light_artifacts: int = 0
    shadow_artifacts: int = 0
    first_artifact_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None


class LocationDetailResponse(LocationResponse):
    """Extended location response with stats"""
    stats: Optional[LocationStats] = None
    user_distance_meters: Optional[float] = None
    is_within_reach: Optional[bool] = None  # True if < 50m


class NearbyCountResponse(BaseModel):
    total: int
    light_count: int
    shadow_count: int
    nearest_distance_meters: Optional[float] = None


class NearbyQuery(BaseModel):
    """GET /api/v1/map/nearby query parameters"""
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    radius: float = Field(default=1000, ge=10, le=10000)
    layer: Optional[LayerType] = None
    category: Optional[LocationCategory] = None
    sort_by: SortBy = Field(default=SortBy.DISTANCE)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ExploredChunkResponse(BaseModel):
    """Explored chunk for Fog of War"""
    chunk_x: int
    chunk_y: int
    explored_at: datetime


class ExplorationStats(BaseModel):
    """User's exploration statistics"""
    total_chunks_explored: int
    total_area_sqm: float  # Square meters
    percentage_of_city: float  # Approximate
    recent_chunks: List[ExploredChunkResponse]
