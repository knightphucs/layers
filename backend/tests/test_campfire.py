"""
LAYERS - Campfire Tests
=======================================
Tests for the campfire system:
  - find-or-create (proximity, rate limit, idempotency)
  - join (proximity check, idempotency)
  - leave
  - nearby (map beacons)
  - members (with online status)
  - expiry (lazy auto-close on read, bulk close utility)

Run:
    cd backend
    pytest tests/test_campfire.py -v
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
from app.services.chat_service import (
    ChatService,
    _campfire_create_history,
    CAMPFIRE_LIFETIME_HOURS,
)
from app.models.chat import (
    ChatRoom,
    ChatRoomType,
    ChatRoomStatus,
    CampfireMember,
)


# =============================================================================
# Coordinates (Ho Chi Minh City)
# =============================================================================

BEN_THANH = (10.7725, 106.6980)           # Reference point
NEARBY_30M = (10.7727, 106.6981)          # ~30m from Ben Thanh — inside fence
NEARBY_80M = (10.7732, 106.6980)          # ~80m — outside 50m fence
FAR_AWAY = (10.7798, 106.6990)            # Notre Dame — ~800m away


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="function", autouse=True)
def clear_rate_limiter():
    """Reset the in-process rate limit dict between tests."""
    _campfire_create_history.clear()
    yield
    _campfire_create_history.clear()


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

USER_A = {"email": "alice@layers.app", "username": "alicecf", "password": "Pass123!"}
USER_B = {"email": "bob@layers.app",   "username": "bobcf",   "password": "Pass123!"}
USER_C = {"email": "carol@layers.app", "username": "carolcf", "password": "Pass123!"}


async def register_and_login(client: AsyncClient, user_data: dict):
    """Returns (user_id, auth_header)."""
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


# =============================================================================
# CAMPFIRE FIND-OR-CREATE TESTS
# =============================================================================

class TestCampfireFindOrCreate:
    @pytest.mark.asyncio
    async def test_creates_new_campfire(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        lat, lng = BEN_THANH

        resp = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": lat, "longitude": lng, "name": "Test Fire"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["room_type"] == "CAMPFIRE"
        assert data["status"] == "ACTIVE"
        assert data["name"] == "Test Fire"
        assert data["creator_id"] == a_id
        # Approximate equality (PostGIS may round-trip)
        assert abs(data["center_latitude"] - lat) < 0.0001
        assert abs(data["center_longitude"] - lng) < 0.0001
        assert data["radius_meters"] == 50

    @pytest.mark.asyncio
    async def test_finds_existing_within_50m(self, setup_db, async_client):
        """A second user nearby gets the same campfire, doesn't create a new one."""
        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)

        # A creates a campfire at Ben Thanh
        resp1 = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        assert resp1.status_code == 200
        first_id = resp1.json()["id"]

        # B is 30m away (within fence) — should join existing
        resp2 = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=b_auth,
            json={"latitude": NEARBY_30M[0], "longitude": NEARBY_30M[1]},
        )
        assert resp2.status_code == 200
        assert resp2.json()["id"] == first_id

    @pytest.mark.asyncio
    async def test_creates_new_when_no_one_nearby(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)

        resp1 = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        first_id = resp1.json()["id"]

        # B is far away (~800m) → new campfire
        resp2 = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=b_auth,
            json={"latitude": FAR_AWAY[0], "longitude": FAR_AWAY[1]},
        )
        assert resp2.json()["id"] != first_id

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_second_creation(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)

        # First creation succeeds
        resp1 = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        assert resp1.status_code == 200

        # Second creation FAR away (no existing campfire to join) should be rate-limited
        resp2 = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": FAR_AWAY[0], "longitude": FAR_AWAY[1]},
        )
        assert resp2.status_code == 429
        assert "recently" in resp2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_creator_is_auto_joined(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        resp = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        room_id = resp.json()["id"]

        members_resp = await async_client.get(
            f"/api/v1/chat/campfires/{room_id}/members",
            headers=a_auth,
        )
        assert members_resp.status_code == 200
        body = members_resp.json()
        assert body["total_count"] == 1
        assert body["members"][0]["user_id"] == a_id


# =============================================================================
# CAMPFIRE JOIN TESTS
# =============================================================================

class TestCampfireJoin:
    @pytest.mark.asyncio
    async def test_join_within_radius(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)

        # A creates campfire
        create = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        room_id = create.json()["id"]

        # B explicit join from 30m away
        resp = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/join",
            headers=b_auth,
            json={"latitude": NEARBY_30M[0], "longitude": NEARBY_30M[1]},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == room_id

    @pytest.mark.asyncio
    async def test_join_outside_radius_rejected(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)

        create = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        room_id = create.json()["id"]

        # B tries from 80m away — outside the 50m fence
        resp = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/join",
            headers=b_auth,
            json={"latitude": NEARBY_80M[0], "longitude": NEARBY_80M[1]},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_join_is_idempotent(self, setup_db, async_client, setup_db_fixture=None):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)

        create = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        room_id = create.json()["id"]

        # B joins twice — second should not error or create duplicate row
        for _ in range(2):
            resp = await async_client.post(
                f"/api/v1/chat/campfires/{room_id}/join",
                headers=b_auth,
                json={"latitude": NEARBY_30M[0], "longitude": NEARBY_30M[1]},
            )
            assert resp.status_code == 200

        members = await async_client.get(
            f"/api/v1/chat/campfires/{room_id}/members",
            headers=a_auth,
        )
        assert members.json()["total_count"] == 2  # A + B, not 3


# =============================================================================
# CAMPFIRE LEAVE TESTS
# =============================================================================

class TestCampfireLeave:
    @pytest.mark.asyncio
    async def test_leave_marks_left_at(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)

        create = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        room_id = create.json()["id"]

        # B joins
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/join",
            headers=b_auth,
            json={"latitude": NEARBY_30M[0], "longitude": NEARBY_30M[1]},
        )

        # Members: 2
        members_before = await async_client.get(
            f"/api/v1/chat/campfires/{room_id}/members",
            headers=a_auth,
        )
        assert members_before.json()["total_count"] == 2

        # B leaves
        leave_resp = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/leave",
            headers=b_auth,
        )
        assert leave_resp.status_code == 204

        # Members: now 1
        members_after = await async_client.get(
            f"/api/v1/chat/campfires/{room_id}/members",
            headers=a_auth,
        )
        assert members_after.json()["total_count"] == 1

    @pytest.mark.asyncio
    async def test_leave_is_idempotent(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)

        create = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        room_id = create.json()["id"]

        for _ in range(3):
            resp = await async_client.post(
                f"/api/v1/chat/campfires/{room_id}/leave",
                headers=a_auth,
            )
            assert resp.status_code == 204


# =============================================================================
# NEARBY (MAP BEACONS)
# =============================================================================

class TestCampfireNearby:
    @pytest.mark.asyncio
    async def test_nearby_returns_campfires_in_radius(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)

        # Create a campfire
        await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )

        # Query nearby from 30m away
        resp = await async_client.get(
            "/api/v1/chat/campfires/nearby",
            headers=a_auth,
            params={
                "lat": NEARBY_30M[0],
                "lng": NEARBY_30M[1],
                "radius_meters": 500,
            },
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["distance_meters"] < 100

    @pytest.mark.asyncio
    async def test_nearby_excludes_distant(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)

        await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )

        # Query from Notre Dame with a small radius — should find nothing
        resp = await async_client.get(
            "/api/v1/chat/campfires/nearby",
            headers=a_auth,
            params={
                "lat": FAR_AWAY[0],
                "lng": FAR_AWAY[1],
                "radius_meters": 100,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []


# =============================================================================
# EXPIRY
# =============================================================================

class TestCampfireExpiry:
    @pytest.mark.asyncio
    async def test_expired_campfire_auto_closes_on_read(self, setup_db, async_client):
        """Hitting GET /rooms/{id} on an expired campfire lazily closes it."""
        a_id, a_auth = await register_and_login(async_client, USER_A)

        create = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        room_id = create.json()["id"]

        # Force expiry in DB
        async with setup_db() as db:
            result = await db.execute(
                select(ChatRoom).where(ChatRoom.id == UUID(room_id))
            )
            room = result.scalar_one()
            room.expires_at = datetime.utcnow() - timedelta(minutes=1)
            await db.commit()

        # GET it → lazy close
        resp = await async_client.get(
            f"/api/v1/chat/rooms/{room_id}",
            headers=a_auth,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "CLOSED"

    @pytest.mark.asyncio
    async def test_bulk_close_utility(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        create = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        room_id = create.json()["id"]

        # Force expiry
        async with setup_db() as db:
            result = await db.execute(
                select(ChatRoom).where(ChatRoom.id == UUID(room_id))
            )
            room = result.scalar_one()
            room.expires_at = datetime.utcnow() - timedelta(minutes=1)
            await db.commit()

        # Run cleanup
        async with setup_db() as db:
            count = await ChatService.close_expired_campfires(db)
        assert count == 1

        # Verify
        async with setup_db() as db:
            result = await db.execute(
                select(ChatRoom).where(ChatRoom.id == UUID(room_id))
            )
            room = result.scalar_one()
            assert room.status == ChatRoomStatus.CLOSED
            assert room.closed_at is not None

    @pytest.mark.asyncio
    async def test_message_extends_expiry(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        create = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        room_id = create.json()["id"]
        original_expiry = datetime.fromisoformat(create.json()["expires_at"].replace("Z", "+00:00"))

        # Wait a moment, then send a message
        await asyncio.sleep(0.05)
        await async_client.post(
            f"/api/v1/chat/rooms/{room_id}/messages",
            headers=a_auth,
            json={"content": "Keep the fire alive"},
        )

        # Fetch room — expires_at should have moved forward
        room_resp = await async_client.get(
            f"/api/v1/chat/rooms/{room_id}",
            headers=a_auth,
        )
        new_expiry = datetime.fromisoformat(
            room_resp.json()["expires_at"].replace("Z", "+00:00")
        )
        assert new_expiry > original_expiry


# =============================================================================
# MEMBERSHIP / WS WS GATE
# =============================================================================

class TestCampfireWSAccess:
    @pytest.mark.asyncio
    async def test_non_member_cannot_get_messages(self, setup_db, async_client):
        """Non-members get 403 on /rooms/{id}/messages even for CAMPFIRE."""
        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)

        create = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        room_id = create.json()["id"]

        # B never joined
        resp = await async_client.get(
            f"/api/v1/chat/rooms/{room_id}/messages",
            headers=b_auth,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_member_can_get_messages(self, setup_db, async_client):
        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)

        create = await async_client.post(
            "/api/v1/chat/campfires/find-or-create",
            headers=a_auth,
            json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
        )
        room_id = create.json()["id"]

        # B joins
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/join",
            headers=b_auth,
            json={"latitude": NEARBY_30M[0], "longitude": NEARBY_30M[1]},
        )

        # Both can now get messages
        resp = await async_client.get(
            f"/api/v1/chat/rooms/{room_id}/messages",
            headers=b_auth,
        )
        assert resp.status_code == 200
