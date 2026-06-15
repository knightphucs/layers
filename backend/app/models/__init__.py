"""
LAYERS - Models Package
All SQLAlchemy models for the application
"""

from app.models.user import User, UserRole
from app.models.location import Location, ExploredChunk, LayerType, LocationCategory
from app.models.artifact import Artifact, ArtifactReply, ContentType, Visibility, ArtifactStatus
from app.models.connection import Connection, ConnectionStatus
from app.models.inventory import InventoryItem, MailQueue
from app.models.chat import (
    ChatRoom, 
    Message, 
    ChatRoomType,
    ChatRoomStatus, 
    CampfireMember
)
from app.models.notification import DeviceToken, NotificationPreference, NotificationHistory
from app.models.social_spark import (
    ArtifactBoost,
    Wave,
    ArtifactDiscovery,
    SynchronicityEvent,
)
from app.models.game import (
    CampfireGame, 
    CampfireGameRound, 
    CampfireGameAnswer,
    GameState, 
    RoundState
)

__all__ = [
    # User
    "User",
    "UserRole",
    
    # Location
    "Location",
    "ExploredChunk",
    "LayerType",
    "LocationCategory",
    
    # Artifact
    "Artifact",
    "ArtifactReply",
    "ContentType",
    "Visibility",
    "ArtifactStatus",
    
    # Social
    "Connection",
    "ConnectionStatus",
    
    # Inventory
    "InventoryItem",
    "MailQueue",
    
    # Social - Chat
    "ChatRoom",
    "Message",
    "ChatRoomType",
    "ChatRoomStatus",
    "CampfireMember",

    # Notifications
    "DeviceToken",
    "NotificationPreference",
    "NotificationHistory",
    
    # Social Spark
    "ArtifactBoost",
    "Wave",
    "ArtifactDiscovery",
    "SynchronicityEvent",
    
    # Campfire Games
    "CampfireGame",
    "CampfireGameRound",
    "CampfireGameAnswer",
    "GameState",
    "RoundState",
    
    # XP Events
    "XPEvent",
    
    # Quest Completions
    "QuestCompletion",
    
    # User Badges
    "UserBadge",
    
    # Moderation Logs
    "ModerationLog",
]
