"""
LAYERS - Reputation Service
==========================================
reputation_score (User column, default 100, clamped 0..1000) finally does
something. It powers two systems:

1. TRUST-WEIGHTED REPORTS
   A report from a long-trusted user should weigh more than one from a
   brand-new account (a common abuse vector: spin up throwaways to mass-
   report a rival). Auto-hide now triggers on a WEIGHTED score, not a raw
   count. See report_service.ReportService._scores().

2. REPUTATION-GATED PUBLISHING (soft shadowban)
   Users who keep getting content removed sink in reputation. Below a
   threshold, their NEW content is auto-held as PENDING (Day 1 status)
   regardless of what the text filter says — a quiet, reversible quarantine
   that doesn't tell bad actors they've been caught. Earn reputation back
   (good posts, validated reports) and publishing returns to normal.

TIERS (by reputation_score)
   >= 250  TRUSTED      report weight 2.0   publish ACTIVE
   100-249 ESTABLISHED  report weight 1.0   publish ACTIVE   (default = 100)
   50-99   NORMAL       report weight 1.0   publish ACTIVE
   20-49   LOW          report weight 0.5   publish PENDING (soft quarantine)
   < 20    RESTRICTED   report weight 0.25  publish PENDING + can't post VOUCHER

REPUTATION DELTAS
   +5   your report was validated (admin removed the content)
   +2   a post of yours survived review / stayed up (optional, via cron)
   -20  your content auto-rejected by the filter   (applied in Day 1)
   -30  your content removed by an admin            (applied in Day 1)
   -10  habitual false reporting (>=3 dismissed reports — see note)
"""

import logging
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)


class ReputationTier(str, Enum):
    TRUSTED = "TRUSTED"
    ESTABLISHED = "ESTABLISHED"
    NORMAL = "NORMAL"
    LOW = "LOW"
    RESTRICTED = "RESTRICTED"


# (min_score_inclusive, tier, report_weight)
_TIER_TABLE = [
    (250, ReputationTier.TRUSTED, 2.0),
    (100, ReputationTier.ESTABLISHED, 1.0),
    (50, ReputationTier.NORMAL, 1.0),
    (20, ReputationTier.LOW, 0.5),
    (0, ReputationTier.RESTRICTED, 0.25),
]

# Below this tier, new content is quarantined to PENDING.
_QUARANTINE_TIERS = {ReputationTier.LOW, ReputationTier.RESTRICTED}

# Reputation deltas (all clamped 0..1000 by User.modify_reputation)
REP_VALID_REPORT = 5
REP_FALSE_REPORTER = -10
FALSE_REPORTS_BEFORE_PENALTY = 3


class ReputationService:

    # ---- pure helpers (unit-testable, no DB) ----

    @staticmethod
    def tier_for(score: int) -> ReputationTier:
        for threshold, tier, _ in _TIER_TABLE:
            if score >= threshold:
                return tier
        return ReputationTier.RESTRICTED

    @staticmethod
    def report_weight(score: int) -> float:
        for threshold, _, weight in _TIER_TABLE:
            if score >= threshold:
                return weight
        return 0.25

    @staticmethod
    def is_quarantined(score: int) -> bool:
        """True if this user's new content should be held for review."""
        return ReputationService.tier_for(score) in _QUARANTINE_TIERS

    @staticmethod
    def gate_initial_status(score: int, base_status: str) -> str:
        """Combine the Day-1 filter decision with reputation.
        A clean post (ACTIVE) from a low-rep user becomes PENDING.
        FLAG/PENDING stays PENDING; the filter is never relaxed."""
        if base_status == "ACTIVE" and ReputationService.is_quarantined(score):
            return "PENDING"
        return base_status

    @staticmethod
    def can_post_voucher(score: int) -> bool:
        """RESTRICTED users can't drop VOUCHER artifacts (scam vector)."""
        return ReputationService.tier_for(score) != ReputationTier.RESTRICTED

    # ---- DB-aware actions ----

    @staticmethod
    async def reward_validated_reporters(
        db: AsyncSession, reporter_ids: list
    ) -> None:
        """Admin removed reported content → everyone who reported it was
        right. Bump their reputation. Caller commits."""
        for rid in reporter_ids:
            user = await db.get(User, rid)
            if user:
                user.modify_reputation(REP_VALID_REPORT)
        if reporter_ids:
            await db.flush()
            logger.info("Rewarded %d validated reporters", len(reporter_ids))

    @staticmethod
    async def penalize_false_reporter_if_habitual(
        db: AsyncSession, reporter_id, dismissed_count: int
    ) -> bool:
        """Dismissing one report is no big deal (we WANT people to report).
        But a user with many dismissed reports is abusing the system.
        Returns True if a penalty was applied. Caller commits."""
        if dismissed_count < FALSE_REPORTS_BEFORE_PENALTY:
            return False
        user = await db.get(User, reporter_id)
        if user:
            user.modify_reputation(REP_FALSE_REPORTER)
            await db.flush()
            logger.info("Penalized habitual false reporter %s", reporter_id)
            return True
        return False

    @staticmethod
    async def get_tier_info(db: AsyncSession, user_id) -> dict:
        """For the profile / my-status screen."""
        user = await db.get(User, user_id)
        score = user.reputation_score if user else 100
        tier = ReputationService.tier_for(score)
        return {
            "reputation_score": score,
            "tier": tier.value,
            "report_weight": ReputationService.report_weight(score),
            "is_quarantined": ReputationService.is_quarantined(score),
            "can_post_voucher": ReputationService.can_post_voucher(score),
        }
