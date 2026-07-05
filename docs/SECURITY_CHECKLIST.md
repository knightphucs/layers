# 🔒 LAYERS Security Checklist

> Review this checklist before deploying to production!

---

## ✅ Week 8 Day 5: Production Hardening

- [x] Strict CORS for production domains only (`CORS_ORIGINS` env, `*` auto-stripped when `DEBUG=False`)
- [x] Rate limit login (5/min), registration (3/hour), password reset (3/hour)
- [x] Security headers (nosniff, X-Frame-Options, HSTS) via `SecurityHeadersMiddleware`
- [x] Content Moderation (Week 8 Day 1–2): rule-based profanity filter + report/reputation system
- [x] Set `DEBUG=False` refuses insecure boot (`validate_production_secrets` raises on startup)
- [ ] HTTPS (cấu hình ở tầng deploy/reverse proxy — Week 10)
- [ ] Token blacklist in Redis (nice-to-have, có thể để post-launch)

See `backend/app/core/security_hardening.py` and `backend/app/core/endpoint_rate_limit.py`.

---

## ✅ Authentication Security

### Password Handling

- [x] Passwords hashed with bcrypt (cost factor 12)
- [x] Plain passwords never stored or logged
- [x] Password strength validation (8+ chars, upper, lower, digit)
- [x] Password reset tokens hashed before storage
- [x] Reset tokens expire after 1 hour

### JWT Tokens

- [x] Short-lived access tokens (30 minutes)
- [x] Longer refresh tokens (7 days)
- [x] Tokens signed with HS256 algorithm
- [x] Secret keys loaded from environment variables
- [ ] **TODO (Production):** Implement token blacklist in Redis
- [ ] **TODO (Production):** Rotate JWT secrets periodically

### Session Management

- [x] Logout endpoint available
- [x] Last login timestamp tracked
- [ ] **TODO (Production):** Invalidate all sessions on password change

---

## ✅ Input Validation

### User Input

- [x] Email validation with Pydantic
- [x] Username validation (alphanumeric, 3-50 chars)
- [x] Password validation rules enforced
- [x] SQL injection prevention via SQLAlchemy ORM
- [x] Request body size limits (FastAPI default)

### API Security

- [x] CORS configured for allowed origins
- [x] Content-Type validation
- [x] Strict CORS for production domains only (`get_cors_origins`, `CORS_ORIGINS` env)

---

## ✅ Database Security

### Data Protection

- [x] UUIDs for primary keys (non-sequential)
- [x] Sensitive data not in URLs
- [x] Password hashes only (no plain text)
- [x] Reset tokens hashed

### Queries

- [x] Parameterized queries (SQLAlchemy)
- [x] No raw SQL with user input
- [x] Database connection pooling
- [ ] **TODO (Production):** Enable SSL for database connection

---

## ✅ API Security

### Rate Limiting

- [x] Global rate limiting (Redis sliding-window, in-memory fallback) — `app/core/rate_limit.py`
- [x] Rate limit login attempts (5/min) — `app/core/endpoint_rate_limit.py`
- [x] Rate limit registration (3/hour)
- [x] Rate limit password reset (3/hour)

### Error Handling

- [x] Generic error messages (no stack traces in production)
- [x] Email enumeration prevention (password reset)
- [x] Consistent error response format
- [x] Set DEBUG=False refuses insecure boot (`validate_production_secrets` raises in `lifespan()`)

---

## ✅ Anti-Cheat (Geo Features)

### Location Verification

- [x] Design: isMocked flag detection
- [x] Design: Jumping check (>5km/sec = suspicious)
- [x] Design: Rate limit artifact creation (3/day)
- [x] Design: Minimum distance between artifacts (20m)
- [ ] **TODO (Week 3):** Implement in location service

---

## ✅ Content Security

### Moderation

- [x] Report system (5 reports = auto-hide)
- [x] Reputation score system
- [x] Profanity filter (rule-based VN + EN, leetspeak/diacritic evasion handling) — `app/services/moderation_service.py`
- [ ] **TODO (Week 8+):** Real AI image scanning (NudeNet/Rekognition) — currently a stub that holds PHOTO artifacts as PENDING for human review

### File Uploads

- [ ] **TODO (Week 5):** Validate file types
- [ ] **TODO (Week 5):** Scan uploads for malware
- [ ] **TODO (Week 5):** Limit file sizes
- [ ] **TODO (Week 5):** Store in separate bucket

---

## 🚨 Production Checklist

### Environment

- [ ] Set `DEBUG=False`
- [ ] Use strong, unique `SECRET_KEY`
- [ ] Use strong, unique `JWT_SECRET_KEY`
- [ ] Configure production database
- [ ] Enable HTTPS only
- [ ] Set strict CORS origins

### Infrastructure

- [ ] Database backups configured
- [ ] Monitoring & alerting set up
- [ ] Error logging to external service
- [ ] Health checks configured
- [ ] Auto-scaling configured

### Secrets Management

- [ ] No secrets in code
- [ ] Use environment variables or secrets manager
- [ ] Rotate secrets regularly
- [ ] Different secrets for dev/staging/prod

---

## 📊 Security Headers (Implemented — Week 8 Day 5)

Wired in `app/main.py` via `setup_security(app, settings)`, defined in
`app/core/security_hardening.py`:

- `SecurityHeadersMiddleware` — nosniff, X-Frame-Options, Referrer-Policy,
  Permissions-Policy, and HSTS (HSTS only sent when `debug=False`)
- `TrustedHostMiddleware` — enabled only in production, hosts from `ALLOWED_HOSTS`
- `HTTPSRedirectMiddleware` — opt-in via `FORCE_HTTPS=True` (enable behind a TLS-terminating reverse proxy)

To configure for a real deploy, set in `.env`:

```
CORS_ORIGINS=https://layers.app,https://www.layers.app
ALLOWED_HOSTS=layers.app,api.layers.app
FORCE_HTTPS=True
DEBUG=False
```

---

## 🔐 Current Security Status

| Area               | Status       | Notes                        |
| ------------------ | ------------ | ---------------------------- |
| Password Hashing   | ✅ Secure    | Bcrypt implemented           |
| JWT Auth           | ✅ Secure    | Proper expiry, signed tokens |
| Input Validation   | ✅ Secure    | Pydantic validation          |
| SQL Injection      | ✅ Protected | SQLAlchemy ORM               |
| Rate Limiting      | ✅ Secure    | Global + per-endpoint (login/register/reset) |
| CORS / Headers     | ✅ Secure    | Settings-driven, `*` stripped in prod, HSTS/nosniff/X-Frame-Options |
| Boot-time secrets  | ✅ Secure    | Refuses to start in prod with default secrets |
| HTTPS              | ⚠️ TODO      | Configure at reverse-proxy/deploy layer (Week 10) |
| Content Moderation | ⚠️ Partial   | Report + reputation + rule-based profanity filter done; real AI image scan still a stub |
| Token Blacklist    | ⚠️ TODO      | Nice-to-have, post-launch    |

---

_Security is a continuous process. Review this checklist regularly!_
