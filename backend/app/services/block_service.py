"""
LAYERS - Block Service
========================================
User-level blocking. Complements the artifact-level report system (Week 8):
reports protect the COMMUNITY, blocks protect the INDIVIDUAL.

ENFORCEMENT MODEL (beta scope — documented, deliberate):
- is_blocked_between() is checked at ConnectionService.record_interaction —
  the funnel through which ALL social escalation flows (replies → SIGNAL →
  CONNECTED → chat). Cutting it there stops new contact between the pair.
- Existing anonymous geo-artifacts stay visible: they're city content,
  not directed messages. (Same reasoning as soft quarantine > hard ban.)
- Blocked users are never told they're blocked (industry standard —
  telling them invites harassment through other channels).
"""

import logging
import uuid
from typing import List

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_block import UserBlock

logger = logging.getLogger(__name__)


class BlockService:

    # ========================================================
    # BLOCK
    # ========================================================

    @staticmethod
    async def block_user(
        db: AsyncSession,
        blocker_id: uuid.UUID,
        blocked_id: uuid.UUID,
    ) -> dict:
        """Block a user (idempotent). Raises ValueError on bad input."""
        if blocker_id == blocked_id:
            raise ValueError("You can't block yourself.")

        target = await db.get(User, blocked_id)
        if target is None:
            raise ValueError("User not found.")

        existing = await db.execute(
            select(UserBlock).where(
                UserBlock.blocker_id == blocker_id,
                UserBlock.blocked_id == blocked_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return {"blocked": True, "message": "User is already blocked."}

        db.add(UserBlock(blocker_id=blocker_id, blocked_id=blocked_id))
        await db.commit()

        logger.info(f"Block created: {blocker_id} ⛔ {blocked_id}")
        return {"blocked": True, "message": "User blocked. They won't be able to interact with you."}

    # ========================================================
    # UNBLOCK
    # ========================================================

    @staticmethod
    async def unblock_user(
        db: AsyncSession,
        blocker_id: uuid.UUID,
        blocked_id: uuid.UUID,
    ) -> dict:
        """Remove a block (idempotent)."""
        result = await db.execute(
            select(UserBlock).where(
                UserBlock.blocker_id == blocker_id,
                UserBlock.blocked_id == blocked_id,
            )
        )
        block = result.scalar_one_or_none()
        if block is None:
            return {"blocked": False, "message": "User was not blocked."}

        await db.delete(block)
        await db.commit()

        logger.info(f"Block removed: {blocker_id} → {blocked_id}")
        return {"blocked": False, "message": "User unblocked."}

    # ========================================================
    # LIST — for the Privacy & Safety screen
    # ========================================================

    @staticmethod
    async def list_blocks(db: AsyncSession, blocker_id: uuid.UUID) -> List[dict]:
        """All users blocked by `blocker_id`, newest first, with usernames."""
        rows = (
            await db.execute(
                select(UserBlock, User.username, User.avatar_url)
                .join(User, User.id == UserBlock.blocked_id)
                .where(UserBlock.blocker_id == blocker_id)
                .order_by(UserBlock.created_at.desc())
            )
        ).all()

        return [
            {
                "user_id": str(block.blocked_id),
                "username": username,
                "avatar_url": avatar_url,
                "blocked_at": block.created_at,
            }
            for block, username, avatar_url in rows
        ]

    # ========================================================
    # PAIR CHECK — the enforcement primitive
    # ========================================================

    @staticmethod
    async def is_blocked_between(
        db: AsyncSession,
        user_a_id: uuid.UUID,
        user_b_id: uuid.UUID,
    ) -> bool:
        """True if a block exists in EITHER direction between the pair.
        Called from ConnectionService.record_interaction (the social funnel)."""
        result = await db.execute(
            select(UserBlock.id).where(
                or_(
                    and_(
                        UserBlock.blocker_id == user_a_id,
                        UserBlock.blocked_id == user_b_id,
                    ),
                    and_(
                        UserBlock.blocker_id == user_b_id,
                        UserBlock.blocked_id == user_a_id,
                    ),
                )
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None
