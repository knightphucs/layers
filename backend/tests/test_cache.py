"""
LAYERS - Cache Helper Tests
Run: pytest tests/test_cache.py -v

Uses fakeredis so no real Redis server is required.
asyncio_mode=auto is set in pytest.ini, so no @pytest.mark.asyncio needed.
"""

import pytest
import fakeredis.aioredis

from app.core import redis_client
from app.core.cache import (
    cache_get,
    cache_set,
    cache_get_or_set,
    cache_delete,
    cache_delete_pattern,
)


@pytest.fixture
async def fake_redis():
    """Inject a fake Redis into the redis_client module for the test."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    redis_client._redis = client
    redis_client._available = True
    yield client
    await client.flushall()
    await client.aclose()
    redis_client._redis = None
    redis_client._available = False


@pytest.fixture
def no_redis():
    """Ensure Redis is treated as unavailable."""
    redis_client._redis = None
    redis_client._available = False
    yield
    redis_client._redis = None
    redis_client._available = False


class TestCacheBasics:
    async def test_set_then_get(self, fake_redis):
        await cache_set("k:1", {"value": 42}, ttl=60)
        assert await cache_get("k:1") == {"value": 42}

    async def test_get_miss_returns_none(self, fake_redis):
        assert await cache_get("does:not:exist") is None

    async def test_get_or_set_caches_after_first_call(self, fake_redis):
        calls = {"n": 0}

        async def fetch():
            calls["n"] += 1
            return [1, 2, 3]

        r1 = await cache_get_or_set("k:list", 60, fetch)
        r2 = await cache_get_or_set("k:list", 60, fetch)
        assert r1 == [1, 2, 3]
        assert r2 == [1, 2, 3]
        assert calls["n"] == 1  # second call served from cache

    async def test_delete(self, fake_redis):
        await cache_set("k:del", "x", ttl=60)
        await cache_delete("k:del")
        assert await cache_get("k:del") is None


class TestCacheInvalidation:
    async def test_delete_pattern_only_matches_prefix(self, fake_redis):
        await cache_set("fog:1", [1], 60)
        await cache_set("fog:2", [2], 60)
        await cache_set("nearby:1", [3], 60)

        deleted = await cache_delete_pattern("fog:*")
        assert deleted == 2
        assert await cache_get("fog:1") is None
        assert await cache_get("fog:2") is None
        assert await cache_get("nearby:1") == [3]  # untouched


class TestGracefulFallback:
    async def test_get_or_set_passthrough_without_redis(self, no_redis):
        calls = {"n": 0}

        async def fetch():
            calls["n"] += 1
            return {"ok": True}

        r1 = await cache_get_or_set("k", 60, fetch)
        r2 = await cache_get_or_set("k", 60, fetch)
        assert r1 == r2 == {"ok": True}
        assert calls["n"] == 2  # no caching → fetched every time

    async def test_set_and_get_noop_without_redis(self, no_redis):
        await cache_set("k", "v", 60)          # no-op, must not raise
        assert await cache_get("k") is None
        assert await cache_delete_pattern("k*") == 0
