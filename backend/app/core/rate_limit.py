"""
LAYERS - Rate Limiting Middleware
Protect API from abuse with request rate limiting
"""

import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio


class RateLimiter:
    """
    Simple in-memory rate limiter.
    
    For production, use Redis-based rate limiting for distributed systems.
    """
    
    def __init__(self):
        # Store: {client_ip: [(timestamp, endpoint), ...]}
        self.requests: Dict[str, list] = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def is_allowed(
        self, 
        client_ip: str, 
        endpoint: str,
        max_requests: int = 60,
        window_seconds: int = 60
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
        async with self.lock:
            now = time.time()
            key = f"{client_ip}:{endpoint}"
            
            # Clean old requests outside window
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < window_seconds
            ]
            
            # Check if under limit
            current_count = len(self.requests[key])
            
            if current_count >= max_requests:
                return False, 0
            
            # Add current request
            self.requests[key].append(now)
            
            return True, max_requests - current_count - 1
    
    def cleanup(self):
        """Remove stale entries (call periodically)"""
        now = time.time()
        for key in list(self.requests.keys()):
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < 3600  # Keep last hour
            ]
            if not self.requests[key]:
                del self.requests[key]


# Global rate limiter instance
rate_limiter = RateLimiter()


# Rate limit configurations per endpoint type
RATE_LIMITS = {
    # Auth endpoints (stricter limits)
    "/api/v1/auth/register": (5, 300),      # 5 per 5 minutes
    "/api/v1/auth/login": (10, 300),        # 10 per 5 minutes
    "/api/v1/auth/password-reset": (3, 300), # 3 per 5 minutes
    
    # General API (more lenient)
    "default": (60, 60),  # 60 per minute
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to apply rate limiting to all requests.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get forwarded IP if behind proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        # Determine rate limit for endpoint
        endpoint = request.url.path
        max_requests, window = RATE_LIMITS.get(
            endpoint, 
            RATE_LIMITS["default"]
        )
        
        # Check rate limit
        allowed, remaining = await rate_limiter.is_allowed(
            client_ip, 
            endpoint,
            max_requests,
            window
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(window)}
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(window)
        
        return response


def get_rate_limiter() -> RateLimiter:
    """Dependency to get rate limiter instance"""
    return rate_limiter
