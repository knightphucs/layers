"""
LAYERS - API v1 Router
Combines all API routes into one router
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.map import router as map_router 
from app.api.v1.artifacts import router as artifacts_router
from app.api.v1.explore import router as explore_router
from app.api.v1.anti_cheat import router as anti_cheat_router
from app.api.v1.health import router as health_router
from app.api.v1.notifications import router as notifications_router
# from app.api.v1.social import router as social_router  # Week 6
# from app.api.v1.commerce import router as commerce_router  # Week 7

api_router = APIRouter()

# Include all routers
api_router.include_router(auth_router)
api_router.include_router(map_router)
api_router.include_router(artifacts_router)
api_router.include_router(explore_router)
api_router.include_router(anti_cheat_router)
api_router.include_router(health_router)
api_router.include_router(notifications_router)
# api_router.include_router(social_router)
# api_router.include_router(commerce_router)


@api_router.get("/", tags=["API Info"])
async def api_info():
    """
    API version information
    """
    return {
        "api_version": "v1",
        "status": "active",
        "week": 5,
        "day": 2,
        "modules": {
            "auth": "✅ Active (Week 1)",
            "map": "✅ Active (Day 1 — PostGIS geo-queries)",
            "artifacts": "✅ Active (Day 2 — CRUD, privacy, Slow Mail)",
            "explore": "✅ Active (Day 3 — Fog of War)",
            "anti_cheat": "✅ Active (Day 4 — 4 detection methods)",
            "health": "✅ Active (Day 5 — System monitoring)",
            "notifications": "✅ Active (Week 5 Day 2 — Push notifications)",
            "social": "🚧 Coming Week 5",
            "commerce": "🚧 Coming Week 7",
        },
        "endpoints_total": 35,
        "test_files": 6,
    }
