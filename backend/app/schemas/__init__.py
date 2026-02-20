"""
LAYERS - Pydantic Schemas Package
Request/Response validation models
"""

from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    UserResponse,
    UserProfile,
    MessageResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePassword
)

from app.schemas.location import (
    LayerType,
    LocationCategory,
    SortBy,
    LocationCreate,
    LocationUpdate,
    LocationResponse,
    LocationListResponse,
    LocationStats,
    LocationDetailResponse,
    NearbyQuery,
    NearbyCountResponse,
    ExploredChunkResponse,
    ExplorationStats
)

from app.schemas.artifact import (
    ContentType,
    Visibility,
    ArtifactStatus,
    ArtifactCreate,
    ArtifactResponse,
    ArtifactDetail,
    ArtifactPreview,
    PaperPlaneCreate,
    PaperPlaneResponse,
    TimeCapsuleCreate,
    ArtifactReplyCreate,
    ArtifactReplyResponse
)

__all__ = [
    # Auth
    "UserRegister",
    "UserLogin", 
    "TokenResponse",
    "TokenRefresh",
    "UserResponse",
    "UserProfile",
    "MessageResponse",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "ChangePassword",
    
    # Location
    "LayerType",
    "LocationCategory",
    "SortBy",
    "LocationCreate",
    "LocationUpdate",
    "LocationResponse",
    "LocationListResponse",
    "LocationStats",
    "LocationDetailResponse",
    "NearbyQuery",
    "NearbyCountResponse",
    "ExploredChunkResponse",
    "ExplorationStats",
    
    # Artifact
    "ContentType",
    "Visibility",
    "ArtifactStatus",
    "ArtifactCreate",
    "ArtifactResponse",
    "ArtifactDetail",
    "ArtifactPreview",
    "PaperPlaneCreate",
    "PaperPlaneResponse",
    "TimeCapsuleCreate",
    "ArtifactReplyCreate",
    "ArtifactReplyResponse",
]
