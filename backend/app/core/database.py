"""
LAYERS - Database Configuration
Async SQLAlchemy setup with PostgreSQL + PostGIS
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData
from typing import AsyncGenerator
import logging

from app.core.config import settings


logger = logging.getLogger(__name__)


# Naming convention for constraints (helps with migrations)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)

# Base class for all models
Base = declarative_base(metadata=metadata)

# Create async engine (create connection pool)
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    pool_pre_ping=True,   # Check connection health
    pool_size=5,
    max_overflow=10
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions.
    
    Usage in routes:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create tables — DEVELOPMENT ONLY.

    Alembic owns the schema. Running create_all in production is worse than
    useless: it is a no-op for tables that already exist, so a model change
    with no matching migration would silently leave the app running against
    a schema that doesn't match its models. Failing loudly is safer.

    The production deploy step is `alembic upgrade head`, not this function.
    """
    if not settings.debug:
        logger.info(
            "Skipping create_all — Alembic owns the schema. "
            "Run 'alembic upgrade head' as a deploy step."
        )
        return

    async with engine.begin() as conn:
        # Import the models PACKAGE so every model is registered. Importing a
        # hand-picked subset silently skips tables for the ones left out.
        from app import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connection"""
    await engine.dispose()
