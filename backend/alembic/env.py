"""
LAYERS - Alembic Migration Environment
Configures how migrations are run
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context
from alembic.operations import ops as alembic_ops
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
from app.models.chat import ChatRoom, Message, CampfireMember
from app.models.social_spark import (
    ArtifactBoost,
    Wave,
    ArtifactDiscovery,
    SynchronicityEvent,
)
from app.models.game import (
    CampfireGame,
    CampfireGameRound,
    CampfireGameAnswer,
)
from app.models.xp_event import XPEvent
from app.models.quest_completion import QuestCompletion
from app.models.notification import DeviceToken, NotificationPreference, NotificationHistory
from app.models.user_badge import UserBadge
from app.models.moderation_log import ModerationLog

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
    )

    with context.begin_transaction():
        context.run_migrations()


def _filter_column_diffs(op_list):
    """Strip AlterColumnOp from autogenerate (comment/nullable/type drift).
    New columns (AddColumnOp), new tables, indexes, and FKs are still reported."""
    result = []
    for op in op_list:
        if isinstance(op, alembic_ops.ModifyTableOps):
            filtered = [
                col_op for col_op in op.ops
                if not isinstance(col_op, alembic_ops.AlterColumnOp)
            ]
            if filtered:
                op.ops = filtered
                result.append(op)
        else:
            result.append(op)
    return result


def process_revision_directives(_context, _revision, directives):
    if directives and directives[0].upgrade_ops:
        directives[0].upgrade_ops.ops = _filter_column_diffs(
            directives[0].upgrade_ops.ops
        )


def _include_object(object, name, type_, reflected, compare_to):
    """Scope autogenerate to app tables only, and ignore indexes/constraints
    that exist in the DB from hand-written migrations but have no model
    counterpart (we want to keep those, not drop them)."""
    if type_ == "table":
        return name in {t.name for t in target_metadata.sorted_tables}
    if type_ in ("index", "unique_constraint", "foreign_key_constraint"):
        # reflected=True + compare_to=None → exists in DB, not in model.
        # These came from hand-written migrations; leave them alone.
        if reflected and compare_to is None:
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
            include_schemas=False,
            include_object=_include_object,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
