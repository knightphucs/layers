#!/usr/bin/env python3
"""
LAYERS - Database Setup Verification Script
Run this to verify your database is set up correctly!

Usage:
    python scripts/verify_db.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine


async def verify_database():
    """Verify database connection and PostGIS setup"""
    
    print("=" * 60)
    print("🌆 LAYERS - Database Verification")
    print("=" * 60)
    
    try:
        async with engine.connect() as conn:
            # Test basic connection
            result = await conn.execute(text("SELECT 1"))
            print("✅ Database connection: OK")
            
            # Check PostgreSQL version
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ PostgreSQL version: {version[:50]}...")
            
            # Check PostGIS
            result = await conn.execute(text("SELECT PostGIS_Version()"))
            postgis_version = result.scalar()
            print(f"✅ PostGIS version: {postgis_version}")
            
            # Check UUID extension
            result = await conn.execute(text(
                "SELECT extname FROM pg_extension WHERE extname = 'uuid-ossp'"
            ))
            if result.scalar():
                print("✅ UUID extension: Installed")
            else:
                print("⚠️  UUID extension: Not installed (will be created by migration)")
            
            # Check if tables exist
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                print(f"\n📋 Existing tables ({len(tables)}):")
                for table in tables:
                    print(f"   - {table}")
            else:
                print("\n📋 No tables yet (run migrations to create them)")
            
            print("\n" + "=" * 60)
            print("✅ Database verification complete!")
            print("=" * 60)
            
            if not tables:
                print("\n🔧 Next step: Run migrations")
                print("   alembic upgrade head")
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n🔧 Make sure Docker is running:")
        print("   docker-compose up -d")
        sys.exit(1)


async def test_geo_query():
    """Test a sample geo-spatial query"""
    print("\n🗺️  Testing geo-spatial query...")
    
    try:
        async with engine.connect() as conn:
            # Create a test point and calculate distance
            result = await conn.execute(text("""
                SELECT ST_Distance(
                    ST_SetSRID(ST_MakePoint(106.6297, 10.8231), 4326)::geography,
                    ST_SetSRID(ST_MakePoint(106.6817, 10.7626), 4326)::geography
                ) as distance_meters
            """))
            distance = result.scalar()
            print(f"✅ Distance from District 1 to District 7: {distance:.0f} meters")
            print("✅ Geo-spatial queries working!")
            
    except Exception as e:
        print(f"❌ Geo query failed: {e}")


async def main():
    """Run all verification steps in a single event loop"""
    await verify_database()
    await test_geo_query()
    
    # Optional: Clean up engine resources explicitly
    await engine.dispose()

if __name__ == "__main__":
    # Use a single asyncio.run() call
    try:
        if sys.platform == 'win32':
            # specific fix for Windows asyncio loop policy if needed
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🚫 Script interrupted.")
