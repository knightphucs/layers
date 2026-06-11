"""
LAYERS - Quest Service Tests
Run: pytest tests/test_quest_service.py -v
"""

import uuid
from datetime import date, timedelta

import pytest
import fakeredis.aioredis

from app.core import redis_client
from app.services import quest_service as qmod
from app.services.quest_service import QuestService, QuestTrigger, DAILY_COUNT


@pytest.fixture
async def fake_redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    redis_client._redis = client
    redis_client._available = True
    yield client
    await client.flushall()
    await client.aclose()
    redis_client._redis = None
    redis_client._available = False


# ============================================================
# CATALOG
# ============================================================

class TestCatalog:
    def test_todays_quests_count(self):
        assert len(QuestService.todays_quests(date(2026, 6, 5))) == DAILY_COUNT

    def test_rotates_by_date(self):
        a = [q["id"] for q in QuestService.todays_quests(date(2026, 6, 5))]
        b = [q["id"] for q in QuestService.todays_quests(date(2026, 6, 6))]
        assert a != b  # different days → different rotation

    def test_deterministic_same_date(self):
        a = QuestService.todays_quests(date(2026, 6, 5))
        b = QuestService.todays_quests(date(2026, 6, 5))
        assert [q["id"] for q in a] == [q["id"] for q in b]


# ============================================================
# STREAK LOGIC (pure)
# ============================================================

class TestStreak:
    def test_first_ever(self):
        cur, longest, changed = QuestService.compute_streak(None, date(2026, 6, 5), 0, 0)
        assert (cur, longest, changed) == (1, 1, True)

    def test_consecutive_day_increments(self):
        today = date(2026, 6, 5)
        cur, longest, changed = QuestService.compute_streak(today - timedelta(days=1), today, 3, 5)
        assert cur == 4 and longest == 5 and changed is True

    def test_new_longest(self):
        today = date(2026, 6, 5)
        cur, longest, changed = QuestService.compute_streak(today - timedelta(days=1), today, 9, 9)
        assert cur == 10 and longest == 10

    def test_gap_resets(self):
        today = date(2026, 6, 5)
        cur, longest, changed = QuestService.compute_streak(today - timedelta(days=3), today, 8, 8)
        assert cur == 1 and longest == 8 and changed is True

    def test_same_day_no_change(self):
        today = date(2026, 6, 5)
        cur, longest, changed = QuestService.compute_streak(today, today, 4, 7)
        assert (cur, longest, changed) == (4, 7, False)


# ============================================================
# PROGRESS / COMPLETION (fakeredis + FakeSession + patched XP)
# ============================================================

class FakeUser:
    def __init__(self):
        self.current_streak = 0
        self.longest_streak = 0
        self.last_quest_date = None


class FakeSession:
    def __init__(self, user):
        self.user = user
        self.added = []
        self.flushed = False
    async def get(self, _model, _ident):
        return self.user
    def add(self, obj):
        self.added.append(obj)
    async def flush(self):
        self.flushed = True


@pytest.fixture
def patch_quests_and_xp(monkeypatch):
    """Pin today's quests to a controlled set and stub XPService.award."""
    fixed = [
        {"id": "q_one", "title": "One Unlock", "icon": "🔓", "layer": "BOTH",
         "description": "x", "trigger": QuestTrigger.ARTIFACT_UNLOCK, "target": 1, "xp": 40},
        {"id": "q_three", "title": "Three Replies", "icon": "💌", "layer": "LIGHT",
         "description": "x", "trigger": QuestTrigger.REPLY_SENT, "target": 3, "xp": 30},
    ]
    monkeypatch.setattr(QuestService, "todays_quests", staticmethod(lambda d=None: fixed))

    awards = []
    async def fake_award(db, user_id, event_type, **kwargs):
        awards.append({"user_id": user_id, "event_type": event_type, **kwargs})
    monkeypatch.setattr(qmod.XPService, "award", staticmethod(fake_award))
    return awards


class TestProgress:
    async def test_single_target_completes_immediately(self, fake_redis, patch_quests_and_xp):
        awards = patch_quests_and_xp
        user_id = uuid.uuid4()
        db = FakeSession(FakeUser())
        completed = await QuestService.report_progress(db, user_id, QuestTrigger.ARTIFACT_UNLOCK)
        assert [c["id"] for c in completed] == ["q_one"]
        assert len(awards) == 1
        assert awards[0]["amount"] == 40
        assert len(db.added) == 1            # QuestCompletion logged
        assert db.user.current_streak == 1   # streak bumped

    async def test_multi_target_needs_repeats(self, fake_redis, patch_quests_and_xp):
        awards = patch_quests_and_xp
        user_id = uuid.uuid4()
        db = FakeSession(FakeUser())
        c1 = await QuestService.report_progress(db, user_id, QuestTrigger.REPLY_SENT)
        c2 = await QuestService.report_progress(db, user_id, QuestTrigger.REPLY_SENT)
        assert c1 == [] and c2 == []          # 1, 2 of 3 — not done
        c3 = await QuestService.report_progress(db, user_id, QuestTrigger.REPLY_SENT)
        assert [c["id"] for c in c3] == ["q_three"]
        assert len(awards) == 1               # awarded exactly once

    async def test_no_double_award_after_completion(self, fake_redis, patch_quests_and_xp):
        awards = patch_quests_and_xp
        user_id = uuid.uuid4()
        db = FakeSession(FakeUser())
        await QuestService.report_progress(db, user_id, QuestTrigger.ARTIFACT_UNLOCK)
        again = await QuestService.report_progress(db, user_id, QuestTrigger.ARTIFACT_UNLOCK)
        assert again == []                    # already done today
        assert len(awards) == 1               # still only one award

    async def test_unrelated_trigger_no_progress(self, fake_redis, patch_quests_and_xp):
        user_id = uuid.uuid4()
        db = FakeSession(FakeUser())
        completed = await QuestService.report_progress(db, user_id, QuestTrigger.GAME_WIN)
        assert completed == []

    async def test_degraded_without_redis(self, patch_quests_and_xp):
        redis_client._redis = None
        redis_client._available = False
        db = FakeSession(FakeUser())
        completed = await QuestService.report_progress(db, uuid.uuid4(), QuestTrigger.ARTIFACT_UNLOCK)
        assert completed == []  # no crash, just no progress


class TestGetToday:
    async def test_get_today_shape(self, fake_redis, patch_quests_and_xp):
        user_id = uuid.uuid4()
        db = FakeSession(FakeUser())
        data = await QuestService.get_today(db, user_id)
        assert data["total_count"] == 2
        assert data["completed_count"] == 0
        assert {q["id"] for q in data["quests"]} == {"q_one", "q_three"}
        assert data["streak"]["current"] == 0

    async def test_get_today_reflects_progress(self, fake_redis, patch_quests_and_xp):
        user_id = uuid.uuid4()
        db = FakeSession(FakeUser())
        await QuestService.report_progress(db, user_id, QuestTrigger.ARTIFACT_UNLOCK)
        data = await QuestService.get_today(db, user_id)
        assert data["completed_count"] == 1
        q_one = next(q for q in data["quests"] if q["id"] == "q_one")
        assert q_one["completed"] is True
        assert q_one["progress"] == 1
