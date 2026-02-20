# 📖 LAYERS API Documentation

> Version: 1.0.0 | Base URL: `http://localhost:8000/api/v1`

---

## 🔐 Authentication

All protected endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer <access_token>
```

---

## 📋 Endpoints Overview

### Authentication (`/auth`)

| Method | Endpoint                          | Auth | Description                 |
| ------ | --------------------------------- | ---- | --------------------------- |
| POST   | `/auth/register`                  | ❌   | Create new account          |
| POST   | `/auth/login`                     | ❌   | Login, get tokens           |
| POST   | `/auth/refresh`                   | ❌   | Refresh access token        |
| POST   | `/auth/logout`                    | ✅   | Logout user                 |
| GET    | `/auth/me`                        | ✅   | Get current user profile    |
| PUT    | `/auth/me`                        | ✅   | Update profile              |
| DELETE | `/auth/me`                        | ✅   | Deactivate account          |
| POST   | `/auth/password-reset/request`    | ❌   | Request password reset      |
| POST   | `/auth/password-reset/confirm`    | ❌   | Confirm password reset      |
| POST   | `/auth/change-password`           | ✅   | Change password             |
| GET    | `/auth/check-email/{email}`       | ❌   | Check email availability    |
| GET    | `/auth/check-username/{username}` | ❌   | Check username availability |

---

## 🔑 Authentication Endpoints

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

**Password Requirements:**

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

**Response (201 Created):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors:**

- `400` - Email already registered
- `400` - Username already taken
- `422` - Validation error (weak password, invalid email)

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

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors:**

- `401` - Invalid email or password
- `403` - Account suspended

---

### Refresh Token

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

### Get Current User

```http
GET /auth/me
Authorization: Bearer <access_token>
```

**Response (200 OK):**

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

---

### Update Profile

```http
PUT /auth/me
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "username": "newusername",
  "bio": "Hello, I'm exploring LAYERS!",
  "avatar_url": "https://example.com/avatar.jpg"
}
```

All fields are optional - only include what you want to update.

---

### Request Password Reset

```http
POST /auth/password-reset/request
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response (200 OK):**

```json
{
  "message": "If an account exists with this email, a reset link has been sent.",
  "success": true
}
```

> **Dev Mode:** Returns the reset token in the response for testing.

---

### Confirm Password Reset

```http
POST /auth/password-reset/confirm
Content-Type: application/json

{
  "token": "abc123def456...",
  "new_password": "NewSecure456!"
}
```

**Response (200 OK):**

```json
{
  "message": "Password has been reset successfully. You can now login.",
  "success": true
}
```

---

### Change Password (Authenticated)

```http
POST /auth/change-password
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "current_password": "OldPass123!",
  "new_password": "NewPass456!"
}
```

---

### Check Email Availability

```http
GET /auth/check-email/newuser@example.com
```

**Response:**

```json
{
  "email": "newuser@example.com",
  "available": true
}
```

---

### Check Username Availability

```http
GET /auth/check-username/coolname
```

**Response:**

```json
{
  "username": "coolname",
  "available": true
}
```

---

## 🗺️ Map Endpoints (Coming Week 3)

| Method | Endpoint        | Auth | Description            |
| ------ | --------------- | ---- | ---------------------- |
| GET    | `/map/nearby`   | ✅   | Get nearby artifacts   |
| GET    | `/map/explored` | ✅   | Get explored chunks    |
| POST   | `/map/explore`  | ✅   | Mark chunk as explored |

---

## 📦 Artifact Endpoints (Coming Week 3)

| Method | Endpoint                 | Auth | Description          |
| ------ | ------------------------ | ---- | -------------------- |
| POST   | `/artifacts`             | ✅   | Create artifact      |
| GET    | `/artifacts/{id}`        | ✅   | Get artifact details |
| POST   | `/artifacts/{id}/reply`  | ✅   | Reply to artifact    |
| POST   | `/artifacts/{id}/save`   | ✅   | Save to inventory    |
| POST   | `/artifacts/{id}/report` | ✅   | Report artifact      |

---

## 🤝 Social Endpoints (Coming Week 6)

| Method | Endpoint                   | Auth | Description             |
| ------ | -------------------------- | ---- | ----------------------- |
| GET    | `/connections`             | ✅   | List connections        |
| POST   | `/connections/request`     | ✅   | Send connection request |
| PUT    | `/connections/{id}/accept` | ✅   | Accept connection       |
| GET    | `/chat/{connection_id}`    | ✅   | Get chat messages       |
| POST   | `/chat/{connection_id}`    | ✅   | Send message            |

---

## ⚠️ Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

**Common Status Codes:**
| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid/missing token |
| 403 | Forbidden - Access denied |
| 404 | Not Found - Resource doesn't exist |
| 422 | Validation Error - Invalid data format |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |

---

## 🔒 Rate Limits

| Endpoint                       | Limit                   |
| ------------------------------ | ----------------------- |
| `/auth/login`                  | 5 attempts per minute   |
| `/auth/register`               | 3 per hour per IP       |
| `/auth/password-reset/request` | 3 per hour per email    |
| General API                    | 100 requests per minute |

---

## 📝 Data Types

### User Object

```typescript
interface User {
  id: string; // UUID
  username: string; // 3-50 chars, alphanumeric + underscore
  email: string; // Valid email
  avatar_url?: string; // URL to avatar image
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
  expires_in: number; // Seconds until access token expires
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
```

---

_Last Updated: Week 1, Day 5_
