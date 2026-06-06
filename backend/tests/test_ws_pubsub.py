"""
LAYERS - WebSocket Pub/Sub Tests
Run: pytest tests/test_ws_pubsub.py -v

Simulates two workers (two ConnectionManager instances) sharing one Redis,
and proves a broadcast published by worker A reaches a socket on worker B.
Uses fakeredis (with a shared server) so no real Redis is required.
"""

import asyncio
import json
from uuid import uuid4

import pytest
import fakeredis.aioredis

from app.core import redis_client
from app.core.ws_manager import ConnectionManager, CHANNEL_PREFIX


class FakeWebSocket:
    """Minimal stand-in for a Starlette WebSocket."""
    def __init__(self):
        self.sent = []

    async def send_json(self, message):
        self.sent.append(message)


@pytest.fixture
async def shared_redis():
    server = fakeredis.aioredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    redis_client._redis = client
    redis_client._available = True
    yield server
    await client.flushall()
    await client.aclose()
    redis_client._redis = None
    redis_client._available = False


@pytest.fixture
def no_redis():
    redis_client._redis = None
    redis_client._available = False
    yield
    redis_client._redis = None
    redis_client._available = False


def _client_on(server):
    return fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)


class TestLocalDelivery:
    async def test_local_broadcast_reaches_all_and_excludes_user(self, no_redis):
        m = ConnectionManager()
        room = uuid4()
        u1, u2 = uuid4(), uuid4()
        ws1, ws2 = FakeWebSocket(), FakeWebSocket()
        await m.connect(ws1, room, u1)
        await m.connect(ws2, room, u2)

        await m._local_broadcast(room, {"t": "msg"})
        assert ws1.sent == [{"t": "msg"}]
        assert ws2.sent == [{"t": "msg"}]

        await m._local_broadcast(room, {"t": "typing"}, exclude_user_id=u1)
        assert ws1.sent[-1] == {"t": "msg"}          # u1 excluded
        assert ws2.sent[-1] == {"t": "typing"}

    async def test_broadcast_local_fallback_without_redis(self, no_redis):
        m = ConnectionManager()
        room = uuid4()
        ws = FakeWebSocket()
        await m.connect(ws, room, uuid4())
        await m.broadcast(room, {"hello": 1})
        assert ws.sent == [{"hello": 1}]

    async def test_disconnect_removes_socket(self, no_redis):
        m = ConnectionManager()
        room = uuid4()
        ws = FakeWebSocket()
        await m.connect(ws, room, uuid4())
        m.disconnect(ws)
        await m.broadcast(room, {"x": 1})
        assert ws.sent == []  # nothing delivered after disconnect


class TestRedisBridge:
    async def test_broadcast_publishes_envelope(self, shared_redis):
        m = ConnectionManager()
        room = uuid4()
        sub = _client_on(shared_redis).pubsub()
        await sub.psubscribe(CHANNEL_PREFIX + "*")
        await asyncio.sleep(0.05)

        await m.broadcast(room, {"body": "hi"})

        received = None
        for _ in range(20):
            msg = await sub.get_message(ignore_subscribe_messages=True, timeout=0.1)
            if msg:
                received = json.loads(msg["data"])
                break
        await sub.aclose()
        assert received is not None
        assert received["room_id"] == str(room)
        assert received["message"] == {"body": "hi"}

    async def test_cross_worker_delivery(self, shared_redis):
        """Broadcast from worker A must reach a socket on worker B."""
        worker_a = ConnectionManager()
        worker_b = ConnectionManager()
        await worker_b.start_pubsub()   # only B has a listener + the socket
        await asyncio.sleep(0.05)

        room = uuid4()
        ws_on_b = FakeWebSocket()
        await worker_b.connect(ws_on_b, room, uuid4())

        await worker_a.broadcast(room, {"msg": "from A"})

        # give B's listener a moment to receive + deliver
        for _ in range(20):
            await asyncio.sleep(0.05)
            if ws_on_b.sent:
                break

        await worker_b.stop_pubsub()
        assert ws_on_b.sent == [{"msg": "from A"}]

    async def test_cross_worker_exclude_by_user(self, shared_redis):
        """exclude=socket on the sender translates to user-level exclusion."""
        worker_a = ConnectionManager()
        worker_b = ConnectionManager()
        await worker_b.start_pubsub()
        await asyncio.sleep(0.05)

        room = uuid4()
        sender_id = uuid4()
        other_id = uuid4()

        # sender's socket lives on worker A; we register it so exclude resolves
        ws_sender = FakeWebSocket()
        await worker_a.connect(ws_sender, room, sender_id)
        # another user's socket on worker B
        ws_other = FakeWebSocket()
        await worker_b.connect(ws_other, room, other_id)

        await worker_a.broadcast(room, {"typing": True}, exclude=ws_sender)

        for _ in range(20):
            await asyncio.sleep(0.05)
            if ws_other.sent:
                break

        await worker_b.stop_pubsub()
        assert ws_other.sent == [{"typing": True}]  # other user gets it
        assert ws_sender.sent == []                  # sender excluded everywhere
