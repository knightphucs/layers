"""
LAYERS - Shadow schemas
"""

from typing import Optional
from pydantic import BaseModel, Field


class GlitchZoneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    center_lat: float = Field(..., ge=-90, le=90)
    center_lng: float = Field(..., ge=-180, le=180)
    radius_m: int = Field(150, ge=20, le=2000)
    glitch_type: str = Field("XP_SURGE", description="XP_SURGE | SHADOW_REVEAL | ANONYMOUS")
    intensity: float = Field(2.0, ge=1.0, le=3.0)
    active_start: Optional[str] = Field("23:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    active_end: Optional[str] = Field("03:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")

    model_config = {"from_attributes": True}


class GlitchZoneResponse(BaseModel):
    id: str
    name: str
    center_lat: float
    center_lng: float
    radius_m: int
    glitch_type: str
    intensity: float
    active_start: Optional[str]
    active_end: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}
