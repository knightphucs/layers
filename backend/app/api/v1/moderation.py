"""
LAYERS - Moderation API
  GET  /api/v1/moderation/queue            — [ADMIN] PENDING/HIDDEN artifacts to review
  POST /api/v1/moderation/{id}/approve     — [ADMIN] publish (PENDING/HIDDEN → ACTIVE)
  POST /api/v1/moderation/{id}/remove      — [ADMIN] confirm bad (→ DELETED, author -30 rep)
  GET  /api/v1/moderation/logs             — [ADMIN] recent moderation decisions
  GET  /api/v1/moderation/stats            — [ADMIN] queue sizes at a glance

Day 3 (SQLAdmin panel) will sit on top of these same primitives.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.anti_cheat import require_admin
from app.models.user import User
from app.models.artifact import Artifact, ArtifactStatus
from app.models.moderation_log import ModerationLog
from app.services.moderation_service import ModerationService, PENALTY_ADMIN_REMOVE
from app.schemas.moderation import ModerationLogOut, QueueItemOut, QueueResponse, LogsResponse

router = APIRouter(prefix="/moderation", tags=["Moderation"])


# ============================================================
# REVIEW QUEUE
# ============================================================

@router.get("/queue", response_model=QueueResponse, summary="[ADMIN] Content review queue")
async def review_queue(
    queue_status: str = Query("PENDING", pattern="^(PENDING|HIDDEN)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """PENDING = held by the auto-filter. HIDDEN = auto-hidden by 5 reports."""
    st = ArtifactStatus(queue_status)

    total = (await db.execute(
        select(func.count(Artifact.id)).where(Artifact.status == st)
    )).scalar() or 0

    result = await db.execute(
        select(Artifact)
        .where(Artifact.status == st)
        .order_by(Artifact.created_at.asc())  # oldest first — FIFO review
        .limit(limit).offset(offset)
    )
    artifacts = result.scalars().all()

    # Pull the FLAG log for each artifact so the admin sees WHY it was held
    reasons_by_artifact = {}
    if artifacts:
        logs = (await db.execute(
            select(ModerationLog)
            .where(ModerationLog.artifact_id.in_([a.id for a in artifacts]))
            .order_by(ModerationLog.created_at.desc())
        )).scalars().all()
        for log in logs:
            reasons_by_artifact.setdefault(str(log.artifact_id), log.reasons)

    items = []
    for a in artifacts:
        text_preview = None
        if isinstance(a.payload, dict):
            text_preview = (
                a.payload.get("text")
                or a.payload.get("caption")
                or a.payload.get("description")
            )
        items.append(QueueItemOut(
            id=a.id,
            user_id=a.user_id,
            content_type=a.content_type,
            layer=a.layer,
            status=a.status,
            report_count=a.report_count,
            text_preview=(text_preview or "")[:200] or None,
            media_url=a.payload.get("url") if isinstance(a.payload, dict) else None,
            flag_reasons=reasons_by_artifact.get(str(a.id)),
            created_at=a.created_at,
        ))

    return QueueResponse(items=items, total=total, limit=limit, offset=offset,
                         has_more=(offset + limit) < total)


# ============================================================
# DECISIONS
# ============================================================

@router.post("/{artifact_id}/approve", summary="[ADMIN] Approve content")
async def approve_artifact(
    artifact_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    artifact = await _get_reviewable(db, artifact_id)
    artifact.status = ArtifactStatus.ACTIVE
    artifact.report_count = 0  # fresh start after a human said it's fine
    await ModerationService.log_admin_action(
        db, admin.id, artifact_id, "ADMIN_APPROVE"
    )
    await db.commit()
    return {"message": "Artifact approved and published", "artifact_id": str(artifact_id)}


@router.post("/{artifact_id}/remove", summary="[ADMIN] Remove content")
async def remove_artifact(
    artifact_id: UUID,
    reason: Optional[str] = Query(None, max_length=500),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Confirms the content was bad: soft-delete + author reputation -30."""
    artifact = await _get_reviewable(db, artifact_id)
    artifact.status = ArtifactStatus.DELETED

    if artifact.user_id:
        author = await db.get(User, artifact.user_id)
        if author:
            author.modify_reputation(PENALTY_ADMIN_REMOVE)

    await ModerationService.log_admin_action(
        db, admin.id, artifact_id, "ADMIN_REMOVE", note=reason
    )
    await db.commit()
    return {
        "message": "Artifact removed; author penalized",
        "artifact_id": str(artifact_id),
        "reputation_penalty": PENALTY_ADMIN_REMOVE,
    }


async def _get_reviewable(db: AsyncSession, artifact_id: UUID) -> Artifact:
    artifact = await db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact not found")
    if artifact.status == ArtifactStatus.DELETED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Artifact already deleted")
    return artifact


# ============================================================
# LOGS & STATS
# ============================================================

@router.get("/logs", response_model=LogsResponse, summary="[ADMIN] Recent moderation decisions")
async def moderation_logs(
    decision: Optional[str] = Query(None, pattern="^(ALLOW|FLAG|REJECT|ADMIN_APPROVE|ADMIN_REMOVE)$"),
    user_id: Optional[UUID] = Query(None, description="Filter by author (repeat offenders)"),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(ModerationLog).order_by(desc(ModerationLog.created_at)).limit(limit)
    if decision:
        query = query.where(ModerationLog.decision == decision)
    if user_id:
        query = query.where(ModerationLog.user_id == user_id)

    logs = (await db.execute(query)).scalars().all()
    return LogsResponse(items=[ModerationLogOut.model_validate(l) for l in logs])


@router.get("/stats", summary="[ADMIN] Moderation overview")
async def moderation_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    pending = (await db.execute(select(func.count(Artifact.id))
               .where(Artifact.status == ArtifactStatus.PENDING))).scalar() or 0
    hidden = (await db.execute(select(func.count(Artifact.id))
              .where(Artifact.status == ArtifactStatus.HIDDEN))).scalar() or 0
    rejects = (await db.execute(select(func.count(ModerationLog.id))
               .where(ModerationLog.decision == "REJECT"))).scalar() or 0
    return {
        "pending_review": pending,
        "auto_hidden_by_reports": hidden,
        "total_rejections": rejects,
    }
