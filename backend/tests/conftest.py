"""
LAYERS - Pytest Configuration
Shared fixtures and configuration for all tests
"""

# pytest-asyncio 0.23+ handles event loop automatically with asyncio_mode=auto
# Configuration is in pytest.ini

import os

import pytest
import pytest_asyncio

# Every test file builds its own engine and drops/creates its own tables, so
# Postgres state is isolated per test. The rate limiters are NOT — they are
# process- and server-wide, and they key on client IP, which is identical
# ("testclient") for every test in every file:
#
#   RateLimitMiddleware   /auth/register  5 per 5 min   (app/core/rate_limit.py)
#   rate_limit("register") 3 per hour     (app/api/v1/auth.py:122)
#
# Almost every test in test_auth / test_chat_* / test_campfire /
# test_social_spark / test_truth_or_dare registers a user during setup, so from
# the 4th test onward registration returns 429 and the test fails on a bogus
# assertion far from the real cause. httpx's ASGITransport does not run the
# lifespan, so Redis is never initialised under pytest and the middleware falls
# back to its in-memory store — which no amount of Redis flushing can clear.
# Its counters live in the imported module for the whole session.
#
# Resetting both stores before each test restores per-test isolation without
# weakening either limiter. Production code is untouched.
REDIS_KEY_PATTERNS = ("rl:ep:*", "ratelimit:*")


@pytest_asyncio.fixture(autouse=True)
async def reset_rate_limits():
    """Clear rate-limit counters so tests don't 429 each other."""
    # In-memory fallback store used by RateLimitMiddleware under pytest.
    try:
        from app.core.rate_limit import rate_limiter

        rate_limiter.requests.clear()
    except Exception:  # noqa: BLE001 - never let cleanup break the suite
        pass

    # Redis counters, for the case where a test run does have Redis wired up.
    try:
        import redis.asyncio as aioredis

        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        client = aioredis.from_url(url, decode_responses=True)
        for pattern in REDIS_KEY_PATTERNS:
            keys = [k async for k in client.scan_iter(match=pattern)]
            if keys:
                await client.delete(*keys)
        await client.aclose()
    except Exception:  # noqa: BLE001 - Redis is optional; tests must still run
        pass

    yield


def pytest_collection_modifyitems(items):
    """Guard rail: refuse to run if TEST_DATABASE_URL points at the dev DB.

    Every test file calls Base.metadata.drop_all on whatever TEST_DATABASE_URL
    resolves to. config.py ships a placeholder password, so a missing
    TEST_DATABASE_URL in backend/.env silently falls back to it — the failure
    mode there is a connection error, but a *matching* password would drop the
    real schema instead.
    """
    from app.core.config import settings

    if settings.test_database_url == settings.database_url:
        pytest.exit(
            "TEST_DATABASE_URL equals DATABASE_URL — tests would drop the "
            "development schema. Set TEST_DATABASE_URL in backend/.env.",
            returncode=1,
        )
