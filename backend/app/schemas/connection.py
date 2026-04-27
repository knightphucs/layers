"""
LAYERS — Connection Schemas
==========================================
Pydantic models for the progressive connection system.

LEVELS:
  Level 0 (Stranger)   — Anonymous, only Slow Mail
  Level 1 (Signal)     — 5+ interactions, see username + avatar
  Level 2 (Connected)  — Both users accepted → realtime chat unlocked
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# ============================================================
# CONNECTION LEVEL
# ============================================================

ConnectionLevel = Literal["STRANGER", "SIGNAL", "CONNECTED"]


# ============================================================
# RESPONSES
# ============================================================

class OtherUserMini(BaseModel):
    """Minimal other-user info for connection lists."""
    id: str
    username: Optional[str] = None  # Hidden at Level 0
    avatar_url: Optional[str] = None
    level: Optional[int] = None  # Their XP level

    class Config:
        from_attributes = True


class ConnectionResponse(BaseModel):
    id: str
    other_user: OtherUserMini
    interaction_count: int
    level: ConnectionLevel
    status: str  # PENDING or CONNECTED
    can_upgrade: bool  # True if 5+ interactions and still PENDING
    upgrade_requested_by_me: bool
    upgrade_requested_by_them: bool
    created_at: datetime
    connected_at: Optional[datetime] = None
    last_interaction_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConnectionListResponse(BaseModel):
    """Paginated connections list."""
    connections: List[ConnectionResponse]
    total: int
    strangers_count: int  # Level 0
    signals_count: int  # Level 1
    connected_count: int  # Level 2


class ConnectionStatsResponse(BaseModel):
    total_connections: int
    strangers: int
    signals: int
    connected: int
    pending_requests_received: int
    pending_requests_sent: int


# ============================================================
# REQUESTS
# ============================================================

class RequestConnectionUpgrade(BaseModel):
    connection_id: str = Field(..., min_length=1)


class AcceptConnectionUpgrade(BaseModel):
    connection_id: str = Field(..., min_length=1)


class RejectConnectionUpgrade(BaseModel):
    connection_id: str = Field(..., min_length=1)
    reason: Optional[str] = Field(None, max_length=200)
