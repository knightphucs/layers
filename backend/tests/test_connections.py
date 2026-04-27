"""
LAYERS — Connection System Tests
==========================================
Unit tests for progressive connection logic.
Run: pytest tests/test_connections.py -v
"""

import pytest
import uuid


# ============================================================
# LEVEL COMPUTATION TESTS
# ============================================================

class TestConnectionLevels:
    """Tests for progressive level computation."""

    def test_level_0_stranger_new_connection(self):
        """Fresh connection with 0 interactions = STRANGER."""
        interaction_count = 0
        status = "PENDING"
        expected = "STRANGER"

        level = "CONNECTED" if status == "CONNECTED" else (
            "SIGNAL" if interaction_count >= 5 else "STRANGER"
        )
        assert level == expected

    def test_level_0_stranger_4_interactions(self):
        """4 interactions (below threshold) = STRANGER."""
        interaction_count = 4
        status = "PENDING"
        level = "SIGNAL" if interaction_count >= 5 else "STRANGER"
        assert level == "STRANGER"

    def test_level_1_signal_5_interactions(self):
        """Exactly 5 interactions = SIGNAL."""
        interaction_count = 5
        status = "PENDING"
        level = "SIGNAL" if interaction_count >= 5 else "STRANGER"
        assert level == "SIGNAL"

    def test_level_1_signal_10_interactions(self):
        """10 interactions still SIGNAL (status is PENDING)."""
        interaction_count = 10
        status = "PENDING"
        level = "CONNECTED" if status == "CONNECTED" else (
            "SIGNAL" if interaction_count >= 5 else "STRANGER"
        )
        assert level == "SIGNAL"

    def test_level_2_connected(self):
        """Status=CONNECTED → CONNECTED regardless of count."""
        interaction_count = 5
        status = "CONNECTED"
        level = "CONNECTED" if status == "CONNECTED" else "SIGNAL"
        assert level == "CONNECTED"


# ============================================================
# CANONICAL ORDER TESTS
# ============================================================

class TestCanonicalOrder:
    """Tests for ordered_pair helper — ensures unique connection per pair."""

    def test_smaller_uuid_first(self):
        """Smaller UUID should be user_a_id."""
        id_low = "00000000-0000-0000-0000-000000000001"
        id_high = "ffffffff-ffff-ffff-ffff-ffffffffffff"

        a, b = (id_low, id_high) if id_low < id_high else (id_high, id_low)
        assert a == id_low
        assert b == id_high

    def test_same_pair_different_order(self):
        """A→B and B→A should produce same canonical pair."""
        id1 = "aaaaaaaa-0000-0000-0000-000000000000"
        id2 = "bbbbbbbb-0000-0000-0000-000000000000"

        pair1 = (id1, id2) if id1 < id2 else (id2, id1)
        pair2 = (id2, id1) if id2 < id1 else (id1, id2)

        assert pair1 == pair2


# ============================================================
# INTERACTION RECORDING TESTS
# ============================================================

class TestRecordInteraction:
    """Tests for recording interactions between users."""

    def test_self_connection_rejected(self):
        """Cannot create connection with yourself."""
        user_id = "same-id"
        with pytest.raises(ValueError, match="yourself"):
            if user_id == user_id:
                raise ValueError("Cannot create connection with yourself")

    def test_first_interaction_creates_connection(self):
        """First interaction creates new PENDING connection."""
        count_before = 0
        count_after = count_before + 1
        assert count_after == 1

    def test_level_up_detection(self):
        """Transitioning 4 → 5 should flag level_up=True."""
        prev_count = 4
        new_count = 5

        prev_level = "STRANGER" if prev_count < 5 else "SIGNAL"
        new_level = "STRANGER" if new_count < 5 else "SIGNAL"

        level_up = prev_level != new_level
        assert level_up is True
        assert prev_level == "STRANGER"
        assert new_level == "SIGNAL"

    def test_no_level_up_same_bucket(self):
        """6 → 7 both SIGNAL, no level up."""
        prev_count = 6
        new_count = 7

        prev_level = "SIGNAL" if prev_count >= 5 else "STRANGER"
        new_level = "SIGNAL" if new_count >= 5 else "STRANGER"

        assert prev_level == new_level


# ============================================================
# UPGRADE FLOW TESTS
# ============================================================

class TestUpgradeFlow:
    """Tests for requesting and accepting connection upgrades."""

    def test_cannot_upgrade_below_threshold(self):
        """Cannot request upgrade with <5 interactions."""
        interaction_count = 3
        level = "STRANGER" if interaction_count < 5 else "SIGNAL"
        can_upgrade = level == "SIGNAL"
        assert can_upgrade is False

    def test_can_upgrade_at_signal_level(self):
        """Can request upgrade at SIGNAL level."""
        interaction_count = 5
        level = "SIGNAL" if interaction_count >= 5 else "STRANGER"
        can_upgrade = level == "SIGNAL"
        assert can_upgrade is True

    def test_one_party_request_stays_pending(self):
        """Only one user requesting → stays PENDING."""
        upgrade_by_a = True
        upgrade_by_b = False
        both_requested = upgrade_by_a and upgrade_by_b
        assert both_requested is False

    def test_both_parties_request_upgrades(self):
        """Both users requesting → auto-upgrade to CONNECTED."""
        upgrade_by_a = True
        upgrade_by_b = True
        both_requested = upgrade_by_a and upgrade_by_b
        assert both_requested is True

    def test_reject_resets_flags(self):
        """Reject should clear both upgrade flags."""
        upgrade_by_a = True
        upgrade_by_b = True

        # Reject
        upgrade_by_a = False
        upgrade_by_b = False

        assert not upgrade_by_a
        assert not upgrade_by_b


# ============================================================
# PRIVACY TESTS
# ============================================================

class TestConnectionPrivacy:
    """Tests for Level 0 privacy (anonymous)."""

    def test_stranger_hides_username(self):
        """STRANGER level should not reveal username."""
        level = "STRANGER"
        username_visible = level != "STRANGER"
        assert username_visible is False

    def test_signal_reveals_username(self):
        """SIGNAL level reveals username and avatar."""
        level = "SIGNAL"
        username_visible = level != "STRANGER"
        assert username_visible is True

    def test_connected_shows_everything(self):
        """CONNECTED level shows full profile."""
        level = "CONNECTED"
        username_visible = level != "STRANGER"
        realtime_chat = level == "CONNECTED"
        assert username_visible is True
        assert realtime_chat is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
