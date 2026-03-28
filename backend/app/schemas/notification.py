"""
LAYERS — Notification Schemas
==========================================
Pydantic request/response models for the notification system.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================
# DEVICE TOKEN
# ============================================================

class DeviceTokenCreate(BaseModel):
    """Register a device for push notifications."""
    token: str = Field(..., min_length=10, max_length=500)
    platform: str = Field(..., pattern="^(ios|android|web)$")
    device_name: Optional[str] = Field(None, max_length=100)


class DeviceTokenResponse(BaseModel):
    """Device token registration response."""
    id: str
    token_last4: str  # show last 4 chars for security
    platform: str
    device_name: Optional[str]
    registered_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# NOTIFICATION PREFERENCES
# ============================================================

class NotificationPreferencesUpdate(BaseModel):
    """Update notification preferences."""
    enabled: Optional[bool] = None
    social: Optional[bool] = None
    discovery: Optional[bool] = None
    inbox: Optional[bool] = None
    capsule: Optional[bool] = None
    system: Optional[bool] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = Field(
        None, pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$"
    )
    quiet_hours_end: Optional[str] = Field(
        None, pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$"
    )


class NotificationPreferencesResponse(BaseModel):
    """Full notification preferences."""
    enabled: bool = True
    social: bool = True
    discovery: bool = True
    inbox: bool = True
    capsule: bool = True
    system: bool = True
    quiet_hours_enabled: bool = True
    quiet_hours_start: str = "23:00"
    quiet_hours_end: str = "07:00"

    class Config:
        from_attributes = True


# ============================================================
# NOTIFICATION HISTORY
# ============================================================

class NotificationItem(BaseModel):
    """A single notification record."""
    id: str
    type: str
    category: str
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    is_read: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationHistoryResponse(BaseModel):
    """Paginated notification history."""
    notifications: List[NotificationItem]
    total: int
    unread_count: int


# ============================================================
# SEND NOTIFICATION (Internal — used by services)
# ============================================================

class SendNotificationRequest(BaseModel):
    """Internal request to send a push notification."""
    user_id: str
    type: str
    category: str
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    # Android channel
    channel_id: Optional[str] = None


class MarkReadRequest(BaseModel):
    """Mark notifications as read."""
    notification_ids: List[str] = Field(..., min_length=1, max_length=100)
