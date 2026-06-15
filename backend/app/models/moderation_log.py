"""
LAYERS - Moderation Log Model
============================================
Append-only audit trail of every moderation decision (auto or admin).

Why a log table?
- "Why was my letter rejected?" → support can answer with evidence
- Admin panel (Day 3) shows recent decisions
- Repeat offenders are detectable: count REJECT logs per user
- Same philosophy as xp_events: durable, append-only, never updated

decision / context are plain Strings (validated by enums in
moderation_service.py) rather than PG enums — same convention as
xp_event.event_type, so adding new values never needs a migration.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class ModerationLog(Base):
    __tablename__ = "moderation_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Who authored the content being moderated (SET NULL if user deleted)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # The artifact involved, if it exists. NULL for content rejected
    # BEFORE creation (the artifact was never persisted) and for replies.
    artifact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Where the decision happened:
    #   "artifact_create" | "reply" | "notebook_page" | "admin_review"
    context: Mapped[str] = mapped_column(String(30), nullable=False)

    # "ALLOW" | "FLAG" | "REJECT" | "ADMIN_APPROVE" | "ADMIN_REMOVE"
    decision: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Machine-readable reasons, e.g. ["profanity", "contact_info"]
    reasons: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # First 200 chars of the offending text (enough for review,
    # small enough to not duplicate whole payloads)
    excerpt: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        # Admin panel query: "recent decisions, newest first"
        Index("ix_moderation_logs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ModerationLog {self.decision} ctx={self.context} user={self.user_id}>"
