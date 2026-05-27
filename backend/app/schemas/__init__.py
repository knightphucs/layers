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

from app.schemas.chat import (
    ChatRoomType,
    ChatRoomStatus,
    MessageResponse as ChatMessageResponse,
    ChatRoomResponse,
    ChatRoomDetail,
    MessageListResponse,
    SendMessageRequest,
    CampfireFindOrCreateRequest,
    CampfireJoinRequest,
    CampfireMemberInfo,
    CampfireMembersResponse,
    CampfireNearbyItem,
    CampfireNearbyResponse,
    WSClientMessage,
    WSClientPing,
    WSClientPayload,
    WSServerMessage,
    WSServerPresence,
    WSServerError,
    WSServerPong,
    WSCloseCode,
)

from app.schemas.social_spark import (
    BoostCreateRequest,
    BoostResponse,
    BoostQuotaResponse,
    BoostedArtifactItem,
    BoostedNearbyResponse,
    WaveCreateRequest,
    WaveCreateResponse,
    WaveNearbyResponse,
    DiscoverRequest,
    DiscoverResponse,
    SynchronicityMatch,
    SynchronicityListItem,
    SynchronicityListResponse,
)

from app.schemas.game import (
    GameState as GameStateSchema,
    RoundState as RoundStateSchema,
    AnswerSubmitRequest,
    VoteCastRequest,
    GameAnswerResponse,
    GameRoundResponse,
    GameResponse,
    WSGameEvent,
    WSClientTyping,
    WSServerTyping,
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
    
    # Chat
    "ChatRoomType",
    "ChatRoomStatus",
    "ChatMessageResponse",
    "ChatRoomResponse",
    "ChatRoomDetail",
    "MessageListResponse",
    "SendMessageRequest",
    "CampfireFindOrCreateRequest",
    "CampfireJoinRequest",
    "CampfireMemberInfo",
    "CampfireMembersResponse",
    "CampfireNearbyItem",
    "CampfireNearbyResponse",
    "WSClientMessage",
    "WSClientPing",
    "WSClientPayload",
    "WSServerMessage",
    "WSServerPresence",
    "WSServerError",
    "WSServerPong",
    "WSCloseCode",
    
    # Social Spark
    "BoostCreateRequest",
    "BoostResponse",
    "BoostQuotaResponse",
    "BoostedArtifactItem",
    "BoostedNearbyResponse",
    "WaveCreateRequest",
    "WaveCreateResponse",
    "WaveNearbyResponse",
    "DiscoverRequest",
    "DiscoverResponse",
    "SynchronicityMatch",
    "SynchronicityListItem",
    "SynchronicityListResponse",
    
    # Game
    "GameStateSchema",
    "RoundStateSchema",
    "AnswerSubmitRequest",
    "VoteCastRequest",
    "GameAnswerResponse",
    "GameRoundResponse",
    "GameResponse",
    "WSGameEvent",
    "WSClientTyping",
    "WSServerTyping",
]
