"""
LAYERS - Truth-or-Dare Tests
============================================
Full lifecycle coverage of the Campfire game system + chat polish.

Run:
    cd backend
    pytest tests/test_truth_or_dare.py -v
"""

import pytest
from uuid import UUID

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, async_sessionmaker,
)
from sqlalchemy import select

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.game import (
    CampfireGame, CampfireGameRound, CampfireGameAnswer,
    GameState, RoundState,
)
from app.services.chat_service import ChatService, _campfire_create_history


# =============================================================================
# Coordinates (HCMC)
# =============================================================================

BEN_THANH = (10.7725, 106.6980)
NEARBY_30M = (10.7727, 106.6981)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="function", autouse=True)
def clear_state():
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

USER_A = {"email": "a@x.com", "username": "alicegame", "password": "Pass123!"}
USER_B = {"email": "b@x.com", "username": "bobgame",   "password": "Pass123!"}
USER_C = {"email": "c@x.com", "username": "carolgame", "password": "Pass123!"}


async def register_and_login(client: AsyncClient, ud: dict):
    resp = await client.post("/api/v1/auth/register", json=ud)
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


async def setup_campfire_with_two(async_client, setup_db):
    """A creates a campfire at Ben Thanh, B joins from 30m away. Returns
    (a_id, a_auth, b_id, b_auth, room_id)."""
    a_id, a_auth = await register_and_login(async_client, USER_A)
    b_id, b_auth = await register_and_login(async_client, USER_B)

    create = await async_client.post(
        "/api/v1/chat/campfires/find-or-create",
        headers=a_auth,
        json={"latitude": BEN_THANH[0], "longitude": BEN_THANH[1]},
    )
    assert create.status_code == 200
    room_id = create.json()["id"]

    join = await async_client.post(
        f"/api/v1/chat/campfires/{room_id}/join",
        headers=b_auth,
        json={"latitude": NEARBY_30M[0], "longitude": NEARBY_30M[1]},
    )
    assert join.status_code == 200
    return a_id, a_auth, b_id, b_auth, room_id


# =============================================================================
# START
# =============================================================================

class TestGameStart:
    @pytest.mark.asyncio
    async def test_start_creates_game_and_round(self, setup_db, async_client):
        a_id, a_auth, b_id, b_auth, room_id = await setup_campfire_with_two(
            async_client, setup_db
        )
        resp = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=a_auth
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["state"] == "WAITING"
        assert body["starter_id"] == a_id
        assert body["round_count"] == 1
        assert body["current_round"] is not None
        assert body["current_round"]["state"] == "ANSWERING"
        assert body["current_round"]["question_text"]  # not empty

    @pytest.mark.asyncio
    async def test_only_member_can_start(self, setup_db, async_client):
        a_id, a_auth, _, _, room_id = await setup_campfire_with_two(
            async_client, setup_db
        )
        # C never joined the campfire
        c_id, c_auth = await register_and_login(async_client, USER_C)
        resp = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=c_auth
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_start_second_game_while_active(self, setup_db, async_client):
        a_id, a_auth, _, _, room_id = await setup_campfire_with_two(
            async_client, setup_db
        )
        r1 = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=a_auth
        )
        assert r1.status_code == 201
        r2 = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=a_auth
        )
        assert r2.status_code == 409


# =============================================================================
# ANSWERS
# =============================================================================

class TestAnswerPhase:
    @pytest.mark.asyncio
    async def test_submit_answer_succeeds(self, setup_db, async_client):
        a_id, a_auth, b_id, b_auth, room_id = await setup_campfire_with_two(
            async_client, setup_db
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=a_auth
        )

        resp = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/answer",
            headers=a_auth,
            json={"content": "A nice quiet hidden cafe"},
        )
        assert resp.status_code == 201
        assert resp.json()["my_answer_submitted"] is True

    @pytest.mark.asyncio
    async def test_answer_hidden_until_reveal(self, setup_db, async_client):
        a_id, a_auth, b_id, b_auth, room_id = await setup_campfire_with_two(
            async_client, setup_db
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=a_auth
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/answer",
            headers=a_auth, json={"content": "A's secret answer"},
        )

        # B fetches state — should see the answer text but NOT the user_id
        resp = await async_client.get(
            f"/api/v1/chat/campfires/{room_id}/game", headers=b_auth
        )
        answers = resp.json()["current_round"]["answers"]
        assert len(answers) == 1
        assert answers[0]["content"] == "A's secret answer"
        assert answers[0]["user_id"] is None  # hidden during answering/voting
        assert answers[0]["username"] is None
        assert answers[0]["is_mine"] is False
        assert answers[0]["vote_count"] == 0  # tally hidden too

    @pytest.mark.asyncio
    async def test_cannot_double_answer(self, setup_db, async_client):
        a_id, a_auth, _, _, room_id = await setup_campfire_with_two(
            async_client, setup_db
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=a_auth
        )
        r1 = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/answer",
            headers=a_auth, json={"content": "first"},
        )
        assert r1.status_code == 201
        r2 = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/answer",
            headers=a_auth, json={"content": "second"},
        )
        assert r2.status_code == 409

    @pytest.mark.asyncio
    async def test_answer_too_long_rejected(self, setup_db, async_client):
        a_id, a_auth, _, _, room_id = await setup_campfire_with_two(
            async_client, setup_db
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=a_auth
        )
        resp = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/answer",
            headers=a_auth, json={"content": "x" * 281},
        )
        assert resp.status_code in (400, 422)


# =============================================================================
# VOTING PHASE
# =============================================================================

class TestVotingPhase:
    @pytest.mark.asyncio
    async def test_cannot_vote_with_one_answer(self, setup_db, async_client):
        a_id, a_auth, b_id, b_auth, room_id = await setup_campfire_with_two(
            async_client, setup_db
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=a_auth
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/answer",
            headers=a_auth, json={"content": "only one"},
        )
        # Try to move to voting with just 1 answer
        resp = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/move-to-voting",
            headers=a_auth,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_only_starter_advances_phase(self, setup_db, async_client):
        a_id, a_auth, b_id, b_auth, room_id = await setup_campfire_with_two(
            async_client, setup_db
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=a_auth
        )
        for auth, content in [(a_auth, "A1"), (b_auth, "B1")]:
            await async_client.post(
                f"/api/v1/chat/campfires/{room_id}/game/answer",
                headers=auth, json={"content": content},
            )
        # B (not starter) tries to advance
        resp = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/move-to-voting",
            headers=b_auth,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_vote_own_answer(self, setup_db, async_client):
        a_id, a_auth, b_id, b_auth, room_id = await setup_campfire_with_two(
            async_client, setup_db
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=a_auth
        )
        ar = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/answer",
            headers=a_auth, json={"content": "A's pick"},
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/answer",
            headers=b_auth, json={"content": "B's pick"},
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/move-to-voting",
            headers=a_auth,
        )

        # Find A's answer id from state
        st = await async_client.get(
            f"/api/v1/chat/campfires/{room_id}/game", headers=a_auth
        )
        a_answer = next(a for a in st.json()["current_round"]["answers"] if a["is_mine"])

        resp = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/vote",
            headers=a_auth, json={"answer_id": a_answer["id"]},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_double_vote(self, setup_db, async_client):
        a_id, a_auth, b_id, b_auth, room_id = await setup_campfire_with_two(
            async_client, setup_db
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=a_auth
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/answer",
            headers=a_auth, json={"content": "A1"},
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/answer",
            headers=b_auth, json={"content": "B1"},
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/move-to-voting",
            headers=a_auth,
        )

        # Find B's answer for A to vote on
        st = await async_client.get(
            f"/api/v1/chat/campfires/{room_id}/game", headers=a_auth
        )
        b_answer = next(a for a in st.json()["current_round"]["answers"] if not a["is_mine"])

        r1 = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/vote",
            headers=a_auth, json={"answer_id": b_answer["id"]},
        )
        assert r1.status_code == 200
        r2 = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/vote",
            headers=a_auth, json={"answer_id": b_answer["id"]},
        )
        assert r2.status_code == 409


# =============================================================================
# REVEAL + WINNER LOGIC
# =============================================================================

class TestRevealAndWinner:
    @pytest.mark.asyncio
    async def test_reveal_picks_highest_votes(self, setup_db, async_client):
        a_id, a_auth, b_id, b_auth, room_id = await setup_campfire_with_two(
            async_client, setup_db
        )
        # Also bring in C
        c_id, c_auth = await register_and_login(async_client, USER_C)
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/join",
            headers=c_auth,
            json={"latitude": NEARBY_30M[0], "longitude": NEARBY_30M[1]},
        )

        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=a_auth
        )
        for auth, content in [(a_auth, "A wins"), (b_auth, "B's try"), (c_auth, "C's try")]:
            await async_client.post(
                f"/api/v1/chat/campfires/{room_id}/game/answer",
                headers=auth, json={"content": content},
            )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/move-to-voting",
            headers=a_auth,
        )

        # B and C both vote for A's answer
        st = await async_client.get(
            f"/api/v1/chat/campfires/{room_id}/game", headers=b_auth
        )
        a_answer_id = next(
            a["id"] for a in st.json()["current_round"]["answers"]
            if a["content"] == "A wins"
        )
        for auth in (b_auth, c_auth):
            await async_client.post(
                f"/api/v1/chat/campfires/{room_id}/game/vote",
                headers=auth, json={"answer_id": a_answer_id},
            )

        # A reveals
        resp = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/reveal", headers=a_auth
        )
        assert resp.status_code == 200
        body = resp.json()
        rnd = body["current_round"]
        assert rnd["state"] == "REVEALED"
        assert rnd["winner_user_id"] == a_id
        # In REVEALED phase, authors are now visible
        for ans in rnd["answers"]:
            assert ans["user_id"] is not None

    @pytest.mark.asyncio
    async def test_next_round_increments_count(self, setup_db, async_client):
        a_id, a_auth, b_id, b_auth, room_id = await setup_campfire_with_two(
            async_client, setup_db
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=a_auth
        )
        for auth, content in [(a_auth, "A1"), (b_auth, "B1")]:
            await async_client.post(
                f"/api/v1/chat/campfires/{room_id}/game/answer",
                headers=auth, json={"content": content},
            )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/move-to-voting",
            headers=a_auth,
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/reveal", headers=a_auth
        )
        nxt = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/next-round", headers=a_auth
        )
        assert nxt.status_code == 201
        assert nxt.json()["round_count"] == 2

    @pytest.mark.asyncio
    async def test_end_completes_game(self, setup_db, async_client):
        a_id, a_auth, _, _, room_id = await setup_campfire_with_two(
            async_client, setup_db
        )
        await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/start", headers=a_auth
        )
        resp = await async_client.post(
            f"/api/v1/chat/campfires/{room_id}/game/end", headers=a_auth
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "COMPLETED"


# =============================================================================
# CHAT POLISH — other_user attached on chat list
# =============================================================================

class TestChatRoomOtherUser:
    @pytest.mark.asyncio
    async def test_other_user_attached_for_direct_room(self, setup_db, async_client):
        """The Day 2 gap closed: chat list returns other_user with username/avatar."""
        from datetime import datetime
        from app.models.connection import Connection, ConnectionStatus

        a_id, a_auth = await register_and_login(async_client, USER_A)
        b_id, b_auth = await register_and_login(async_client, USER_B)

        # Seed a CONNECTED pair
        smaller, bigger = sorted([a_id, b_id])
        async with setup_db() as db:
            conn = Connection(
                user_a_id=UUID(smaller), user_b_id=UUID(bigger),
                interaction_count=6, status=ConnectionStatus.CONNECTED,
                connected_at=datetime.utcnow(),
            )
            db.add(conn)
            await db.commit()

        # A opens direct room with B
        await async_client.post(
            "/api/v1/chat/rooms/direct", headers=a_auth,
            json={"other_user_id": b_id},
        )

        # Now list A's rooms
        resp = await async_client.get("/api/v1/chat/rooms", headers=a_auth)
        assert resp.status_code == 200
        rooms = resp.json()
        direct_rooms = [r for r in rooms if r["room_type"] == "DIRECT"]
        assert len(direct_rooms) == 1
        other = direct_rooms[0]["other_user"]
        assert other is not None
        assert other["id"] == b_id
        assert other["username"] == USER_B["username"]
