---
name: release-check
description: Pre-deploy gate for LAYERS — verify blockers are closed, migrations apply, tests pass, the app boots in production config, and the mobile build is submittable. Use before any deploy, EAS build, TestFlight/Play submission, or when asked whether the project is ready to ship.
---

# Release check (LAYERS)

Run top to bottom. **Stop at the first failure and report it** — do not continue and summarize at
the end. A release check that reports six problems at once gets skimmed; one problem gets fixed.

Report results honestly, including partial passes. "Tests pass except X" is a useful answer;
"all good" when X failed is not.

## 1. Blockers

Open `docs/PRODUCTION_READINESS.md`. Every 🔴 Blocker must be closed. If any remain, stop here
and report which — the rest of this check is meaningless if a production build cannot reach the
backend.

Verify each claimed fix in the code rather than trusting the doc; the doc can lag.

## 2. Clean tree

```bash
git status --short
git log --oneline -5
```

Uncommitted work means you cannot reproduce what you are about to ship. Confirm the branch is the
one you intend to release from.

## 3. Migrations

```bash
cd backend && source venv/bin/activate
alembic current
alembic upgrade head
```

Then confirm models and migrations agree — this is the check that catches the `create_all` trap
(see `PRODUCTION_READINESS.md` B4):

```bash
alembic revision --autogenerate -m "_tmp_drift_check"
```

The generated file must have an **empty** upgrade body. If it does not, a model change is missing
a migration. Delete the temp file either way.

## 4. Tests

```bash
pytest
```

Needs a live Postgres+PostGIS at `TEST_DATABASE_URL`. Report the actual pass/fail counts. Any
failure blocks the release — do not rationalize a "known flaky" test without evidence it is
flaky rather than broken.

## 5. Production boot

The single most valuable step, because this path is rarely exercised:

```bash
DEBUG=False uvicorn app.main:app --port 8001
```

With `DEBUG=False` and real secrets, confirm:

- it starts — `validate_production_secrets()` raises on default/leaked secrets, which is the
  check working, not a bug to work around
- `GET /health` → 200, `"redis": "up"`
- `GET /docs` → 404 (Swagger must be off in production)
- security headers present: `curl -I` shows `X-Frame-Options`, `X-Content-Type-Options`,
  `Strict-Transport-Security`
- `CORS_ORIGINS` and `ALLOWED_HOSTS` name real domains, no `*`

## 6. Config sanity

- `JWT_SECRET_KEY` and `SECRET_KEY` are unique, high-entropy, and not in git
  (`git ls-files | grep -i env` should show only `.env.example`)
- `DATABASE_URL` points at the production DB, with SSL
- `MINIO_PUBLIC_URL` is a real reachable host, not `10.0.2.2` or `localhost`
- `FORCE_HTTPS=True` if TLS terminates upstream
- `mobile/src/constants/config.ts` — production `API_URL` matches the deployed path *including*
  the `/api/v1` prefix, and `MINIO_URL` points at real storage

## 7. Mobile build

```bash
cd mobile
npx tsc --noEmit          # type check
eas build --profile production --platform all
```

Before building, confirm in `app.json`: real `name`/`slug`, bundle identifiers set,
`usesCleartextTraffic` **false**, permission usage strings for location and notifications,
version and build number incremented.

## 8. Post-deploy smoke test

Against the deployed environment, not localhost:

1. `GET /health` → 200
2. Register a throwaway account → 201
3. Log in → tokens returned
4. `GET /api/v1/artifacts/nearby` with real coordinates → 200
5. Upload an avatar → the returned URL actually loads
6. Open a WebSocket to a chat room → connects and receives frames
7. Trigger one push notification → it arrives on a real device

Watch the logs for `🐌 SLOW` warnings during the smoke test and note anything over 300 ms.

## 9. Report

State plainly: what passed, what failed, what you skipped and why. If the release is not safe,
say so directly and name the one thing to fix first.
