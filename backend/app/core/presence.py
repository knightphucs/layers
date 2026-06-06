"""
LAYERS - Presence (Redis-backed)
=================================
Tracks who is online and who is currently in each campfire, across all
workers. Replaces the in-process `manager.users_in_room()` count, which
under-counts once you run more than one worker.

Design:
- User online flag: a key `presence:user:{id}` with a short TTL, refreshed
  on each WebSocket ping/heartbeat. If the client goes away, the key expires.
- Campfire membership: a sorted set `campfire:online:{room}` scored by each
  member's expiry timestamp. Reads trim expired members first, so the count
  is self-healing even if a client disconnects without a clean "leave".

All functions are no-ops / safe defaults when Redis is unavailable.
"""

import time
from typing import Iterable, List, Set
from uuid import UUID

from app.core.redis_client import get_optional_redis

PRESENCE_TTL = 60  # seconds; client should ping well within this window


def _user_key(user_id) -> str:
    return f"presence:user:{user_id}"


def _campfire_key(room_id) -> str:
    return f"campfire:online:{room_id}"


# ============================================================
# USER ONLINE PRESENCE
# ============================================================

async def mark_online(user_id, ttl: int = PRESENCE_TTL) -> None:
    client = get_optional_redis()
    if client is None:
        return
    await client.set(_user_key(user_id), "1", ex=ttl)


async def mark_offline(user_id) -> None:
    client = get_optional_redis()
    if client is None:
        return
    await client.delete(_user_key(user_id))


async def is_online(user_id) -> bool:
    client = get_optional_redis()
    if client is None:
        return False
    return bool(await client.exists(_user_key(user_id)))


async def filter_online(user_ids: Iterable) -> Set[str]:
    """Return the subset of user_ids that are currently online."""
    client = get_optional_redis()
    ids = [str(u) for u in user_ids]
    if client is None or not ids:
        return set()
    pipe = client.pipeline()
    for uid in ids:
        pipe.exists(_user_key(uid))
    results = await pipe.execute()
    return {uid for uid, flag in zip(ids, results) if flag}


# ============================================================
# CAMPFIRE MEMBERSHIP (self-expiring)
# ============================================================

async def campfire_touch(room_id, user_id, ttl: int = PRESENCE_TTL) -> None:
    """Add/refresh a user's membership in a campfire (call on join + each ping)."""
    client = get_optional_redis()
    if client is None:
        return
    now = time.time()
    pipe = client.pipeline()
    pipe.zadd(_campfire_key(room_id), {str(user_id): now + ttl})
    pipe.zremrangebyscore(_campfire_key(room_id), 0, now)  # drop expired
    pipe.expire(_campfire_key(room_id), ttl * 2)
    await pipe.execute()


async def campfire_leave(room_id, user_id) -> None:
    client = get_optional_redis()
    if client is None:
        return
    await client.zrem(_campfire_key(room_id), str(user_id))


async def campfire_online(room_id) -> List[str]:
    """Return current (non-expired) member user_ids of a campfire."""
    client = get_optional_redis()
    if client is None:
        return []
    now = time.time()
    await client.zremrangebyscore(_campfire_key(room_id), 0, now)
    return await client.zrange(_campfire_key(room_id), 0, -1)


async def campfire_count(room_id) -> int:
    return len(await campfire_online(room_id))
