"""
LAYERS - Campfire Game Schemas
==============================================
Pydantic models for the Truth-or-Dare endpoints + WS payloads.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# ENUMS
# ============================================================

class GameState(str, Enum):
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"


class RoundState(str, Enum):
    ANSWERING = "ANSWERING"
    VOTING = "VOTING"
    REVEALED = "REVEALED"


# ============================================================
# REQUESTS
# ============================================================

class AnswerSubmitRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=280)


class VoteCastRequest(BaseModel):
    answer_id: UUID


# ============================================================
# RESPONSES — building blocks
# ============================================================

class GameAnswerResponse(BaseModel):
    """A single answer. Author/content hidden until REVEALED phase."""
    id: UUID
    round_id: UUID
    # During ANSWERING/VOTING the API returns user_id=None to keep voting blind.
    # Once REVEALED, user_id is filled in.
    user_id: Optional[UUID] = None
    content: str
    vote_count: int
    is_mine: bool = False  # so the UI can stop the user voting their own
    username: Optional[str] = None  # filled in REVEALED phase
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}


class GameRoundResponse(BaseModel):
    id: UUID
    round_number: int
    question_text: str
    state: RoundState
    answers: List[GameAnswerResponse] = Field(default_factory=list)
    winner_user_id: Optional[UUID] = None
    winning_answer_id: Optional[UUID] = None
    winner_username: Optional[str] = None
    winner_avatar_url: Optional[str] = None
    created_at: datetime
    revealed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class GameResponse(BaseModel):
    """Full game state for the client."""
    id: UUID
    room_id: UUID
    starter_id: UUID
    state: GameState
    round_count: int
    current_round: Optional[GameRoundResponse] = None
    created_at: datetime
    ended_at: Optional[datetime] = None

    # Convenience: did I submit/vote already this round?
    my_answer_submitted: bool = False
    my_vote_cast: bool = False

    model_config = {"from_attributes": True}


# ============================================================
# WEBSOCKET PAYLOADS (server → client)
# ============================================================

class WSGameEvent(BaseModel):
    """Generic envelope for game events. The 'event' discriminator carries
    the payload shape; clients re-fetch the full game state on receipt."""
    type: Literal["game_event"] = "game_event"
    event: Literal[
        "started",
        "answer_submitted",
        "phase_changed",
        "vote_cast",
        "round_revealed",
        "next_round",
        "ended",
    ]
    game_id: UUID
    room_id: UUID
    # Optional extras (lightweight — clients refetch for source of truth)
    actor_user_id: Optional[UUID] = None
    phase: Optional[str] = None
    round_id: Optional[UUID] = None


# ============================================================
# TYPING INDICATORS (Day 5 chat polish)
# ============================================================

class WSClientTyping(BaseModel):
    """Client → server typing event. Both start and stop use the same shape."""
    type: Literal["typing_start", "typing_stop"]


class WSServerTyping(BaseModel):
    """Server → client typing broadcast."""
    type: Literal["typing"] = "typing"
    event: Literal["start", "stop"]
    user_id: UUID
