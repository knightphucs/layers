# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LAYERS is a location-based social network with AR and gamification features. It has a dual-layer experience (Light/Shadow) where users discover and leave "artifacts" (memories, messages, vouchers) at real-world locations.

## Build & Run Commands

### Infrastructure (Docker)
```bash
docker-compose up -d          # Start PostgreSQL, Redis, MinIO
docker-compose down -v        # Stop and remove volumes
```

### Backend (FastAPI + Python)
```bash
cd backend
python -m venv venv
venv\Scripts\activate         # Windows
source venv/bin/activate      # Mac/Linux
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload # Runs on http://localhost:8000
```

API docs available at `/docs` (Swagger) and `/redoc`.

### Mobile (React Native + Expo)
```bash
cd mobile
npm install
npx expo start                # Start Expo dev server
npx expo start --android      # Android emulator
npx expo start --ios          # iOS simulator
npx expo start --web          # Web browser
```

### Testing
```bash
cd backend
pytest                        # Run all tests
pytest tests/test_auth.py     # Run single test file
pytest -v                     # Verbose output
```

## Architecture

### Backend (`/backend`)
- **Framework:** FastAPI with async/await throughout
- **Database:** PostgreSQL 16 + PostGIS for geo-spatial queries
- **ORM:** SQLAlchemy 2.0 async with `AsyncSession`
- **Auth:** JWT tokens (30min access, 7-day refresh) with bcrypt passwords
- **Cache/Queue:** Redis for caching and Celery task queue
- **Storage:** MinIO (S3-compatible) for file uploads

**Structure:**
- `app/api/v1/` - HTTP route handlers
- `app/schemas/` - Pydantic request/response validation
- `app/models/` - SQLAlchemy ORM models
- `app/core/` - Config, database setup, security utilities

### Mobile (`/mobile`)
- **Framework:** React Native with Expo SDK 54
- **State:** Zustand for global state management
- **Navigation:** React Navigation 7.x
- **Maps:** react-native-maps with expo-location

**Planned structure:**
- `screens/` - Full-page components
- `components/` - Reusable UI elements
- `services/` - API client (Axios)
- `store/` - Zustand stores

### Key Data Models

**User** - Includes gamification (XP, level, reputation), roles (USER/ADMIN/PARTNER), ban/verification status

**Artifact** - Core content type with:
- `content_type`: LETTER, VOICE, PHOTO, PAPER_PLANE, VOUCHER, TIME_CAPSULE, NOTEBOOK
- `visibility`: PUBLIC, TARGETED, PASSCODE
- `layer`: LIGHT or SHADOW
- `payload`: JSONB for flexible content per type

**Location** - PostGIS Geography POINT with categories (CAFE, PARK, LANDMARK, GHOST, etc.)

### Geo-Spatial Patterns

All location queries use PostGIS functions:
- `ST_DWithin` for proximity searches
- Geography type uses WGS84 (SRID 4326)
- `Location.create_point_wkt()` converts lat/lng to PostGIS format

### Environment Configuration

Key `.env` variables:
- `DATABASE_URL` - PostgreSQL async connection string (postgresql+asyncpg://...)
- `REDIS_URL` - Redis connection
- `JWT_SECRET_KEY` - Token signing key
- `MINIO_*` - Object storage config
- `GEO_LOCK_RADIUS=50` - Meters required to access artifacts
- `DEFAULT_NEARBY_RADIUS=1000` - Default search radius in meters

## Development Notes

- Backend uses full async - always use `async def` and `await` for database operations
- All database sessions use `AsyncSessionLocal` context manager
- Mobile app entry point is currently a blank template (Week 2 setup pending)
- Docker services: `layers_postgres` (5432), `layers_redis` (6379), `layers_minio` (9000/9001)
