"""
LAYERS - Moderation Schemas
"""

from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import UUID


class ModerationLogOut(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    artifact_id: Optional[UUID]
    context: str
    decision: str
    reasons: Dict[str, Any]
    excerpt: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class QueueItemOut(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    content_type: str
    layer: str
    status: str
    report_count: int
    text_preview: Optional[str]
    media_url: Optional[str]
    flag_reasons: Optional[Dict[str, Any]]
    report_reasons: Optional[Dict[str, int]]
    created_at: datetime


class QueueResponse(BaseModel):
    items: List[QueueItemOut]
    total: int
    limit: int
    offset: int
    has_more: bool


class LogsResponse(BaseModel):
    items: List[ModerationLogOut]
