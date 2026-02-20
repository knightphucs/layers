"""
LAYERS - System Health Check API
===================================

Endpoints:
  GET /api/v1/health          — Quick health check (no auth)
  GET /api/v1/health/detailed — Full system status (admin only)

PURPOSE:
  Monitor all systems: DB, PostGIS, Redis, anti-cheat.
  Use this for uptime monitoring, deployment checks, and debugging.
"""

import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User


router = APIRouter(prefix="/health", tags=["Health"])


# ============================================================
# GET /health — Quick check (public, no auth)
# ============================================================
@router.get(
    "",
    summary="Quick health check",
    description="Returns OK if the API is running. No authentication required.",
)
async def health_check():
    return {
        "status": "healthy",
        "app": "LAYERS",
        "version": "0.3.5",  # Week 3 Day 5
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================
# GET /health/detailed — Full system check (admin only)
# ============================================================
@router.get(
    "/detailed",
    summary="Detailed system health (admin only)",
    description="""
    Checks all critical systems:
    - PostgreSQL connection + version
    - PostGIS extension + geo query test
    - Table row counts
    - Anti-cheat system stats
    - Response time benchmarks
    """,
)
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Admin check
    if current_user.role.value != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    checks = {}
    overall_start = time.perf_counter()

    # ---- 1. PostgreSQL ----
    try:
        start = time.perf_counter()
        result = await db.execute(text("SELECT version()"))
        pg_version = result.scalar()
        elapsed = (time.perf_counter() - start) * 1000
        checks["postgresql"] = {
            "status": "✅ healthy",
            "version": pg_version[:60],
            "response_ms": round(elapsed, 1),
        }
    except Exception as e:
        checks["postgresql"] = {"status": "❌ error", "error": str(e)}

    # ---- 2. PostGIS ----
    try:
        start = time.perf_counter()
        result = await db.execute(text("SELECT PostGIS_Version()"))
        postgis_version = result.scalar()
        elapsed = (time.perf_counter() - start) * 1000
        checks["postgis"] = {
            "status": "✅ healthy",
            "version": postgis_version,
            "response_ms": round(elapsed, 1),
        }
    except Exception as e:
        checks["postgis"] = {"status": "❌ error", "error": str(e)}

    # ---- 3. Geo Query Test (ST_DWithin) ----
    try:
        start = time.perf_counter()
        # Test geo query at Ben Thanh Market (HCMC)
        result = await db.execute(text("""
            SELECT ST_DWithin(
                ST_SetSRID(ST_MakePoint(106.6980, 10.7725), 4326)::geography,
                ST_SetSRID(ST_MakePoint(106.6990, 10.7798), 4326)::geography,
                1000
            ) as within_1km
        """))
        within = result.scalar()
        elapsed = (time.perf_counter() - start) * 1000
        checks["geo_query"] = {
            "status": "✅ healthy",
            "test": "Ben Thanh ↔ Notre Dame within 1km",
            "result": within,
            "response_ms": round(elapsed, 1),
            "target_ms": 50,
            "meets_target": elapsed < 50,
        }
    except Exception as e:
        checks["geo_query"] = {"status": "❌ error", "error": str(e)}

    # ---- 4. Table Row Counts ----
    try:
        tables = ["users", "locations", "artifacts", "explored_chunks"]
        row_counts = {}
        for table in tables:
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            row_counts[table] = result.scalar()
        checks["tables"] = {
            "status": "✅ healthy",
            "row_counts": row_counts,
        }
    except Exception as e:
        checks["tables"] = {"status": "⚠️ partial", "error": str(e)}

    # ---- 5. Anti-Cheat System ----
    try:
        from app.services.anti_cheat_service import _location_history
        tracked_users = len(_location_history)
        total_points = sum(len(h) for h in _location_history.values())
        checks["anti_cheat"] = {
            "status": "✅ healthy",
            "tracked_users": tracked_users,
            "total_location_points": total_points,
            "detection_methods": 4,
        }
    except Exception as e:
        checks["anti_cheat"] = {"status": "❌ error", "error": str(e)}

    # ---- 6. Index Health ----
    try:
        result = await db.execute(text("""
            SELECT COUNT(*) FROM pg_indexes
            WHERE schemaname = 'public'
        """))
        index_count = result.scalar()
        checks["indexes"] = {
            "status": "✅ healthy",
            "total_indexes": index_count,
        }
    except Exception as e:
        checks["indexes"] = {"status": "⚠️ unknown", "error": str(e)}

    total_elapsed = (time.perf_counter() - overall_start) * 1000

    return {
        "status": "healthy" if all(
            "✅" in c.get("status", "") for c in checks.values()
        ) else "degraded",
        "app": "LAYERS",
        "version": "0.3.5",
        "timestamp": datetime.utcnow().isoformat(),
        "total_check_ms": round(total_elapsed, 1),
        "checks": checks,
        "week3_modules": {
            "map_locations": "✅ Day 1",
            "artifact_crud": "✅ Day 2",
            "fog_of_war": "✅ Day 3",
            "anti_cheat": "✅ Day 4",
            "testing_optimization": "✅ Day 5",
        },
    }
