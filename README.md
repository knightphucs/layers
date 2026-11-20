# LAYERS

> **"See the hidden layers of your city"**

A location-based social network with AR and gamification. Users discover and leave **artifacts** (memories, messages, vouchers) at real-world locations through a dual-layer experience — **Light** (public) and **Shadow** (mysterious).

---

## Tech Stack

| Layer         | Technology                         |
| ------------- | ---------------------------------- |
| Mobile        | React Native + Expo SDK 54         |
| Backend       | Python FastAPI (async)             |
| Database      | PostgreSQL 16 + PostGIS            |
| Cache / Queue | Redis + Celery                     |
| File Storage  | MinIO (S3-compatible)              |
| Auth          | JWT (30min access / 7-day refresh) |

---

## Quick Start

### Prerequisites

- Docker Desktop
- Python 3.11+
- Node.js 18+
- Expo Go app on phone

### 1. Infrastructure (Docker)

```bash
docker-compose up -d
# Services: layers_postgres :5433, layers_redis :6379, layers_minio :9000 (console :9001)
```

Requires a root `.env` with `POSTGRES_PASSWORD`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`.
Note Postgres is published on **5433**, and the compose DB user is `layers_admin`. Set a real
`DATABASE_URL` in `backend/.env` — the default in `config.py` matches the compose user and port
but carries a placeholder password.

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head          # Run migrations (required)
uvicorn app.main:app --reload # http://localhost:8000
```

Testing on a physical phone? Bind to all interfaces, not localhost:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API docs: `http://localhost:8000/docs`

### 3. Mobile

```bash
cd mobile
npm install
npx expo start
```

Scan the QR code in Expo Go on your phone.

### 4. Verify — Register a user

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"Test1234!"}'
```

---

## Project Structure

```
layers_project/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers (auth, map, artifacts, social)
│   │   ├── core/            # Config, database, security (JWT)
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic (all of it)
│   │   ├── admin/           # SQLAdmin panel mounted at /admin
│   │   ├── workers/         # Batch image moderation scanner
│   │   └── utils/           # Geo calculations, anti-cheat, shadow time windows
│   ├── alembic/versions/    # Database migrations
│   ├── tests/               # pytest unit & integration tests
│   ├── .env.example
│   ├── requirements.txt
│   └── Dockerfile
├── mobile/
│   ├── src/
│   │   ├── screens/         # LoginScreen, MapScreen, ProfileScreen, etc.
│   │   ├── components/      # ArtifactMarker, FogOverlay, LayerToggle
│   │   ├── services/        # Axios API client
│   │   ├── store/           # Zustand state (auth, map, artifacts, chat, inbox, ...)
│   │   ├── hooks/           # Location, notifications, fog of war, network status
│   │   ├── types/           # Shared TS types mirroring backend schemas
│   │   ├── navigation/      # Root → Auth | Onboarding | Main
│   │   └── constants/       # Colors, config, Light/Shadow themes
│   ├── App.tsx
│   └── package.json
├── docs/
│   ├── API_DOCUMENTATION.md      # All 107 endpoints
│   ├── ARCHITECTURE.md           # Data model, lifecycles, pipelines, perf playbook
│   ├── PRODUCTION_READINESS.md   # Launch blockers — read before deploying
│   └── SECURITY_CHECKLIST.md
├── docker-compose.yml
├── CLAUDE.md                     # Agent guide (mirror: AGENTS.md)
└── AGENTS.md
```

---

## Key Concepts

### Artifact Types

`LETTER` · `VOICE` · `PHOTO` · `PAPER_PLANE` · `VOUCHER` · `TIME_CAPSULE` · `NOTEBOOK`

### Visibility Modes

- **PUBLIC** — anyone nearby can see it
- **TARGETED** — sent to a specific user
- **PASSCODE** — requires a secret code to unlock

### Geo-Lock

Artifacts require the user to be **within 50 m** of the location to open them (`GEO_LOCK_RADIUS=50`).

### Fog of War

The map starts fully covered. As users walk around, they reveal explored areas in ~100 m × 100 m chunks. The client batches GPS points every 30 s and sends them to `POST /explore/batch`. Grid math at Ho Chi Minh City latitude:

```
chunk_x = int(longitude / 0.000917°)   # ~100m longitude
chunk_y = int(latitude  / 0.0009°)     # ~100m latitude
```

### Anti-Cheat

- Mock GPS detection
- Speed check: > 5 km/s flags as suspicious
- Rate limit: 3 location drops per day

---

## 10-Week Roadmap

| Week | Phase        | Focus                                                    |
| ---- | ------------ | -------------------------------------------------------- |
| 1    | Foundation   | Backend auth, DB schema, JWT, tests                      |
| 2    | Foundation   | React Native + Expo, navigation, map                     |
| 3    | Geo          | Location model, artifact APIs, Fog of War backend        |
| 4    | Geo          | Map markers, fog overlay, artifact creation/viewing      |
| 5    | Social       | Memory types (voice/photo), slow mail, paper planes      |
| 6    | Social       | Connections, real-time WebSocket chat, campfire rooms    |
| 7    | Gamification | XP/levels, daily missions, badges, leaderboards          |
| 8    | Moderation   | AI content moderation, reports, admin panel, push notifs |
| 9    | Polish       | AR garden, Shadow layer effects, onboarding flow         |
| 10   | Launch       | App Store prep, beta, launch                             |

### Current Status — Week 9 Day 4 (in progress)

**Backend:** 107 endpoints across 19 route modules, 28 models / 28 tables, 21 Alembic migrations,
26 test files, SQLAdmin panel at `/admin`.
**Mobile:** 22 screens, 14 API service modules, 12 Zustand stores.

Shipped:

| Area | State |
| --- | --- |
| Auth, profiles, avatars, account deletion | ✅ |
| PostGIS map, artifacts, geo-lock, Slow Mail, paper planes, time capsules | ✅ |
| Fog of war + exploration stats/heatmap/leaderboard | ✅ |
| Anti-cheat (mock GPS, jump detection, drop limits) | ✅ |
| Connections + WebSocket chat + campfires (multi-worker via Redis pub/sub) | ✅ |
| Social spark: boost / anonymous wave / synchronicity | ✅ |
| Campfire games (Truth or Dare) | ✅ |
| XP, levels, ranks, daily quests, streaks, badges, leaderboards | ✅ |
| Moderation, trust-weighted reports, reputation, admin panel | ✅ |
| Shadow layer: glitch zones, midnight lock | ✅ |
| Onboarding + story mode, inbox with letter reader, user blocking | ✅ |
| Push notification plumbing | ⚠️ tokens/preferences/history work; **nothing is actually sent yet** |

**In flight (Day 4 — performance):** request timing middleware, Postgres perf audit script,
image caching via expo-image, skeleton loaders, map marker memoization, logging removed from hot
paths.

**Before launch:** see [`docs/PRODUCTION_READINESS.md`](docs/PRODUCTION_READINESS.md) — there is
no deployment path, no CI, and no crash reporting yet.

---

## Planned Features (Post-MVP)

**High priority:** Echo System (voice artifacts), Treasure Hunt Chains, Story-mode onboarding

**Growth:** Mood Weather map layer, Memory Duet (paired memories), Digital Graffiti Wall

**Monetization:** Premium Layers ($4.99/mo), Business Portal (voucher campaigns, foot traffic analytics)

**Expansion:** Custom user-created layers, City vs City events, Time Portals (historical AR)

---

## Testing

```bash
cd backend
pytest              # All tests
pytest tests/test_auth.py -v
```

## Troubleshooting

```bash
# Docker reset
docker-compose down -v && docker-compose up -d

# Expo cache clear
npx expo start -c

# PostGIS check
docker exec -it layers_postgres psql -U layers_user -d layers_db \
  -c "SELECT PostGIS_Version();"
```

---

_Stack: FastAPI · PostgreSQL/PostGIS · Redis · React Native · Expo_
_Founder: Kazyy_
