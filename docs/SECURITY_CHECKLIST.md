# 🔒 LAYERS Security Checklist

> Review this checklist before deploying to production!

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
- [ ] **TODO (Production):** Strict CORS for production domains only

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

- [ ] **TODO:** Implement rate limiting (use slowapi or Redis)
- [ ] **TODO:** Rate limit login attempts (5/min)
- [ ] **TODO:** Rate limit registration (3/hour)
- [ ] **TODO:** Rate limit password reset (3/hour)

### Error Handling

- [x] Generic error messages (no stack traces in production)
- [x] Email enumeration prevention (password reset)
- [x] Consistent error response format
- [ ] **TODO (Production):** Set DEBUG=False

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

- [x] Design: Report system (5 reports = auto-hide)
- [x] Design: Reputation score system
- [ ] **TODO (Week 8):** AI content scanning
- [ ] **TODO (Week 8):** Profanity filter

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

## 📊 Security Headers (Add to Production)

```python
# Add these headers in production
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

# Force HTTPS
app.add_middleware(HTTPSRedirectMiddleware)

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["layers.app", "*.layers.app"]
)
```

Add security headers middleware:

```python
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response
```

---

## 🔐 Current Security Status

| Area               | Status       | Notes                        |
| ------------------ | ------------ | ---------------------------- |
| Password Hashing   | ✅ Secure    | Bcrypt implemented           |
| JWT Auth           | ✅ Secure    | Proper expiry, signed tokens |
| Input Validation   | ✅ Secure    | Pydantic validation          |
| SQL Injection      | ✅ Protected | SQLAlchemy ORM               |
| Rate Limiting      | ⚠️ TODO      | Add before launch            |
| HTTPS              | ⚠️ TODO      | Configure in production      |
| Content Moderation | ⚠️ TODO      | Week 8                       |

---

_Security is a continuous process. Review this checklist regularly!_
