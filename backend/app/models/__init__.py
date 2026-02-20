"""
LAYERS - Models Package
All SQLAlchemy models for the application
"""

from app.models.user import User, UserRole
from app.models.location import Location, ExploredChunk, LayerType, LocationCategory
from app.models.artifact import Artifact, ArtifactReply, ContentType, Visibility, ArtifactStatus
from app.models.connection import Connection, ConnectionStatus
from app.models.inventory import InventoryItem, MailQueue

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
]