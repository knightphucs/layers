"""
LAYERS - Authentication Unit Tests
Test all auth endpoints: register, login, refresh, password reset
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings


@pytest.fixture(scope="function")
async def client():
    """Create async test client with isolated test database."""
    # Use separate test database
    engine = create_async_engine(settings.test_database_url, pool_pre_ping=True)

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Drop and recreate tables for clean state
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Override the get_db dependency
    async def override_get_db():
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    # Create test client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup
    app.dependency_overrides.clear()
    await engine.dispose()


# =============================================================================
# Test Data
# =============================================================================

TEST_USER = {
    "email": "testuser@layers.app",
    "username": "testuser",
    "password": "TestPass123!"
}

TEST_USER_2 = {
    "email": "another@layers.app",
    "username": "anotheruser",
    "password": "Another123!"
}


# =============================================================================
# Helper Functions
# =============================================================================

async def register_test_user(client, user_data=None):
    """Helper to register a user and return the response."""
    if user_data is None:
        user_data = TEST_USER
    response = await client.post("/api/v1/auth/register", json=user_data)
    return response


async def login_test_user(client, user_data=None):
    """Helper to login a user and return tokens."""
    if user_data is None:
        user_data = TEST_USER
    response = await client.post("/api/v1/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })
    return response.json()


# =============================================================================
# Registration Tests
# =============================================================================

class TestRegistration:
    """Tests for /auth/register endpoint"""
    
    @pytest.mark.asyncio
    async def test_register_success(self, client):
        """Test successful user registration."""
        response = await client.post("/api/v1/auth/register", json=TEST_USER)
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client):
        """Test registration with existing email fails."""
        # First registration
        await client.post("/api/v1/auth/register", json=TEST_USER_2)
        
        # Try to register with same email
        duplicate = {
            "email": TEST_USER_2["email"],
            "username": "different",
            "password": "Different123!"
        }
        response = await client.post("/api/v1/auth/register", json=duplicate)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client):
        """Test registration with existing username fails."""
        # First register TEST_USER
        await register_test_user(client)

        # Try to register with same username
        duplicate = {
            "email": "new@layers.app",
            "username": TEST_USER["username"],  # Same username
            "password": "NewPass123!"
        }
        response = await client.post("/api/v1/auth/register", json=duplicate)

        assert response.status_code == 400
        assert "already taken" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_weak_password(self, client):
        """Test registration with weak password fails."""
        weak = {
            "email": "weak@layers.app",
            "username": "weakuser",
            "password": "weak"  # Too short, no uppercase, no numbers
        }
        response = await client.post("/api/v1/auth/register", json=weak)
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client):
        """Test registration with invalid email fails."""
        invalid = {
            "email": "not-an-email",
            "username": "validuser",
            "password": "ValidPass123!"
        }
        response = await client.post("/api/v1/auth/register", json=invalid)
        
        assert response.status_code == 422


# =============================================================================
# Login Tests
# =============================================================================

class TestLogin:
    """Tests for /auth/login endpoint"""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """Test successful login."""
        # First register the user
        await register_test_user(client)

        # Then login
        response = await client.post("/api/v1/auth/login", json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        """Test login with wrong password fails."""
        response = await client.post("/api/v1/auth/login", json={
            "email": TEST_USER["email"],
            "password": "WrongPassword123!"
        })
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        """Test login with non-existent email fails."""
        response = await client.post("/api/v1/auth/login", json={
            "email": "nonexistent@layers.app",
            "password": "SomePass123!"
        })
        
        assert response.status_code == 401


# =============================================================================
# Token Tests
# =============================================================================

class TestTokens:
    """Tests for token operations"""
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, client):
        """Test token refresh."""
        # Register and login first
        await register_test_user(client)
        tokens = await login_test_user(client)
        refresh_token = tokens["refresh_token"]

        # Refresh
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    @pytest.mark.asyncio
    async def test_invalid_refresh_token(self, client):
        """Test refresh with invalid token fails."""
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid-token"
        })
        
        assert response.status_code == 401


# =============================================================================
# Protected Routes Tests
# =============================================================================

class TestProtectedRoutes:
    """Tests for authenticated endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_me_authenticated(self, client):
        """Test getting current user profile."""
        # Register and login
        await register_test_user(client)
        tokens = await login_test_user(client)
        access_token = tokens["access_token"]

        # Get profile
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_USER["email"].lower()
        assert data["username"] == TEST_USER["username"].lower()
    
    @pytest.mark.asyncio
    async def test_get_me_unauthenticated(self, client):
        """Test accessing protected route without token fails."""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 403  # Or 401, depends on setup
    
    @pytest.mark.asyncio
    async def test_update_profile(self, client):
        """Test updating user profile."""
        # Register and login
        await register_test_user(client)
        tokens = await login_test_user(client)
        access_token = tokens["access_token"]

        # Update profile
        response = await client.put(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"bio": "Hello, I'm testing LAYERS!"}
        )

        assert response.status_code == 200
        assert response.json()["bio"] == "Hello, I'm testing LAYERS!"


# =============================================================================
# Utility Endpoint Tests
# =============================================================================

class TestUtilityEndpoints:
    """Tests for utility endpoints"""
    
    @pytest.mark.asyncio
    async def test_check_email_taken(self, client):
        """Test checking if email is taken."""
        # Register user first
        await register_test_user(client)

        response = await client.get(f"/api/v1/auth/check-email/{TEST_USER['email']}")

        assert response.status_code == 200
        assert response.json()["available"] == False
    
    @pytest.mark.asyncio
    async def test_check_email_available(self, client):
        """Test checking if email is available."""
        response = await client.get("/api/v1/auth/check-email/available@layers.app")
        
        assert response.status_code == 200
        assert response.json()["available"] == True
    
    @pytest.mark.asyncio
    async def test_check_username_taken(self, client):
        """Test checking if username is taken."""
        # Register user first
        await register_test_user(client)

        response = await client.get(f"/api/v1/auth/check-username/{TEST_USER['username']}")

        assert response.status_code == 200
        assert response.json()["available"] == False


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
