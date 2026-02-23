"""
LAYERS - FastAPI Main Entry Point
"See the hidden layers of your city"
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.v1.router import api_router


# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs on startup and shutdown.
    """
    # Startup
    logger.info("🚀 Starting LAYERS API...")
    logger.info(f"📍 Debug mode: {settings.debug}")
    
    # Initialize database (create tables if not exist)
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down LAYERS API...")
    await close_db()
    logger.info("✅ Database connection closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
    ## 🌆 LAYERS API
    
    **"See the hidden layers of your city"**
    
    A location-based social network with AR and gamification.
    
    ### Features
    - 🗺️ **Geo-Spatial** - Location-based artifacts and memories
    - 🌅 **Light Layer** - Healing, memories, slow connections
    - 🌙 **Shadow Layer** - Mystery, urban legends, challenges
    - 🎮 **Gamification** - XP, levels, missions, badges
    - ✈️ **Paper Planes** - Random message delivery
    - ⏰ **Time Capsules** - Messages to the future
    
    ### Authentication
    All endpoints except `/auth/*` require Bearer token authentication.
    
    ---
    Built with ❤️ by Kazyy
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,  # Swagger UI
    redoc_url="/redoc" if settings.debug else None,  # ReDoc
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",       # React dev
        "http://localhost:19006",      # Expo web
        "http://localhost:8081",       # Expo
        "exp://localhost:8081",        # Expo Go
        "*",  # Allow all for development (restrict in production!)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API router
app.include_router(api_router, prefix="/api/v1")


# Health check endpoint
# @app.get("/health", tags=["Health"])
# async def health_check():
#     """
#     Health check endpoint.
#     Returns service status for monitoring.
#     """
#     return {
#         "status": "healthy",
#         "service": settings.app_name,
#         "version": settings.app_version
#     }


# Hello endpoint
@app.get("/hello", tags=["Greeting"])
async def greeting():
    """
    Simple greeting endpoint to test API is running.
    """
    return {
        "message": f"Welcome to {settings.app_name} API!",
        "version": settings.app_version,
        "description": "See /docs for API documentation."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
