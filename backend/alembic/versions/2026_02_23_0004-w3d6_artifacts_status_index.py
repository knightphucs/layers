"""Rename artifacts status index to match expected name

Revision ID: w3d6_artifacts_status_index
Revises: w3d5_performance_indexes_001
Create Date: 2026-02-23

Ensures the artifacts status partial index is named idx_artifacts_status
to match optimization checks. Renames existing idx_artifacts_active
when present, otherwise creates idx_artifacts_status.
"""
from typing import Sequence, Union

from alembic import op


revision = 'w3d6_artifacts_status_index'
down_revision = 'w3d5_performance_indexes_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'idx_artifacts_active'
            ) AND NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'idx_artifacts_status'
            ) THEN
                ALTER INDEX idx_artifacts_active RENAME TO idx_artifacts_status;
            ELSIF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'idx_artifacts_status'
            ) THEN
                CREATE INDEX IF NOT EXISTS idx_artifacts_status
                ON artifacts(status) WHERE status = 'ACTIVE';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'idx_artifacts_status'
            ) AND NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'idx_artifacts_active'
            ) THEN
                ALTER INDEX idx_artifacts_status RENAME TO idx_artifacts_active;
            END IF;
        END $$;
    """)
