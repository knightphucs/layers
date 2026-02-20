#!/usr/bin/env python3
"""
LAYERS - Backend Startup Test Script
Run this to verify your FastAPI setup is correct!

Usage:
    python scripts/test_startup.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test all critical imports"""
    print("🔍 Testing imports...")
    
    try:
        from app.core.config import settings
        print(f"   ✅ Config loaded: {settings.app_name} v{settings.app_version}")
    except Exception as e:
        print(f"   ❌ Config failed: {e}")
        return False
    
    try:
        from app.core.database import Base, engine, AsyncSessionLocal
        print("   ✅ Database module loaded")
    except Exception as e:
        print(f"   ❌ Database module failed: {e}")
        return False
    
    try:
        from app.core.security import create_token_pair, get_password_hash
        print("   ✅ Security module loaded")
    except Exception as e:
        print(f"   ❌ Security module failed: {e}")
        return False
    
    try:
        from app.models import User, Location, Artifact
        print("   ✅ Models loaded")
    except Exception as e:
        print(f"   ❌ Models failed: {e}")
        return False
    
    try:
        from app.api.v1.router import api_router
        print("   ✅ API router loaded")
    except Exception as e:
        print(f"   ❌ API router failed: {e}")
        return False
    
    try:
        from app.main import app
        print("   ✅ FastAPI app loaded")
    except Exception as e:
        print(f"   ❌ FastAPI app failed: {e}")
        return False
    
    return True


async def test_database_connection():
    """Test database connection"""
    print("\n🔍 Testing database connection...")
    
    try:
        from app.core.database import engine
        from sqlalchemy import text
        
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("   ✅ Database connection successful")
            
            # Check PostGIS
            result = await conn.execute(text("SELECT PostGIS_Version()"))
            version = result.scalar()
            print(f"   ✅ PostGIS version: {version}")
            
            return True
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        print("\n   🔧 Make sure Docker is running: docker-compose up -d")
        return False


def test_jwt_tokens():
    """Test JWT token generation"""
    print("\n🔍 Testing JWT tokens...")
    
    try:
        from app.core.security import create_token_pair, verify_access_token
        import uuid
        
        # Create test tokens
        test_user_id = str(uuid.uuid4())
        tokens = create_token_pair(test_user_id)
        print(f"   ✅ Access token created (length: {len(tokens.access_token)})")
        print(f"   ✅ Refresh token created (length: {len(tokens.refresh_token)})")
        
        # Verify token
        data = verify_access_token(tokens.access_token)
        if data and data.user_id == test_user_id:
            print("   ✅ Token verification successful")
            return True
        else:
            print("   ❌ Token verification failed")
            return False
    except Exception as e:
        print(f"   ❌ JWT test failed: {e}")
        return False


def test_password_hashing():
    """Test password hashing"""
    print("\n🔍 Testing password hashing...")
    
    try:
        from app.core.security import get_password_hash, verify_password
        
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        print(f"   ✅ Password hashed (length: {len(hashed)})")
        
        if verify_password(password, hashed):
            print("   ✅ Password verification successful")
            return True
        else:
            print("   ❌ Password verification failed")
            return False
    except Exception as e:
        print(f"   ❌ Password test failed: {e}")
        return False


def test_fastapi_routes():
    """Test FastAPI route registration"""
    print("\n🔍 Testing FastAPI routes...")
    
    try:
        from app.main import app
        
        routes = [route.path for route in app.routes]
        print(f"   ✅ Total routes registered: {len(routes)}")
        
        # Check critical routes exist
        critical_routes = ["/", "/health", "/api/v1/auth/register", "/api/v1/auth/login"]
        for route in critical_routes:
            if route in routes:
                print(f"   ✅ Route exists: {route}")
            else:
                print(f"   ⚠️  Route missing: {route}")
        
        return True
    except Exception as e:
        print(f"   ❌ Route test failed: {e}")
        return False


async def main():
    print("=" * 60)
    print("🌆 LAYERS - Backend Startup Test")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Database", await test_database_connection()))
    results.append(("JWT Tokens", test_jwt_tokens()))
    results.append(("Password Hash", test_password_hashing()))
    results.append(("FastAPI Routes", test_fastapi_routes()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! Your backend is ready!")
        print("=" * 60)
        print("\n🚀 Start the server with:")
        print("   uvicorn app.main:app --reload")
        print("\n📖 Then open:")
        print("   http://localhost:8000      → Welcome message")
        print("   http://localhost:8000/docs → Swagger UI")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
