"""
LAYERS — Connection Endpoints
==========================================
Progressive Connection System API.

Endpoints:
  GET  /connections              — List all connections (with level filter)
  GET  /connections/stats        — Connection counts per level
  POST /connections/{id}/request — Request upgrade Level 1 → Level 2
  POST /connections/{id}/accept  — Accept upgrade request
  POST /connections/{id}/reject  — Reject upgrade request

Note: There is NO "create connection" endpoint.
Connections are created automatically by ArtifactService.reply_to_artifact()
when two users exchange their first interaction.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.connection import Connection
from app.services.connection_service import ConnectionService
from app.services.xp_service import XPService, XPEventType
from app.services.quest_service import QuestService, QuestTrigger
from app.schemas.connection import (
    ConnectionListResponse,
    ConnectionStatsResponse,
)

router = APIRouter(prefix="/connections", tags=["Connections"])


# ============================================================
# GET /connections — List connections
# ============================================================

@router.get(
    "",
    summary="List your connections",
    description="""
    Returns all connections with progressive level info.

    Levels:
    - **STRANGER** (Level 0): Anonymous, <5 interactions
    - **SIGNAL** (Level 1): 5+ interactions, username revealed
    - **CONNECTED** (Level 2): Both accepted upgrade, realtime chat unlocked

    Use `level` query param to filter.
    """,
)
async def list_connections(
    level: Optional[str] = Query(
        None, description="Filter: STRANGER, SIGNAL, or CONNECTED"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ConnectionService.list_connections(
        db=db,
        user_id=current_user.id,
        level_filter=level,
        limit=limit,
        offset=offset,
    )


# ============================================================
# GET /connections/stats — Stats for profile
# ============================================================

@router.get(
    "/stats",
    summary="Get connection statistics",
    description="Returns counts per level and pending upgrade requests.",
)
async def get_connection_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ConnectionService.get_stats(
        db=db, user_id=current_user.id,
    )


# ============================================================
# POST /connections/{id}/request — Request upgrade
# ============================================================

@router.post(
    "/{connection_id}/request",
    summary="Request to upgrade connection to Level 2",
    description="""
    Request to move from SIGNAL (Level 1) to CONNECTED (Level 2).
    Requires 5+ interactions.

    If the other user has also requested → auto-upgrades to CONNECTED.
    Otherwise, waits for their acceptance.
    """,
)
async def request_upgrade(
    connection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await ConnectionService.request_upgrade(
            db=db,
            user_id=current_user.id,
            connection_id=connection_id,
        )
        if result.get("upgraded"):
            conn = await db.get(Connection, connection_id)
            for uid in (conn.user_a_id, conn.user_b_id):
                await XPService.award(db, uid, XPEventType.CONNECTION_UPGRADE)
                await QuestService.report_progress(db, uid, QuestTrigger.CONNECTION_UPGRADE)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


# ============================================================
# POST /connections/{id}/accept — Accept upgrade
# ============================================================

@router.post(
    "/{connection_id}/accept",
    summary="Accept an incoming upgrade request",
    description="Equivalent to /request — if other party already requested, upgrades.",
)
async def accept_upgrade(
    connection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await ConnectionService.request_upgrade(
            db=db,
            user_id=current_user.id,
            connection_id=connection_id,
        )
        if result.get("upgraded"):
            conn = await db.get(Connection, connection_id)
            for uid in (conn.user_a_id, conn.user_b_id):
                await XPService.award(db, uid, XPEventType.CONNECTION_UPGRADE)
                await QuestService.report_progress(db, uid, QuestTrigger.CONNECTION_UPGRADE)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


# ============================================================
# POST /connections/{id}/reject — Reject upgrade
# ============================================================

@router.post(
    "/{connection_id}/reject",
    summary="Reject a connection upgrade request",
    description="Resets both upgrade flags. Connection stays at SIGNAL level.",
)
async def reject_upgrade(
    connection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await ConnectionService.reject_upgrade(
            db=db,
            user_id=current_user.id,
            connection_id=connection_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
