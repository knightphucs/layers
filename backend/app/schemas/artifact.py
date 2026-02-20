"""
LAYERS - Artifact Schemas
Pydantic models for artifact-related requests/responses
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ContentType(str, Enum):
    LETTER = "LETTER"
    VOICE = "VOICE"
    PHOTO = "PHOTO"
    PAPER_PLANE = "PAPER_PLANE"
    VOUCHER = "VOUCHER"
    TIME_CAPSULE = "TIME_CAPSULE"
    NOTEBOOK = "NOTEBOOK"


class Visibility(str, Enum):
    PUBLIC = "PUBLIC"
    TARGETED = "TARGETED"
    PASSCODE = "PASSCODE"


class ArtifactStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    HIDDEN = "HIDDEN"
    DELETED = "DELETED"


class ArtifactCreate(BaseModel):
    """Create a new artifact"""
    # Location
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    
    # Content
    content_type: ContentType
    payload: Dict[str, Any] = Field(
        ...,
        description="""
        Content varies by type:
        - LETTER: {"text": "Your message here"}
        - VOICE: {"url": "s3://...", "duration_sec": 30}
        - PHOTO: {"url": "s3://...", "caption": "Optional caption"}
        - PAPER_PLANE: {"text": "Short message"}
        - TIME_CAPSULE: {"text": "Message", "unlock_date": "2026-01-01"}
        """
    )
    
    # Privacy
    visibility: Visibility = Visibility.PUBLIC
    target_username: Optional[str] = None  # For TARGETED
    passcode: Optional[str] = None  # For PASSCODE (will be hashed)
    
    # Layer
    layer: str = "LIGHT"
    
    # Unlock conditions (optional)
    unlock_conditions: Optional[Dict[str, Any]] = None
    
    @field_validator("payload")
    @classmethod
    def validate_payload(cls, v: Dict, info):
        """Validate payload has required fields based on content_type"""
        # Note: Full validation would check content_type, but Pydantic v2
        # handles this differently. We'll do full validation in the service.
        if not v:
            raise ValueError("Payload cannot be empty")
        return v


class ArtifactResponse(BaseModel):
    """Artifact response (public view)"""
    id: str
    content_type: ContentType
    layer: str
    visibility: Visibility
    status: ArtifactStatus
    
    # Location info
    latitude: float
    longitude: float
    distance_meters: Optional[float] = None
    
    # Engagement
    view_count: int
    reply_count: int
    save_count: int
    
    # Timestamps
    created_at: datetime
    
    # Unlock info
    is_locked: bool = False  # True if geo-locked or time-locked
    lock_reason: Optional[str] = None  # "distance", "time", "passcode"
    
    # Creator info (optional, hidden for anonymous)
    creator_username: Optional[str] = None
    creator_avatar: Optional[str] = None
    
    class Config:
        from_attributes = True


class ArtifactDetail(ArtifactResponse):
    """Full artifact detail (when unlocked)"""
    payload: Dict[str, Any]
    unlock_conditions: Optional[Dict[str, Any]] = None
    
    # For targeted artifacts
    is_for_me: bool = False


class ArtifactPreview(BaseModel):
    """Minimal artifact preview for map markers"""
    id: str
    content_type: ContentType
    layer: str
    latitude: float
    longitude: float
    is_locked: bool
    preview_text: Optional[str] = None  # First 50 chars for LETTER
    
    class Config:
        from_attributes = True


class PaperPlaneCreate(BaseModel):
    """Create a paper plane (simplified)"""
    text: str = Field(..., min_length=1, max_length=280)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class PaperPlaneResponse(BaseModel):
    """Paper plane after being thrown"""
    id: str
    text: str
    landed_at: Dict[str, float]  # {"latitude": ..., "longitude": ...}
    flight_distance_meters: float
    created_at: datetime


class TimeCapsuleCreate(BaseModel):
    """Create a time capsule"""
    text: str = Field(..., min_length=1, max_length=2000)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    unlock_date: datetime
    media_url: Optional[str] = None


class ArtifactReplyCreate(BaseModel):
    """Reply to an artifact"""
    content: str = Field(..., min_length=1, max_length=1000)


class ArtifactReplyResponse(BaseModel):
    """Artifact reply response"""
    id: str
    content: str
    is_delivered: bool
    deliver_at: datetime
    created_at: datetime
    
    # Sender info (anonymous until connected)
    sender_username: Optional[str] = None
    
    class Config:
        from_attributes = True
