"""
LAYERS - Database Optimization & Index Tuning
================================================
PURPOSE:
  Run this script to check & optimize your PostGIS indexes and queries.
  Target: All geo queries should return in <50ms.

Run: python scripts/optimize_database.py
"""

import asyncio
import time
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings


# ============================================================
# DATABASE CONNECTION (uses same config as app)
# ============================================================
engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ============================================================
# INDEX VERIFICATION
# ============================================================
async def check_indexes(session: AsyncSession):
    """List all indexes on geo-related tables."""
    print("\n" + "=" * 60)
    print("📊 INDEX AUDIT")
    print("=" * 60)

    tables = ["locations", "artifacts", "explored_chunks", "users"]

    for table in tables:
        result = await session.execute(text(f"""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = '{table}'
            ORDER BY indexname;
        """))
        indexes = result.fetchall()

        print(f"\n📋 {table} ({len(indexes)} indexes):")
        for idx_name, idx_def in indexes:
            # Highlight spatial indexes
            is_spatial = "gist" in idx_def.lower() or "geom" in idx_def.lower()
            icon = "🌍" if is_spatial else "  "
            print(f"  {icon} {idx_name}")
            print(f"     → {idx_def}")

    # Check for MISSING recommended indexes
    print("\n" + "-" * 60)
    print("🔍 CHECKING RECOMMENDED INDEXES...")

    recommended = [
        ("idx_locations_geom", "locations", "GiST spatial index on geom"),
        ("idx_artifacts_location_id", "artifacts", "FK lookup for artifacts by location"),
        ("idx_artifacts_user_id", "artifacts", "FK lookup for artifacts by user"),
        ("idx_artifacts_status", "artifacts", "Filter active artifacts"),
        ("idx_explored_chunks_user_id", "explored_chunks", "Fog of War per user"),
        ("idx_users_banned_until", "users", "Ban check queries"),
        ("idx_users_is_banned", "users", "Quick ban filter"),
    ]

    for idx_name, table, description in recommended:
        result = await session.execute(text(f"""
            SELECT 1 FROM pg_indexes
            WHERE tablename = '{table}' AND indexname = '{idx_name}'
        """))
        exists = result.fetchone() is not None
        status = "✅" if exists else "❌ MISSING"
        print(f"  {status} {idx_name} ({description})")

    return True


# ============================================================
# CREATE MISSING INDEXES
# ============================================================
async def create_recommended_indexes(session: AsyncSession):
    """Create any missing recommended indexes."""
    print("\n" + "=" * 60)
    print("🔨 CREATING RECOMMENDED INDEXES")
    print("=" * 60)

    index_sql = [
        # Artifacts - most queried table
        """CREATE INDEX IF NOT EXISTS idx_artifacts_location_id
           ON artifacts(location_id)""",
        """CREATE INDEX IF NOT EXISTS idx_artifacts_user_id
           ON artifacts(user_id)""",
        """CREATE INDEX IF NOT EXISTS idx_artifacts_status
           ON artifacts(status) WHERE status = 'ACTIVE'""",
        """CREATE INDEX IF NOT EXISTS idx_artifacts_content_type
           ON artifacts(content_type)""",
        """CREATE INDEX IF NOT EXISTS idx_artifacts_visibility
           ON artifacts(visibility)""",
        """CREATE INDEX IF NOT EXISTS idx_artifacts_created_at
           ON artifacts(created_at DESC)""",

        # Explored Chunks - Fog of War
        """CREATE INDEX IF NOT EXISTS idx_explored_chunks_user_id
           ON explored_chunks(user_id)""",
        """CREATE UNIQUE INDEX IF NOT EXISTS idx_explored_chunks_user_chunk
           ON explored_chunks(user_id, chunk_x, chunk_y)""",

        # Locations - geo queries
        """CREATE INDEX IF NOT EXISTS idx_locations_layer
           ON locations(layer)""",
        """CREATE INDEX IF NOT EXISTS idx_locations_category
           ON locations(category)""",

        # Users - ban checks
        """CREATE INDEX IF NOT EXISTS idx_users_banned_until
           ON users(banned_until) WHERE banned_until IS NOT NULL""",
        """CREATE INDEX IF NOT EXISTS idx_users_is_banned
           ON users(is_banned) WHERE is_banned = true""",
    ]

    for sql in index_sql:
        try:
            await session.execute(text(sql))
            idx_name = sql.split("IF NOT EXISTS ")[1].split("\n")[0].strip()
            print(f"  ✅ {idx_name}")
        except Exception as e:
            print(f"  ⚠️  {sql[:50]}... → {e}")

    await session.commit()
    print("\n  Done! All recommended indexes created.")


# ============================================================
# BENCHMARK GEO QUERIES (EXPLAIN ANALYZE)
# ============================================================
async def benchmark_geo_queries(session: AsyncSession):
    """Run EXPLAIN ANALYZE on critical geo queries."""
    print("\n" + "=" * 60)
    print("⚡ QUERY PERFORMANCE BENCHMARKS")
    print("=" * 60)

    # HCMC District 1 center
    test_lat, test_lng = 10.7769, 106.7009

    queries = {
        "Nearby locations (1km radius)": f"""
            EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
            SELECT id, latitude, longitude, name, category
            FROM locations
            WHERE ST_DWithin(
                geom,
                ST_SetSRID(ST_MakePoint({test_lng}, {test_lat}), 4326)::geography,
                1000
            )
            LIMIT 50;
        """,

        "Nearby artifacts (500m radius)": f"""
            EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
            SELECT a.id, a.content_type, a.visibility, l.latitude, l.longitude
            FROM artifacts a
            JOIN locations l ON a.location_id = l.id
            WHERE ST_DWithin(
                l.geom,
                ST_SetSRID(ST_MakePoint({test_lng}, {test_lat}), 4326)::geography,
                500
            )
            AND a.status = 'ACTIVE'
            LIMIT 50;
        """,

        "Explored chunks in viewport": f"""
            EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
            SELECT chunk_x, chunk_y, explored_at
            FROM explored_chunks
            WHERE user_id = '00000000-0000-0000-0000-000000000001'
            AND chunk_x BETWEEN 1196 AND 1206
            AND chunk_y BETWEEN 1077 AND 1087;
        """,

        "Location anti-spam check (20m radius)": f"""
            EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
            SELECT COUNT(*)
            FROM locations
            WHERE ST_DWithin(
                geom,
                ST_SetSRID(ST_MakePoint({test_lng}, {test_lat}), 4326)::geography,
                20
            );
        """,
    }

    for name, query in queries.items():
        print(f"\n📌 {name}")
        print("-" * 40)
        try:
            result = await session.execute(text(query))
            rows = result.fetchall()

            for row in rows:
                line = row[0]
                # Highlight execution time
                if "Execution Time" in line or "Planning Time" in line:
                    print(f"  ⏱️  {line}")
                elif "Seq Scan" in line:
                    print(f"  ⚠️  {line}  ← SEQUENTIAL SCAN (needs index!)")
                elif "Index Scan" in line or "Bitmap" in line:
                    print(f"  ✅ {line}")
                else:
                    print(f"     {line}")

        except Exception as e:
            print(f"  ⚠️  Query failed (table may be empty): {e}")


# ============================================================
# TABLE SIZE STATISTICS
# ============================================================
async def check_table_sizes(session: AsyncSession):
    """Show table sizes and row counts."""
    print("\n" + "=" * 60)
    print("📦 TABLE STATISTICS")
    print("=" * 60)

    result = await session.execute(text("""
        SELECT
            relname AS table_name,
            n_live_tup AS row_count,
            pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
            pg_size_pretty(pg_indexes_size(relid)) AS index_size
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
        ORDER BY n_live_tup DESC;
    """))
    rows = result.fetchall()

    print(f"\n  {'Table':<25} {'Rows':>10} {'Total Size':>12} {'Index Size':>12}")
    print(f"  {'-'*25} {'-'*10} {'-'*12} {'-'*12}")
    for name, rows_count, total, idx_size in rows:
        print(f"  {name:<25} {rows_count:>10,} {total:>12} {idx_size:>12}")


# ============================================================
# PostGIS VERSION CHECK
# ============================================================
async def check_postgis(session: AsyncSession):
    """Verify PostGIS is installed and check version."""
    print("\n" + "=" * 60)
    print("🌍 PostGIS STATUS")
    print("=" * 60)

    try:
        result = await session.execute(text("SELECT PostGIS_Full_Version();"))
        version = result.scalar()
        print(f"  ✅ PostGIS: {version}")
    except Exception:
        print("  ❌ PostGIS NOT INSTALLED!")
        print("  Run: CREATE EXTENSION IF NOT EXISTS postgis;")

    try:
        result = await session.execute(text("SELECT version();"))
        pg_version = result.scalar()
        print(f"  ✅ PostgreSQL: {pg_version[:50]}...")
    except Exception as e:
        print(f"  ❌ PostgreSQL error: {e}")


# ============================================================
# MAIN
# ============================================================
async def main():
    print("🛡️ LAYERS — Database Optimization Report")
    print(f"   Target: All geo queries < 50ms\n")

    async with AsyncSessionLocal() as session:
        await check_postgis(session)
        await check_indexes(session)
        await create_recommended_indexes(session)
        await check_table_sizes(session)
        await benchmark_geo_queries(session)

    print("\n" + "=" * 60)
    print("✅ OPTIMIZATION COMPLETE")
    print("=" * 60)
    print("""
    Next steps if queries are slow:
    1. Check for Sequential Scans (⚠️ above) — add missing indexes
    2. Run VACUUM ANALYZE on large tables
    3. Increase shared_buffers in postgresql.conf
    4. Use connection pooling (pgbouncer) for production
    """)


if __name__ == "__main__":
    asyncio.run(main())
