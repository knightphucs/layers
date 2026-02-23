"""
LAYERS - Alembic Migration Environment
Configures how migrations are run
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import Base

# Import ALL models here so Alembic can detect them
from app.models.user import User
from app.models.location import Location, ExploredChunk
from app.models.artifact import Artifact, ArtifactReply
from app.models.inventory import InventoryItem, MailQueue
from app.models.connection import Connection

# Alembic Config object
config = context.config

# Set database URL from settings (sync version for Alembic)
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This generates SQL scripts without connecting to the database.
    Useful for generating migration scripts to run manually.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def _include_object(object, name, type_, reflected, compare_to):
    """Exclude PostGIS internal tables from autogenerate."""
    if type_ == "table" and name in (
        "spatial_ref_sys", "geometry_columns", "geography_columns",
        "raster_columns", "raster_overviews",
    ):
        return False
    return True


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    Creates an engine and connects to the database to run migrations.
    """
    connectable = create_engine(
        settings.database_url_sync,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_schemas=False,
            include_object=_include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
