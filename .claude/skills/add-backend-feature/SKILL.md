---
name: add-backend-feature
description: Add a backend feature to LAYERS end to end — model, migration, schema, service, route, tests, and the mobile client wiring. Use when adding a new API domain or a substantial endpoint group to this repo, or when a change needs a new table.
---

# Add a backend feature (LAYERS)

The order below is not style preference — each step exists because skipping it has silently
broken this repo before. Follow it in sequence.

## 0. Orient

Read `CLAUDE.md` §3 (request path) and the closest existing domain end to end. Pick the one that
most resembles what you are building — `shadow` for read-mostly geo, `social_spark` for
write-heavy social, `chat` for anything with WebSockets. Match its structure rather than
inventing a new one.

Decide up front: does this need a new table? If not, skip to step 3.

## 1. Model

Create `backend/app/models/<domain>.py`. UUID primary key, `DateTime(timezone=True)` timestamps,
`index=True` on every foreign key and on any column you will filter by.

**Then export it from `backend/app/models/__init__.py`** — both the import and the `__all__`
entry. Alembic autogenerate only sees imported models; a missing export produces an empty
migration and a table that never exists.

## 2. Migration

```bash
cd backend && source venv/bin/activate
alembic revision --autogenerate -m "w<N>d<N>_<domain>_<short_description>"
```

**Read the generated file before applying it.** Autogenerate has missed foreign keys in this
repo before — commit `3f71ba9` had to backfill them. Check specifically:

- every `ForeignKey` present, with the right `ondelete`
- indexes you declared actually appear
- no unintended `drop_table` / `drop_column` (a sign your models are out of sync with the DB)
- PostGIS columns render as `Geography(...)`, not `NULL`

```bash
alembic upgrade head
alembic downgrade -1 && alembic upgrade head   # prove the downgrade works
```

## 3. Schema

`backend/app/schemas/<domain>.py` — separate request and response models. Constrain at the edge:
`Field(..., max_length=...)`, lat/lng bounds, enums for anything with fixed values. Never accept
a raw dict from the client for something you could type.

## 4. Service

`backend/app/services/<domain>_service.py` — a class of `@staticmethod`s taking `db: AsyncSession`
first, matching `AuthService` / `ArtifactService` / `ChatService`.

**All business logic lives here.** The route must not contain rules.

Checklist while writing it:

- `async def` + `await` on every DB call — one sync call blocks the whole event loop
- geo queries: `ST_MakePoint(lng, lat)` — longitude first; prefer `Location.create_point_wkt()`
- awarding XP? call `XPService.award(...)`, never `User.add_xp()` and never a local formula
- social escalation between two users? it must flow through
  `ConnectionService.record_interaction`, which is where blocking is enforced
- user-generated text or media? run it through `ModerationService.enforce(...)`
- caching? use `app/core/cache.py` helpers with a quantized key from `geo_cache.py`, and make
  sure a Redis outage degrades instead of raising
- broadcasting to sockets? `manager.broadcast()` only — never touch `manager.active` directly
- module docstring explains *why*, matching the surrounding files

## 5. Route

`backend/app/api/v1/<domain>.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user   # NOT app.core.deps — there is no deps.py
from app.core.database import get_db
from app.models.user import User

router = APIRouter(prefix="/<domain>", tags=["<Domain>"])
```

Thin handlers: validate → call service → return schema. Correct status codes (`201` on create,
`204` on delete). Admin-only routes check `user.role == UserRole.ADMIN`. Abuse-prone
unauthenticated routes get `dependencies=[Depends(rate_limit("bucket", n, seconds))]`.

**Then register it in `backend/app/api/v1/router.py`** — import plus `include_router`. Creating
the module is not enough; this is the most common way a new endpoint 404s.

## 6. Tests

`backend/tests/test_<domain>.py`, following the existing pattern (each file builds its own engine
against `TEST_DATABASE_URL` and runs `drop_all`/`create_all`).

Cover: happy path, auth required (401), ownership/permission (403), validation (422), and the one
domain rule that would hurt most if it broke. If the feature is a safety feature — blocking,
moderation, reporting — the test is not optional.

```bash
pytest tests/test_<domain>.py -v
```

## 7. Mobile client

1. `mobile/src/types/<domain>.ts` — mirror the response schemas
2. `mobile/src/services/<domain>.ts` — import the shared `api` instance from `./api`, never bare
   axios; export from `services/index.ts`
3. `mobile/src/store/<domain>Store.ts` — Zustand store owning loading/error state and async
   actions; screens stay presentational
4. Screen/components — `Colors[layer]` theming so it works in Light *and* Shadow, `CachedImage`
   for remote images, a `Skeleton` preset for first load, explicit `memo` comparators on list rows

## 8. Close out

- Update `docs/API_DOCUMENTATION.md` with the new endpoints
- Update the domain table in `CLAUDE.md` **and `AGENTS.md`** (they are mirrors)
- New gap or known limitation? Add it to `docs/PRODUCTION_READINESS.md` with file:line and
  consequence — an honest entry now is cheaper than a surprise at launch
- Verify the route is actually registered, not just written:

  ```bash
  cd backend && venv/bin/python -c "
  from app.main import app
  print([r.path for r in app.routes if '<domain>' in getattr(r, 'path', '')])"
  ```

  An empty list means you forgot step 5's `include_router`.
