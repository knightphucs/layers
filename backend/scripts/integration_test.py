#!/usr/bin/env python3
"""
LAYERS - Final Integration Test Script
Run this to verify your entire Week 1 setup is working!

Usage:
    python scripts/integration_test.py
"""

import asyncio
import httpx
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

# Test user data
TEST_USER = {
    "email": f"integrationtest_{datetime.now().strftime('%H%M%S')}@layers.app",
    "username": f"testuser_{datetime.now().strftime('%H%M%S')}",
    "password": "TestPass123!"
}


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")


def error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")


def info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")


def warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")


async def test_health():
    """Test health endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        return True


async def test_root():
    """Test root endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_URL)
        assert response.status_code == 200
        data = response.json()
        assert "LAYERS" in data["message"]
        return True


async def test_api_info():
    """Test API info endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert data["api_version"] == "v1"
        return True


async def test_register():
    """Test user registration"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/auth/register",
            json=TEST_USER
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        return data


async def test_login():
    """Test user login"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/auth/login",
            json={
                "email": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        return data


async def test_get_profile(access_token: str):
    """Test getting user profile"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_USER["email"].lower()
        assert data["username"] == TEST_USER["username"].lower()
        assert "experience_points" in data
        assert "level" in data
        return data


async def test_update_profile(access_token: str):
    """Test updating user profile"""
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{API_URL}/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"bio": "Integration test bio!"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["bio"] == "Integration test bio!"
        return data


async def test_refresh_token(refresh_token: str):
    """Test token refresh"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        return data


async def test_check_email():
    """Test email availability check"""
    async with httpx.AsyncClient() as client:
        # Check taken email
        response = await client.get(f"{API_URL}/auth/check-email/{TEST_USER['email']}")
        assert response.status_code == 200
        assert response.json()["available"] == False
        
        # Check available email
        response = await client.get(f"{API_URL}/auth/check-email/available@example.com")
        assert response.status_code == 200
        assert response.json()["available"] == True
        return True


async def test_check_username():
    """Test username availability check"""
    async with httpx.AsyncClient() as client:
        # Check taken username
        response = await client.get(f"{API_URL}/auth/check-username/{TEST_USER['username']}")
        assert response.status_code == 200
        assert response.json()["available"] == False
        
        # Check available username
        response = await client.get(f"{API_URL}/auth/check-username/availableuser999")
        assert response.status_code == 200
        assert response.json()["available"] == True
        return True


async def test_password_reset_request():
    """Test password reset request"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/auth/password-reset/request",
            json={"email": TEST_USER["email"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data
        return data


async def test_invalid_login():
    """Test login with wrong password"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/auth/login",
            json={
                "email": TEST_USER["email"],
                "password": "WrongPassword123!"
            }
        )
        assert response.status_code == 401
        return True


async def test_unauthorized_access():
    """Test accessing protected route without token"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/auth/me")
        assert response.status_code == 403
        return True


async def test_invalid_token():
    """Test accessing with invalid token"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401
        return True


async def main():
    print("=" * 60)
    print("🌆 LAYERS - Week 1 Integration Test")
    print("=" * 60)
    print()
    
    results = []
    access_token = None
    refresh_token = None
    
    # Test health & basic endpoints
    print("📍 Testing Basic Endpoints...")
    try:
        await test_health()
        success("Health check passed")
        results.append(("Health Check", True))
    except Exception as e:
        error(f"Health check failed: {e}")
        error("Make sure the server is running: uvicorn app.main:app --reload")
        results.append(("Health Check", False))
        return
    
    try:
        await test_root()
        success("Root endpoint passed")
        results.append(("Root Endpoint", True))
    except Exception as e:
        error(f"Root endpoint failed: {e}")
        results.append(("Root Endpoint", False))
    
    try:
        await test_api_info()
        success("API info endpoint passed")
        results.append(("API Info", True))
    except Exception as e:
        error(f"API info failed: {e}")
        results.append(("API Info", False))
    
    # Test registration
    print("\n📍 Testing Authentication...")
    try:
        data = await test_register()
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]
        success(f"Registration passed (user: {TEST_USER['username']})")
        results.append(("Registration", True))
    except Exception as e:
        error(f"Registration failed: {e}")
        results.append(("Registration", False))
    
    # Test login
    try:
        data = await test_login()
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]
        success("Login passed")
        results.append(("Login", True))
    except Exception as e:
        error(f"Login failed: {e}")
        results.append(("Login", False))
    
    # Test profile operations
    print("\n📍 Testing Profile Operations...")
    if access_token:
        try:
            await test_get_profile(access_token)
            success("Get profile passed")
            results.append(("Get Profile", True))
        except Exception as e:
            error(f"Get profile failed: {e}")
            results.append(("Get Profile", False))
        
        try:
            await test_update_profile(access_token)
            success("Update profile passed")
            results.append(("Update Profile", True))
        except Exception as e:
            error(f"Update profile failed: {e}")
            results.append(("Update Profile", False))
    
    # Test token refresh
    print("\n📍 Testing Token Operations...")
    if refresh_token:
        try:
            await test_refresh_token(refresh_token)
            success("Token refresh passed")
            results.append(("Token Refresh", True))
        except Exception as e:
            error(f"Token refresh failed: {e}")
            results.append(("Token Refresh", False))
    
    # Test utility endpoints
    print("\n📍 Testing Utility Endpoints...")
    try:
        await test_check_email()
        success("Email availability check passed")
        results.append(("Check Email", True))
    except Exception as e:
        error(f"Email check failed: {e}")
        results.append(("Check Email", False))
    
    try:
        await test_check_username()
        success("Username availability check passed")
        results.append(("Check Username", True))
    except Exception as e:
        error(f"Username check failed: {e}")
        results.append(("Check Username", False))
    
    # Test password reset
    try:
        await test_password_reset_request()
        success("Password reset request passed")
        results.append(("Password Reset", True))
    except Exception as e:
        error(f"Password reset failed: {e}")
        results.append(("Password Reset", False))
    
    # Test error handling
    print("\n📍 Testing Error Handling...")
    try:
        await test_invalid_login()
        success("Invalid login rejection passed")
        results.append(("Invalid Login", True))
    except Exception as e:
        error(f"Invalid login test failed: {e}")
        results.append(("Invalid Login", False))
    
    try:
        await test_unauthorized_access()
        success("Unauthorized access rejection passed")
        results.append(("Unauthorized Access", True))
    except Exception as e:
        error(f"Unauthorized test failed: {e}")
        results.append(("Unauthorized Access", False))
    
    try:
        await test_invalid_token()
        success("Invalid token rejection passed")
        results.append(("Invalid Token", True))
    except Exception as e:
        error(f"Invalid token test failed: {e}")
        results.append(("Invalid Token", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Integration Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"   {name}: {status}")
    
    print("\n" + "=" * 60)
    
    if passed == total:
        print(f"{Colors.GREEN}🎉 All {total} tests passed! Week 1 is complete!{Colors.END}")
        print("=" * 60)
        print(f"\n{Colors.BLUE}🚀 Ready for Week 2: Mobile App Development!{Colors.END}")
    else:
        print(f"{Colors.YELLOW}⚠️  {passed}/{total} tests passed{Colors.END}")
        print("=" * 60)
        print("\nPlease fix failing tests before proceeding.")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {e}{Colors.END}")
        print("Make sure the server is running!")
        sys.exit(1)
