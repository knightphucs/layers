"""
LAYERS - Security Hardening tests
Runnable without DB. Run: pytest tests/test_security_hardening.py -v
"""

import pytest

from app.core.security_hardening import (
    get_cors_origins,
    get_allowed_hosts,
    validate_production_secrets,
    SecurityHeadersMiddleware,
    DEFAULT_DEV_ORIGINS,
)


class FakeSettings:
    def __init__(self, **kw):
        self.debug = kw.get("debug", True)
        self.cors_origins = kw.get("cors_origins", None)
        self.allowed_hosts = kw.get("allowed_hosts", None)
        self.secret_key = kw.get("secret_key", "change-me-in-production")
        self.jwt_secret_key = kw.get("jwt_secret_key", "jwt-secret-change-me")
        self.force_https = kw.get("force_https", False)


class TestCorsResolution:
    def test_dev_defaults_when_unset(self):
        origins = get_cors_origins(FakeSettings(debug=True))
        assert origins == DEFAULT_DEV_ORIGINS

    def test_string_parsing(self):
        s = FakeSettings(debug=False, cors_origins="https://layers.app, https://www.layers.app")
        assert get_cors_origins(s) == ["https://layers.app", "https://www.layers.app"]

    def test_wildcard_stripped_in_production(self):
        s = FakeSettings(debug=False, cors_origins="https://layers.app,*")
        origins = get_cors_origins(s)
        assert "*" not in origins
        assert "https://layers.app" in origins

    def test_wildcard_allowed_in_dev(self):
        s = FakeSettings(debug=True, cors_origins="http://localhost:3000,*")
        assert "*" in get_cors_origins(s)

    def test_list_input(self):
        s = FakeSettings(debug=False, cors_origins=["https://a.com", "https://b.com"])
        assert get_cors_origins(s) == ["https://a.com", "https://b.com"]


class TestAllowedHosts:
    def test_dev_allows_all(self):
        assert get_allowed_hosts(FakeSettings(debug=True)) == ["*"]

    def test_prod_uses_configured(self):
        s = FakeSettings(debug=False, allowed_hosts="layers.app,api.layers.app")
        assert get_allowed_hosts(s) == ["layers.app", "api.layers.app"]


class TestSecretValidation:
    def test_dev_never_complains(self):
        assert validate_production_secrets(FakeSettings(debug=True)) == []

    def test_prod_flags_default_secrets(self):
        s = FakeSettings(debug=False, cors_origins="https://layers.app",
                         allowed_hosts="layers.app")
        problems = validate_production_secrets(s)
        assert any("SECRET_KEY" in p for p in problems)
        assert any("JWT_SECRET_KEY" in p for p in problems)

    def test_prod_flags_wildcard_cors(self):
        s = FakeSettings(debug=False, cors_origins="*",
                         allowed_hosts="layers.app",
                         secret_key="a" * 40, jwt_secret_key="b" * 40)
        problems = validate_production_secrets(s)
        assert any("CORS" in p for p in problems)

    def test_prod_clean_config_passes(self):
        s = FakeSettings(
            debug=False,
            cors_origins="https://layers.app",
            allowed_hosts="layers.app",
            secret_key="x" * 48,
            jwt_secret_key="y" * 48,
        )
        assert validate_production_secrets(s) == []

    def test_short_jwt_flagged(self):
        s = FakeSettings(debug=False, cors_origins="https://layers.app",
                         allowed_hosts="layers.app",
                         secret_key="x" * 48, jwt_secret_key="short")
        assert any("shorter than 32" in p for p in validate_production_secrets(s))


class TestSecurityHeaders:
    def _app(self, debug):
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route

        async def home(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", home)])
        app.add_middleware(SecurityHeadersMiddleware, debug=debug)
        return app

    def test_headers_present(self):
        from starlette.testclient import TestClient
        client = TestClient(self._app(debug=False))
        r = client.get("/")
        assert r.headers["X-Content-Type-Options"] == "nosniff"
        assert r.headers["X-Frame-Options"] == "DENY"
        assert "Strict-Transport-Security" in r.headers

    def test_hsts_absent_in_debug(self):
        from starlette.testclient import TestClient
        client = TestClient(self._app(debug=True))
        r = client.get("/")
        assert "Strict-Transport-Security" not in r.headers
        assert r.headers["X-Frame-Options"] == "DENY"  # others still present
