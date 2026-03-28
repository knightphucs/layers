"""
LAYERS — Notification Models
==========================================
SQLAlchemy models for push notification system.

Tables:
  device_tokens            — Expo push tokens per user+device
  notification_preferences — Per-user category toggles + quiet hours
  notification_history     — Sent notification log (for in-app list)
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text, ForeignKey,
    UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


# ============================================================
# DEVICE TOKENS
# ============================================================

class DeviceToken(Base):
    """
    Stores Expo push tokens for each user's device.
    A user may have multiple devices (phone + tablet).
    """
    __tablename__ = "device_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Expo push token (ExponentPushToken[...])",
    )
    platform: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="ios, android, or web",
    )
    device_name: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        comment="e.g. iPhone 15, Pixel 8",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="False if token is expired/invalid",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "token", name="uq_user_device_token"),
    )

    def __repr__(self) -> str:
        return f"<DeviceToken {self.platform} ...{self.token[-8:]}>"


# ============================================================
# NOTIFICATION PREFERENCES
# ============================================================

class NotificationPreference(Base):
    """
    Per-user notification preferences.
    One row per user (created on first preference update).
    """
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Master toggle
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Category toggles
    social: Mapped[bool] = mapped_column(Boolean, default=True)
    discovery: Mapped[bool] = mapped_column(Boolean, default=True)
    inbox: Mapped[bool] = mapped_column(Boolean, default=True)
    capsule: Mapped[bool] = mapped_column(Boolean, default=True)
    system: Mapped[bool] = mapped_column(Boolean, default=True)

    # Quiet hours
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    quiet_hours_start: Mapped[str] = mapped_column(
        String(5), default="23:00"
    )
    quiet_hours_end: Mapped[str] = mapped_column(
        String(5), default="07:00"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<NotificationPreference user={self.user_id} enabled={self.enabled}>"


# ============================================================
# NOTIFICATION HISTORY
# ============================================================

class NotificationHistory(Base):
    """
    Log of sent notifications (for in-app notification center).
    Kept for 30 days, then cleaned up by periodic task.
    """
    __tablename__ = "notification_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="e.g. new_reply, slow_mail_delivered",
    )
    category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="social, discovery, inbox, capsule, system",
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="Deep link data: screen, params, artifact_id, etc.",
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_notification_history_user_unread",
            "user_id",
            "is_read",
            postgresql_where=(~Column("is_read",)),
        ),
    )

    def __repr__(self) -> str:
        return f"<NotificationHistory {self.type} → user={self.user_id}>"
