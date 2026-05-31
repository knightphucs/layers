"""
LAYERS - Rate Limiter Tests (Redis sliding window + fallback)
Run: pytest tests/test_rate_limit_redis.py -v

Uses fakeredis so no real Redis server is required.
"""

import pytest
import fakeredis.aioredis

from app.core import redis_client
from app.core.rate_limit import RateLimiter


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


class TestRedisSlidingWindow:
    async def test_allows_up_to_limit_then_blocks(self, fake_redis):
        rl = RateLimiter()
        results = []
        for _ in range(7):
            allowed, _ = await rl.is_allowed(
                "1.2.3.4", "/api/v1/auth/login",
                max_requests=5, window_seconds=60,
            )
            results.append(allowed)
        assert results == [True, True, True, True, True, False, False]

    async def test_remaining_counts_down(self, fake_redis):
        rl = RateLimiter()
        _, r0 = await rl.is_allowed("9.9.9.9", "/ep", max_requests=3, window_seconds=60)
        _, r1 = await rl.is_allowed("9.9.9.9", "/ep", max_requests=3, window_seconds=60)
        assert r0 == 2
        assert r1 == 1

    async def test_blocked_request_is_not_counted(self, fake_redis):
        """A rejected request should not consume window space (rolled back)."""
        rl = RateLimiter()
        for _ in range(2):
            await rl.is_allowed("5.5.5.5", "/ep", max_requests=2, window_seconds=60)
        # over limit now
        allowed, _ = await rl.is_allowed("5.5.5.5", "/ep", max_requests=2, window_seconds=60)
        assert allowed is False
        # the zset should still hold exactly max_requests members
        count = await fake_redis.zcard("ratelimit:5.5.5.5:/ep")
        assert count == 2

    async def test_separate_keys_per_ip_and_endpoint(self, fake_redis):
        rl = RateLimiter()
        a, _ = await rl.is_allowed("1.1.1.1", "/ep", max_requests=1, window_seconds=60)
        b, _ = await rl.is_allowed("2.2.2.2", "/ep", max_requests=1, window_seconds=60)
        assert a is True and b is True  # different IPs are independent


class TestInMemoryFallback:
    async def test_fallback_when_no_redis(self, no_redis):
        rl = RateLimiter()
        results = []
        for _ in range(4):
            allowed, _ = await rl.is_allowed(
                "7.7.7.7", "/ep", max_requests=3, window_seconds=60
            )
            results.append(allowed)
        assert results == [True, True, True, False]
