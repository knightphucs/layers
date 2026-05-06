"""
LAYERS - Chat REST Tests
========================================
Tests for REST additions:
  POST /chat/rooms/direct              — CONNECTED gate
  POST /chat/rooms/{room_id}/messages  — REST send fallback

Run:
    cd backend
    pytest tests/test_chat_rest.py -v
"""

import os
import sys
from pathlib import Path

import pytest
from uuid import uuid4
from datetime import datetime

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, async_sessionmaker,
)
from sqlalchemy import select, text


valid_debug_values = {"", "0", "1", "true", "false", "yes", "no", "on", "off"}
if os.environ.get("DEBUG", "").strip().lower() not in valid_debug_values:
    os.environ.pop("DEBUG", None)

if __name__ == "__main__":
    backend_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_root))

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.connection import Connection, ConnectionStatus
from app.services.chat_service import ChatService


# =============================================================================
# Fixtures (mirror test_chat_websocket.py)
# =============================================================================

@pytest.fixture(scope="function")
async def setup_db():
    engine = create_async_engine(settings.test_database_url, pool_pre_ping=True)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )

    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS reports CASCADE"))
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

USER_A = {"email": "alice@layers.app", "username": "alicechat", "password": "Pass123!"}
USER_B = {"email": "bob@layers.app",   "username": "bobchat",   "password": "Pass123!"}


async def register_and_login(client: AsyncClient, user_data: dict):
    """Returns (user_id, access_token, auth_header)."""
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
    return user_id, body["access_token"], {"Authorization": f"Bearer {body['access_token']}"}


def uuid_from(s: str):
    from uuid import UUID
    return UUID(s)


def canonical_pair(a, b):
    if str(a) < str(b):
        return a, b
    return b, a


async def _seed_connection(
    session_factory,
    user_a: str,
    user_b: str,
    *,
    status: ConnectionStatus = ConnectionStatus.PENDING,
    interaction_count: int = 0,
):
    """Insert a Connection row directly via session factory."""
    a, b = canonical_pair(uuid_from(user_a), uuid_from(user_b))
    async with session_factory() as db:
        conn = Connection(
            user_a_id=a,
            user_b_id=b,
            interaction_count=interaction_count,
            status=status,
        )
        if status == ConnectionStatus.CONNECTED:
            conn.connected_at = datetime.utcnow()
        db.add(conn)
        await db.commit()
        await db.refresh(conn)
    return conn


# =============================================================================
# CONNECTED gate tests
# =============================================================================

class TestDirectRoomConnectedGate:
    """POST /chat/rooms/direct must enforce CONNECTED status."""

    @pytest.mark.asyncio
    async def test_no_connection_returns_403(self, setup_db, async_client):
        a_id, _, a_auth = await register_and_login(async_client, USER_A)
        b_id, _, _ = await register_and_login(async_client, USER_B)

        resp = await async_client.post(
            "/api/v1/chat/rooms/direct",
            headers=a_auth,
            json={"other_user_id": b_id},
        )
        assert resp.status_code == 403
        assert "connection" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_pending_connection_returns_403(self, setup_db, async_client):
        a_id, _, a_auth = await register_and_login(async_client, USER_A)
        b_id, _, _ = await register_and_login(async_client, USER_B)

        # Seed PENDING connection (would be SIGNAL level on mobile)
        await _seed_connection(
            setup_db, a_id, b_id,
            status=ConnectionStatus.PENDING,
            interaction_count=5,
        )

        resp = await async_client.post(
            "/api/v1/chat/rooms/direct",
            headers=a_auth,
            json={"other_user_id": b_id},
        )
        assert resp.status_code == 403
        assert "real-time chat" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_connected_creates_room(self, setup_db, async_client):
        a_id, _, a_auth = await register_and_login(async_client, USER_A)
        b_id, _, _ = await register_and_login(async_client, USER_B)

        await _seed_connection(
            setup_db, a_id, b_id,
            status=ConnectionStatus.CONNECTED,
            interaction_count=5,
        )

        resp = await async_client.post(
            "/api/v1/chat/rooms/direct",
            headers=a_auth,
            json={"other_user_id": b_id},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["room_type"] == "DIRECT"
        assert data["status"] == "ACTIVE"
        assert data["other_user_id"] == b_id

    @pytest.mark.asyncio
    async def test_idempotent_returns_same_room(self, setup_db, async_client):
        a_id, _, a_auth = await register_and_login(async_client, USER_A)
        b_id, _, _ = await register_and_login(async_client, USER_B)

        await _seed_connection(
            setup_db, a_id, b_id,
            status=ConnectionStatus.CONNECTED,
        )

        resp1 = await async_client.post(
            "/api/v1/chat/rooms/direct",
            headers=a_auth,
            json={"other_user_id": b_id},
        )
        resp2 = await async_client.post(
            "/api/v1/chat/rooms/direct",
            headers=a_auth,
            json={"other_user_id": b_id},
        )
        assert resp1.json()["id"] == resp2.json()["id"]

    @pytest.mark.asyncio
    async def test_self_chat_rejected(self, setup_db, async_client):
        a_id, _, a_auth = await register_and_login(async_client, USER_A)

        resp = await async_client.post(
            "/api/v1/chat/rooms/direct",
            headers=a_auth,
            json={"other_user_id": a_id},
        )
        assert resp.status_code == 400


# =============================================================================
# REST send tests
# =============================================================================

class TestRESTSendFallback:
    @pytest.mark.asyncio
    async def test_rest_send_persists_and_returns(self, setup_db, async_client):
        a_id, _, a_auth = await register_and_login(async_client, USER_A)
        b_id, _, _ = await register_and_login(async_client, USER_B)

        async with setup_db() as db:
            room = await ChatService.get_or_create_direct_room(
                db, uuid_from(a_id), uuid_from(b_id),
            )
            room_id = str(room.id)

        resp = await async_client.post(
            f"/api/v1/chat/rooms/{room_id}/messages",
            headers=a_auth,
            json={"content": "REST send test"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["content"] == "REST send test"
        assert body["sender_id"] == a_id

        # Verify persisted via list endpoint
        list_resp = await async_client.get(
            f"/api/v1/chat/rooms/{room_id}/messages",
            headers=a_auth,
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()["items"]) == 1

    @pytest.mark.asyncio
    async def test_rest_send_non_member_403(self, setup_db, async_client):
        a_id, _, _ = await register_and_login(async_client, USER_A)
        b_id, _, _ = await register_and_login(async_client, USER_B)
        c_id, _, c_auth = await register_and_login(
            async_client,
            {"email": "c@x.com", "username": "carolchat", "password": "Pass123!"},
        )

        async with setup_db() as db:
            room = await ChatService.get_or_create_direct_room(
                db, uuid_from(a_id), uuid_from(b_id),
            )
            room_id = str(room.id)

        resp = await async_client.post(
            f"/api/v1/chat/rooms/{room_id}/messages",
            headers=c_auth,
            json={"content": "Hi from outsider"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_rest_send_empty_400(self, setup_db, async_client):
        a_id, _, a_auth = await register_and_login(async_client, USER_A)
        b_id, _, _ = await register_and_login(async_client, USER_B)

        async with setup_db() as db:
            room = await ChatService.get_or_create_direct_room(
                db, uuid_from(a_id), uuid_from(b_id),
            )
            room_id = str(room.id)

        resp = await async_client.post(
            f"/api/v1/chat/rooms/{room_id}/messages",
            headers=a_auth,
            json={"content": ""},
        )
        # Pydantic min_length=1 → 422
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_rest_send_too_long_422(self, setup_db, async_client):
        a_id, _, a_auth = await register_and_login(async_client, USER_A)
        b_id, _, _ = await register_and_login(async_client, USER_B)

        async with setup_db() as db:
            room = await ChatService.get_or_create_direct_room(
                db, uuid_from(a_id), uuid_from(b_id),
            )
            room_id = str(room.id)

        resp = await async_client.post(
            f"/api/v1/chat/rooms/{room_id}/messages",
            headers=a_auth,
            json={"content": "x" * 2001},
        )
        assert resp.status_code in (400, 422)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
