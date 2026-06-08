"""
LAYERS - XP Service Tests
Run: pytest tests/test_xp_service.py -v

Pure-logic tests run anywhere. award() tests use a lightweight FakeSession so
they run without a real database (the award control flow — mutation, level-up
detection, idempotency, notify — is what we verify here).
"""

import pytest

from app.services import xp_service as xpmod
from app.services.xp_service import XPService, XPEventType, XP_VALUES, XP_PER_LEVEL


# ============================================================
# PURE FORMULAS
# ============================================================

class TestFormulas:
    def test_level_for_xp_boundaries(self):
        assert XPService.level_for_xp(0) == 1
        assert XPService.level_for_xp(999) == 1
        assert XPService.level_for_xp(1000) == 2
        assert XPService.level_for_xp(2500) == 3
        assert XPService.level_for_xp(-50) == 1  # clamped

    def test_xp_floor_for_level(self):
        assert XPService.xp_floor_for_level(1) == 0
        assert XPService.xp_floor_for_level(2) == 1000
        assert XPService.xp_floor_for_level(5) == 4000

    def test_progress_math(self):
        p = XPService.progress(1250)
        assert p.level == 2
        assert p.xp_into_level == 250
        assert p.xp_needed == 1000
        assert p.xp_to_next == 750
        assert p.pct == 25.0

    def test_amount_for(self):
        assert XPService.amount_for(XPEventType.ARTIFACT_CREATE) == 50
        assert XPService.amount_for(XPEventType.REPLY_RECEIVED) == 30


class TestRanks:
    def test_rank_ladder_matches_mobile(self):
        assert XPService.rank_for_level(1).title == "Wanderer"
        assert XPService.rank_for_level(5).title == "Trailblazer"
        assert XPService.rank_for_level(10).title == "Mythic"

    def test_rank_caps_at_mythic(self):
        assert XPService.rank_for_level(50).title == "Mythic"
        assert XPService.rank_for_level(50).tier == 10

    def test_rank_floor(self):
        assert XPService.rank_for_level(0).title == "Wanderer"


# ============================================================
# AWARD (FakeSession)
# ============================================================

class FakeUser:
    def __init__(self, xp=0, level=1):
        self.experience_points = xp
        self.level = level


class FakeResult:
    def __init__(self, value):
        self._value = value
    def scalar_one_or_none(self):
        return self._value


class FakeSession:
    """Minimal async session double for award() control-flow tests."""
    def __init__(self, user, existing_event=None):
        self.user = user
        self.existing_event = existing_event
        self.added = []
        self.flushed = False

    async def execute(self, _stmt):
        return FakeResult(self.existing_event)

    async def get(self, _model, _ident):
        return self.user

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True


import uuid


class TestAward:
    async def test_basic_award_adds_xp_and_logs(self):
        user = FakeUser(xp=100, level=1)
        db = FakeSession(user)
        res = await XPService.award(
            db, uuid.uuid4(), XPEventType.REPLY_SENT, notify=False
        )
        assert res.amount == 20
        assert user.experience_points == 120
        assert res.leveled_up is False
        assert len(db.added) == 1          # XPEvent logged
        assert db.flushed is True

    async def test_award_triggers_level_up(self, monkeypatch):
        captured = {}

        async def fake_send(user_id, message):
            captured["user_id"] = user_id
            captured["message"] = message

        monkeypatch.setattr(xpmod, "logger", xpmod.logger)  # keep logger
        # patch the manager used inside _notify_level_up
        import app.core.ws_manager as wsmod
        monkeypatch.setattr(wsmod.manager, "send_to_user", fake_send)

        user = FakeUser(xp=980, level=1)
        db = FakeSession(user)
        res = await XPService.award(
            db, uuid.uuid4(), XPEventType.ARTIFACT_CREATE, notify=True
        )
        assert user.experience_points == 1030
        assert res.level_after == 2
        assert res.leveled_up is True
        assert captured["message"]["type"] == "level_up"
        assert captured["message"]["new_level"] == 2

    async def test_no_level_up_no_notify(self, monkeypatch):
        calls = {"n": 0}

        async def fake_send(user_id, message):
            calls["n"] += 1

        import app.core.ws_manager as wsmod
        monkeypatch.setattr(wsmod.manager, "send_to_user", fake_send)

        user = FakeUser(xp=100, level=1)
        db = FakeSession(user)
        res = await XPService.award(
            db, uuid.uuid4(), XPEventType.REPLY_SENT, notify=True
        )
        assert res.leveled_up is False
        assert calls["n"] == 0

    async def test_idempotency_skips_double_award(self):
        # Simulate an already-logged event for this key
        class ExistingEvent:
            xp_before = 200
            xp_after = 250
            level_before = 1
            level_after = 1
        user = FakeUser(xp=250, level=1)
        db = FakeSession(user, existing_event=ExistingEvent())
        res = await XPService.award(
            db, uuid.uuid4(), XPEventType.ARTIFACT_UNLOCK,
            idempotency_key="artifact_unlock:abc", notify=False,
        )
        assert res.duplicate is True
        assert res.amount == 0
        assert user.experience_points == 250  # unchanged
        assert db.added == []                  # nothing logged again

    async def test_amount_override(self):
        user = FakeUser(xp=0, level=1)
        db = FakeSession(user)
        res = await XPService.award(
            db, uuid.uuid4(), XPEventType.DAILY_QUEST, amount=5, notify=False
        )
        assert res.amount == 5
        assert user.experience_points == 5
