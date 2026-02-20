"""
LAYERS - Artifact Model
The heart of the app! Digital memories and content at locations.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from sqlalchemy import String, Integer, DateTime, Text, Enum as SQLEnum, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class ContentType(str, Enum):
    """Type of artifact content"""
    LETTER = "LETTER"           # Text memory/message
    VOICE = "VOICE"             # Voice note
    PHOTO = "PHOTO"             # Photo memory
    PAPER_PLANE = "PAPER_PLANE" # Random flying message
    VOUCHER = "VOUCHER"         # Business voucher/coupon
    TIME_CAPSULE = "TIME_CAPSULE"  # Future unlock
    NOTEBOOK = "NOTEBOOK"       # Shared writing (append-only)


class Visibility(str, Enum):
    """Artifact privacy settings"""
    PUBLIC = "PUBLIC"           # Anyone can read
    TARGETED = "TARGETED"       # Specific user only
    PASSCODE = "PASSCODE"       # Need secret code


class ArtifactStatus(str, Enum):
    """Artifact moderation status"""
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"         # Under review
    HIDDEN = "HIDDEN"           # Auto-hidden by reports
    DELETED = "DELETED"


class Artifact(Base):
    """
    Digital artifact placed at a location.
    
    This is THE core entity of LAYERS. Each artifact represents
    a piece of content (memory, message, voucher) anchored to
    a physical location.
    
    The payload JSONB column stores different data based on content_type:
    
    - LETTER: {"text": "...", "font": "handwritten"}
    - VOICE: {"url": "s3://...", "duration_sec": 30, "transcript": "..."}
    - PHOTO: {"url": "s3://...", "caption": "...", "filter": "vintage"}
    - PAPER_PLANE: {"text": "...", "flight_distance": 500}
    - VOUCHER: {"code": "SALE50", "discount": 50, "expiry": "2025-12-31"}
    - TIME_CAPSULE: {"text": "...", "media_url": null}
    - NOTEBOOK: {"pages": ["User A wrote...", "User B added..."]}
    """
    __tablename__ = "artifacts"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Relationships
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # Allow anonymous artifacts
        index=True
    )
    
    # Content
    content_type: Mapped[ContentType] = mapped_column(
        SQLEnum(ContentType),
        nullable=False,
        index=True
    )
    
    # Flexible payload - different structure per content_type
    payload: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False
    )
    
    # Privacy Controls
    visibility: Mapped[Visibility] = mapped_column(
        SQLEnum(Visibility),
        default=Visibility.PUBLIC
    )
    
    # For TARGETED visibility - who can see it
    target_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # For PASSCODE visibility - hashed secret code
    secret_code_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # Unlock Conditions (JSONB for flexibility)
    # Examples:
    # - Time window: {"time_start": "23:00", "time_end": "03:00"}
    # - Future date: {"unlock_date": "2026-01-01T00:00:00Z"}
    # - Weather: {"weather": "rainy"} (future feature)
    unlock_conditions: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )
    
    # Which layer it belongs to
    layer: Mapped[str] = mapped_column(
        String(20),
        default="LIGHT"
    )
    
    # Status & Moderation
    status: Mapped[ArtifactStatus] = mapped_column(
        SQLEnum(ArtifactStatus),
        default=ArtifactStatus.ACTIVE
    )
    report_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    
    # Engagement Stats
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    reply_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    save_count: Mapped[int] = mapped_column(
        Integer,
        default=0  # Saved to inventory
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
    
    # For TIME_CAPSULE - when it can be opened
    unlock_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # For VOUCHER - expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    location = relationship("Location", back_populates="artifacts", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Artifact {self.id} ({self.content_type.value})>"
    
    def is_visible_to(self, user_id: Optional[uuid.UUID]) -> bool:
        """
        Check if artifact is visible to a specific user.
        
        Note: This doesn't check geo-lock (distance), only privacy.
        """
        if self.status != ArtifactStatus.ACTIVE:
            return False
            
        if self.visibility == Visibility.PUBLIC:
            return True
            
        if self.visibility == Visibility.TARGETED:
            return user_id is not None and self.target_user_id == user_id
            
        if self.visibility == Visibility.PASSCODE:
            # Passcode check is done separately
            return True  # Icon visible, content locked
            
        return False
    
    def is_time_unlocked(self) -> bool:
        """Check if time-based unlock conditions are met"""
        if not self.unlock_conditions:
            return True
            
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        
        # Check unlock_date (for TIME_CAPSULE)
        unlock_date = self.unlock_conditions.get("unlock_date")
        if unlock_date:
            if isinstance(unlock_date, str):
                unlock_date = datetime.fromisoformat(unlock_date.replace("Z", "+00:00"))
            if now < unlock_date:
                return False
        
        # Check time window (for MIDNIGHT_LOCK)
        time_start = self.unlock_conditions.get("time_start")
        time_end = self.unlock_conditions.get("time_end")
        if time_start and time_end:
            current_time = now.time()
            start = datetime.strptime(time_start, "%H:%M").time()
            end = datetime.strptime(time_end, "%H:%M").time()
            
            # Handle overnight windows (e.g., 23:00 - 03:00)
            if start > end:
                if not (current_time >= start or current_time <= end):
                    return False
            else:
                if not (start <= current_time <= end):
                    return False
        
        return True


class ArtifactReply(Base):
    """
    Replies to artifacts (for Memory Inbox feature).
    """
    __tablename__ = "artifact_replies"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    # For Slow Mail - actual delivery time
    deliver_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    
    is_delivered: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
