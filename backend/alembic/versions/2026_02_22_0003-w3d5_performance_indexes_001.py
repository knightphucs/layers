"""Add recommended performance indexes

Revision ID: w3d5_performance_indexes_001
Revises: w3d4_anti_cheat_001
Create Date: 2026-02-22

Adds indexes recommended by optimization analysis for <50ms geo queries.
These are SAFE to add — they only improve read speed, never change data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision = 'w3d5_performance_indexes_001'
down_revision = 'w3d4_anti_cheat_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === ARTIFACTS (most queried table) ===
    op.create_index(
        'idx_artifacts_location_id', 'artifacts', ['location_id'],
        if_not_exists=True,
    )
    op.create_index(
        'idx_artifacts_user_id', 'artifacts', ['user_id'],
        if_not_exists=True,
    )
    op.create_index(
        'idx_artifacts_content_type', 'artifacts', ['content_type'],
        if_not_exists=True,
    )
    op.create_index(
        'idx_artifacts_visibility', 'artifacts', ['visibility'],
        if_not_exists=True,
    )
    op.create_index(
        'idx_artifacts_created_at_desc', 'artifacts', [sa.text('created_at DESC')],
        if_not_exists=True,
    )
    # Partial index: only active artifacts (most queries filter by status)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_artifacts_active
        ON artifacts(status) WHERE status = 'ACTIVE'
    """)

    # === EXPLORED_CHUNKS (Fog of War) ===
    op.create_index(
        'idx_explored_chunks_user_id', 'explored_chunks', ['user_id'],
        if_not_exists=True,
    )
    # Unique composite: one chunk per user
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_explored_chunks_user_chunk
        ON explored_chunks(user_id, chunk_x, chunk_y)
    """)

    # === LOCATIONS ===
    op.create_index(
        'idx_locations_layer', 'locations', ['layer'],
        if_not_exists=True,
    )
    op.create_index(
        'idx_locations_category', 'locations', ['category'],
        if_not_exists=True,
    )

    # === USERS (ban checks) ===
    # Partial indexes: only non-null / true values
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_banned_partial
        ON users(banned_until) WHERE banned_until IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_is_banned_partial
        ON users(is_banned) WHERE is_banned = true
    """)

    print("✅ Performance indexes created successfully")


def downgrade() -> None:
    # Drop all new indexes (safe — doesn't affect data)
    indexes = [
        ('idx_artifacts_location_id', 'artifacts'),
        ('idx_artifacts_user_id', 'artifacts'),
        ('idx_artifacts_content_type', 'artifacts'),
        ('idx_artifacts_visibility', 'artifacts'),
        ('idx_artifacts_created_at_desc', 'artifacts'),
        ('idx_artifacts_active', 'artifacts'),
        ('idx_explored_chunks_user_id', 'explored_chunks'),
        ('idx_explored_chunks_user_chunk', 'explored_chunks'),
        ('idx_locations_layer', 'locations'),
        ('idx_locations_category', 'locations'),
        ('idx_users_banned_partial', 'users'),
        ('idx_users_is_banned_partial', 'users'),
    ]

    for idx_name, table in indexes:
        op.execute(f"DROP INDEX IF EXISTS {idx_name}")

    print("✅ Performance indexes removed")
