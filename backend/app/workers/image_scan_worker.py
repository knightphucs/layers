"""
LAYERS - Image Scan Worker
===================================================
Day 1 made every PHOTO artifact start as PENDING (status held until a human
or an AI scanner clears it). This worker is the AI half of that contract.

Right now it just calls ModerationService.scan_image (the Day-1 stub that
returns FLAG), so nothing auto-approves yet — that's intentional and safe
for launch. When you wire a real model (NudeNet locally, or AWS Rekognition
/ Google Vision), only `scan_image` in moderation_service.py changes; this
worker's loop stays the same.

HOW IT RUNS — three options, pick one when you deploy:
  (a) Manual / cron:  POST /api/v1/moderation/scan-photos?limit=20  (admin)
  (b) APScheduler:    schedule run_scan_batch() every N minutes
  (c) Standalone:     `python -m app.workers.image_scan_worker`  (loop below)

We deliberately do NOT add Celery — the existing stack has no broker, and a
periodic batch is more than enough at launch volume. Keep it simple.

DECISION MAPPING (per photo)
  scan ALLOW  → status ACTIVE   (auto-approved, published)
  scan FLAG   → stays PENDING   (human review in the Day-1 queue)
  scan REJECT → status DELETED  + author reputation penalty
"""

import asyncio
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact, ArtifactStatus, ContentType
from app.models.user import User
from app.services.moderation_service import (
    ModerationService,
    ModerationContext,
    ModerationDecision,
    scan_image,
    PENALTY_REJECT,
)

logger = logging.getLogger(__name__)

SCAN_BATCH_LIMIT = 20
SCAN_INTERVAL_SECONDS = 300  # 5 min, for the standalone loop


async def run_scan_batch(db: AsyncSession, limit: int = SCAN_BATCH_LIMIT) -> dict:
    """Scan up to `limit` PENDING photo artifacts. Returns a summary.

    Safe to call repeatedly (cron/scheduler/manual). Each photo is
    independent; one bad scan won't block the rest.
    """
    pending_photos = (await db.execute(
        select(Artifact)
        .where(
            Artifact.status == ArtifactStatus.PENDING,
            Artifact.content_type == ContentType.PHOTO,
        )
        .order_by(Artifact.created_at.asc())
        .limit(limit)
    )).scalars().all()

    approved = flagged = removed = errored = 0

    for artifact in pending_photos:
        url = artifact.payload.get("url") if isinstance(artifact.payload, dict) else None
        if not url:
            # No image to scan; leave for human review.
            flagged += 1
            continue
        try:
            result = scan_image(url)
            if result.decision == ModerationDecision.ALLOW:
                artifact.status = ArtifactStatus.ACTIVE
                approved += 1
            elif result.decision == ModerationDecision.REJECT:
                artifact.status = ArtifactStatus.DELETED
                if artifact.user_id:
                    author = await db.get(User, artifact.user_id)
                    if author:
                        author.modify_reputation(PENALTY_REJECT)
                await ModerationService.log_admin_action(
                    db, admin_id=artifact.user_id, artifact_id=artifact.id,
                    decision="ADMIN_REMOVE", note="auto image scan: reject",
                )
                removed += 1
            else:  # FLAG → stays PENDING for human
                flagged += 1
        except Exception as exc:  # never let one photo kill the batch
            logger.exception("Image scan failed for %s: %s", artifact.id, exc)
            errored += 1

    await db.commit()
    summary = {
        "scanned": len(pending_photos),
        "approved": approved,
        "still_pending": flagged,
        "removed": removed,
        "errored": errored,
    }
    if pending_photos:
        logger.info("Image scan batch: %s", summary)
    return summary


async def _standalone_loop():  # pragma: no cover — for option (c)
    """Run forever, scanning every SCAN_INTERVAL_SECONDS.
    Wire your AsyncSessionLocal here when you run this as a process."""
    from app.core.database import AsyncSessionLocal  # type: ignore
    logger.info("Image scan worker started (interval=%ds)", SCAN_INTERVAL_SECONDS)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await run_scan_batch(db)
        except Exception as exc:
            logger.exception("Scan loop error: %s", exc)
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_standalone_loop())
