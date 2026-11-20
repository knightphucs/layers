# 🚀 LAYERS — Production Readiness

> Status as of **Week 9 Day 4 (in progress)**. Every item below was verified against the code,
> not assumed. Each entry names the file and line so you can go straight there.
>
> **This is the first file to open when returning to launch work.**

LAYERS is being built to run as a real product with real users and real money. The feature work
is far ahead of the operational work: 108 endpoints and a full mobile app exist, but there is
currently **no deployment path, no CI, no crash reporting, and push notifications are never
actually sent**. The list below is what stands between the current build and a launch you would
not be embarrassed by.

> **Fixed on 2026-08-26** and removed from this list: production API URL missing the `/api/v1`
> prefix; `create_all` competing with Alembic; config defaults that could not reach the compose
> database; the `/api/v1/` info endpoint's hand-maintained counts; the test runner pointing at a
> nonexistent file.
>
> **Fixed on 2026-09-05** (Week 9 Day 4 performance pass): seven duplicate indexes dropped
> (migration `w9d4_perf_002`, 23% faster fog writes); `xp_events (user_id, event_type)` added
> (`w9d4_perf_001`, badge evaluation 17.3 ms → 5.0 ms); `TEST_DATABASE_URL` added to
> `backend/.env`; rate-limit counters reset between tests, taking the suite from 97 collection
> errors to 429 passing.

---

## 🔴 Blockers — cannot launch without these

### B1. No deployment path exists

- The `backend` service in `docker-compose.yml` is entirely commented out (lines 58–77).
- No `mobile/eas.json`, so `eas build` has nothing to read.
- `backend/Dockerfile` exists but is never built by anything.
- No hosting target, no TLS termination, no process manager, no secrets store chosen.

*Fix:* pick a host, uncomment/adapt the backend service, add `eas.json` with development /
preview / production profiles, and decide where `JWT_SECRET_KEY` and DB credentials live.

Note the production API URL now reads `EXPO_PUBLIC_API_URL` with a sane default, so the deploy
only needs to set that env var per build profile — no code change.

### B2. Push notifications are never sent

`backend/app/services/notification_service.py:266`

```python
# TODO: Implement actual Expo Push API call
# For now, we log and store in history
```

Device tokens, preferences, quiet hours, categories, and history all work end to end. The final
HTTP call to Expo's push service is missing, so users receive **nothing**. The mobile app's
notification UI is fully built and will look broken to a real user.

*Fix:* POST to `https://exp.host/--/api/v2/push/send` with batched tickets, then handle the
receipt endpoint to prune `DeviceInstalled`/`InvalidCredentials` tokens.

### B3. App identity is placeholder

`mobile/app.json`

```json
"name": "mobile",
"slug": "mobile",
"android": { "usesCleartextTraffic": true }
```

`name` and `slug` are literally `"mobile"` — that is the store listing name and the EAS project
slug. `usesCleartextTraffic: true` permits plain HTTP on Android; it exists for LAN dev testing
and must not ship. Google Play flags it, and it makes every token interceptable on a hostile
network.

*Fix:* real name/slug/bundle identifiers, `usesCleartextTraffic` false (or dev-profile only),
plus the store metadata Expo needs: privacy policy URL, permission usage strings for location and
notifications, icons at required sizes.

---

## 🟠 High — fix before real users, not necessarily before first build

### H1. No CI

No `.github/` directory. 26 test files exist and nothing runs them automatically. Every
regression is caught by hand, or not at all.

*Blocked by M1* — the suite needs a live Postgres+PostGIS, so CI requires a service container.

### H2. No crash or error reporting

Three separate places already point at the gap:

- `mobile/App.tsx` — `// TODO: Sentry.captureException(error);` in the error boundary
- `mobile/src/utils/errorHandler.ts:172`
- `mobile/src/components/map/StatusOverLays.tsx:164`

A production crash on a user's phone is currently invisible to you. `backend/app/core/timing.py`
already logs slow requests in a Sentry-friendly shape — wire the SDK on both sides.

### H3. Image moderation is a stub

`backend/app/services/moderation_service.py:293` and `backend/app/workers/image_scan_worker.py`.
`scan_image()` returns FLAG for every photo by design, so **every PHOTO artifact stays PENDING until a human
opens the admin panel**. This is safe (nothing bad auto-publishes) but it does not scale past a
handful of users, and photo posters see their content never appear.

*Fix:* wire a real scanner (NudeNet locally, or Rekognition / Vision API) behind the existing
`scan_image` interface — only that function changes — and schedule `run_scan_batch()`.

### H4. No token revocation

A stolen JWT stays valid for its full lifetime (30 min access, **7 days refresh**). There is no
blacklist, and changing a password does not invalidate existing sessions.

*Fix:* Redis blacklist keyed by `jti`, checked in `verify_access_token`, plus a
`tokens_valid_after` timestamp on the user row bumped on password change.

### H5. Production secret hygiene is untested

`backend/app/core/security_hardening.py` has `validate_production_secrets()` and refuses to boot
with default secrets when `DEBUG=False` — good. But nothing has ever actually booted with
`DEBUG=False`, so the whole production path (docs disabled, HSTS on, TrustedHost active,
CORS allowlist enforced) is unexercised.

*Fix:* boot once with `DEBUG=False` and real values, and confirm the app starts and serves.

### H6. Media storage bucket is world-readable

`backend/app/core/storage.py` — `_ensure_bucket()` applies a bucket policy granting
`s3:GetObject` to `Principal: {"AWS": ["*"]}`. Every uploaded avatar, photo artifact, and voice
note is publicly readable by URL, forever.

Object names are UUIDs so they cannot be enumerated, but that is obscurity, not access control:
a shared or leaked URL bypasses geo-lock, TARGETED visibility, and artifact deletion. For an app
whose entire premise is that content is locked to a place and sometimes to one recipient, this
undercuts the product promise, not just the security posture.

*Fix:* private bucket + presigned URLs with short expiry, generated per authorized request.
Optionally split buckets: avatars public, artifact media private.

### H7. Anti-cheat checks are skipped by a wall-clock cooldown

`app/services/anti_cheat_service.py:385` gates the whole analysis on
`ANTI_CHEAT_COOLDOWN_SECONDS = 5`, measured against `datetime.utcnow()` — real elapsed time
between API calls, not the timestamps in the payload. Any client that sends location updates
less than 5 s apart has every check after the first one skipped: the point is still appended to
history, and the function returns `is_clean=True` with no violations. The mobile location watcher
already ticks at 5 s, so this fires in normal use, and a spoofer only has to update faster.

Four tests demonstrate it end to end: `test_teleport_after_walking`,
`test_teleport_between_districts`, `test_desk_spoofer_caught`, `test_legitimate_then_cheat` all
walk normally, then teleport 8 km, and get `CheatDetectionResult(is_clean=True, violations=[])`.

*Fix:* key the cooldown on `metadata.timestamp` rather than wall clock, or drop the cooldown and
address the concurrent-call false positives it was added for at the source. Either way this is a
behaviour change to a ban path — decide the semantics deliberately.

### H8. The teleport rule is unreachable in practice

`app/services/anti_cheat_service.py:236` — `if distance_km > TELEPORT_THRESHOLD_KM and
time_diff <= 1.0`. Two GPS points a real device sends are essentially never *exactly* ≤ 1.000 s
apart, so the branch loses to the `IMPOSSIBLE_SPEED` branch below it. The difference matters:
`TELEPORT_DETECTED` sets `severity="critical"` and `should_ban=True` (line 411), while
`IMPOSSIBLE_SPEED` only sets `"suspicious"`. `test_teleport_instant` moves 10 km in ~1.00007 s and
gets the suspicious path — a teleporting user is not banned.

*Fix:* widen the window (a few seconds) or key the severity on speed rather than on an exact
1-second boundary.

### H9. create_all and Alembic produce different schemas

`layers_db`, built by `init_db()`'s `create_all` under `DEBUG=True`, was missing **24 indexes**
that `alembic upgrade head` creates on a fresh database — including partial indexes on
`users.is_banned` / `banned_until`, `artifacts` status/visibility indexes, and the GiST index on
`chat_rooms.center_geom`. Production runs migrations, so local EXPLAIN output is measured against
a schema production will not have, and any index audit run locally is misleading.

Verify with `backend/scripts/perf_audit.sql` §4c, which diffs the two.

*Fix:* stop treating the dev database as representative — rebuild it from `alembic upgrade head`,
or accept that performance work has to happen against a migrated database.

---

## 🟡 Medium — quality and correctness debt

### M1. Test suite still duplicates its fixtures

`backend/tests/conftest.py` now carries an autouse fixture that clears the rate-limit counters
between tests and a guard rail that refuses to run if `TEST_DATABASE_URL` resolves to the dev
database. That took the suite from 97 collection errors to **429 passing, 6 failing** (the 6 are
H7/H8 above, plus `test_rapid_updates`, which asserts behaviour the code deliberately changed —
sub-0.5 s updates are documented as *not* a violation at `anti_cheat_service.py:220`).

Still outstanding: every test file builds its own engine and runs `drop_all`/`create_all`, so the
suite needs a live PostGIS instance and duplicates ~30 lines of fixture per file.

*Fix:* lift the client/db fixtures into `conftest.py`; that also unblocks H1.

### M2. User blocking has no tests

`app/api/v1/users.py` + `app/services/block_service.py` (Week 9 Day 3) ship without a test file,
unlike every other domain. Blocking is a safety feature; a silent regression there is a real-user
harm, not a cosmetic bug.

### M3. Profile stats are partly fake

`mobile/src/services/profile.ts:177` — `replies_received: 0, // TODO: Add dedicated endpoint`.
A user's profile shows a number that is always zero.

---

## ✅ Already in good shape

Worth stating, so the list above is not read as "nothing works":

- **Graceful degradation.** Every Redis path fails open — cache, rate limits, presence, WS pub/sub.
  A Redis outage degrades the app instead of taking it down.
- **Multi-worker correctness.** `ws_manager` bridges WebSocket broadcasts through Redis pub/sub,
  and rate limiting is Redis-backed, so scaling past one worker will not silently break chat or
  multiply the effective rate limits.
- **Auth.** bcrypt, short-lived access tokens, hashed and expiring reset tokens, email-enumeration
  resistance, per-endpoint brute-force limits.
- **Security headers and CORS** are settings-driven with production defaults that refuse `*`.
- **Trust-weighted moderation.** Reports weigh by reporter reputation, so throwaway accounts
  cannot mass-hide a rival's content.
- **Anti-cheat** is implemented, not just designed: mock-GPS flag, jump detection, drop limits.
- **Client resilience.** Axios refresh-token queue, WebSocket reconnect with backoff, offline
  banner, error boundary.
- **Account deletion is real.** `DELETE /auth/me/delete` requires password confirmation, then
  anonymizes PII and removes artifacts — the thing app stores and privacy regulators ask about,
  already built rather than promised.

---

## Launch sequence

1. **Close B1–B3.** Nothing else matters until a production build can talk to a deployed backend.
2. **M1 → H1.** Shared fixtures, then CI running pytest on every push.
3. **H2.** Sentry on both sides — you need eyes on production before you have users.
4. **H5.** One clean `DEBUG=False` boot against production-shaped config.
5. **Build.** `eas build --profile production`, submit to TestFlight and Play internal testing.
6. **Small closed beta** in one city district. Watch the 🐌 slow-request warnings and Sentry.
7. **H6** before any private media goes live; **H3, H4, M2–M3** during beta.
8. **Staged rollout.**

---

## How to keep this file honest

Update it whenever an item is fixed — delete the entry rather than marking it done, so the file
stays a to-do list and not a changelog. When adding an item, always include `file:line`, the
user-visible consequence, and a fix sketch. An entry without a consequence is a preference, not a
blocker, and does not belong here.
