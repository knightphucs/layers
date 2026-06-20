"""
LAYERS - Report Service
=======================
Owns all report logic. The old ArtifactService.report_artifact just did
`report_count += 1`; this replaces it with a real system:

- one report per (user, artifact)  → no report-bombing
- structured reason (enum)          → filterable admin queue
- TRUST-WEIGHTED auto-hide          → 5 throwaway accounts ≠ 5 trusted users
- admin resolution closes the loop  → validated reporters gain reputation

AUTO-HIDE MATH
  weighted_score = Σ report_weight(reporter.reputation_score)
  hide when weighted_score >= AUTO_HIDE_WEIGHT_THRESHOLD (5.0)

  So: 5 ESTABLISHED users (1.0 each) → 5.0 → hide. ✅
      5 RESTRICTED throwaways (0.25) → 1.25 → NOT hidden. ✅ (abuse blocked)
      3 TRUSTED users (2.0 each)     → 6.0 → hide fast. ✅ (trust rewarded)

report_count (the existing Artifact column) is kept as the DISTINCT
reporter count, for display. The weighted score is computed at decision
time from the few report rows — cheap, and avoids migrating artifacts.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact, ArtifactStatus
from app.models.report import Report
from app.models.user import User
from app.services.reputation_service import ReputationService

logger = logging.getLogger(__name__)

AUTO_HIDE_WEIGHT_THRESHOLD = 5.0


class ReportReason(str, Enum):
    SPAM = "SPAM"
    HARASSMENT = "HARASSMENT"
    SEXUAL_CONTENT = "SEXUAL_CONTENT"
    VIOLENCE = "VIOLENCE"
    HATE_SPEECH = "HATE_SPEECH"
    MISINFORMATION = "MISINFORMATION"
    PERSONAL_INFO = "PERSONAL_INFO"  # doxxing
    OTHER = "OTHER"


class ReportService:

    # ========================================================
    # SUBMIT (user-facing)
    # ========================================================

    @staticmethod
    async def submit_report(
        db: AsyncSession,
        artifact_id: UUID,
        reporter_id: UUID,
        reason: str,
        detail: Optional[str] = None,
    ) -> dict:
        """Record a report. Idempotent per (user, artifact).
        Recomputes report_count and applies trust-weighted auto-hide."""

        # Validate reason
        try:
            reason_enum = ReportReason(reason)
        except ValueError:
            valid = ", ".join(r.value for r in ReportReason)
            raise ValueError(f"Invalid reason. Must be one of: {valid}")

        artifact = await db.get(Artifact, artifact_id)
        if not artifact or artifact.status == ArtifactStatus.DELETED:
            raise ValueError("Artifact not found")

        # Can't report your own content
        if artifact.user_id and str(artifact.user_id) == str(reporter_id):
            raise ValueError("You can't report your own artifact")

        # Already reported? (idempotent — don't error, just acknowledge)
        existing = (await db.execute(
            select(Report).where(
                Report.artifact_id == artifact_id,
                Report.reporter_id == reporter_id,
            )
        )).scalar_one_or_none()
        if existing:
            return {
                "message": "You've already reported this. Thanks — our team will review it.",
                "already_reported": True,
                "artifact_hidden": artifact.status == ArtifactStatus.HIDDEN,
            }

        db.add(Report(
            artifact_id=artifact_id,
            reporter_id=reporter_id,
            reason=reason_enum.value,
            detail=(detail or None),
        ))
        try:
            await db.flush()
        except IntegrityError:
            # Race: two requests at once. Unique constraint caught it.
            await db.rollback()
            return {
                "message": "You've already reported this. Thanks!",
                "already_reported": True,
                "artifact_hidden": artifact.status == ArtifactStatus.HIDDEN,
            }

        # Recompute distinct reporter count + trust-weighted score
        report_count, weighted = await ReportService._scores(db, artifact_id)
        artifact.report_count = report_count

        if (weighted >= AUTO_HIDE_WEIGHT_THRESHOLD
                and artifact.status == ArtifactStatus.ACTIVE):
            artifact.status = ArtifactStatus.HIDDEN
            logger.info(
                "Auto-hid artifact %s (reporters=%d weighted=%.2f)",
                artifact_id, report_count, weighted,
            )

        await db.commit()
        return {
            "message": "Report submitted. Thank you for keeping LAYERS safe!",
            "already_reported": False,
            "report_count": report_count,
            "artifact_hidden": artifact.status == ArtifactStatus.HIDDEN,
        }

    @staticmethod
    async def _scores(db: AsyncSession, artifact_id: UUID) -> tuple:
        """Return (distinct_reporter_count, trust_weighted_score)
        over OPEN reports only."""
        rows = (await db.execute(
            select(User.reputation_score)
            .join(Report, Report.reporter_id == User.id)
            .where(Report.artifact_id == artifact_id, Report.status == "OPEN")
        )).scalars().all()
        count = len(rows)
        weighted = sum(ReputationService.report_weight(s or 100) for s in rows)
        return count, weighted

    # ========================================================
    # RESOLVE (admin — called from moderation approve/remove)
    # ========================================================

    @staticmethod
    async def resolve_for_artifact(
        db: AsyncSession,
        artifact_id: UUID,
        removed: bool,
    ) -> dict:
        """Close all OPEN reports for an artifact after an admin decision.

        removed=True  → reports were valid → reward reporters (+reputation)
        removed=False → reports dismissed  → penalize habitual false reporters

        Caller (moderation.py) commits. Returns a small summary.
        """
        reports = (await db.execute(
            select(Report).where(
                Report.artifact_id == artifact_id,
                Report.status == "OPEN",
            )
        )).scalars().all()

        if not reports:
            return {"resolved": 0, "rewarded": 0, "penalized": 0}

        now = datetime.now(timezone.utc)
        new_status = "RESOLVED_REMOVED" if removed else "RESOLVED_DISMISSED"
        reporter_ids = []
        for r in reports:
            r.status = new_status
            r.resolved_at = now
            reporter_ids.append(r.reporter_id)

        rewarded = penalized = 0
        if removed:
            await ReputationService.reward_validated_reporters(db, reporter_ids)
            rewarded = len(reporter_ids)
        else:
            # Count each reporter's lifetime dismissed reports; penalize repeat offenders
            for rid in set(reporter_ids):
                dismissed = (await db.execute(
                    select(func.count(Report.id)).where(
                        Report.reporter_id == rid,
                        Report.status == "RESOLVED_DISMISSED",
                    )
                )).scalar() or 0
                if await ReputationService.penalize_false_reporter_if_habitual(
                    db, rid, dismissed
                ):
                    penalized += 1

        await db.flush()
        return {
            "resolved": len(reports),
            "rewarded": rewarded,
            "penalized": penalized,
        }

    # ========================================================
    # READ (admin queue support)
    # ========================================================

    @staticmethod
    async def reasons_breakdown(db: AsyncSession, artifact_id: UUID) -> dict:
        """e.g. {"SPAM": 3, "HARASSMENT": 1} — shown in an artifact detail view."""
        rows = (await db.execute(
            select(Report.reason, func.count(Report.id))
            .where(Report.artifact_id == artifact_id, Report.status == "OPEN")
            .group_by(Report.reason)
        )).all()
        return {reason: count for reason, count in rows}

    @staticmethod
    async def reasons_breakdown_bulk(db: AsyncSession, artifact_ids) -> dict:
        """Same as reasons_breakdown but batched for the review queue listing
        (one query for the whole page instead of one per artifact)."""
        if not artifact_ids:
            return {}
        rows = (await db.execute(
            select(Report.artifact_id, Report.reason, func.count(Report.id))
            .where(Report.artifact_id.in_(artifact_ids), Report.status == "OPEN")
            .group_by(Report.artifact_id, Report.reason)
        )).all()
        breakdown: dict = {}
        for artifact_id, reason, count in rows:
            breakdown.setdefault(str(artifact_id), {})[reason] = count
        return breakdown
