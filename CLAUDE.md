# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

> **Keep in sync with `AGENTS.md`.** The two files are intentional mirrors — same content,
> different addressee. If you change one, change the other in the same commit.

---

## 1. What LAYERS is

A location-based social network with a dual-layer experience. Users discover and leave
**artifacts** (letters, voice notes, photos, vouchers, time capsules) anchored to real GPS
coordinates. You must physically walk within 50 m of an artifact to open it. The map starts
covered in fog and clears as you explore. **Light layer** is public and warm; **Shadow layer**
is nocturnal, mysterious, and time-gated.

This is a solo-built product heading for a real production launch with paying users — not a
learning exercise. Treat data loss, auth holes, and silent failures as launch blockers, not
TODOs. Before shipping anything user-facing, read `docs/PRODUCTION_READINESS.md`.

### Current build state — Week 9, Day 4 (complete, uncommitted)

<!-- UPDATE THIS SECTION when the week/day advances. It is the only part of this file
     that is time-sensitive, and it is deliberately placed first so it is hard to forget. -->

Shipped through Week 9 Day 3: auth, geo/PostGIS map, artifacts, fog of war, anti-cheat,
notifications plumbing, connections, WebSocket chat + campfires, social spark, campfire games,
XP/quests/badges/leaderboards, moderation, reports/reputation, admin panel, security hardening,
shadow layer, onboarding/story mode, inbox with letter reader, and user blocking.

**Day 4 is the performance pass and is done but uncommitted.** A large diff across `mobile/src/`
plus new backend files is that work, not stray edits:

| Piece | Location |
| --- | --- |
| Request timing middleware — `X-Response-Time` header, 🐌 warn over 300 ms | `backend/app/core/timing.py` |
| Postgres audit script — inventory → seq-scan smell → EXPLAIN → recorded verdicts | `backend/scripts/perf_audit.sql` |
| `xp_events (user_id, event_type)` composite — badge eval 17.3 ms → 5.0 ms | migration `w9d4_perf_001` |
| Seven duplicate indexes dropped — fog writes 23% faster | migration `w9d4_perf_002` |
| Rate-limit reset between tests + `TEST_DATABASE_URL` guard rail | `backend/tests/conftest.py` |
| `CachedImage` — expo-image wrapper, disk cache + blurhash, replaces raw `<Image>` | `mobile/src/components/common/CachedImage.tsx` |
| `Skeleton` loaders mirroring real card layouts | `mobile/src/components/common/Skeleton.tsx` |
| Tighter `ArtifactMarker` memo comparator + managed `tracksViewChanges` | `mobile/src/components/map/ArtifactMarker.tsx` |
| `console.log` removed from axios / WebSocket / store hot paths | `mobile/src/services/`, `mobile/src/store/` |

The `/api/v1/` info endpoint now derives `endpoints_total` from `api_router.routes` instead of
a hand-maintained number (it had drifted 95 → 108 unnoticed). Bump its `week`/`day` when you close
the day.

**What the perf audit turned up, beyond the planned work.** Three findings that are not
performance bugs and are deliberately not fixed here — they change ban behaviour or dev workflow
and need a decision. Written up as H7/H8/H9 in `docs/PRODUCTION_READINESS.md`:

- The anti-cheat cooldown (`anti_cheat_service.py:385`) keys on wall clock, not on the payload
  timestamps, so a client updating faster than 5 s has every check after the first one skipped.
- The teleport rule (`anti_cheat_service.py:236`) requires `time_diff <= 1.0` exactly, which real
  GPS never satisfies, so teleporters land on the non-banning `IMPOSSIBLE_SPEED` path instead.
- `create_all` and Alembic build different schemas: `layers_db` was short 24 indexes that a fresh
  `alembic upgrade head` creates. **EXPLAIN against the dev database is not measuring the schema
  production will have** — seed a migrated database instead (`perf_audit.sql` §4c diffs them).

The test suite runs now — 429 passing, 6 failing, where the 6 are the two anti-cheat bugs above
plus one stale assertion. Before Day 4 it could not connect at all: `TEST_DATABASE_URL` was
missing from `backend/.env`, so it fell back to the placeholder password in `config.py`.

---

## 2. Repo map

```
backend/
  app/
    api/v1/       19 route modules + router.py (registers them all)
    schemas/      Pydantic request/response models, one file per domain
    services/     ALL business logic. Static-method classes. Routes stay thin.
    models/       SQLAlchemy 2.0 ORM — 28 model classes in 16 modules, 28 tables
    core/         config, database, security, cache, rate limits, WS manager, storage
    admin/        SQLAdmin panel mounted at /admin (auth.py, views.py, setup.py)
    workers/      image_scan_worker.py — standalone/cron batch, deliberately NOT Celery
    utils/        geo math, anti-cheat helpers, shadow time windows
  alembic/versions/   21 migrations — the schema source of truth
  tests/              26 pytest files (need a live Postgres+PostGIS, see §7)
  scripts/            perf_audit.sql, benchmark.py, verify_db.py, optimize_database.py
mobile/
  src/
    screens/      auth/ (3), main/ (15), onboarding/ (4)
    components/   by domain: map/ chat/ inbox/ profile/ game/ spark/ common/ ...
    services/     14 API modules, all on the shared axios instance in api.ts
    store/        12 Zustand stores
    hooks/        location, notifications, fog of war, network status, map perf
    navigation/   Root → Auth | Onboarding | Main, plus navigationRef for deep links
    types/        shared TS types, mirrors backend schemas
    constants/    colors.ts (Light/Shadow palettes), config.ts (API URL, geo constants)
docs/             API reference, architecture, production readiness, security checklist
```

---

## 3. Backend: the path every request takes

```
app/api/v1/<domain>.py     route, auth dependency, HTTP status codes
        ↓
app/schemas/<domain>.py    Pydantic validation in and out
        ↓
app/services/<domain>_service.py   ALL business logic (static methods on a class)
        ↓
app/models/<domain>.py     SQLAlchemy model
```

Routes must stay thin: validate, call a service, shape the response. Business rules that live
in a route instead of a service are a review defect.

**Auth dependency — non-obvious import.** There is no `deps.py`. `get_current_user` lives in
the auth route module:

```python
from app.api.v1.auth import get_current_user   # also: get_current_user_optional
```

It rejects invalid tokens with 401 and banned/inactive accounts with 403.

**Database session:**

```python
from app.core.database import get_db
async def endpoint(db: AsyncSession = Depends(get_db)): ...
```

`get_db` commits on success and rolls back on exception — do not add your own commit at the end
of a route.

### Feature domains — find anything in one hop

| Route module | Prefix | Service | Model | Tests |
| --- | --- | --- | --- | --- |
| `auth.py` | `/auth` | `auth_service` | `user` | `test_auth` |
| `map.py` | `/map` | `location_service` | `location` | `test_locations` |
| `artifacts.py` | `/artifacts` | `artifact_service` | `artifact` | `test_artifacts` |
| `explore.py` | `/explore` | `exploration_service` | `location.ExploredChunk` | `test_exploration` |
| `anti_cheat.py` | `/anti-cheat` | `anti_cheat_service` | `user` (cheat cols) | `test_anti_cheat` |
| `health.py` | `/health` | — | — | — |
| `notifications.py` | `/notifications` | `notification_service` | `notification` | `test_notifications` |
| `connections.py` | `/connections` | `connection_service` | `connection` | `test_connections` |
| `files.py` | `/files` | `core/storage.py` | — | — |
| `chat.py` | `/chat` | `chat_service` | `chat` | `test_chat_rest`, `test_chat_websocket`, `test_campfire`, `test_ws_pubsub` |
| `game.py` | `/chat` ⚠️ shared | `game_service` | `game` | `test_truth_or_dare` |
| `social_spark.py` | `/spark` | `social_spark_service` | `social_spark` | `test_social_spark` |
| `xp.py` | `/xp` | `xp_service` | `xp_event` | `test_xp_service` |
| `quests.py` | `/quests` | `quest_service` | `quest_completion` | `test_quest_service` |
| `gamification.py` | `/badges`, `/leaderboard` ⚠️ no prefix | `badge_service`, `leaderboard_service` | `user_badge` | `test_gamification` |
| `moderation.py` | `/moderation` | `moderation_service` | `moderation_log` | `test_moderation` |
| `reports.py` | `/reports` | `report_service`, `reputation_service` | `report` | `test_reputation`, `test_week8_integration` |
| `shadow.py` | `/shadow` | `shadow_service` | `glitch_zone` | `test_shadow` |
| `users.py` | `/users` | `block_service` | `user_block` | ⚠️ none yet |

⚠️ Two prefix quirks, both intentional — do not "clean them up", the mobile client depends on
the current paths: `game.py` shares the `/chat` prefix (campfire games are nested under a room),
and `gamification.py` declares no prefix at all, serving `/badges/me`, `/badges/sync`, and
`/leaderboard`.

---

## 4. Cross-cutting infrastructure (`app/core/`)

| Module | Responsibility |
| --- | --- |
| `config.py` | Pydantic settings from `backend/.env`. Import the `settings` singleton. |
| `database.py` | Async engine, `AsyncSessionLocal`, `get_db`, `Base` |
| `security.py` | JWT create/verify, bcrypt hashing |
| `security_hardening.py` | CORS allowlist, security headers, trusted hosts, prod secret validation |
| `rate_limit.py` | Global sliding-window limiter (middleware, all traffic) |
| `endpoint_rate_limit.py` | Tighter per-route buckets for auth endpoints (`Depends(rate_limit(...))`) |
| `cache.py` | JSON-over-Redis helpers: `cache_get_or_set`, `cache_delete_pattern` |
| `geo_cache.py` | Quantized cache keys for PostGIS reads. `fog:` TTL 20 s, `nearby:` TTL 15 s |
| `ws_manager.py` | WebSocket registry + Redis pub/sub bridge |
| `presence.py` | Redis-backed online/in-campfire presence across workers |
| `storage.py` | MinIO uploads (avatars, photos, voice) |
| `redis_client.py` | Connection lifecycle, `get_optional_redis()` |
| `timing.py` | Request duration header + slow-request warnings |

### Two invariants you must not break

**1. Redis is optional, always.** Every Redis path degrades instead of raising: cache misses
fall through to Postgres, rate limiters fail *open*, WebSocket broadcast falls back to local
sockets. If you add Redis code, wrap it so a Redis outage cannot 500 a request.

**2. WebSocket broadcasts go through `manager.broadcast()`, never a local socket loop.**
`manager.broadcast()` publishes to the Redis channel `ws:room:{room_id}`; every worker's
listener delivers to its own sockets. Writing directly to `manager.active[room]` silently drops
messages for users connected to a different worker. Same for `ws:user:{id}`.

### Middleware order in `main.py`

Starlette wraps the **last-added middleware outermost**. Current order of `add_middleware`
calls: security headers → CORS → rate limit → timing. `TimingMiddleware` is added last on
purpose so it measures the entire stack. Adding middleware in the wrong place changes what gets
measured and what gets rate limited.

---

## 5. Geo-spatial patterns

- All proximity queries use PostGIS `ST_DWithin` on a `Geography` column, SRID 4326 (WGS84).
- **`ST_MakePoint(longitude, latitude)` — longitude first.** This is the single most common bug
  in geo code. `Location.create_point_wkt()` handles the ordering for you; use it.
- `GEO_LOCK_RADIUS=50` m — proof-of-presence radius to open an artifact.
- `DEFAULT_NEARBY_RADIUS=1000` m — default search radius.
- **Fog of war** grid, tuned at Ho Chi Minh City latitude (~100 m cells):
  ```
  chunk_x = int(longitude / 0.000917)
  chunk_y = int(latitude  / 0.0009)
  ```
  The client batches GPS points every 30 s → `POST /explore/batch` (max 50 points).
- Anti-cheat: OS mock-location flag, >5 km/s jump detection, 3 artifact drops/day, 20 m minimum
  spacing between drops.

---

## 6. Mobile conventions

- **Every API call goes through `src/services/api.ts`.** That axios instance carries the auth
  header, the refresh-token queue (concurrent 401s wait on one refresh), and error normalization
  via `getErrorMessage`. Never import bare `axios` in a feature module.
- **Tokens** live in `expo-secure-store` under `access_token` / `refresh_token` / `user`.
- **State**: one Zustand store per domain in `src/store/`. Async actions live in the store;
  screens stay presentational.
- **Navigation**: `RootNavigator` switches on `isAuthenticated` → `hasCompletedOnboarding`.
  Notification deep links go through `src/navigation/navigationRef.ts` (queues navigation if the
  container is not ready yet).
- **Theming**: `Colors[layer.toLowerCase()]` from `constants/colors.ts`. Every new surface must
  render correctly in both Light and Shadow — a hardcoded light grey blinds a Shadow user at 2am.
- **API base URL** is resolved at runtime in `constants/config.ts`: `EXPO_PUBLIC_API_HOST` env
  → Expo `hostUri` LAN IP → `10.0.2.2` (Android emulator) → `localhost`.

### Performance conventions (Week 9 Day 4 — now in force)

- Remote images use `<CachedImage uri={...} />` from `components/common`, never RN `<Image>`.
- First-load states use a `Skeleton` preset, not a bare `ActivityIndicator`.
- List rows and map markers get an explicit `memo` comparator listing only render-affecting
  fields — see `ArtifactMarker.tsx` for the reference implementation.
- No `console.log` in render paths, network interceptors, or WebSocket handlers.

---

## 7. Commands

### Infrastructure

```bash
docker-compose up -d       # postgres :5433, redis :6379, minio :9000/:9001
docker-compose down -v     # destroys volumes — you lose local data
```

⚠️ Postgres is published on **5433**, not 5432. Requires a root `.env` with
`POSTGRES_PASSWORD`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`. The compose DB user is
`layers_admin`; the defaults in `app/core/config.py` now match that, but the password there is a
placeholder — always set `DATABASE_URL` in `backend/.env`.

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head                    # REQUIRED before first run
uvicorn app.main:app --reload
uvicorn app.main:app --host 0.0.0.0 --port 8000   # for testing on a physical device
```

Swagger `/docs` and ReDoc `/redoc` are served **only when `DEBUG=True`**. Admin panel: `/admin`.

### Migrations

```bash
alembic revision --autogenerate -m "w9d4_short_description"
alembic upgrade head
alembic downgrade -1
```

Always read the generated migration before applying it — autogenerate has missed foreign keys
in this repo before (see commit `3f71ba9`, which had to backfill them).

### Tests

```bash
cd backend
pytest                       # all 26 files
pytest tests/test_auth.py -v
```

Tests need a live Postgres + PostGIS at `TEST_DATABASE_URL`; each file builds its own engine and
runs `drop_all`/`create_all`. **That drop is real** — `TEST_DATABASE_URL` must point at a
throwaway database, never at `layers_db`. `conftest.py` aborts the run if it resolves to the same
URL as `DATABASE_URL`. Create the database once:

```bash
docker compose exec postgres createdb -U layers_admin layers_test_db
```

**`TEST_DATABASE_URL` must be set in `backend/.env`.** If it is missing, `config.py`'s default
kicks in — and its password is a placeholder, so every test fails with
`InvalidPasswordError` rather than anything that points at the real problem.

`tests/conftest.py` holds an autouse fixture that clears the rate-limit counters before each test.
Without it the suite 429s itself: `RateLimitMiddleware` allows 5 registrations per 5 minutes per
IP, every test client shares one IP, and httpx's `ASGITransport` skips the lifespan so the
limiter falls back to a process-wide in-memory store that no Redis flush can reach. A test that
needs several registrations in one test body has to clear the counters between calls itself — see
the `register` helper in `tests/test_week8_integration.py`.

Each file still duplicates its own engine/client fixtures. There is no CI.

### Mobile

```bash
cd mobile
npm install
npx expo start          # --android | --ios | --web
npx expo start -c       # clear cache when Metro acts strange
```

---

## 8. Conventions and known traps

- **Async everywhere on the backend.** `async def` + `await` for every DB call. A sync DB call
  blocks the entire event loop.
- **Migrations are the schema source of truth.** `init_db()` in `core/database.py` still runs
  `create_all`, but only when `DEBUG=True` — it is a local-dev convenience. With `DEBUG=False` it
  is a no-op, so a model change with no migration fails loudly instead of running against a
  mismatched schema. The deploy step is `alembic upgrade head`.
- **Register every new model in `app/models/__init__.py`.** If it is not imported there, Alembic
  autogenerate will not see it and will silently produce an empty migration.
- **Register every new router in `app/api/v1/router.py`.** Creating the module is not enough.
- **New service = new file in `app/services/`**, static methods on a class, matching the
  existing pattern (`AuthService`, `ArtifactService`, `ChatService`, …).
- **Backend comments are in English**, with occasional Vietnamese in security notes. Match the
  surrounding file. Module docstrings in this codebase explain *why*, not *what* — keep that.
- Adding a backend feature end to end? Use the `/add-backend-feature` skill in
  `.claude/skills/` — it encodes the full order of operations including the mobile side.

---

## 9. Reference docs

| File | What it is for |
| --- | --- |
| `docs/PRODUCTION_READINESS.md` | **Read before any launch work.** Every known blocker, with file:line |
| `docs/ARCHITECTURE.md` | Data model reference, request/WS lifecycle, pipelines, perf playbook |
| `docs/API_DOCUMENTATION.md` | All 107 endpoints, grouped by module |
| `docs/SECURITY_CHECKLIST.md` | Security posture, what is done and what is not |
| `README.md` | Human-facing overview, quick start, roadmap |
