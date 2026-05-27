"""
LAYERS - Campfire Game Models
=============================================
The Truth-or-Dare game lives inside a campfire room. Each campfire can have
AT MOST one non-completed game at a time, enforced by a partial unique index.

State machine:
    GAME:    WAITING (rounds may be created) → COMPLETED
    ROUND:   ANSWERING → VOTING → REVEALED

The state on the parent Game is the *current round's* phase, surfaced for
quick reads. The Round itself owns its own state independently so that
"end the game" closes the Game while leaving the Round REVEALED.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Text,
    Enum as SQLEnum,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# ============================================================
# ENUMS
# ============================================================

class GameState(str, Enum):
    """Top-level state for a Campfire game session."""
    WAITING = "WAITING"      # active round in ANSWERING or VOTING or REVEALED
    COMPLETED = "COMPLETED"  # game ended (winner declared or starter ended it)


class RoundState(str, Enum):
    """State of an individual question round."""
    ANSWERING = "ANSWERING"
    VOTING = "VOTING"
    REVEALED = "REVEALED"


# ============================================================
# CAMPFIRE GAME  🔥
# ============================================================

class CampfireGame(Base):
    """One game session inside a campfire room.

    Constraint (enforced by partial unique index in the migration):
      at most one row per room_id where state != COMPLETED.
    """
    __tablename__ = "campfire_games"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    starter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    state: Mapped[GameState] = mapped_column(
        SQLEnum(GameState, name="campfiregamestate"),
        default=GameState.WAITING,
        nullable=False,
        index=True,
    )
    current_round_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    round_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<CampfireGame {self.id} room={self.room_id} state={self.state.value}>"


# ============================================================
# GAME ROUND
# ============================================================

class CampfireGameRound(Base):
    """A single question round within a CampfireGame."""
    __tablename__ = "campfire_game_rounds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campfire_games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[RoundState] = mapped_column(
        SQLEnum(RoundState, name="campfireroundstate"),
        default=RoundState.ANSWERING,
        nullable=False,
        index=True,
    )
    winner_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    winning_answer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    revealed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<CampfireGameRound {self.id} game={self.game_id} "
            f"#{self.round_number} state={self.state.value}>"
        )


# ============================================================
# GAME ANSWER
# ============================================================

class CampfireGameAnswer(Base):
    """A user's answer to a round's question, with embedded vote tracking.

    Votes are stored as:
      - vote_count: int  (denormalized for fast sort)
      - voter_ids:  JSONB list[str(uuid)]  (enforces 1 vote/user/round in service)

    The partial unique index `uq_campfire_game_answer_user` (in migration)
    ensures one answer per user per round.
    """
    __tablename__ = "campfire_game_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campfire_game_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    vote_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    voter_ids: Mapped[list] = mapped_column(
        JSONB, default=list, nullable=False,
        comment="JSON array of voter UUIDs (as strings)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        preview = self.content[:30] + "…" if len(self.content) > 30 else self.content
        return f"<CampfireGameAnswer user={self.user_id} votes={self.vote_count}: {preview!r}>"
