"""
LAYERS - Report & Reputation tests
Pure-logic tests — no DB. Run: pytest tests/test_reputation.py -v
"""

import pytest

from app.services.reputation_service import ReputationService, ReputationTier
from app.services.report_service import ReportReason, AUTO_HIDE_WEIGHT_THRESHOLD


class TestReputationTiers:
    def test_default_user_is_established(self):
        # New users start at 100 → ESTABLISHED, full publishing rights
        assert ReputationService.tier_for(100) == ReputationTier.ESTABLISHED

    def test_trusted_threshold(self):
        assert ReputationService.tier_for(250) == ReputationTier.TRUSTED
        assert ReputationService.tier_for(999) == ReputationTier.TRUSTED

    def test_low_and_restricted(self):
        assert ReputationService.tier_for(30) == ReputationTier.LOW
        assert ReputationService.tier_for(19) == ReputationTier.RESTRICTED
        assert ReputationService.tier_for(0) == ReputationTier.RESTRICTED

    def test_boundaries_are_inclusive(self):
        assert ReputationService.tier_for(50) == ReputationTier.NORMAL
        assert ReputationService.tier_for(49) == ReputationTier.LOW
        assert ReputationService.tier_for(20) == ReputationTier.LOW


class TestReportWeights:
    def test_trusted_weighs_double(self):
        assert ReputationService.report_weight(300) == 2.0

    def test_normal_weighs_one(self):
        assert ReputationService.report_weight(100) == 1.0
        assert ReputationService.report_weight(60) == 1.0

    def test_low_rep_weighs_less(self):
        assert ReputationService.report_weight(30) == 0.5
        assert ReputationService.report_weight(10) == 0.25


class TestQuarantine:
    def test_normal_user_not_quarantined(self):
        assert ReputationService.is_quarantined(100) is False
        assert ReputationService.is_quarantined(50) is False

    def test_low_rep_quarantined(self):
        assert ReputationService.is_quarantined(40) is True
        assert ReputationService.is_quarantined(5) is True

    def test_gate_holds_clean_post_from_low_rep(self):
        # A clean (ACTIVE) post from a quarantined user → PENDING
        assert ReputationService.gate_initial_status(40, "ACTIVE") == "PENDING"

    def test_gate_leaves_normal_user_alone(self):
        assert ReputationService.gate_initial_status(100, "ACTIVE") == "ACTIVE"

    def test_gate_never_relaxes_filter(self):
        # PENDING from the text filter stays PENDING even for a trusted user
        assert ReputationService.gate_initial_status(500, "PENDING") == "PENDING"


class TestVoucherGate:
    def test_restricted_cannot_post_voucher(self):
        assert ReputationService.can_post_voucher(10) is False

    def test_low_rep_can_still_post_voucher(self):
        assert ReputationService.can_post_voucher(30) is True

    def test_normal_can_post_voucher(self):
        assert ReputationService.can_post_voucher(100) is True


class TestWeightedAutoHide:
    """The core anti-report-bombing property, expressed as arithmetic."""

    def _weighted(self, scores):
        return sum(ReputationService.report_weight(s) for s in scores)

    def test_five_established_users_trigger_hide(self):
        scores = [100, 120, 150, 100, 200]  # all weight 1.0
        assert self._weighted(scores) >= AUTO_HIDE_WEIGHT_THRESHOLD

    def test_five_throwaway_accounts_do_not_trigger_hide(self):
        scores = [10, 10, 10, 10, 10]  # weight 0.25 each → 1.25
        assert self._weighted(scores) < AUTO_HIDE_WEIGHT_THRESHOLD

    def test_three_trusted_users_trigger_hide_fast(self):
        scores = [300, 400, 260]  # weight 2.0 each → 6.0
        assert self._weighted(scores) >= AUTO_HIDE_WEIGHT_THRESHOLD

    def test_single_reporter_never_hides(self):
        assert self._weighted([999]) < AUTO_HIDE_WEIGHT_THRESHOLD


class TestReportReason:
    def test_valid_reasons(self):
        assert ReportReason("SPAM") == ReportReason.SPAM
        assert ReportReason("PERSONAL_INFO") == ReportReason.PERSONAL_INFO

    def test_invalid_reason_raises(self):
        with pytest.raises(ValueError):
            ReportReason("NONSENSE")

    def test_all_reasons_present(self):
        names = {r.value for r in ReportReason}
        assert {"SPAM", "HARASSMENT", "SEXUAL_CONTENT", "VIOLENCE",
                "HATE_SPEECH", "MISINFORMATION", "PERSONAL_INFO", "OTHER"} == names
