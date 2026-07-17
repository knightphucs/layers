"""
LAYERS - Users API
  GET    /api/v1/users/me/blocks        — my block list
  POST   /api/v1/users/{user_id}/block  — block a user
  DELETE /api/v1/users/{user_id}/block  — unblock a user

NOTE: /me/blocks is declared BEFORE /{user_id}/block so the literal
path wins over the path parameter (FastAPI matches in declaration order).
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.services.block_service import BlockService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me/blocks", summary="List users I've blocked")
async def my_blocks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    blocks = await BlockService.list_blocks(db, current_user.id)
    return {"items": blocks, "total": len(blocks)}


@router.post(
    "/{user_id}/block",
    status_code=status.HTTP_201_CREATED,
    summary="Block a user",
    description="Stops all new interactions between you and this user "
    "(replies won't create connections, no upgrades, no chat). "
    "They are not notified.",
)
async def block_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await BlockService.block_user(db, current_user.id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{user_id}/block", summary="Unblock a user")
async def unblock_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BlockService.unblock_user(db, current_user.id, user_id)
