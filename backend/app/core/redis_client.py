"""
LAYERS - Redis Client
=====================
Async Redis connection for caching, rate limiting, presence, and
real-time pub/sub.

Design goals (mirrors the DB engine pattern in database.py):
- A single shared connection pool for the whole app.
- Initialized on startup / closed on shutdown via the app lifespan.
- GRACEFUL DEGRADATION: if Redis is unreachable, the app still starts.
  Callers use is_redis_available() / get_optional_redis() and fall back
  safely (cache becomes a passthrough; rate limiting falls back to
  in-memory). This avoids taking the whole API down if Redis blips.

Usage:
    # startup / shutdown (app lifespan)
    await init_redis()
    await close_redis()

    # as a FastAPI dependency (Redis required):
    async def handler(r: Redis = Depends(get_redis)): ...

    # for optional / fail-open use:
    client = get_optional_redis()
    if client is not None:
        ...
"""

import logging
import time
from typing import Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level singletons (like `engine` / `AsyncSessionLocal` in database.py)
_redis: Optional[Redis] = None
_available: bool = False


async def init_redis() -> None:
    """
    Create the Redis connection pool and verify connectivity.
    Does NOT raise if Redis is down — logs a warning and runs degraded.
    """
    global _redis, _available
    try:
        _redis = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,        # str in / str out (we JSON-encode values)
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
            max_connections=20,
        )
        await _redis.ping()
        _available = True
        logger.info("✅ Redis connected: %s", _safe_url(settings.redis_url))
    except Exception as e:  # noqa: BLE001 - we intentionally degrade gracefully
        _available = False
        logger.warning(
            "⚠️ Redis unavailable (%s). Running in degraded mode "
            "(cache passthrough, in-memory rate limiting).",
            e,
        )


async def close_redis() -> None:
    """Close the Redis connection pool on shutdown."""
    global _redis, _available
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception as e:  # noqa: BLE001
            logger.debug("Redis close error: %s", e)
    _redis = None
    _available = False


def is_redis_available() -> bool:
    """True if Redis was reachable at startup / last health check."""
    return _available and _redis is not None


def get_redis_client() -> Redis:
    """
    Return the live client or raise RuntimeError.
    Use when Redis is REQUIRED (e.g. pub/sub, leaderboards).
    """
    if _redis is None or not _available:
        raise RuntimeError("Redis is not available")
    return _redis


def get_optional_redis() -> Optional[Redis]:
    """Return the client if available, else None (for graceful fallback)."""
    return _redis if (_available and _redis is not None) else None


async def get_redis() -> Redis:
    """FastAPI dependency — returns the Redis client (raises if down)."""
    return get_redis_client()


async def redis_health() -> dict:
    """Health snapshot for /api/v1/health/detailed."""
    client = get_optional_redis()
    if client is None:
        return {"status": "❌ unavailable"}
    try:
        start = time.perf_counter()
        pong = await client.ping()
        elapsed = (time.perf_counter() - start) * 1000
        info = await client.info("server")
        return {
            "status": "✅ healthy" if pong else "❌ error",
            "version": info.get("redis_version", "unknown"),
            "response_ms": round(elapsed, 1),
        }
    except Exception as e:  # noqa: BLE001
        return {"status": "❌ error", "error": str(e)}


def _safe_url(url: str) -> str:
    """Hide credentials when logging the Redis URL."""
    if "@" in url:
        return "redis://***@" + url.split("@")[-1]
    return url
