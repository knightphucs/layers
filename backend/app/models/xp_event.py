"""
LAYERS - XP Event Model
======================================
An append-only transaction log of every XP award. Gives us:
- An audit trail ("why is my XP 1,230?")
- Idempotency: a unique idempotency_key prevents double-awarding on retries
- Source for the XP history screen

We store event_type as a plain String (validated by the XPEventType enum in
xp_service.py) rather than a PG enum, to keep migrations simple as the set of
event types grows.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class XPEvent(Base):
    """One XP award (or a recorded duplicate attempt)."""
    __tablename__ = "xp_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # XPEventType value, e.g. "ARTIFACT_CREATE"
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    amount: Mapped[int] = mapped_column(Integer, nullable=False)

    # Optional reference to the entity that caused the award (artifact, reply, ...)
    ref_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Idempotency: e.g. "reply_received:{reply_id}". Unique → safe retries.
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True, unique=True
    )

    # Snapshot before/after for the audit trail
    xp_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    xp_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level_before: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    level_after: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, index=True
    )

    def __repr__(self) -> str:
        return f"<XPEvent {self.event_type} +{self.amount} user={self.user_id}>"
