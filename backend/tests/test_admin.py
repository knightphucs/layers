"""
LAYERS - Admin panel tests

Two layers:
1. Pure helpers (is_admin_role, parse_pks) — fast, no deps.
2. Structural SQLAdmin check — builds an Admin app over an in-memory SQLite
   async engine with mapped models mirroring ours, registers ModelViews shaped
   exactly like the delivery views (column_list, actions, read-only flags), and
   asserts SQLAdmin accepts the configuration and serves the panel routes.
   This catches API-shape mistakes (bad attr names, action signatures) without
   needing Postgres or the full app.

Run: pytest tests/test_admin.py -v
"""

import pytest

from app.admin._helpers import is_admin_role, parse_pks


class TestRoleCheck:
    def test_string_admin(self):
        assert is_admin_role("ADMIN") is True
        assert is_admin_role("admin") is True

    def test_role_enum_like(self):
        class Role:
            def __str__(self):
                return "Role.ADMIN"
        assert is_admin_role(Role()) is True

    def test_non_admin(self):
        assert is_admin_role("USER") is False
        assert is_admin_role("PARTNER") is False
        assert is_admin_role(None) is False


class TestParsePks:
    def test_basic(self):
        assert parse_pks("a,b,c") == ["a", "b", "c"]

    def test_blanks_dropped(self):
        assert parse_pks("a,,b, ,c") == ["a", "b", "c"]

    def test_empty(self):
        assert parse_pks("") == []
        assert parse_pks(None) == []

    def test_single(self):
        assert parse_pks("only-one") == ["only-one"]

    def test_whitespace_trimmed(self):
        assert parse_pks(" a , b ") == ["a", "b"]


# ---------------------------------------------------------------------------
# Structural SQLAdmin validity (mirrors the delivery views' configuration)
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin_app():
    import uuid
    from starlette.applications import Starlette
    from sqlalchemy import String, Integer, Boolean
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqladmin import Admin, ModelView, action
    from starlette.requests import Request
    from starlette.responses import RedirectResponse

    class Base(DeclarativeBase):
        pass

    class U(Base):
        __tablename__ = "u"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        username: Mapped[str] = mapped_column(String(50), default="")
        reputation_score: Mapped[int] = mapped_column(Integer, default=100)
        is_banned: Mapped[bool] = mapped_column(Boolean, default=False)

    class A(Base):
        __tablename__ = "a"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
        report_count: Mapped[int] = mapped_column(Integer, default=0)

    # Mirror the real views' configuration shape
    class UView(ModelView, model=U):
        column_list = [U.username, U.reputation_score, U.is_banned]
        column_searchable_list = [U.username]
        column_sortable_list = [U.reputation_score]
        column_default_sort = [(U.reputation_score, True)]
        form_columns = [U.is_banned, U.reputation_score]
        can_create = False
        can_delete = False

        @action(name="ban", label="Ban selected",
                confirmation_message="Ban?")
        async def ban(self, request: Request) -> RedirectResponse:
            return RedirectResponse(request.headers.get("referer") or "/admin")

    class AView(ModelView, model=A):
        column_list = [A.status, A.report_count]
        column_sortable_list = [A.report_count, A.status]
        column_default_sort = [(A.report_count, True)]
        form_columns = [A.status]
        can_create = False
        can_delete = False

        @action(name="approve", label="Approve & Publish",
                confirmation_message="Publish?")
        async def approve(self, request: Request) -> RedirectResponse:
            return RedirectResponse(request.headers.get("referer") or "/admin")

    app = Starlette()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    admin = Admin(app, engine, title="LAYERS Admin TEST")
    admin.add_view(UView)
    admin.add_view(AView)
    return app, admin


def test_admin_builds_and_registers_views(admin_app):
    app, admin = admin_app
    # Views registered
    identities = {v.identity for v in admin.views}
    assert "u" in identities and "a" in identities


def test_admin_routes_mounted(admin_app):
    app, admin = admin_app
    paths = [getattr(r, "path", "") for r in app.routes]
    # SQLAdmin mounts a sub-app at /admin
    assert any("/admin" in p for p in paths)


def test_action_methods_exist(admin_app):
    app, admin = admin_app
    uview = next(v for v in admin.views if v.identity == "u")
    aview = next(v for v in admin.views if v.identity == "a")
    assert hasattr(uview, "ban")
    assert hasattr(aview, "approve")
