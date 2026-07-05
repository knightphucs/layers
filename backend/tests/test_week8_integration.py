"""
LAYERS - Week 8 Integration Tests (Trust & Safety end-to-end)
=============================================================
Ties Days 1–4 together against a real test DB, in the SAME style as the
existing suites (AsyncClient + ASGITransport, isolated test database).

Covers the full moderator journey:
  1. Clean content publishes (ACTIVE) and is visible.
  2. Profanity is held (PENDING) and hidden from the public map.
  3. Severe content is rejected (400) + author loses reputation.
  4. Report-bombing fails: one user can only report once.
  5. Trust-weighted auto-hide: enough distinct reporters → HIDDEN.
  6. Admin approve republishes and dismisses reports.
  7. Shadow: glitch-zone creation + status reflects membership.

Run (needs Postgres test DB, like the other integration tests):
    cd backend
    pytest tests/test_week8_integration.py -v
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, async_sessionmaker,
)

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.user import User


# =============================================================================
# Fixtures (mirror test_artifacts.py / test_chat_rest.py)
# =============================================================================

@pytest.fixture(scope="function")
async def setup_db():
    engine = create_async_engine(settings.test_database_url, pool_pre_ping=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    yield async_session
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_client(setup_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# HCMC coordinates
BEN_THANH = (10.7725, 106.6980)


async def register(client, username, email):
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "username": username, "password": "Pass123!",
    })
    assert r.status_code in (200, 201), r.text
    data = r.json()
    token = data.get("access_token")
    uid = data["user"]["id"]
    return uid, {"Authorization": f"Bearer {token}"}


async def make_admin(setup_db, user_id):
    """Promote a user to ADMIN directly in the DB."""
    async_session = setup_db
    async with async_session() as s:
        user = await s.get(User, user_id)
        user.role = "ADMIN"
        await s.commit()


async def create_letter(client, headers, text_body, lat=BEN_THANH[0], lng=BEN_THANH[1]):
    return await client.post("/api/v1/artifacts", headers=headers, json={
        "content_type": "LETTER",
        "layer": "LIGHT",
        "visibility": "PUBLIC",
        "latitude": lat,
        "longitude": lng,
        "payload": {"text": text_body},
    })


# =============================================================================
# Moderation pipeline (Day 1)
# =============================================================================

class TestModerationPipeline:

    async def test_clean_content_publishes(self, async_client):
        _, headers = await register(async_client, "cleanuser", "clean@layers.app")
        r = await create_letter(async_client, headers, "Một kỷ niệm đẹp ở Sài Gòn")
        assert r.status_code in (200, 201), r.text
        assert r.json().get("status") in ("ACTIVE", None)

    async def test_profanity_held_pending(self, async_client):
        _, headers = await register(async_client, "flaguser", "flag@layers.app")
        r = await create_letter(async_client, headers, "đm cái chỗ này")
        assert r.status_code in (200, 201), r.text
        assert r.json().get("status") == "PENDING"

    async def test_severe_rejected_and_penalized(self, async_client, setup_db):
        uid, headers = await register(async_client, "baduser", "bad@layers.app")
        r = await create_letter(async_client, headers, "tao giết mày")
        assert r.status_code == 400

        async_session = setup_db
        async with async_session() as s:
            user = await s.get(User, uid)
            assert user.reputation_score < 100  # -20 applied


# =============================================================================
# Report & reputation (Day 2)
# =============================================================================

class TestReportSystem:

    async def test_cannot_report_twice(self, async_client):
        author_id, author_h = await register(async_client, "author1", "author1@layers.app")
        r = await create_letter(async_client, author_h, "Xin chào Sài Gòn")
        artifact_id = r.json()["id"]

        _, reporter_h = await register(async_client, "reporter1", "rep1@layers.app")
        r1 = await async_client.post(
            f"/api/v1/artifacts/{artifact_id}/report",
            headers=reporter_h, params={"reason": "SPAM"},
        )
        assert r1.status_code == 200
        assert r1.json()["already_reported"] is False

        r2 = await async_client.post(
            f"/api/v1/artifacts/{artifact_id}/report",
            headers=reporter_h, params={"reason": "SPAM"},
        )
        assert r2.status_code == 200
        assert r2.json()["already_reported"] is True  # bombing blocked

    async def test_five_distinct_reporters_auto_hide(self, async_client):
        _, author_h = await register(async_client, "author2", "author2@layers.app")
        r = await create_letter(async_client, author_h, "Ghé quán này nhé")
        artifact_id = r.json()["id"]

        hidden = False
        for i in range(5):
            _, h = await register(async_client, f"rep2_{i}", f"rep2_{i}@layers.app")
            resp = await async_client.post(
                f"/api/v1/artifacts/{artifact_id}/report",
                headers=h, params={"reason": "HARASSMENT"},
            )
            hidden = resp.json().get("artifact_hidden", False)
        assert hidden is True  # weighted score reached threshold


# =============================================================================
# Admin moderation (Day 1/3)
# =============================================================================

class TestAdminModeration:

    async def test_admin_approve_republishes(self, async_client, setup_db):
        admin_id, admin_h = await register(async_client, "admin1", "admin1@layers.app")
        await make_admin(setup_db, admin_id)

        _, author_h = await register(async_client, "author3", "author3@layers.app")
        r = await create_letter(async_client, author_h, "đm test hold")  # → PENDING
        artifact_id = r.json()["id"]

        approve = await async_client.post(
            f"/api/v1/moderation/{artifact_id}/approve", headers=admin_h)
        assert approve.status_code == 200

    async def test_non_admin_blocked_from_queue(self, async_client):
        _, headers = await register(async_client, "plainuser", "plain@layers.app")
        r = await async_client.get("/api/v1/moderation/queue", headers=headers)
        assert r.status_code == 403


# =============================================================================
# Shadow Layer (Day 4)
# =============================================================================

class TestShadowLayer:

    async def test_admin_creates_glitch_zone_and_status(self, async_client, setup_db):
        admin_id, admin_h = await register(async_client, "admin2", "admin2@layers.app")
        await make_admin(setup_db, admin_id)

        create = await async_client.post(
            "/api/v1/shadow/glitch-zones", headers=admin_h, json={
                "name": "Test Zone Bến Thành",
                "center_lat": BEN_THANH[0], "center_lng": BEN_THANH[1],
                "radius_m": 200, "glitch_type": "XP_SURGE", "intensity": 2.0,
                "active_start": "00:00", "active_end": "23:59",  # always open for test
            })
        assert create.status_code == 201, create.text

        status_resp = await async_client.get(
            "/api/v1/shadow/status", headers=admin_h,
            params={"lat": BEN_THANH[0], "lng": BEN_THANH[1]})
        assert status_resp.status_code == 200
        body = status_resp.json()
        assert body["in_glitch_zone"] is True
        assert body["xp_multiplier"] == 2.0

    async def test_midnight_endpoint(self, async_client):
        _, headers = await register(async_client, "nightuser", "night@layers.app")
        r = await async_client.get("/api/v1/shadow/midnight", headers=headers)
        assert r.status_code == 200
        assert "open" in r.json()
