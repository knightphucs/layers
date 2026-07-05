# 📖 LAYERS API Documentation

> Version: 1.0.0 (Week 8 Day 5) | Base URL: `http://localhost:8000/api/v1`
> 92 endpoints across 18 route modules + 1 WebSocket endpoint + a separate SQLAdmin panel at `/admin`.

---

## 🔐 Authentication

All protected endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer <access_token>
```

Tokens are short-lived (access: 30 min, refresh: 7 days). A request with an invalid/expired
token gets `401`; a banned or deactivated account gets `403` even with a valid token.

The WebSocket endpoint (`/chat/ws/{room_id}`) is the one exception — it takes the JWT as a
**query parameter** (`?token=...`), not a header, since browsers/RN can't set headers on the
WS handshake. See [Chat & WebSocket](#-chat--campfire-chatpy) below.

---

## 📋 Endpoints Overview

Legend: ✅ = Bearer token required · 🔓 = no auth · 🛡️ = admin only.

### Authentication (`/auth`)

| Method | Endpoint                          | Auth | Description                                |
| ------ | --------------------------------- | ---- | ------------------------------------------ |
| POST   | `/auth/register`                  | 🔓   | Create new account (rate-limited 3/hour)   |
| POST   | `/auth/login`                     | 🔓   | Login, get tokens (rate-limited 5/min)     |
| POST   | `/auth/refresh`                   | 🔓   | Refresh access token                       |
| POST   | `/auth/password-reset/request`    | 🔓   | Request password reset (rate-limited 3/hr) |
| POST   | `/auth/password-reset/confirm`    | 🔓   | Confirm password reset                     |
| POST   | `/auth/change-password`           | ✅   | Change password (requires current)         |
| GET    | `/auth/me`                        | ✅   | Get current user profile                   |
| PUT    | `/auth/me`                        | ✅   | Update profile                             |
| DELETE | `/auth/me`                        | ✅   | Deactivate account                         |
| POST   | `/auth/logout`                    | ✅   | Logout (stateless JWT — logs it only)      |
| GET    | `/auth/check-email/{email}`       | 🔓   | Check email availability                   |
| GET    | `/auth/check-username/{username}` | 🔓   | Check username availability                |
| POST   | `/auth/avatar`                    | ✅   | Upload avatar (multipart, max 5MB)         |

### Map / Locations (`/map`)

| Method | Endpoint              | Auth | Description                                        |
| ------ | --------------------- | ---- | -------------------------------------------------- |
| POST   | `/map/locations`      | ✅   | Create a new location                              |
| GET    | `/map/nearby`         | ✅   | Geo-query: nearby locations (PostGIS `ST_DWithin`) |
| GET    | `/map/nearby/count`   | ✅   | Quick count of nearby locations                    |
| GET    | `/map/locations/mine` | ✅   | Locations created by current user                  |
| GET    | `/map/locations/{id}` | ✅   | Single location detail                             |
| PATCH  | `/map/locations/{id}` | ✅   | Update a location (owner only)                     |
| DELETE | `/map/locations/{id}` | ✅   | Soft delete a location (owner only) → 204          |

### Artifacts (`/artifacts`)

| Method | Endpoint                            | Auth | Description                                      |
| ------ | ----------------------------------- | ---- | ------------------------------------------------ |
| POST   | `/artifacts`                        | ✅   | Drop an artifact at current GPS position         |
| GET    | `/artifacts/nearby`                 | ✅   | Artifact previews for map markers (locked <50m)  |
| GET    | `/artifacts/mine`                   | ✅   | Artifacts created by current user                |
| GET    | `/artifacts/{id}`                   | ✅   | Full detail if unlocked                          |
| POST   | `/artifacts/{id}/unlock`            | ✅   | Unlock a PASSCODE artifact                       |
| POST   | `/artifacts/{id}/reply`             | ✅   | Reply via Slow Mail (6–12h delayed delivery)     |
| POST   | `/artifacts/{id}/report`            | ✅   | Report inappropriate content                     |
| DELETE | `/artifacts/{id}`                   | ✅   | Soft delete (owner only) → 204                   |
| PATCH  | `/artifacts/{id}/unlock-conditions` | ✅   | Owner-only: edit/remove the Midnight Lock window |
| POST   | `/artifacts/paper-plane`            | ✅   | Throw a paper plane (lands 200m–1km away)        |
| POST   | `/artifacts/time-capsule`           | ✅   | Create a time capsule (unlocks at a future date) |

### Fog of War (`/explore`)

| Method | Endpoint               | Auth | Description                                           |
| ------ | ---------------------- | ---- | ----------------------------------------------------- |
| POST   | `/explore`             | ✅   | Mark current ~100m chunk as explored (idempotent)     |
| POST   | `/explore/batch`       | ✅   | Process a GPS trail (max 50 points)                   |
| GET    | `/explore/chunks`      | ✅   | Explored chunks within a viewport (for fog rendering) |
| GET    | `/explore/stats`       | ✅   | Exploration stats (area, % of city, recent chunks)    |
| GET    | `/explore/heatmap`     | ✅   | Community heatmap of explored areas                   |
| GET    | `/explore/leaderboard` | ✅   | Top explorers leaderboard                             |

### Anti-Cheat (`/anti-cheat`)

| Method | Endpoint                            | Auth | Description                                         |
| ------ | ----------------------------------- | ---- | --------------------------------------------------- |
| POST   | `/anti-cheat/validate`              | ✅   | Test detection logic on submitted location metadata |
| GET    | `/anti-cheat/my-status`             | ✅   | Own ban status, strike count, last known position   |
| GET    | `/anti-cheat/admin/log/{user_id}`   | 🛡️   | A user's cheat log + last 20 location points        |
| POST   | `/anti-cheat/admin/ban/{user_id}`   | 🛡️   | Manually ban a user                                 |
| POST   | `/anti-cheat/admin/unban/{user_id}` | 🛡️   | Manually unban a user, resets strikes               |
| GET    | `/anti-cheat/admin/stats`           | 🛡️   | System-wide anti-cheat stats                        |

### Health (`/health`)

| Method | Endpoint           | Auth | Description                                                    |
| ------ | ------------------ | ---- | -------------------------------------------------------------- |
| GET    | `/health`          | 🔓   | Quick health check                                             |
| GET    | `/health/detailed` | 🛡️   | Postgres/Redis/PostGIS status, geo-query benchmark, row counts |

### Push Notifications (`/notifications`)

| Method | Endpoint                      | Auth | Description                                 |
| ------ | ----------------------------- | ---- | ------------------------------------------- |
| POST   | `/notifications/device-token` | ✅   | Register an Expo push token for this device |
| DELETE | `/notifications/device-token` | ✅   | Unregister a device token                   |
| GET    | `/notifications/preferences`  | ✅   | Get notification preferences                |
| PUT    | `/notifications/preferences`  | ✅   | Partial update of preferences               |
| GET    | `/notifications/history`      | ✅   | Recent notifications, paginated             |
| POST   | `/notifications/read`         | ✅   | Mark notification IDs as read               |
| POST   | `/notifications/clear-badge`  | ✅   | Clear badge count (currently a no-op stub)  |

> ⚠️ **Known gap:** the device-token/preferences/history plumbing is fully built, but the actual
> outbound push call in `notification_service.py::send_to_user` is still a
> `# TODO: Implement actual Expo Push API call` — it logs and stores history but doesn't push yet.

### Connections (`/connections`)

| Method | Endpoint                    | Auth | Description                                                  |
| ------ | --------------------------- | ---- | ------------------------------------------------------------ |
| GET    | `/connections`              | ✅   | List connections (optional `level` filter), paginated        |
| GET    | `/connections/stats`        | ✅   | Counts per level + pending upgrade requests                  |
| POST   | `/connections/{id}/request` | ✅   | Request upgrade SIGNAL → CONNECTED (auto-upgrades if mutual) |
| POST   | `/connections/{id}/accept`  | ✅   | Accept an incoming upgrade request                           |
| POST   | `/connections/{id}/reject`  | ✅   | Reject an upgrade request                                    |

> Note: there is no "create connection" endpoint — connections are created automatically the
> first time you reply to someone's artifact (`ArtifactService.reply_to_artifact`).

### Files (`/files`)

| Method | Endpoint        | Auth | Description                                                      |
| ------ | --------------- | ---- | ---------------------------------------------------------------- |
| GET    | `/files/{path}` | 🔓   | Streams a stored object (e.g. avatar) from MinIO through the API |

### Chat & Campfires (`/chat`)

| Method | Endpoint                            | Auth | Description                                                     |
| ------ | ----------------------------------- | ---- | --------------------------------------------------------------- |
| GET    | `/chat/rooms`                       | ✅   | List current user's direct-message rooms                        |
| POST   | `/chat/rooms/direct`                | ✅   | Get-or-create a DM room (**requires CONNECTED status**)         |
| GET    | `/chat/rooms/{room_id}`             | ✅   | Room detail + recent messages                                   |
| GET    | `/chat/rooms/{room_id}/messages`    | ✅   | Paginated history, cursor via `before` (ISO datetime)           |
| POST   | `/chat/rooms/{room_id}/messages`    | ✅   | REST fallback send (also broadcasts to live WS clients)         |
| POST   | `/chat/campfires/find-or-create`    | ✅   | Find/create a campfire within 50m (rate-limited 1 create/10min) |
| POST   | `/chat/campfires/{room_id}/join`    | ✅   | Join a campfire (verifies proximity)                            |
| POST   | `/chat/campfires/{room_id}/leave`   | ✅   | Leave a campfire → 204                                          |
| GET    | `/chat/campfires/nearby`            | ✅   | Active campfires near (lat,lng) with live online count          |
| GET    | `/chat/campfires/{room_id}/members` | ✅   | Campfire members with online status                             |
| GET    | `/chat/ws/stats`                    | ✅   | Debug snapshot of the in-memory WS connection manager           |
| WS     | `/chat/ws/{room_id}?token={jwt}`    | ✅\* | Real-time chat + presence + typing (\*JWT via query param)      |

### Social Spark — boost / wave / synchronicity (`/spark`)

| Method | Endpoint                         | Auth | Description                                                          |
| ------ | -------------------------------- | ---- | -------------------------------------------------------------------- |
| POST   | `/spark/artifacts/{id}/boost`    | ✅   | Boost an artifact for 24h (wider discovery radius)                   |
| GET    | `/spark/boosts/quota`            | ✅   | Remaining boosts today                                               |
| GET    | `/spark/boosted-nearby`          | ✅   | Boosted artifacts near (lat,lng)                                     |
| POST   | `/spark/wave`                    | ✅   | Drop an anonymous "I'm here too" wave                                |
| GET    | `/spark/waves/nearby`            | ✅   | Anonymous count of active waves nearby                               |
| POST   | `/spark/artifacts/{id}/discover` | ✅   | Record an unlock; matches with others who discovered it <30min apart |
| GET    | `/spark/synchronicities`         | ✅   | Paginated synchronicity match history                                |

### Campfire Games — Truth or Dare (`/chat/campfires/{room_id}/game...`)

> Lives under the `/chat` prefix (same router group as chat), not a separate `/game` path.

| Method | Endpoint                                        | Auth | Description                                                        |
| ------ | ----------------------------------------------- | ---- | ------------------------------------------------------------------ |
| GET    | `/chat/campfires/{room_id}/game`                | ✅   | Current game state (404 if none)                                   |
| POST   | `/chat/campfires/{room_id}/game/start`          | ✅   | Start a game (creates first round)                                 |
| POST   | `/chat/campfires/{room_id}/game/answer`         | ✅   | Submit an answer for the current round                             |
| POST   | `/chat/campfires/{room_id}/game/move-to-voting` | ✅   | Close answering, open voting (starter only)                        |
| POST   | `/chat/campfires/{room_id}/game/vote`           | ✅   | Cast a vote (not for your own answer)                              |
| POST   | `/chat/campfires/{room_id}/game/reveal`         | ✅   | Tally votes, reveal winner (starter only) → winner gets XP + badge |
| POST   | `/chat/campfires/{room_id}/game/next-round`     | ✅   | Start next round (starter only)                                    |
| POST   | `/chat/campfires/{room_id}/game/end`            | ✅   | End the game (starter only)                                        |

### XP (`/xp`)

| Method | Endpoint      | Auth | Description                                        |
| ------ | ------------- | ---- | -------------------------------------------------- |
| GET    | `/xp/me`      | ✅   | Current XP / level / rank / progress to next level |
| GET    | `/xp/history` | ✅   | Paginated XP event log, cursor-based               |
| GET    | `/xp/rewards` | ✅   | Canonical XP-value table (event type → amount)     |

### Quests (`/quests`)

| Method | Endpoint        | Auth | Description                        |
| ------ | --------------- | ---- | ---------------------------------- |
| GET    | `/quests/today` | ✅   | Today's quests + progress + streak |

### Badges & Leaderboard — **no `/gamification` prefix**

> ⚠️ This router has no path prefix — its routes live directly at `/badges/*` and `/leaderboard`,
> not `/gamification/*`. Easy to get wrong.

| Method | Endpoint       | Auth | Description                                                            |
| ------ | -------------- | ---- | ---------------------------------------------------------------------- |
| GET    | `/badges/me`   | ✅   | All badges from the catalog with unlocked state/date                   |
| POST   | `/badges/sync` | ✅   | Re-evaluate badge criteria; returns newly-unlocked badges              |
| GET    | `/leaderboard` | ✅   | Ranked leaderboard, `scope=global\|weekly`, includes caller's own rank |

### Moderation (`/moderation`) — all admin only

| Method | Endpoint                            | Auth | Description                                                      |
| ------ | ----------------------------------- | ---- | ---------------------------------------------------------------- |
| GET    | `/moderation/queue`                 | 🛡️   | Review queue: PENDING / auto-HIDDEN artifacts, FIFO oldest-first |
| POST   | `/moderation/{artifact_id}/approve` | 🛡️   | Approve → ACTIVE, resets report_count                            |
| POST   | `/moderation/{artifact_id}/remove`  | 🛡️   | Confirm bad → DELETED, author reputation −30                     |
| GET    | `/moderation/logs`                  | 🛡️   | Recent moderation decisions                                      |
| GET    | `/moderation/stats`                 | 🛡️   | Queue-size overview                                              |
| POST   | `/moderation/scan-photos`           | 🛡️   | Trigger a batch image-scan worker run over pending photos        |

### Reports (`/reports`)

| Method | Endpoint                 | Auth | Description                                                      |
| ------ | ------------------------ | ---- | ---------------------------------------------------------------- |
| POST   | `/reports/{artifact_id}` | ✅   | Submit a content report (idempotent — one per user per artifact) |

### Shadow Layer (`/shadow`)

| Method | Endpoint               | Auth | Description                                                            |
| ------ | ---------------------- | ---- | ---------------------------------------------------------------------- |
| GET    | `/shadow/status`       | ✅   | Glitch-zone membership + effects + midnight-window status at (lat,lng) |
| GET    | `/shadow/midnight`     | ✅   | Is the 23:00–03:00 (HCMC time) window open right now? (city-wide)      |
| GET    | `/shadow/glitch-zones` | ✅   | Glitch zones near (lat,lng) for map overlay                            |
| POST   | `/shadow/glitch-zones` | 🛡️   | Create a glitch zone                                                   |

### Admin Panel (not part of `/api/v1`)

A SQLAdmin panel is mounted separately at **`/admin`** (`app/admin/setup.py`, wired from
`app/main.py`) for direct DB-model browsing/editing (users, artifacts, reports, moderation logs).
It has its own auth backend (`app/admin/auth.py`) and is not part of the versioned JSON API, so
it's not itemized endpoint-by-endpoint here.

---

## 🔑 Authentication Endpoints — Detailed

### Register New User

```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "myusername",
  "password": "SecurePass123!"
}
```

**Password Requirements:** min 8 chars, 1 uppercase, 1 lowercase, 1 digit.

**Response (201 Created):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors:** `400` email/username taken · `422` validation error · `429` rate limited (3/hour)

---

### Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200 OK):** same shape as register.

**Errors:** `401` invalid credentials · `403` account suspended · `429` rate limited (5/min)

---

### Refresh Token

```http
POST /auth/refresh
Content-Type: application/json

{ "refresh_token": "eyJhbGciOiJIUzI1NiIs..." }
```

**Response (200 OK):** same token shape as login.

---

### Get / Update Current User

```http
GET /auth/me
Authorization: Bearer <access_token>
```

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "myusername",
  "email": "user@example.com",
  "avatar_url": null,
  "bio": null,
  "experience_points": 0,
  "level": 1,
  "reputation_score": 100,
  "is_verified": false,
  "created_at": "2025-01-21T10:30:00Z"
}
```

```http
PUT /auth/me
Authorization: Bearer <access_token>
Content-Type: application/json

{ "username": "newusername", "bio": "Hello, I'm exploring LAYERS!" }
```

All fields optional — only send what you want to change.

---

### Password Reset

```http
POST /auth/password-reset/request
Content-Type: application/json

{ "email": "user@example.com" }
```

```json
{
  "message": "If an account exists with this email, a reset link has been sent.",
  "success": true
}
```

> **Dev Mode:** returns the reset token directly in the response for testing (no email sending yet).

```http
POST /auth/password-reset/confirm
Content-Type: application/json

{ "token": "abc123def456...", "new_password": "NewSecure456!" }
```

---

### Avatar Upload

```http
POST /auth/avatar
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file: <binary image, max 5MB, image/* content-type>
```

**Response:** `{ "url": "<object name in MinIO>" }` — served back via `GET /files/{path}`.

---

## 🗺️ Map Endpoints — Detailed

### Nearby Locations

```http
GET /map/nearby?lat=10.7769&lng=106.7009&radius=1000&layer=LIGHT&sort_by=distance&limit=20&offset=0
Authorization: Bearer <access_token>
```

Query params: `lat`/`lng` (required), `radius` (10–10000m, default 1000), `layer` (`LIGHT`/`SHADOW`),
`category` (`CAFE`, `PARK`, `LANDMARK`, `GHOST`, `VOUCHER`, ... see `LocationCategory` enum),
`sort_by` (`distance` | `newest` | `most_visited` | `most_artifacts`), `limit` (1–100), `offset`.

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "b3f1...",
      "latitude": 10.7769,
      "longitude": 106.7009,
      "layer": "LIGHT",
      "category": "CAFE",
      "name": "Café Luna",
      "is_verified": false,
      "visit_count": 12,
      "artifact_count": 3,
      "created_at": "2026-01-10T08:00:00Z",
      "distance_meters": 42.1
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0,
  "has_more": false
}
```

### Create Location

```http
POST /map/locations
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "latitude": 10.7769,
  "longitude": 106.7009,
  "layer": "LIGHT",
  "category": "CAFE",
  "name": "Café Luna",
  "description": "Quiet corner spot"
}
```

Passes through anti-cheat validation (`validate_location` dependency) before the location is saved.

---

## 📦 Artifact Endpoints — Detailed

### Create an Artifact ("drop a memory")

```http
POST /artifacts
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "latitude": 10.7769,
  "longitude": 106.7009,
  "content_type": "LETTER",
  "payload": { "text": "Left my heart at this café." },
  "visibility": "PUBLIC",
  "layer": "LIGHT"
}
```

`content_type` ∈ `LETTER | VOICE | PHOTO | PAPER_PLANE | VOUCHER | TIME_CAPSULE | NOTEBOOK`.
`payload` shape depends on `content_type` (e.g. `VOICE`: `{"url": "...", "duration_sec": 30}`,
`PHOTO`: `{"url": "...", "caption": "..."}`). `visibility` ∈ `PUBLIC | TARGETED | PASSCODE` — for
`TARGETED` pass `target_username`, for `PASSCODE` pass `passcode` (hashed server-side).

Runs through anti-cheat (`validate_location`) and the moderation pipeline (`ModerationService.enforce`)
before saving — content may come back `ACTIVE` (published) or `PENDING` (held for review).

**Response (201 Created)** — a hand-built dict (not a declared `response_model`):

```json
{
  "id": "a1b2...",
  "content_type": "LETTER",
  "visibility": "PUBLIC",
  "layer": "LIGHT",
  "status": "ACTIVE",
  "created_at": "2026-07-04T10:00:00Z",
  "message": "Artifact created!",
  "xp": { "amount": 15, "event": "ARTIFACT_CREATE" },
  "quests_completed": []
}
```

### Nearby Artifacts (Map Markers)

```http
GET /artifacts/nearby?lat=10.7769&lng=106.7009&radius=1000&layer=LIGHT
Authorization: Bearer <access_token>
```

Returns lightweight previews; artifacts further than 50m show `"is_locked": true` and
withhold the full payload/preview text.

### Unlock / Reply / Report

```http
POST /artifacts/{id}/unlock?passcode=1234&lat=10.7769&lng=106.7009
POST /artifacts/{id}/reply
Content-Type: application/json
{ "content": "This made my day!" }

POST /artifacts/{id}/report?reason=SPAM&detail=optional+free+text
```

Replies use the Slow Mail mechanic — delivered 6–12h later (`deliver_at` timestamp, no
Celery/queue; the delay is just filtered on at read time). The first reply between two users
auto-creates a `Connection` at SIGNAL level.

### Paper Plane / Time Capsule

```http
POST /artifacts/paper-plane
Content-Type: application/json
{ "text": "Hi from District 1!", "latitude": 10.7769, "longitude": 106.7009 }

POST /artifacts/time-capsule
Content-Type: application/json
{
  "text": "Open this in a year.",
  "latitude": 10.7769,
  "longitude": 106.7009,
  "unlock_date": "2027-07-04T00:00:00Z"
}
```

Paper planes land randomly 200m–1km from the drop point (Haversine-based).

---

## 🌫️ Fog of War Endpoints — Detailed

```http
POST /explore
Content-Type: application/json
{ "latitude": 10.7769, "longitude": 106.7009 }
```

Marks the ~100m chunk containing that point as explored for the current user (idempotent —
`is_new: false` if already explored). Awards XP + quest progress only on genuinely new chunks.

```http
POST /explore/batch
Content-Type: application/json
{ "coordinates": [ {"lat": 10.7769, "lng": 106.7009}, {"lat": 10.7772, "lng": 106.7011} ] }
```

Max 50 points per call; dedupes chunks before scoring XP.

```http
GET /explore/chunks?min_lat=10.77&min_lng=106.69&max_lat=10.79&max_lng=106.71
GET /explore/stats
GET /explore/heatmap
GET /explore/leaderboard
```

---

## 💬 Chat & Campfire (`chat.py`)

### REST

```http
POST /chat/rooms/direct
Content-Type: application/json
{ "other_user_id": "550e8400-..." }
```

Requires the two users already be at **CONNECTED** level (403 otherwise — this is not an
open DM system, it's gated behind the connection progression).

```http
POST /chat/campfires/find-or-create
Content-Type: application/json
{ "latitude": 10.7769, "longitude": 106.7009 }
```

Finds the nearest active campfire within 50m, or creates one and auto-joins the caller.
Rate-limited to 1 creation per 10 minutes per user.

```http
GET /chat/campfires/nearby?lat=10.7769&lng=106.7009&radius_meters=200
GET /chat/rooms/{room_id}/messages?before=2026-07-04T09:00:00Z&limit=50
```

### WebSocket

```
WS /chat/ws/{room_id}?token=<jwt access_token>
```

The JWT is validated **before** the WebSocket handshake is accepted. Membership in the room is
also checked at connect time. Close codes:

| Code | Meaning                                                   |
| ---- | --------------------------------------------------------- |
| 4001 | Unauthorized — bad/missing token, or banned/inactive user |
| 4003 | Forbidden — not a member of this room                     |
| 4004 | Room not found                                            |
| 4005 | Room closed                                               |
| 4400 | Invalid payload from client                               |
| 4500 | Internal error                                            |

**Client → server message types:**

```json
{"type": "ping"}
{"type": "typing_start"}
{"type": "typing_stop"}
{"type": "message", "content": "Hello!"}
```

**Server → client events:** `pong`, `typing` (broadcast to others, not the sender), `message`
(broadcast to the whole room including sender, persisted via a fresh DB session per message),
`presence` (join/leave, broadcast on connect/disconnect), `error` (`UNKNOWN_TYPE` for bad payloads).

---

## 🔥 Social Spark (`social_spark.py`)

```http
POST /spark/artifacts/{id}/boost
POST /spark/wave
Content-Type: application/json
{ "latitude": 10.7769, "longitude": 106.7009 }

POST /spark/artifacts/{id}/discover
```

"Discover" records an unlock; if a different user discovered the _same_ artifact within 30
minutes, both users get a "Synchronicity" match and their connection strengthens automatically.

---

## 🎮 Campfire Games — Truth or Dare (`game.py`)

```http
POST /chat/campfires/{room_id}/game/start
POST /chat/campfires/{room_id}/game/answer
Content-Type: application/json
{ "content": "My answer to the prompt" }

POST /chat/campfires/{room_id}/game/vote
Content-Type: application/json
{ "answer_id": "..." }

POST /chat/campfires/{room_id}/game/reveal
```

Every mutating call broadcasts a minimal `WSGameEvent` over the room's WebSocket so connected
clients know to refetch state. The round winner (from `/reveal`) gets XP (`CAMPFIRE_GAME_WIN`),
quest progress, and the `campfire_star` badge.

---

## 🏆 XP, Quests, Badges & Leaderboard

```http
GET /xp/me
GET /xp/history?cursor=2026-07-04T00:00:00Z&limit=20
GET /xp/rewards
GET /quests/today
GET /badges/me
POST /badges/sync
GET /leaderboard?scope=weekly&limit=20
```

`GET /leaderboard` always includes the caller's own rank/score in the response even if they
fall outside the requested page.

---

## 🛡️ Moderation, Reports & Anti-Cheat

```http
POST /reports/{artifact_id}
Content-Type: application/json
{ "reason": "SPAM", "detail": "optional free text, truncated server-side" }
```

One report per user per artifact (idempotent). 5 reports auto-hides the artifact
(`status = HIDDEN`) pending admin review.

```http
GET /moderation/queue          # admin — PENDING + auto-HIDDEN artifacts, oldest first
POST /moderation/{id}/approve  # admin — ACTIVE, resets report_count
POST /moderation/{id}/remove   # admin — DELETED, author reputation -30
```

Text content is pre-scanned on create via a rule-based VN+EN profanity/contact-info filter
(`moderation_service.py`) with three outcomes: `ALLOW` (publish), `FLAG` (hold as `PENDING`),
`REJECT` (400 + reputation penalty). **Image scanning is still a stub** — `scan_image()` always
returns `FLAG`, so every PHOTO artifact starts `PENDING` until a human (or a future real model)
approves it via `POST /moderation/scan-photos` or the admin queue.

```http
POST /anti-cheat/validate      # test GPS-spoofing/teleport detection on submitted metadata
GET  /anti-cheat/my-status     # your own strike count / ban status
```

Anti-cheat runs as part of request auth (`Depends(validate_location)`) on GPS-carrying write
endpoints: creating a location, creating/paper-planing/time-capsuling an artifact, and
`/explore`. Detects mocked GPS, teleportation (>5km/s), and sensor mismatches; accumulates
strikes toward an automatic ban.

---

## 🌙 Shadow Layer (`shadow.py`)

```http
GET /shadow/status?lat=10.7769&lng=106.7009
GET /shadow/midnight
GET /shadow/glitch-zones?lat=10.7769&lng=106.7009&radius=1000
```

`/shadow/midnight` checks a fixed 23:00–03:00 window in Ho Chi Minh City local time,
city-wide — no location needed. Glitch zones (admin-created via `POST /shadow/glitch-zones`)
have a `glitch_type` of `XP_SURGE | SHADOW_REVEAL | ANONYMOUS`, an intensity, and an active
time-of-day window.

---

## ⚠️ Error Responses

All errors follow this format:

```json
{ "detail": "Error message here" }
```

**Common Status Codes:**

| Code | Description                                                                |
| ---- | -------------------------------------------------------------------------- |
| 400  | Bad Request - Invalid input                                                |
| 401  | Unauthorized - Invalid/missing token                                       |
| 403  | Forbidden - Access denied (banned, not a room member, not CONNECTED, etc.) |
| 404  | Not Found - Resource doesn't exist                                         |
| 422  | Validation Error - Invalid data format                                     |
| 429  | Too Many Requests - Rate limited                                           |
| 500  | Internal Server Error                                                      |

---

## 🔒 Rate Limits

Two layers, both Redis-backed with an in-memory fallback if Redis is down (fail-open — never
blocks requests just because the cache is unavailable):

**1. Per-endpoint (tighter, governs in practice) — `app/core/endpoint_rate_limit.py`:**

| Endpoint                         | Limit                          |
| -------------------------------- | ------------------------------ |
| `/auth/login`                    | 5 per minute per IP            |
| `/auth/register`                 | 3 per hour per IP              |
| `/auth/password-reset/request`   | 3 per hour per IP              |
| `/chat/campfires/find-or-create` | 1 creation per 10 min per user |

**2. Global middleware baseline — `app/core/rate_limit.py`:**

| Scope                           | Limit                  |
| ------------------------------- | ---------------------- |
| `/auth/register` (global layer) | 5 per 5 minutes        |
| `/auth/login` (global layer)    | 10 per 5 minutes       |
| `/auth/password-reset` (global) | 3 per 5 minutes        |
| Everything else                 | 60 requests per minute |

`/health`, `/docs`, `/redoc`, `/openapi.json`, and the WS handshake path are exempt from the
global middleware. Rate-limit responses include `Retry-After`, `X-RateLimit-Limit`,
`X-RateLimit-Remaining` headers.

---

## 📝 Data Types

### User Object

```typescript
interface User {
  id: string; // UUID
  username: string; // 3-50 chars, alphanumeric + underscore
  email: string;
  avatar_url?: string;
  bio?: string; // Max 500 chars
  experience_points: number;
  level: number;
  reputation_score: number; // 0-1000
  is_verified: boolean;
  created_at: string; // ISO 8601 datetime
}
```

### Token Response

```typescript
interface TokenResponse {
  access_token: string; // JWT, expires in 30 min
  refresh_token: string; // JWT, expires in 7 days
  token_type: "bearer";
  expires_in: number; // seconds until access token expires
}
```

### Artifact Object (core content type)

```typescript
interface Artifact {
  id: string;
  content_type:
    | "LETTER"
    | "VOICE"
    | "PHOTO"
    | "PAPER_PLANE"
    | "VOUCHER"
    | "TIME_CAPSULE"
    | "NOTEBOOK";
  layer: "LIGHT" | "SHADOW";
  visibility: "PUBLIC" | "TARGETED" | "PASSCODE";
  status: "ACTIVE" | "PENDING" | "HIDDEN" | "DELETED";
  latitude: number;
  longitude: number;
  distance_meters?: number;
  view_count: number;
  reply_count: number;
  save_count: number;
  created_at: string;
  is_locked: boolean; // geo-locked, time-locked, or passcode-locked
  lock_reason?: "distance" | "time" | "passcode";
  payload?: Record<string, unknown>; // only present when unlocked
}
```

---

## 🧪 Testing with cURL

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"Test123!"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}'

# Get Profile (replace TOKEN)
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer TOKEN"

# Nearby locations
curl "http://localhost:8000/api/v1/map/nearby?lat=10.7769&lng=106.7009&radius=1000" \
  -H "Authorization: Bearer TOKEN"

# Drop an artifact
curl -X POST http://localhost:8000/api/v1/artifacts \
  -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{"latitude":10.7769,"longitude":106.7009,"content_type":"LETTER","payload":{"text":"Hi!"},"visibility":"PUBLIC"}'

# Today's quests
curl http://localhost:8000/api/v1/quests/today -H "Authorization: Bearer TOKEN"
```

For interactive testing, Swagger UI is available at `/docs` (and ReDoc at `/redoc`) whenever
`DEBUG=True` — both are disabled automatically in production.

---

_Last Updated: 2026-07-04 — rewritten to cover the full 92-endpoint surface across all 18
`/api/v1` route modules (previously only Week 1 auth was documented in detail)._
