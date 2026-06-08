"""
LAYERS - Presence + Geo-cache Tests
Run: pytest tests/test_presence_geocache.py -v
"""

import asyncio
import time
from uuid import uuid4

import pytest
import fakeredis.aioredis

from app.core import redis_client
from app.core import presence
from app.core.geo_cache import nearby_key, viewport_key, invalidate_on_artifact_create
from app.core.cache import cache_set, cache_get


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


@pytest.fixture
def no_redis():
    redis_client._redis = None
    redis_client._available = False
    yield
    redis_client._redis = None
    redis_client._available = False


class TestUserPresence:
    async def test_mark_online_offline(self, fake_redis):
        u = uuid4()
        assert await presence.is_online(u) is False
        await presence.mark_online(u)
        assert await presence.is_online(u) is True
        await presence.mark_offline(u)
        assert await presence.is_online(u) is False

    async def test_online_ttl_expires(self, fake_redis):
        u = uuid4()
        await presence.mark_online(u, ttl=1)
        assert await presence.is_online(u) is True
        await fake_redis.expire(presence._user_key(u), 0)  # force expire
        assert await presence.is_online(u) is False

    async def test_filter_online_subset(self, fake_redis):
        u1, u2, u3 = uuid4(), uuid4(), uuid4()
        await presence.mark_online(u1)
        await presence.mark_online(u3)
        online = await presence.filter_online([u1, u2, u3])
        assert online == {str(u1), str(u3)}


class TestCampfirePresence:
    async def test_touch_and_count(self, fake_redis):
        room = uuid4()
        await presence.campfire_touch(room, uuid4())
        await presence.campfire_touch(room, uuid4())
        assert await presence.campfire_count(room) == 2

    async def test_leave(self, fake_redis):
        room = uuid4()
        u = uuid4()
        await presence.campfire_touch(room, u)
        await presence.campfire_leave(room, u)
        assert await presence.campfire_count(room) == 0

    async def test_expired_members_are_dropped(self, fake_redis):
        room = uuid4()
        u_stale, u_fresh = uuid4(), uuid4()
        now = time.time()
        # stale member already past expiry
        await fake_redis.zadd(presence._campfire_key(room), {str(u_stale): now - 5})
        await presence.campfire_touch(room, u_fresh)
        members = await presence.campfire_online(room)
        assert str(u_fresh) in members
        assert str(u_stale) not in members


class TestGeoCacheKeys:
    def test_nearby_key_buckets_close_coords(self):
        k1 = nearby_key(10.7769, 106.7009, 1000, "LIGHT")
        k2 = nearby_key(10.77691, 106.70088, 1000, "LIGHT")  # within ~1m
        assert k1 == k2  # quantization buckets them together

    def test_nearby_key_separates_layers(self):
        assert nearby_key(10.77, 106.70, 1000, "LIGHT") != \
               nearby_key(10.77, 106.70, 1000, "SHADOW")

    def test_viewport_key_shape(self):
        k = viewport_key(10.0, 106.0, 10.1, 106.1, "SHADOW")
        assert k.startswith("fog:SHADOW:")


class TestInvalidation:
    async def test_artifact_create_clears_nearby_not_fog(self, fake_redis):
        await cache_set(nearby_key(10.77, 106.70, 1000), [1, 2], 60)
        await cache_set(viewport_key(10.0, 106.0, 10.1, 106.1), [3], 60)

        removed = await invalidate_on_artifact_create()
        assert removed == 1
        assert await cache_get(nearby_key(10.77, 106.70, 1000)) is None  # cleared
        assert await cache_get(viewport_key(10.0, 106.0, 10.1, 106.1)) == [3]  # kept

    async def test_invalidation_noop_without_redis(self, no_redis):
        assert await invalidate_on_artifact_create() == 0
