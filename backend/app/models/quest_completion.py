"""
LAYERS - Quest Completion Model
==============================================
Durable record of a completed daily quest. Live progress lives in Redis
(ephemeral, resets at midnight), but completions are persisted here so XP,
streaks, and history survive a Redis restart.

Unique (user_id, quest_id, quest_date) → a quest completes at most once per day.
"""

import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class QuestCompletion(Base):
    __tablename__ = "quest_completions"
    __table_args__ = (
        UniqueConstraint("user_id", "quest_id", "quest_date",
                         name="uq_quest_completion_user_quest_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    quest_id: Mapped[str] = mapped_column(String(50), nullable=False)
    quest_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    xp_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<QuestCompletion {self.quest_id} user={self.user_id} {self.quest_date}>"
