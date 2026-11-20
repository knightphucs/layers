"""
LAYERS - Request Timing Middleware
==================================================
You can't fix what you can't see. This middleware:

  1. Measures wall-clock duration of every request
  2. Adds an `X-Response-Time` header (visible in the mobile network tab
     and curl -i — free profiling on device)
  3. Logs a WARNING for anything slower than SLOW_THRESHOLD_MS —
     these warnings are the Day 4 hit list.

Overhead: one perf_counter() pair per request (~nanoseconds). Safe to keep
in production — Sentry (Week 10) will pick the warnings up automatically.

WIRING (app/main.py) — see SETUP.md:
    from app.core.timing import TimingMiddleware
    app.add_middleware(TimingMiddleware)

NOTE on ordering: Starlette wraps middlewares so the LAST added is the
OUTERMOST. Add TimingMiddleware LAST so it measures the full stack
(rate limiting + CORS + security headers included).
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("layers.timing")

# Endpoints slower than this get a WARNING log. Tune per taste;
# geo-queries on a warm cache should sit well under it.
SLOW_THRESHOLD_MS = 300

# Paths we never care about
EXCLUDED_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"

        path = request.url.path
        if path not in EXCLUDED_PATHS:
            if duration_ms > SLOW_THRESHOLD_MS:
                logger.warning(
                    "🐌 SLOW %s %s → %d in %.1fms",
                    request.method,
                    path,
                    response.status_code,
                    duration_ms,
                )
            else:
                logger.debug(
                    "%s %s → %d in %.1fms",
                    request.method,
                    path,
                    response.status_code,
                    duration_ms,
                )

        return response
