# 🏗️ LAYERS — Architecture Reference

> The depth that does not belong in `CLAUDE.md`. Read that file first for orientation; read this
> one when you need to know how a specific subsystem actually behaves.

---

## 1. Request lifecycle

```
HTTP request
   │
   ├─ SecurityHeadersMiddleware   nosniff, X-Frame-Options, HSTS (prod), Permissions-Policy
   ├─ CORSMiddleware              allowlist from settings; "*" stripped when DEBUG=False
   ├─ TrustedHostMiddleware       production only, from ALLOWED_HOSTS
   ├─ RateLimitMiddleware         Redis sliding window, in-memory fallback → 429 JSONResponse
   ├─ TimingMiddleware            X-Response-Time header; WARN over 300 ms
   │
   ├─ /admin      → SQLAdmin panel (session auth, separate from the JWT API)
   ├─ /health     → liveness, includes Redis status
   └─ /api/v1/*   → api_router
                      └─ route (app/api/v1/<domain>.py)
                            ├─ Depends(get_current_user)   401 invalid, 403 banned
                            ├─ Depends(get_db)             commit on success, rollback on raise
                            ├─ Depends(rate_limit(...))    auth routes only, fail-open
                            ├─ Pydantic schema validation
                            └─ Service call → SQLAlchemy → Postgres/PostGIS
```

**Ordering rule.** Starlette wraps the last-added middleware outermost. `main.py` adds security
headers → CORS → rate limit → timing, so timing measures everything inside it. If you add
middleware, decide deliberately whether it should be inside or outside the timing measurement.

**Startup** (`lifespan` in `main.py`), in order: validate production secrets (raises and refuses
to boot when `DEBUG=False` with default secrets) → `init_db()` → `init_redis()` (never raises;
degraded mode if down) → `manager.start_pubsub()`. Shutdown reverses it.

---

## 2. Data model

28 model classes across 16 modules, one table each. Primary keys are UUIDs everywhere (non-sequential, so IDs
cannot be enumerated).

### Core

| Model | Table | Notes |
| --- | --- | --- |
| `User` | `users` | auth + gamification (`experience_points`, `level`, `reputation_score` 0–1000 default 100, `current_streak`, `longest_streak`) + moderation (`is_banned`, `cheat_strikes`, `banned_until`) + reset token |
| `Location` | `locations` | PostGIS `Geography(POINT, 4326)`; categories CAFE, PARK, LANDMARK, GHOST … |
| `ExploredChunk` | `explored_chunks` | fog of war; one row per (user, ~100 m chunk) |
| `Artifact` | `artifacts` | the core entity; `payload` JSONB varies by `content_type` |
| `ArtifactReply` | `artifact_replies` | Slow Mail — `deliver_at`, `is_delivered` |
| `InventoryItem` / `MailQueue` | `inventory`, `mail_queue` | saved artifacts, pending delivery |

### Enums to know

| Enum | Values |
| --- | --- |
| `ContentType` | LETTER · VOICE · PHOTO · PAPER_PLANE · VOUCHER · TIME_CAPSULE · NOTEBOOK |
| `Visibility` | PUBLIC · TARGETED (one user) · PASSCODE (hashed secret) |
| `ArtifactStatus` | ACTIVE · PENDING (held for review) · HIDDEN (auto-hidden by reports) · DELETED |
| `UserRole` | USER · ADMIN · PARTNER (businesses) |
| `ConnectionStatus` | PENDING (Slow Mail only) · CONNECTED (real-time chat unlocked) |
| `ChatRoomType` / `ChatRoomStatus` | DIRECT vs CAMPFIRE; lifecycle state |
| `GameState` / `RoundState` | campfire Truth-or-Dare state machine |

`layer` is a plain string column (`"LIGHT"` / `"SHADOW"`), not an enum — it appears on artifacts
and on cache keys.

### Social, gamification, safety

| Model | Table | Purpose |
| --- | --- | --- |
| `Connection` | `connections` | progressive connection: 5 interactions → Signal → Connected |
| `ChatRoom`, `Message`, `CampfireMember` | `chat_rooms`, `messages`, `campfire_members` | direct + campfire chat |
| `CampfireGame`, `CampfireGameRound`, `CampfireGameAnswer` | `campfire_games`, `campfire_game_rounds`, `campfire_game_answers` | Truth-or-Dare |
| `ArtifactBoost`, `Wave`, `ArtifactDiscovery`, `SynchronicityEvent` | `artifact_boosts`, `waves`, `artifact_discoveries`, `synchronicity_events` | social spark |
| `XPEvent` | `xp_events` | append-only XP ledger — also the source for badge criteria |
| `QuestCompletion` | `quest_completions` | daily quest completions |
| `UserBadge` | `user_badges` | unlocked achievements (catalog lives in code) |
| `DeviceToken`, `NotificationPreference`, `NotificationHistory` | `device_tokens`, `notification_preferences`, `notification_history` | push plumbing |
| `Report` | `reports` | one per (user, artifact); structured reason |
| `ModerationLog` | `moderation_logs` | audit trail of automated + admin decisions |
| `UserBlock` | `user_blocks` | individual-level blocking |
| `GlitchZone` | `glitch_zones` | Shadow layer zones with time windows + radius |

**Adding a model:** create it, export it from `app/models/__init__.py` (Alembic autogenerate only
sees imported models), generate the migration, then read the migration before applying it.

---

## 3. Geo engine

PostGIS does the work; `LocationService` is the only place that should build spatial SQL.

```sql
ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography   -- LONGITUDE FIRST
ST_DWithin(a, b, meters)                              -- proximity, uses the GIST index
ST_Distance(a, b)                                     -- meters between two geographies
```

- `Location.create_point_wkt(lat, lng)` builds the WKT string with the correct argument order.
  Use it rather than hand-writing `POINT(...)`.
- **Geo-lock:** an artifact is visible on the map from any distance but its content requires the
  reader to be within `GEO_LOCK_RADIUS` (50 m). The nearby endpoint returns previews with
  `is_within_range` / `is_unlocked` flags; the detail endpoint enforces the radius server-side.
  Never rely on the client to enforce a lock.
- **Fog of war:** `chunk_x = int(lng / 0.000917)`, `chunk_y = int(lat / 0.0009)` — roughly 100 m
  cells at HCMC latitude. Chunk exploration is idempotent; the client batches GPS points every
  30 s into `POST /explore/batch` (max 50 points per call).
- **Anti-cheat** (`anti_cheat_service`): OS mock-location flag, >5 km/s jump detection, sensor
  cross-check, 3 drops/day, 20 m minimum spacing. Three strikes → permanent ban;
  `banned_until` handles temporary bans.

---

## 4. WebSocket + presence

**Endpoint:** `WS /api/v1/chat/ws/{room_id}?token={jwt}` — the token is a query parameter because
React Native cannot set headers on the WS handshake. The handshake validates the JWT and room
membership before accepting.

**Why the pub/sub bridge exists.** `ConnectionManager.active` only knows sockets attached to
*this* worker process. With more than one worker, a REST endpoint on worker B broadcasting to a
room whose members are connected to worker A would silently drop the message.

```
worker B: manager.broadcast(room_id, msg)
             └─ PUBLISH ws:room:{room_id}
                      ↓ Redis
   every worker's start_pubsub() listener (pattern ws:room:*)
             └─ deliver to ITS OWN local sockets in that room
```

`ws:user:{id}` does the same for user-targeted frames. If Redis is unavailable, `broadcast()`
falls back to local delivery — correct for a single worker, degraded for many.

**Rule:** always call `manager.broadcast()` / `manager.send_personal()`. Never iterate
`manager.active[...]` yourself.

**Presence** (`core/presence.py`) is Redis-backed for the same reason: `presence:user:{id}` with
a short TTL refreshed by client heartbeats, and `campfire:online:{room}` as a sorted set scored
by expiry so stale members are trimmed on read.

**Client** (`mobile/src/services/chat.ts`): `WebSocketClient` handles reconnect with backoff,
queues outbound frames while disconnected, and flushes on open. `chatStore` owns the client
instance — screens never construct one directly.

---

## 5. Caching and invalidation

Built on `core/cache.py` (JSON over Redis, fails open) with keys from `core/geo_cache.py`.

| Key pattern | TTL | Contents |
| --- | --- | --- |
| `nearby:{layer}:{lat}_{lng}_{radius}` | 15 s | nearby artifact previews |
| `fog:{layer}:{minlat}_{minlng}_{maxlat}_{maxlng}` | 20 s | explored chunks in a viewport |
| `lb:global`, `lb:weekly:{ISOyear}-W{week}`, `lb:district:{d}` | weekly keys ~16 d | leaderboard sorted sets |
| `ratelimit:{ip}:{endpoint}` | window | global sliding-window log |
| `rl:ep:{bucket}:{ip}` | window | per-endpoint auth buckets |
| `presence:user:{id}`, `campfire:online:{room}` | short | presence |

**Coordinate quantization is the trick that makes this work.** Map panning produces thousands of
near-identical viewports; rounding to ~3 decimals (~110 m buckets) makes neighboring pans share a
key, so a 15–20 s TTL absorbs a burst of near-duplicate queries.

**Invalidation** is deliberately coarse: `invalidate_on_artifact_create()` clears `nearby:*`,
`invalidate_fog_for_layer()` clears `fog:*`. With TTLs this short, precision is not worth the
complexity.

---

## 6. Gamification pipeline

```
action (create artifact, unlock, reply, explore chunk, win game, finish quest)
   └─ XPService.award(user, event_type)
        ├─ INSERT xp_events            (append-only ledger)
        ├─ user.experience_points += XP_VALUES[event_type]
        ├─ level = 1 + xp // 1000      (canonical formula — mobile mirrors it)
        ├─ LeaderboardService.record() → ZADD lb:global, ZINCRBY lb:weekly:*
        └─ BadgeService.evaluate(user) → award any newly-met badges
```

| Event | XP |
| --- | --- |
| `ARTIFACT_CREATE` | 50 |
| `ARTIFACT_UNLOCK` | 25 |
| `REPLY_SENT` / `REPLY_RECEIVED` | 20 / 30 |
| `EXPLORE_NEW_CHUNK` | 15 |
| `CONNECTION_UPGRADE` | 75 |
| `CAMPFIRE_GAME_WIN` | 40 |
| `DAILY_QUEST` | 100 |
| `FIRST_CHECK_IN` | 25 |

- **`XPService` is the single source of truth** for XP values, the level formula, and the rank
  ladder (10 tiers). `User.add_xp()` predates it; do not add new callers.
- **`BadgeService.evaluate()` is idempotent** — it re-checks every criterion against durable
  state (user row + `xp_events` counts), so calling it too often is safe and nothing is ever
  missed. Criteria are `count` (XP events of a type) and threshold checks on level/streak.
- **Quests** need no assignment table: the catalog is static, today's set is a deterministic
  date-seeded slice, and progress lives in Redis counters with a TTL to the next Asia/Ho_Chi_Minh
  midnight. Only completions are persisted.
- **Mobile must mirror, never re-derive.** `RANKS` in `xp_service.py` and `RANK_TITLES` in
  `mobile/src/services/profile.ts` must stay identical.

---

## 7. Trust and safety pipeline

```
create content
   └─ ModerationService.enforce()
        ├─ text filter (VN + EN, leetspeak and diacritic evasion)
        │     SAFE  → ACTIVE
        │     FLAG  → PENDING   (saved, invisible to public, human review queue)
        │     BLOCK → rejected + reputation penalty
        └─ PHOTO/VOICE → scan_image()  ← currently a stub returning FLAG
                                          (see docs/PRODUCTION_READINESS.md H3)

report content
   └─ ReportService  one report per (user, artifact)
        └─ weighted_score = Σ report_weight(reporter.reputation_score)
             ≥ 5.0 → status HIDDEN
```

Three-tier moderation instead of binary is deliberate: false positives on a social app destroy
trust faster than mild profanity does.

**Trust weighting** is what makes reports abuse-resistant:

| Reporter standing | Weight | 5 reports total |
| --- | --- | --- |
| TRUSTED | 2.0 | 10.0 → hidden fast |
| ESTABLISHED | 1.0 | 5.0 → hidden |
| RESTRICTED (throwaway) | 0.25 | 1.25 → **not** hidden |

`Artifact.report_count` remains the distinct reporter count for display; the weighted score is
computed at decision time from the report rows.

**Blocks vs reports** — different jobs, and the distinction matters when extending either:
reports protect the *community* (content-level, weighted, admin-reviewed); blocks protect the
*individual* (pair-level, immediate, no review). Blocking is enforced at
`ConnectionService.record_interaction`, the funnel all social escalation flows through, so a
block stops new contact. Existing anonymous geo-artifacts stay visible — they are city content,
not directed messages.

**Admin panel** at `/admin` (SQLAdmin, session auth) is the human review surface for PENDING
content and the report queue.

---

## 8. Performance playbook

The method, not just the Day-4 changes. Use it whenever something feels slow.

### Backend

1. **Find the slow endpoint.** `TimingMiddleware` puts `X-Response-Time` on every response and
   logs `🐌 SLOW <method> <path> → <status> in <ms>` above 300 ms. Watch the log under real use;
   that list is the work queue. Read the header with `curl -i` or the mobile network inspector.
2. **Prove the cause in Postgres** with `backend/scripts/perf_audit.sql`, in order:
   - §1 existing indexes — ground truth, so you do not create duplicates
   - §2 `pg_stat_user_tables` — high `seq_scan` on a big table is the missing-index smell
   - §3 `EXPLAIN ANALYZE` on the hot paths (nearby artifacts, badge evaluation, mail sweep).
     `Index Scan` good; `Seq Scan` on a large table bad; huge "Rows Removed by Filter" means the
     index is not selective enough
   - §4 candidate indexes — create **only** what §1 shows missing *and* §3 proves is needed
3. **Cache last, not first.** A cache over an unindexed query hides the problem and expires into
   the same stall. Fix the query, then cache with a quantized key (§5).

### Mobile

- **Images:** `CachedImage` (expo-image) for every remote URI — disk + memory cache, blurhash
  placeholder, crossfade. Raw `<Image>` re-downloads on every mount.
- **Perceived speed:** `Skeleton` presets that mirror the real card layout on first load. A
  skeleton reads as meaningfully faster than a spinner for the same wait.
- **Lists and markers:** explicit `memo` comparators listing only render-affecting fields.
  `ArtifactMarker.tsx` is the reference: markers are rebuilt wholesale on every nearby fetch, so
  a default shallow compare re-renders every pin on every poll.
- **Map specifically:** `tracksViewChanges` must be `false` while a marker is static. Keeping it
  true forces the native map to re-snapshot each marker every frame — the single biggest Android
  map cost. `ArtifactMarker` turns it on for 350 ms when range/unlock state changes, then off.
- **Hot paths stay silent:** no `console.log` in render, network interceptors, or WS handlers.
  In dev they serialize objects on every frame; in production they are dead weight.
