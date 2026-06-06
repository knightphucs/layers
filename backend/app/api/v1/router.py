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
from app.api.v1.connections import router as connections_router
from app.api.v1.files import router as files_router
from app.api.v1.chat import router as chat_router
from app.api.v1.social_spark import router as social_spark_router
from app.api.v1.game import router as game_router
from app.api.v1.xp import router as xp_router

api_router = APIRouter()

# Include all routers
api_router.include_router(auth_router)
api_router.include_router(map_router)
api_router.include_router(artifacts_router)
api_router.include_router(explore_router)
api_router.include_router(anti_cheat_router)
api_router.include_router(health_router)
api_router.include_router(notifications_router)
api_router.include_router(connections_router)
api_router.include_router(files_router)
api_router.include_router(chat_router)
api_router.include_router(social_spark_router)
api_router.include_router(game_router)
api_router.include_router(xp_router)


@api_router.get("/", tags=["API Info"])
async def api_info():
    """
    API version information
    """
    return {
        "api_version": "v1",
        "status": "active",
        "week": 7,
        "day": 3,
        "modules": {
            "auth": "✅ Active (Week 1)",
            "map": "✅ Active (Day 1 — PostGIS geo-queries)",
            "artifacts": "✅ Active (Day 2 — CRUD, privacy, Slow Mail)",
            "explore": "✅ Active (Day 3 — Fog of War)",
            "anti_cheat": "✅ Active (Day 4 — 4 detection methods)",
            "health": "✅ Active (Day 5 — System monitoring)",
            "notifications": "✅ Active (Week 5 Day 2 — Push notifications)",
            "connections": "✅ Active (Week 5 Day 4 — Connection system)",
            "chat": "✅ Active (Week 6 Day 3 — Campfire chat system)",
            "social_spark": "✅ Active (Week 6 Day 4 — boost/wave/synchronicity)",
            "game": "✅ Active (Week 6 Day 5 — Truth or Dare in campfires)",
            "xp": "✅ Active (Week 7 Day 3 — XP system)",
            "commerce": "🚧 Coming Week 7",
        },
        "websocket_endpoints": [
            "WS /api/v1/chat/ws/{room_id}?token={jwt}",
        ],
        "endpoints_total": 72,
        "test_files": 18,
    }
