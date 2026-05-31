"""
LAYERS - Rate Limiting Middleware
=================================
Protect API from abuse with request rate limiting.
Redis-backed sliding-window rate limiter with an in-memory fallback.

WHY REDIS: with more than one worker/instance, an in-memory limiter counts
per-process, so the effective limit multiplies by the worker count and resets
on every restart. Redis centralizes counters across all workers.

Features:
- Falls back to in-memory automatically if Redis is unavailable (dev-friendly).
- Returns a JSONResponse(429) instead of raising HTTPException inside the
  middleware to prevent 500 errors from BaseHTTPMiddleware.
- Supports endpoint exemptions (e.g., /health, /docs).
"""

import asyncio
import time
import uuid
from collections import defaultdict
from typing import Dict, List, Tuple

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Ensure you have this function in your project, or replace it with your Redis connection logic
from app.core.redis_client import get_optional_redis


# Rate limit configurations per endpoint type: (max_requests, window_seconds)
RATE_LIMITS = {
    # Auth endpoints (stricter limits)
    "/api/v1/auth/register": (5, 300),        # 5 per 5 minutes
    "/api/v1/auth/login": (10, 300),          # 10 per 5 minutes
    "/api/v1/auth/password-reset": (3, 300),  # 3 per 5 minutes

    # General API (more lenient)
    "default": (60, 60),                      # 60 per minute
}

# Paths never rate limited (monitoring, docs, websockets handshake on /ws).
_EXEMPT_EXACT = {"/", "/openapi.json"}
_EXEMPT_PREFIXES = ("/health", "/api/v1/health", "/docs", "/redoc", "/ws")


class RateLimiter:
    """
    Sliding-window rate limiter.

    Uses a Redis sorted set per (ip, endpoint) as a sliding window log:
      - ZREMRANGEBYSCORE trims timestamps older than the window
      - ZCARD counts requests currently in the window
      - ZADD records this request; EXPIRE keeps the key tidy
      
    Falls back to a per-process in-memory log if Redis is unavailable.
    """

    def __init__(self):
        # Fallback in-memory store: {f"{ip}:{endpoint}": [timestamp, ...]}
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.lock = asyncio.Lock()

    async def is_allowed(
        self,
        client_ip: str,
        endpoint: str,
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> Tuple[bool, int]:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            client_ip: Client's IP address
            endpoint: API endpoint being accessed
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        client = get_optional_redis()
        if client is not None:
            try:
                return await self._redis_is_allowed(
                    client, client_ip, endpoint, max_requests, window_seconds
                )
            except Exception:  # noqa: BLE001 - never let limiter errors break requests
                pass  # fall through to in-memory fallback
                
        return await self._memory_is_allowed(
            client_ip, endpoint, max_requests, window_seconds
        )

    async def _redis_is_allowed(
        self, client, client_ip: str, endpoint: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int]:
        key = f"ratelimit:{client_ip}:{endpoint}"
        now = time.time()
        window_start = now - window_seconds
        member = f"{now}:{uuid.uuid4().hex}"

        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)                       # count BEFORE adding this request
        pipe.zadd(key, {member: now})
        pipe.expire(key, window_seconds)
        results = await pipe.execute()

        current_count = int(results[1])
        if current_count >= max_requests:
            # roll back the request we optimistically recorded
            await client.zrem(key, member)
            return False, 0
            
        remaining = max_requests - current_count - 1
        return True, max(remaining, 0)

    async def _memory_is_allowed(
        self, client_ip: str, endpoint: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int]:
        """In-memory rate limiting logic (Fallback)"""
        async with self.lock:
            now = time.time()
            key = f"{client_ip}:{endpoint}"
            
            # Clean old requests outside window
            self.requests[key] = [
                t for t in self.requests[key] if now - t < window_seconds
            ]
            
            # Check if under limit
            current_count = len(self.requests[key])
            if current_count >= max_requests:
                return False, 0
                
            # Add current request
            self.requests[key].append(now)
            return True, max_requests - current_count - 1

    def cleanup(self):
        """Remove stale in-memory entries (call periodically if desired)."""
        now = time.time()
        for key in list(self.requests.keys()):
            self.requests[key] = [
                t for t in self.requests[key] if now - t < 3600  # Keep last hour
            ]
            if not self.requests[key]:
                del self.requests[key]


# Global rate limiter instance
rate_limiter = RateLimiter()


def _is_exempt(path: str) -> bool:
    """Check if the path is exempt from rate limiting."""
    if path in _EXEMPT_EXACT:
        return True
    return path.startswith(_EXEMPT_PREFIXES)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to apply rate limiting to all non-exempt HTTP requests.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Skip rate limiting for exempt endpoints
        if _is_exempt(path):
            return await call_next(request)

        # Get client IP (respect reverse proxy)
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        # Determine rate limit for endpoint
        max_requests, window = RATE_LIMITS.get(path, RATE_LIMITS["default"])
        
        # Check rate limit
        allowed, remaining = await rate_limiter.is_allowed(
            client_ip, path, max_requests, window
        )

        if not allowed:
            # Use JSONResponse instead of raising HTTPException to prevent Starlette 500 error
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."},
                headers={
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Window": str(window),
                },
            )

        # Process request normally and add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(window)
        
        return response


def get_rate_limiter() -> RateLimiter:
    """Dependency to get the rate limiter instance."""
    return rate_limiter