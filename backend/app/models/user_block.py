"""
LAYERS - UserBlock Model
========================================
A directional block: blocker_id blocks blocked_id.

DESIGN NOTES:
- DIRECTIONAL (unlike Connection's canonical pair ordering) — "A blocked B"
  and "B blocked A" are different facts, and unblocking one side must not
  silently unblock the other.
- Enforcement is symmetric though: if EITHER direction exists, interactions
  between the pair are suppressed (see BlockService.is_blocked_between).
- Soft philosophy (same as moderation): blocking stops NEW interactions
  (replies→connections, upgrades, chat). Existing public geo-artifacts stay
  on the map — they're anonymous city content, not a DM channel.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserBlock(Base):
    __tablename__ = "user_blocks"
    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_user_blocks_pair"),
        Index("ix_user_blocks_blocker", "blocker_id"),
        Index("ix_user_blocks_blocked", "blocked_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    blocker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    blocked_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<UserBlock {self.blocker_id} ⛔ {self.blocked_id}>"
