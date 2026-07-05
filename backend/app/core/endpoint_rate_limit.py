"""
LAYERS - Per-Endpoint Rate Limiting
==================================================
The global RateLimitMiddleware covers general traffic. This adds TIGHTER,
per-endpoint limits for the abuse-sensitive auth routes the security checklist
calls out:
    login            5 / minute      (brute-force protection)
    register         3 / hour        (spam-account protection)
    password-reset   3 / hour        (enumeration / email-bomb protection)

Usage (FastAPI dependency) — see SETUP for exact lines:
    @router.post("/login", dependencies=[Depends(rate_limit("login", 5, 60))])

KEYING: by client IP (these routes are unauthenticated). Behind a proxy, honour
X-Forwarded-For's first hop so users aren't all bucketed under the proxy IP.

FAIL-OPEN: mirrors the app-wide Redis philosophy — if Redis is down, we do NOT
block logins. Availability wins; the global middleware still provides a floor.
"""

import logging
from typing import Callable

from fastapi import HTTPException, Request, status

from app.core.redis_client import get_optional_redis

logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(bucket: str, limit: int, window_seconds: int) -> Callable:
    """Build a dependency that allows `limit` requests per `window_seconds`
    per client IP for the named bucket. Fixed-window via Redis INCR+EXPIRE."""

    async def _dependency(request: Request) -> None:
        client = get_optional_redis()
        if client is None:
            return  # fail-open: never block auth on a cache outage

        key = f"rl:ep:{bucket}:{_client_ip(request)}"
        try:
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, window_seconds)
            if count > limit:
                ttl = await client.ttl(key)
                retry = ttl if ttl and ttl > 0 else window_seconds
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Try again in {retry}s.",
                    headers={"Retry-After": str(retry)},
                )
        except HTTPException:
            raise
        except Exception as e:  # noqa: BLE001 - degrade gracefully
            logger.debug("Rate limit check skipped (%s): %s", bucket, e)
            return

    return _dependency
