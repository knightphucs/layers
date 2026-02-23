"""Cleanup duplicate artifacts status index

Revision ID: w3d7_cleanup_artifacts_idx
Revises: w3d6_artifacts_status_index
Create Date: 2026-02-23

Ensures only idx_artifacts_status exists (drops or renames idx_artifacts_active).
"""
from typing import Sequence, Union

from alembic import op


revision = 'w3d7_cleanup_artifacts_idx'
down_revision = 'w3d6_artifacts_status_index'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'idx_artifacts_status'
            ) AND EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'idx_artifacts_active'
            ) THEN
                DROP INDEX IF EXISTS idx_artifacts_active;
            ELSIF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'idx_artifacts_status'
            ) AND EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'idx_artifacts_active'
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
