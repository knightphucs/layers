"""
LAYERS - Social Spark Tests
===========================================
Covers boost, wave, and synchronicity.

Run:
    cd backend
    pytest tests/test_social_spark.py -v
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import UUID

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, async_sessionmaker,
)
from sqlalchemy import select

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.location import Location, LayerType
from app.models.artifact import Artifact, ContentType, Visibility, ArtifactStatus
from app.models.social_spark import (
    ArtifactBoost,
    Wave,
    ArtifactDiscovery,
    SynchronicityEvent,
)
from app.services.social_spark_service import (
    SocialSparkService,
    _wave_cooldown,
    BOOST_DAILY_LIMIT,
)


# =============================================================================
# Coordinates (HCMC)
# =============================================================================

BEN_THANH = (10.7725, 106.6980)
NEARBY_30M = (10.7727, 106.6981)
FAR_AWAY = (10.7798, 106.6990)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="function", autouse=True)
def clear_wave_cooldown():
    _wave_cooldown.clear()
    yield
    _wave_cooldown.clear()


@pytest.fixture(scope="function")
async def setup_db():
    engine = create_async_engine(settings.test_database_url, pool_pre_ping=True)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )
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


# =============================================================================
# Helpers
# =============================================================================

USER_A = {"email": "alice@layers.app", "username": "alicesp", "password": "Pass123!"}
USER_B = {"email": "bob@layers.app",   "username": "bobsp",   "password": "Pass123!"}


async def register_and_login(client: AsyncClient, user_data: dict):
    resp = await client.post("/api/v1/auth/register", json=user_data)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    if "user" in body:
        user_id = body["user"]["id"]
    else:
        me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        user_id = me.json()["id"]
    return user_id, {"Authorization": f"Bearer {body['access_token']}"}


async def seed_artifact(session_factory, creator_id: str) -> str:
    """Create a location + public artifact directly. Returns artifact_id."""
    async with session_factory() as db:
        loc = Location(
            geom=f"SRID=4326;POINT({BEN_THANH[1]} {BEN_THANH[0]})",
            latitude=BEN_THANH[0],
            longitude=BEN_THANH[1],
            layer=LayerType.LIGHT,
            category="GENERAL",
            name="Test Spot",
            created_by=UUID(creator_id),
        )
        db.add(loc)
        await db.commit()
        await db.refresh(loc)

        art = Artifact(
            location_id=loc.id,
            user_id=UUID(creator_id),
            content_type=ContentType.LETTER,
            payload={"text": "A memory left here"},
            visibility=Visibility.PUBLIC,
            layer="LIGHT",
            status=ArtifactStatus.ACTIVE,
        )
        db.add(art)
        await db.commit()
        await db.refresh(art)
        return str(art.id)


# =============================================================================
# 📡 BOOST
# =============================================================================

class TestSignalBoost:
    @pytest.mark.asyncio
    async def test_boost_artifact_succeeds(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        art_id = await seed_artifact(setup_db, a_id)

        resp = await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/boost", headers=a_auth
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["artifact_id"] == art_id
        assert body["booster_id"] == a_id
        assert body["boost_radius_meters"] == 2000

    @pytest.mark.asyncio
    async def test_boost_quota_decrements(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        art_id = await seed_artifact(setup_db, a_id)

        before = await async_client.get("/api/v1/spark/boosts/quota", headers=a_auth)
        assert before.json()["remaining"] == BOOST_DAILY_LIMIT

        await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/boost", headers=a_auth
        )

        after = await async_client.get("/api/v1/spark/boosts/quota", headers=a_auth)
        assert after.json()["used_today"] == 1
        assert after.json()["remaining"] == BOOST_DAILY_LIMIT - 1

    @pytest.mark.asyncio
    async def test_duplicate_active_boost_conflicts(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        art_id = await seed_artifact(setup_db, a_id)

        r1 = await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/boost", headers=a_auth
        )
        assert r1.status_code == 201
        r2 = await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/boost", headers=a_auth
        )
        assert r2.status_code == 409

    @pytest.mark.asyncio
    async def test_daily_limit_enforced(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        # Need BOOST_DAILY_LIMIT + 1 distinct artifacts
        art_ids = [await seed_artifact(setup_db, a_id)
                   for _ in range(BOOST_DAILY_LIMIT + 1)]

        for i in range(BOOST_DAILY_LIMIT):
            r = await async_client.post(
                f"/api/v1/spark/artifacts/{art_ids[i]}/boost", headers=a_auth
            )
            assert r.status_code == 201

        # One more → 429
        over = await async_client.post(
            f"/api/v1/spark/artifacts/{art_ids[-1]}/boost", headers=a_auth
        )
        assert over.status_code == 429

    @pytest.mark.asyncio
    async def test_boosted_nearby_returns_within_radius(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        art_id = await seed_artifact(setup_db, a_id)
        await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/boost", headers=a_auth
        )

        # Query from ~800m away — well within 2000m boost radius
        resp = await async_client.get(
            "/api/v1/spark/boosted-nearby",
            headers=a_auth,
            params={"lat": FAR_AWAY[0], "lng": FAR_AWAY[1]},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["artifact_id"] == art_id


# =============================================================================
# 👋 WAVE
# =============================================================================

class TestAnonymousWave:
    @pytest.mark.asyncio
    async def test_wave_creates_and_returns_count(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)

        resp = await async_client.post(
            "/api/v1/spark/wave",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert "wave_id" in body
        assert body["others_waving_nearby"] == 0
        assert body["waved_back"] is False

    @pytest.mark.asyncio
    async def test_second_wave_sees_first(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)

        await async_client.post(
            "/api/v1/spark/wave",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        # B waves 30m away — should see A's wave
        resp = await async_client.post(
            "/api/v1/spark/wave",
            headers=b_auth,
            json={"latitude": NEARBY_30M[0], "longitude": NEARBY_30M[1]},
        )
        body = resp.json()
        assert body["others_waving_nearby"] == 1
        assert body["waved_back"] is True

    @pytest.mark.asyncio
    async def test_wave_cooldown_enforced(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)

        r1 = await async_client.post(
            "/api/v1/spark/wave",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        assert r1.status_code == 201
        r2 = await async_client.post(
            "/api/v1/spark/wave",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        assert r2.status_code == 429

    @pytest.mark.asyncio
    async def test_waves_nearby_is_anonymous_count(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)

        await async_client.post(
            "/api/v1/spark/wave",
            headers=b_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        resp = await async_client.get(
            "/api/v1/spark/waves/nearby",
            headers=a_auth,
            params={"lat": BEN_THANH[0], "lng": BEN_THANH[1]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        # No identity fields anywhere
        assert "sender_id" not in str(body)
        assert "user_id" not in str(body)


# =============================================================================
# ✨ SYNCHRONICITY
# =============================================================================

class TestSynchronicity:
    @pytest.mark.asyncio
    async def test_first_discovery_no_sync(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        art_id = await seed_artifact(setup_db, a_id)

        resp = await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/discover", headers=a_auth, json={}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_new_discovery"] is True
        assert body["synchronicity"] is None

    @pytest.mark.asyncio
    async def test_repeat_discovery_is_noop(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        art_id = await seed_artifact(setup_db, a_id)

        await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/discover", headers=a_auth, json={}
        )
        resp = await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/discover", headers=a_auth, json={}
        )
        body = resp.json()
        assert body["is_new_discovery"] is False
        assert body["synchronicity"] is None

    @pytest.mark.asyncio
    async def test_two_users_within_window_spark_sync(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)
        art_id = await seed_artifact(setup_db, a_id)

        # A discovers
        r_a = await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/discover", headers=a_auth, json={}
        )
        assert r_a.json()["synchronicity"] is None

        # B discovers moments later → synchronicity
        r_b = await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/discover", headers=b_auth, json={}
        )
        body = r_b.json()
        assert body["is_new_discovery"] is True
        assert body["synchronicity"] is not None
        assert body["message"] == "Someone else felt this too ✨"

    @pytest.mark.asyncio
    async def test_sync_event_persisted_canonical(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)
        art_id = await seed_artifact(setup_db, a_id)

        await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/discover", headers=a_auth, json={}
        )
        await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/discover", headers=b_auth, json={}
        )

        async with setup_db() as db:
            result = await db.execute(select(SynchronicityEvent))
            events = result.scalars().all()
            assert len(events) == 1
            ev = events[0]
            # Canonical: smaller UUID first
            smaller, bigger = sorted([a_id, b_id])
            assert str(ev.user_a_id) == smaller
            assert str(ev.user_b_id) == bigger

    @pytest.mark.asyncio
    async def test_sync_grows_connection(self, setup_db, async_client):
        """Synchronicity should call ConnectionService.record_interaction."""
        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)
        art_id = await seed_artifact(setup_db, a_id)

        await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/discover", headers=a_auth, json={}
        )
        await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/discover", headers=b_auth, json={}
        )

        # A Connection row should now exist with interaction_count >= 1
        from app.models.connection import Connection
        async with setup_db() as db:
            result = await db.execute(select(Connection))
            conns = result.scalars().all()
            assert len(conns) == 1
            assert conns[0].interaction_count >= 1

    @pytest.mark.asyncio
    async def test_list_synchronicities(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)
        art_id = await seed_artifact(setup_db, a_id)

        await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/discover", headers=a_auth, json={}
        )
        await async_client.post(
            f"/api/v1/spark/artifacts/{art_id}/discover", headers=b_auth, json={}
        )

        for auth in (a_auth, b_auth):
            resp = await async_client.get(
                "/api/v1/spark/synchronicities", headers=auth
            )
            assert resp.status_code == 200
            assert resp.json()["total"] == 1
