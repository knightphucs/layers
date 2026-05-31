"""
LAYERS - Cache Helpers
======================
A thin JSON cache layer on top of Redis, with graceful fallback.

If Redis is unavailable, cache_get_or_set() simply calls the fetch
function (no caching) so requests still succeed — the cache is an
optimization, never a hard dependency.

Primary use: cache expensive PostGIS queries such as the
fog-of-war viewport and nearby-artifact lookups, keyed by a quantized
viewport so map panning doesn't hammer the database.

Key convention:  "<domain>:<id...>"  e.g. "fog:10.77_106.69_z15"
                 "nearby:<lat>_<lng>_<radius>"
"""

import json
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, Optional

from app.core.redis_client import get_optional_redis

logger = logging.getLogger(__name__)

DEFAULT_TTL = 30  # seconds — short, because geo data changes often


async def cache_get(key: str) -> Optional[Any]:
    """Return the cached value (JSON-decoded) or None on miss / error / no-redis."""
    client = get_optional_redis()
    if client is None:
        return None
    try:
        raw = await client.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception as e:  # noqa: BLE001
        logger.debug("cache_get error key=%s: %s", key, e)
        return None


async def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    """Store a JSON-serializable value with a TTL. No-op if Redis is down."""
    client = get_optional_redis()
    if client is None:
        return
    try:
        await client.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as e:  # noqa: BLE001
        logger.debug("cache_set error key=%s: %s", key, e)


async def cache_get_or_set(
    key: str,
    ttl: int,
    fetch_fn: Callable[[], Awaitable[Any]],
) -> Any:
    """
    Return the cached value, or call fetch_fn(), cache it, and return it.

    fetch_fn must be an async callable taking no arguments, e.g.:
        data = await cache_get_or_set(
            key=f"fog:{vp_key}",
            ttl=20,
            fetch_fn=lambda: ExplorationService.get_viewport(db, bbox),
        )
    """
    cached_val = await cache_get(key)
    if cached_val is not None:
        return cached_val
    value = await fetch_fn()
    await cache_set(key, value, ttl)
    return value


async def cache_delete(*keys: str) -> None:
    """Delete one or more exact keys. No-op if Redis is down."""
    client = get_optional_redis()
    if client is None or not keys:
        return
    try:
        await client.delete(*keys)
    except Exception as e:  # noqa: BLE001
        logger.debug("cache_delete error: %s", e)


async def cache_delete_pattern(pattern: str) -> int:
    """
    Delete all keys matching a glob pattern (e.g. "fog:*").
    Uses SCAN (non-blocking) rather than KEYS. Returns count deleted.

    Use for invalidation, e.g. when an artifact is created, clear the
    nearby-artifact cache around that point.
    """
    client = get_optional_redis()
    if client is None:
        return 0
    deleted = 0
    try:
        async for k in client.scan_iter(match=pattern, count=200):
            await client.delete(k)
            deleted += 1
    except Exception as e:  # noqa: BLE001
        logger.debug("cache_delete_pattern error pattern=%s: %s", pattern, e)
    return deleted


def cached(key_builder: Callable[..., str], ttl: int = DEFAULT_TTL):
    """
    Decorator for async functions. `key_builder(*args, **kwargs)` returns the
    cache key from the call arguments.

        @cached(lambda db, bbox: f"fog:{bbox.key()}", ttl=20)
        async def get_viewport(db, bbox): ...
    """
    def decorator(fn: Callable[..., Awaitable[Any]]):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            key = key_builder(*args, **kwargs)
            return await cache_get_or_set(key, ttl, lambda: fn(*args, **kwargs))
        return wrapper
    return decorator
