"""
LAYERS - Security Hardening
==========================================
Everything that turns the dev server into something safe to point real users at.
Grouped here so main.py stays clean and there's ONE place to audit before launch.

What this does:
  1. get_cors_origins()          — settings-driven allowlist; strips "*" in prod
  2. SecurityHeadersMiddleware   — X-Frame-Options, nosniff, HSTS, referrer policy
  3. setup_security(app)         — wires headers + TrustedHost (+ optional HTTPS redirect)
  4. validate_production_secrets — refuses to boot prod with default/leaked secrets

Design principle: SAFE BY DEFAULT IN PRODUCTION, CONVENIENT IN DEV. Everything is
gated on settings.debug. When debug=False we assume "real users are watching" and
lock things down; when debug=True we stay permissive so local work isn't annoying.
"""

import logging
from typing import List

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


# Origins we always allow in local development.
DEFAULT_DEV_ORIGINS = [
    "http://localhost:3000",    # React web dev
    "http://localhost:19006",   # Expo web
    "http://localhost:8081",    # Expo / Metro
    "exp://localhost:8081",     # Expo Go
]

# Values that must NEVER survive into production.
INSECURE_SECRET_VALUES = {
    "change-me-in-production",
    "change-me-in-production-123456789",
    "your-super-secret-key-change-in-production-123456789",
    "jwt-secret-change-me",
    "another-super-secret-key-for-jwt-tokens",
    "secret",
    "",
}


def get_cors_origins(settings) -> List[str]:
    """Resolve the CORS allowlist from settings.

    settings.cors_origins may be a comma-separated string ("https://a,https://b")
    or a list. If unset, fall back to the dev origins. In production ("debug=False")
    the "*" wildcard is stripped — you must name your real domains.
    """
    raw = getattr(settings, "cors_origins", None)
    if raw:
        origins = ([o.strip() for o in raw.split(",") if o.strip()]
                   if isinstance(raw, str) else [str(o).strip() for o in raw])
    else:
        origins = list(DEFAULT_DEV_ORIGINS)

    if not getattr(settings, "debug", False):
        stripped = [o for o in origins if o != "*"]
        if len(stripped) != len(origins):
            logger.warning("Removed '*' from CORS origins in production mode.")
        origins = stripped or list(DEFAULT_DEV_ORIGINS)

    return origins


def get_allowed_hosts(settings) -> List[str]:
    """Hostnames TrustedHostMiddleware will accept. Dev allows all."""
    raw = getattr(settings, "allowed_hosts", None)
    if getattr(settings, "debug", False):
        return ["*"]
    if raw:
        return ([h.strip() for h in raw.split(",") if h.strip()]
                if isinstance(raw, str) else [str(h).strip() for h in raw])
    return ["*"]  # explicit opt-in required; warned about in validation


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard hardening headers to every response.

    HSTS is only sent when NOT in debug, because forcing HTTPS on localhost
    breaks local testing.
    """

    def __init__(self, app, debug: bool = False):
        super().__init__(app)
        self.debug = debug

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"
        if not self.debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


def setup_security(app, settings) -> None:
    """Register hardening middleware. Call from main.py after creating `app`
    and BEFORE include_router (middleware wraps outermost-first)."""
    app.add_middleware(SecurityHeadersMiddleware, debug=getattr(settings, "debug", False))

    # Trusted hosts (prod only — dev accepts anything).
    if not getattr(settings, "debug", False):
        try:
            from starlette.middleware.trustedhost import TrustedHostMiddleware
            app.add_middleware(TrustedHostMiddleware, allowed_hosts=get_allowed_hosts(settings))
        except Exception as e:  # noqa: BLE001
            logger.warning("TrustedHostMiddleware not added: %s", e)

        # Optional HTTPS redirect (enable via settings.force_https=True).
        if getattr(settings, "force_https", False):
            try:
                from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
                app.add_middleware(HTTPSRedirectMiddleware)
            except Exception as e:  # noqa: BLE001
                logger.warning("HTTPSRedirectMiddleware not added: %s", e)

    logger.info("🔒 Security middleware registered (debug=%s)", getattr(settings, "debug", False))


def validate_production_secrets(settings) -> List[str]:
    """Return a list of security problems. Empty list = all good.

    In production these should be FATAL (raise on startup). In dev they're
    just warnings so you know what to fix before shipping.
    """
    problems: List[str] = []
    debug = getattr(settings, "debug", False)
    if debug:
        return problems  # nothing to enforce locally

    if getattr(settings, "secret_key", "") in INSECURE_SECRET_VALUES:
        problems.append("SECRET_KEY is a default/insecure value")
    if getattr(settings, "jwt_secret_key", "") in INSECURE_SECRET_VALUES:
        problems.append("JWT_SECRET_KEY is a default/insecure value")

    # Inspect the RAW setting (get_cors_origins defensively strips "*", so we
    # must check what the operator actually configured to warn them).
    raw_cors = getattr(settings, "cors_origins", None)
    raw_cors_list = (
        [o.strip() for o in raw_cors.split(",")] if isinstance(raw_cors, str)
        else [str(o).strip() for o in raw_cors] if raw_cors else []
    )
    if "*" in raw_cors_list:
        problems.append("CORS still allows '*' in production")

    if "*" in get_allowed_hosts(settings):
        problems.append("ALLOWED_HOSTS is unset ('*') — name your real domains")
    if len(getattr(settings, "jwt_secret_key", "")) < 32:
        problems.append("JWT_SECRET_KEY is shorter than 32 chars (weak)")

    return problems
