"""
LAYERS - Campfire Game Service
==============================================
Truth-or-Dare lifecycle inside a campfire.

STATE MACHINE:
    [start] → Round(ANSWERING)
       └─ submit answers (one per member, max 280 chars)
       └─ [move-to-voting] → Round(VOTING)        (starter only)
          └─ cast votes (one per member, not on own answer)
          └─ [reveal] → Round(REVEALED)           (starter only)
             └─ winner = answer with most votes (ties → earliest submitted)
             └─ [next-round] → new Round(ANSWERING) (starter only)
             └─ [end] → Game(COMPLETED)             (starter only)

CONSTRAINTS:
  • AT MOST one non-COMPLETED game per room (partial unique index in migration)
  • Caller must be an active campfire member to do anything
  • Starter is the only one who can advance state
  • answers/votes uniqueness enforced at DB + service layer
"""

import logging
import random
import uuid
from datetime import datetime
from typing import Optional, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatRoom, ChatRoomType, ChatRoomStatus
from app.models.game import (
    CampfireGame,
    CampfireGameRound,
    CampfireGameAnswer,
    GameState,
    RoundState,
)
from app.models.user import User
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)


# ============================================================
# QUESTION POOL
# ============================================================
# Curated for HCMC Gen Z — warm, mostly Truth-style with a few light Dares.
# Keep family-friendly by default. A spicier pack can be added in Week 7+.
#
# Editing tips: short, vivid, answerable in ≤280 chars, leaves space for honesty
# without forcing it. Avoid anything sexual, political, religious, or that
# requires real-world action that's awkward in public.

QUESTION_POOL = [
    # Memory / place
    "What's the most beautiful place you've discovered in this city?",
    "Tell us about a stranger who quietly changed your day.",
    "What's a part of the city that feels like 'yours'?",
    "Describe a moment this year that felt like time stopped.",
    "What's a place you keep meaning to visit but never do?",

    # Self
    "What's something you're proud of that no one knows about?",
    "If you had to live in another city tomorrow, which would it be — and why?",
    "What's a song that always makes you feel less alone?",
    "What's a small habit that actually makes your life better?",
    "Describe your perfect Sunday morning in 3 sentences.",
    "What's the best meal you've had in the past month?",
    "What's a compliment you struggle to accept?",

    # Lightly daring (still safe)
    "Open your camera roll — describe the last photo without showing it.",
    "Say something kind about the person sitting nearest to you right now.",
    "Show us one thing in your pocket or bag and tell us its story.",

    # Hypotheticals
    "If you could leave one note for tomorrow's stranger here, what would it say?",
    "What would your 14-year-old self think of you right now?",
    "If this city could whisper one thing to you, what would you want to hear?",
    "What's a question you wish more people asked you?",
    "What's the most LAYERS thing about your life right now?",
]

MAX_ROUNDS_PER_GAME = 10
ANSWER_MAX_LENGTH = 280


# ============================================================
# HELPERS
# ============================================================

def _pick_random_question(seen: set) -> str:
    """Pick a question we haven't used yet in this game. Reset pool if exhausted."""
    available = [q for q in QUESTION_POOL if q not in seen]
    if not available:
        available = QUESTION_POOL
    return random.choice(available)


def _round_to_response_dict(
    round_obj: CampfireGameRound,
    answers: List[CampfireGameAnswer],
    current_user_id: uuid.UUID,
    user_map: dict,
) -> dict:
    """Build the GameRoundResponse dict, hiding author identity in non-REVEALED phases."""
    is_revealed = round_obj.state == RoundState.REVEALED
    answer_dicts = []
    for a in answers:
        user_id_field = a.user_id if is_revealed else None
        user = user_map.get(a.user_id) if is_revealed else None
        answer_dicts.append({
            "id": a.id,
            "round_id": a.round_id,
            "user_id": user_id_field,
            "content": a.content,
            "vote_count": a.vote_count if is_revealed else 0,  # hide tally pre-reveal
            "is_mine": a.user_id == current_user_id,
            "username": user.username if user else None,
            "avatar_url": user.avatar_url if user else None,
        })

    winner_user = user_map.get(round_obj.winner_user_id) if round_obj.winner_user_id else None
    return {
        "id": round_obj.id,
        "round_number": round_obj.round_number,
        "question_text": round_obj.question_text,
        "state": round_obj.state,
        "answers": answer_dicts,
        "winner_user_id": round_obj.winner_user_id,
        "winning_answer_id": round_obj.winning_answer_id,
        "winner_username": winner_user.username if winner_user else None,
        "winner_avatar_url": winner_user.avatar_url if winner_user else None,
        "created_at": round_obj.created_at,
        "revealed_at": round_obj.revealed_at,
    }


async def _load_user_map(
    db: AsyncSession, user_ids: List[uuid.UUID]
) -> dict:
    """Bulk-load users for response hydration."""
    if not user_ids:
        return {}
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    return {u.id: u for u in result.scalars().all()}


# ============================================================
# GAME SERVICE
# ============================================================

class GameService:

    # ========================================================
    # MEMBERSHIP / GAME LOOKUP
    # ========================================================

    @staticmethod
    async def _require_campfire_membership(
        db: AsyncSession,
        room_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ChatRoom:
        """Make sure the user is in this campfire (and it's active)."""
        room = await ChatService._fetch_and_auto_close_if_expired(db, room_id)
        if not room:
            raise HTTPException(404, "Campfire not found")
        if room.room_type != ChatRoomType.CAMPFIRE:
            raise HTTPException(400, "Games only run inside campfires")
        if room.status != ChatRoomStatus.ACTIVE:
            raise HTTPException(400, "This campfire is closed")
        is_member = await ChatService.is_campfire_member(db, room_id, user_id)
        if not is_member:
            raise HTTPException(403, "Join the campfire to play")
        return room

    @staticmethod
    async def get_active_game(
        db: AsyncSession,
        room_id: uuid.UUID,
    ) -> Optional[CampfireGame]:
        """The single non-completed game for this room, if any."""
        result = await db.execute(
            select(CampfireGame).where(
                and_(
                    CampfireGame.room_id == room_id,
                    CampfireGame.state != GameState.COMPLETED,
                )
            )
        )
        return result.scalar_one_or_none()

    # ========================================================
    # LIFECYCLE — START
    # ========================================================

    @staticmethod
    async def start_game(
        db: AsyncSession,
        room_id: uuid.UUID,
        starter_id: uuid.UUID,
    ) -> CampfireGame:
        """Start a new game. Errors if one is already active."""
        await GameService._require_campfire_membership(db, room_id, starter_id)

        existing = await GameService.get_active_game(db, room_id)
        if existing is not None:
            raise HTTPException(
                409, "A game is already running in this campfire"
            )

        now = datetime.utcnow()
        game = CampfireGame(
            room_id=room_id,
            starter_id=starter_id,
            state=GameState.WAITING,
            round_count=0,
            created_at=now,
        )
        db.add(game)
        await db.flush()  # need game.id for the first round

        # First round
        first_round = CampfireGameRound(
            game_id=game.id,
            round_number=1,
            question_text=_pick_random_question(set()),
            state=RoundState.ANSWERING,
            created_at=now,
        )
        db.add(first_round)
        await db.flush()

        game.current_round_id = first_round.id
        game.round_count = 1
        await db.commit()
        await db.refresh(game)

        logger.info(f"🔥 Truth-or-Dare started in {room_id} by {starter_id}")
        return game

    # ========================================================
    # ANSWER PHASE
    # ========================================================

    @staticmethod
    async def submit_answer(
        db: AsyncSession,
        room_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
    ) -> CampfireGameAnswer:
        await GameService._require_campfire_membership(db, room_id, user_id)

        game = await GameService.get_active_game(db, room_id)
        if not game or game.current_round_id is None:
            raise HTTPException(404, "No active round to answer")

        round_q = await db.execute(
            select(CampfireGameRound).where(CampfireGameRound.id == game.current_round_id)
        )
        current_round = round_q.scalar_one_or_none()
        if not current_round or current_round.state != RoundState.ANSWERING:
            raise HTTPException(400, "Answering phase is closed for this round")

        # Already answered?
        dup = await db.execute(
            select(CampfireGameAnswer).where(
                and_(
                    CampfireGameAnswer.round_id == current_round.id,
                    CampfireGameAnswer.user_id == user_id,
                )
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(409, "You already answered this round")

        content = (content or "").strip()
        if not content:
            raise HTTPException(400, "Answer cannot be empty")
        if len(content) > ANSWER_MAX_LENGTH:
            raise HTTPException(400, f"Answer exceeds {ANSWER_MAX_LENGTH} chars")

        answer = CampfireGameAnswer(
            round_id=current_round.id,
            user_id=user_id,
            content=content,
            vote_count=0,
            voter_ids=[],
        )
        db.add(answer)
        await db.commit()
        await db.refresh(answer)
        return answer

    # ========================================================
    # PHASE TRANSITION — ANSWERING → VOTING
    # ========================================================

    @staticmethod
    async def move_to_voting(
        db: AsyncSession,
        room_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> CampfireGameRound:
        await GameService._require_campfire_membership(db, room_id, actor_id)

        game = await GameService.get_active_game(db, room_id)
        if not game:
            raise HTTPException(404, "No active game")
        if game.starter_id != actor_id:
            raise HTTPException(403, "Only the starter can advance phases")

        round_q = await db.execute(
            select(CampfireGameRound).where(CampfireGameRound.id == game.current_round_id)
        )
        rnd = round_q.scalar_one_or_none()
        if not rnd:
            raise HTTPException(404, "Round not found")
        if rnd.state != RoundState.ANSWERING:
            raise HTTPException(400, "Round is not in ANSWERING phase")

        # Need at least 2 answers to make voting meaningful
        ans_count = (await db.execute(
            select(func.count(CampfireGameAnswer.id))
            .where(CampfireGameAnswer.round_id == rnd.id)
        )).scalar() or 0
        if ans_count < 2:
            raise HTTPException(400, "Need at least 2 answers before voting")

        rnd.state = RoundState.VOTING
        await db.commit()
        await db.refresh(rnd)
        return rnd

    # ========================================================
    # VOTING
    # ========================================================

    @staticmethod
    async def cast_vote(
        db: AsyncSession,
        room_id: uuid.UUID,
        voter_id: uuid.UUID,
        answer_id: uuid.UUID,
    ) -> CampfireGameAnswer:
        await GameService._require_campfire_membership(db, room_id, voter_id)

        game = await GameService.get_active_game(db, room_id)
        if not game:
            raise HTTPException(404, "No active game")

        round_q = await db.execute(
            select(CampfireGameRound).where(CampfireGameRound.id == game.current_round_id)
        )
        rnd = round_q.scalar_one_or_none()
        if not rnd or rnd.state != RoundState.VOTING:
            raise HTTPException(400, "Not in VOTING phase")

        ans_q = await db.execute(
            select(CampfireGameAnswer).where(CampfireGameAnswer.id == answer_id)
        )
        answer = ans_q.scalar_one_or_none()
        if not answer or answer.round_id != rnd.id:
            raise HTTPException(404, "Answer not found in this round")
        if answer.user_id == voter_id:
            raise HTTPException(400, "You can't vote for your own answer")

        # One vote per user per round (across ALL answers in the round).
        # Cross-answer check: load all answers and inspect voter_ids.
        all_ans = (await db.execute(
            select(CampfireGameAnswer).where(CampfireGameAnswer.round_id == rnd.id)
        )).scalars().all()
        voter_str = str(voter_id)
        for a in all_ans:
            if voter_str in (a.voter_ids or []):
                raise HTTPException(409, "You already voted this round")

        # Record vote — append voter_id to JSONB list + bump count
        voters = list(answer.voter_ids or [])
        voters.append(voter_str)
        answer.voter_ids = voters
        answer.vote_count = len(voters)
        await db.commit()
        await db.refresh(answer)
        return answer

    # ========================================================
    # REVEAL
    # ========================================================

    @staticmethod
    async def reveal_round(
        db: AsyncSession,
        room_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> CampfireGameRound:
        await GameService._require_campfire_membership(db, room_id, actor_id)

        game = await GameService.get_active_game(db, room_id)
        if not game:
            raise HTTPException(404, "No active game")
        if game.starter_id != actor_id:
            raise HTTPException(403, "Only the starter can reveal")

        round_q = await db.execute(
            select(CampfireGameRound).where(CampfireGameRound.id == game.current_round_id)
        )
        rnd = round_q.scalar_one_or_none()
        if not rnd or rnd.state != RoundState.VOTING:
            raise HTTPException(400, "Not in VOTING phase")

        # Tally — highest vote_count wins; ties broken by earliest created_at
        answers = (await db.execute(
            select(CampfireGameAnswer)
            .where(CampfireGameAnswer.round_id == rnd.id)
            .order_by(
                CampfireGameAnswer.vote_count.desc(),
                CampfireGameAnswer.created_at.asc(),
            )
        )).scalars().all()

        winner_ans = answers[0] if answers and answers[0].vote_count > 0 else None
        rnd.state = RoundState.REVEALED
        rnd.revealed_at = datetime.utcnow()
        if winner_ans:
            rnd.winner_user_id = winner_ans.user_id
            rnd.winning_answer_id = winner_ans.id

        await db.commit()
        await db.refresh(rnd)
        return rnd

    # ========================================================
    # NEXT ROUND
    # ========================================================

    @staticmethod
    async def next_round(
        db: AsyncSession,
        room_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> CampfireGameRound:
        await GameService._require_campfire_membership(db, room_id, actor_id)

        game = await GameService.get_active_game(db, room_id)
        if not game:
            raise HTTPException(404, "No active game")
        if game.starter_id != actor_id:
            raise HTTPException(403, "Only the starter can start the next round")
        if game.round_count >= MAX_ROUNDS_PER_GAME:
            raise HTTPException(400, f"Max {MAX_ROUNDS_PER_GAME} rounds reached")

        # Must come after a REVEALED round
        prev_q = await db.execute(
            select(CampfireGameRound).where(CampfireGameRound.id == game.current_round_id)
        )
        prev = prev_q.scalar_one_or_none()
        if not prev or prev.state != RoundState.REVEALED:
            raise HTTPException(400, "Reveal the current round before advancing")

        # Pick a question that hasn't been used yet in this game
        seen_q = await db.execute(
            select(CampfireGameRound.question_text)
            .where(CampfireGameRound.game_id == game.id)
        )
        seen = {row[0] for row in seen_q.all()}

        new_round = CampfireGameRound(
            game_id=game.id,
            round_number=game.round_count + 1,
            question_text=_pick_random_question(seen),
            state=RoundState.ANSWERING,
        )
        db.add(new_round)
        await db.flush()

        game.current_round_id = new_round.id
        game.round_count += 1
        await db.commit()
        await db.refresh(new_round)
        return new_round

    # ========================================================
    # END GAME
    # ========================================================

    @staticmethod
    async def end_game(
        db: AsyncSession,
        room_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> CampfireGame:
        await GameService._require_campfire_membership(db, room_id, actor_id)

        game = await GameService.get_active_game(db, room_id)
        if not game:
            raise HTTPException(404, "No active game")
        if game.starter_id != actor_id:
            raise HTTPException(403, "Only the starter can end the game")

        game.state = GameState.COMPLETED
        game.ended_at = datetime.utcnow()
        await db.commit()
        await db.refresh(game)

        logger.info(f"🏁 Game {game.id} ended in room {room_id}")
        return game

    # ========================================================
    # FULL STATE BUILDER (used by every endpoint return)
    # ========================================================

    @staticmethod
    async def get_full_game_state(
        db: AsyncSession,
        room_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> Optional[dict]:
        """
        Return the full GameResponse dict (or None if no active game).
        Includes the current round + all answers + my-answer/vote flags.
        Authors of answers are hidden until the round is REVEALED.
        """
        game = await GameService.get_active_game(db, room_id)
        if game is None:
            # Also check for the most-recent COMPLETED game so the UI can flash results
            done_q = await db.execute(
                select(CampfireGame)
                .where(
                    and_(
                        CampfireGame.room_id == room_id,
                        CampfireGame.state == GameState.COMPLETED,
                    )
                )
                .order_by(CampfireGame.created_at.desc())
                .limit(1)
            )
            game = done_q.scalar_one_or_none()
            if game is None:
                return None

        round_data = None
        my_answer_submitted = False
        my_vote_cast = False

        if game.current_round_id is not None:
            rnd_q = await db.execute(
                select(CampfireGameRound).where(CampfireGameRound.id == game.current_round_id)
            )
            rnd = rnd_q.scalar_one_or_none()
            if rnd:
                ans_q = await db.execute(
                    select(CampfireGameAnswer)
                    .where(CampfireGameAnswer.round_id == rnd.id)
                    .order_by(CampfireGameAnswer.created_at.asc())
                )
                answers = list(ans_q.scalars().all())

                # User map: only need for REVEALED phase
                user_ids = []
                if rnd.state == RoundState.REVEALED:
                    user_ids = [a.user_id for a in answers]
                if rnd.winner_user_id and rnd.winner_user_id not in user_ids:
                    user_ids.append(rnd.winner_user_id)
                user_map = await _load_user_map(db, user_ids)

                round_data = _round_to_response_dict(
                    rnd, answers, current_user_id, user_map
                )

                cur_str = str(current_user_id)
                my_answer_submitted = any(a.user_id == current_user_id for a in answers)
                my_vote_cast = any(
                    cur_str in (a.voter_ids or []) for a in answers
                )

        return {
            "id": game.id,
            "room_id": game.room_id,
            "starter_id": game.starter_id,
            "state": game.state,
            "round_count": game.round_count,
            "current_round": round_data,
            "created_at": game.created_at,
            "ended_at": game.ended_at,
            "my_answer_submitted": my_answer_submitted,
            "my_vote_cast": my_vote_cast,
        }
