"""
LAYERS - Badge + Leaderboard Tests
Run: pytest tests/test_gamification.py -v
"""

import uuid

import pytest
import fakeredis.aioredis

from app.core import redis_client
from app.services import badge_service as bmod
from app.services.badge_service import BadgeService, BADGE_BY_ID
from app.services.leaderboard_service import LeaderboardService


# ============================================================
# LEADERBOARD (fakeredis sorted sets)
# ============================================================

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


class TestLeaderboard:
    async def test_global_orders_by_total_xp(self, fake_redis):
        a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        await LeaderboardService.record(a, total_xp=500, delta=500)
        await LeaderboardService.record(b, total_xp=1200, delta=1200)
        await LeaderboardService.record(c, total_xp=800, delta=800)
        top = await LeaderboardService.top("global", 10)
        assert [uid for uid, _ in top] == [str(b), str(c), str(a)]
        assert top[0][1] == 1200

    async def test_global_zadd_is_absolute(self, fake_redis):
        a = uuid.uuid4()
        await LeaderboardService.record(a, total_xp=500, delta=500)
        await LeaderboardService.record(a, total_xp=560, delta=60)  # new total
        top = await LeaderboardService.top("global", 10)
        assert top[0] == (str(a), 560)  # absolute, not 500+560

    async def test_weekly_is_incremental(self, fake_redis):
        a = uuid.uuid4()
        await LeaderboardService.record(a, total_xp=500, delta=500)
        await LeaderboardService.record(a, total_xp=560, delta=60)
        top = await LeaderboardService.top("weekly", 10)
        assert top[0] == (str(a), 560)  # 500 + 60 accumulated this week

    async def test_rank_of(self, fake_redis):
        a, b = uuid.uuid4(), uuid.uuid4()
        await LeaderboardService.record(a, total_xp=100, delta=100)
        await LeaderboardService.record(b, total_xp=900, delta=900)
        rank_b, score_b = await LeaderboardService.rank_of("global", b)
        rank_a, score_a = await LeaderboardService.rank_of("global", a)
        assert (rank_b, score_b) == (1, 900)
        assert (rank_a, score_a) == (2, 100)

    async def test_fail_open_without_redis(self):
        redis_client._redis = None
        redis_client._available = False
        await LeaderboardService.record(uuid.uuid4(), 100, 100)  # no crash
        assert await LeaderboardService.top("global") == []
        assert await LeaderboardService.rank_of("global", uuid.uuid4()) == (None, 0)


# ============================================================
# BADGES (FakeSession + stubbed queries)
# ============================================================

class FakeUser:
    def __init__(self, level=1, streak=0):
        self.level = level
        self.current_streak = streak


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
def stub_queries(monkeypatch):
    """Control existing badges + event counts for evaluate()."""
    state = {"existing": set(), "counts": {}}

    async def fake_existing(db, user_id):
        return set(state["existing"])

    async def fake_counts(db, user_id):
        return dict(state["counts"])

    monkeypatch.setattr(BadgeService, "_existing_badge_ids", staticmethod(fake_existing))
    monkeypatch.setattr(BadgeService, "_event_counts", staticmethod(fake_counts))
    return state


class TestBadgeEvaluate:
    async def test_count_badge_unlocks_at_threshold(self, stub_queries):
        stub_queries["counts"] = {"ARTIFACT_CREATE": 1}
        db = FakeSession(FakeUser(level=1))
        newly = await BadgeService.evaluate(db, uuid.uuid4())
        ids = {b["id"] for b in newly}
        assert "first_memory" in ids          # threshold 1 met
        assert "storyteller" not in ids        # threshold 10 not met

    async def test_level_and_streak_badges(self, stub_queries):
        db = FakeSession(FakeUser(level=5, streak=7))
        newly = {b["id"] for b in await BadgeService.evaluate(db, uuid.uuid4())}
        assert "rising_star" in newly          # level 5
        assert "dedicated" in newly            # streak 7
        assert "mythic" not in newly           # level 10 not reached

    async def test_event_badge_not_auto_awarded(self, stub_queries):
        db = FakeSession(FakeUser(level=10, streak=30))
        newly = {b["id"] for b in await BadgeService.evaluate(db, uuid.uuid4())}
        assert "campfire_star" not in newly    # event type — direct only

    async def test_existing_badges_skipped(self, stub_queries):
        stub_queries["counts"] = {"ARTIFACT_CREATE": 50}
        stub_queries["existing"] = {"first_memory", "storyteller"}
        db = FakeSession(FakeUser())
        newly = {b["id"] for b in await BadgeService.evaluate(db, uuid.uuid4())}
        assert "first_memory" not in newly
        assert "storyteller" not in newly

    async def test_idempotent_no_new_awards(self, stub_queries):
        db = FakeSession(FakeUser(level=1))
        first = await BadgeService.evaluate(db, uuid.uuid4())
        stub_queries["existing"] = {b["id"] for b in first}
        second = await BadgeService.evaluate(db, uuid.uuid4())
        assert second == []


class TestAwardBadge:
    async def test_award_event_badge(self, monkeypatch):
        async def no_existing(db, user_id):
            return set()
        monkeypatch.setattr(BadgeService, "_existing_badge_ids", staticmethod(no_existing))
        db = FakeSession(FakeUser())
        badge = await BadgeService.award_badge(db, uuid.uuid4(), "campfire_star")
        assert badge is not None and badge["id"] == "campfire_star"
        assert len(db.added) == 1

    async def test_award_already_owned_returns_none(self, monkeypatch):
        async def has_it(db, user_id):
            return {"campfire_star"}
        monkeypatch.setattr(BadgeService, "_existing_badge_ids", staticmethod(has_it))
        db = FakeSession(FakeUser())
        badge = await BadgeService.award_badge(db, uuid.uuid4(), "campfire_star")
        assert badge is None
        assert db.added == []

    async def test_award_unknown_badge(self, monkeypatch):
        async def none(db, user_id):
            return set()
        monkeypatch.setattr(BadgeService, "_existing_badge_ids", staticmethod(none))
        db = FakeSession(FakeUser())
        assert await BadgeService.award_badge(db, uuid.uuid4(), "nope") is None
