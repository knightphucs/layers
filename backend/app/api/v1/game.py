"""
LAYERS - Campfire Game Router
=============================================
Truth-or-Dare endpoints. Mounted at /chat/campfires/{room_id}/game/...

  POST  /chat/campfires/{room_id}/game/start
  GET   /chat/campfires/{room_id}/game
  POST  /chat/campfires/{room_id}/game/answer
  POST  /chat/campfires/{room_id}/game/move-to-voting
  POST  /chat/campfires/{room_id}/game/vote
  POST  /chat/campfires/{room_id}/game/reveal
  POST  /chat/campfires/{room_id}/game/next-round
  POST  /chat/campfires/{room_id}/game/end

Each mutating endpoint broadcasts a lightweight WSGameEvent to the room's
WebSocket subscribers so mobile clients can refetch state.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.ws_manager import manager
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.schemas.game import (
    AnswerSubmitRequest,
    VoteCastRequest,
    GameResponse,
    GameRoundResponse,
    WSGameEvent,
)
from app.services.game_service import GameService
from app.services.badge_service import BadgeService
from app.services.xp_service import XPService, XPEventType
from app.services.quest_service import QuestService, QuestTrigger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat (Game)"])


# ============================================================
# Internal helper — broadcast a game event over WS
# ============================================================

async def _broadcast_event(
    room_id: UUID,
    event: str,
    *,
    game_id: UUID,
    actor_user_id: Optional[UUID] = None,
    phase: Optional[str] = None,
    round_id: Optional[UUID] = None,
) -> None:
    """
    Push a tiny envelope to all WS subscribers in the room. Clients are expected
    to GET the full game state on receipt — keeping these messages small avoids
    schema drift between client and server.
    """
    try:
        payload = WSGameEvent(
            event=event,
            game_id=game_id,
            room_id=room_id,
            actor_user_id=actor_user_id,
            phase=phase,
            round_id=round_id,
        ).model_dump(mode="json")
        await manager.broadcast(room_id, payload)
    except Exception as e:  # noqa: BLE001 — broadcast must never fail the write
        logger.warning(f"_broadcast_event {event} failed: {e}")


async def _get_state_or_404(
    db: AsyncSession, room_id: UUID, user_id: UUID
) -> dict:
    state = await GameService.get_full_game_state(db, room_id, user_id)
    if state is None:
        raise HTTPException(404, "No game in this campfire")
    return state


# ============================================================
# GET current game state
# ============================================================

@router.get(
    "/campfires/{room_id}/game",
    response_model=GameResponse,
    summary="Get the current Truth-or-Dare game state (or 404 if none)",
)
async def get_game(
    room_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_state_or_404(db, room_id, current_user.id)


# ============================================================
# START
# ============================================================

@router.post(
    "/campfires/{room_id}/game/start",
    response_model=GameResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a Truth-or-Dare game (creates the first round)",
)
async def start_game(
    room_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    game = await GameService.start_game(db, room_id, current_user.id)
    await _broadcast_event(
        room_id, "started", game_id=game.id,
        actor_user_id=current_user.id, phase="ANSWERING",
        round_id=game.current_round_id,
    )
    return await _get_state_or_404(db, room_id, current_user.id)


# ============================================================
# ANSWER
# ============================================================

@router.post(
    "/campfires/{room_id}/game/answer",
    response_model=GameResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit your answer to the current round",
)
async def submit_answer(
    room_id: UUID,
    data: AnswerSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    answer = await GameService.submit_answer(
        db, room_id, current_user.id, data.content
    )
    state = await _get_state_or_404(db, room_id, current_user.id)
    await _broadcast_event(
        room_id, "answer_submitted",
        game_id=state["id"], actor_user_id=current_user.id,
        round_id=answer.round_id,
    )
    return state


# ============================================================
# MOVE TO VOTING (starter only)
# ============================================================

@router.post(
    "/campfires/{room_id}/game/move-to-voting",
    response_model=GameResponse,
    summary="Close answering, open voting (starter only)",
)
async def move_to_voting(
    room_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rnd = await GameService.move_to_voting(db, room_id, current_user.id)
    state = await _get_state_or_404(db, room_id, current_user.id)
    await _broadcast_event(
        room_id, "phase_changed",
        game_id=state["id"], actor_user_id=current_user.id,
        phase="VOTING", round_id=rnd.id,
    )
    return state


# ============================================================
# VOTE
# ============================================================

@router.post(
    "/campfires/{room_id}/game/vote",
    response_model=GameResponse,
    summary="Cast a vote for an answer (one per round, not your own)",
)
async def cast_vote(
    room_id: UUID,
    data: VoteCastRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    answer = await GameService.cast_vote(
        db, room_id, current_user.id, data.answer_id
    )
    state = await _get_state_or_404(db, room_id, current_user.id)
    await _broadcast_event(
        room_id, "vote_cast",
        game_id=state["id"], actor_user_id=current_user.id,
        round_id=answer.round_id,
    )
    return state


# ============================================================
# REVEAL (starter only)
# ============================================================

@router.post(
    "/campfires/{room_id}/game/reveal",
    response_model=GameResponse,
    summary="Tally votes and reveal the round's winner (starter only)",
)
async def reveal_round(
    room_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rnd = await GameService.reveal_round(db, room_id, current_user.id)
    if rnd.winner_user_id:
        await XPService.award(db, rnd.winner_user_id, XPEventType.CAMPFIRE_GAME_WIN)
        await QuestService.report_progress(db, rnd.winner_user_id, QuestTrigger.GAME_WIN)
        await BadgeService.award_badge(db, rnd.winner_user_id, "campfire_star")
    state = await _get_state_or_404(db, room_id, current_user.id)
    await _broadcast_event(
        room_id, "round_revealed",
        game_id=state["id"], actor_user_id=current_user.id,
        phase="REVEALED", round_id=rnd.id,
    )
    return state


# ============================================================
# NEXT ROUND (starter only)
# ============================================================

@router.post(
    "/campfires/{room_id}/game/next-round",
    response_model=GameResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start the next round with a fresh question (starter only)",
)
async def next_round(
    room_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rnd = await GameService.next_round(db, room_id, current_user.id)
    state = await _get_state_or_404(db, room_id, current_user.id)
    await _broadcast_event(
        room_id, "next_round",
        game_id=state["id"], actor_user_id=current_user.id,
        phase="ANSWERING", round_id=rnd.id,
    )
    return state


# ============================================================
# END (starter only)
# ============================================================

@router.post(
    "/campfires/{room_id}/game/end",
    response_model=GameResponse,
    summary="End the current game (starter only)",
)
async def end_game(
    room_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    game = await GameService.end_game(db, room_id, current_user.id)
    state = await GameService.get_full_game_state(db, room_id, current_user.id)
    if state is None:
        raise HTTPException(404, "Game vanished after end")
    await _broadcast_event(
        room_id, "ended",
        game_id=game.id, actor_user_id=current_user.id,
    )
    return state
