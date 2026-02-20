"""
LAYERS - User Model
User accounts and profiles
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class UserRole(str, Enum):
    """User roles for access control"""
    USER = "USER"
    ADMIN = "ADMIN"
    PARTNER = "PARTNER"  # Business partners (cafes, etc.)


class User(Base):
    """
    User account model.
    
    Stores user credentials, profile info, and gamification data.
    """
    __tablename__ = "users"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Profile
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Gamification
    experience_points: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    reputation_score: Mapped[int] = mapped_column(
        Integer,
        default=100  # Start with good reputation
    )
    level: Mapped[int] = mapped_column(
        Integer,
        default=1
    )
    
    # Status
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.USER
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False  # Email verification
    )
    is_banned: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Password Reset
    reset_token_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    reset_token_expiry: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    # Anti-Cheat columns
    # Anti-Cheat (Week 3 Day 4)
    cheat_strikes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Anti-cheat violation count (3 = perm ban)"
    )
    banned_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Temp ban expiry (NULL = not temp banned)"
    )
    ban_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Reason for ban"
    )
    
    # Relationships (defined later to avoid circular imports)
    # artifacts = relationship("Artifact", back_populates="user")
    # inventory_items = relationship("InventoryItem", back_populates="user")
    
    def __repr__(self) -> str:
        return f"<User {self.username} ({self.email})>"
    
    def add_xp(self, amount: int) -> bool:
        """
        Add experience points and check for level up.
        
        Returns True if leveled up.
        """
        self.experience_points += amount
        
        # Simple level formula: level = 1 + (xp / 1000)
        new_level = 1 + (self.experience_points // 1000)
        
        if new_level > self.level:
            self.level = new_level
            return True
        return False
    
    def modify_reputation(self, change: int) -> None:
        """
        Modify reputation score (positive or negative).
        
        Score is clamped between 0 and 1000.
        """
        self.reputation_score = max(0, min(1000, self.reputation_score + change))


# XP rewards for actions (can be moved to config)
XP_REWARDS = {
    "create_artifact": 50,
    "receive_reply": 30,
    "send_reply": 20,
    "complete_mission": 100,
    "first_check_in": 25,
    "explore_new_area": 15,
}
