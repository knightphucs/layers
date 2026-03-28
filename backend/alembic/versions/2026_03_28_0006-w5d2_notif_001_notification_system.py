"""
Migration: w5d2_notification_system_001
Creates: device_tokens, notification_preferences, notification_history

Run: alembic upgrade head

Revision ID: w5d2_notif_001
Revises: w3d7_cleanup_artifacts_idx
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = "w5d2_notif_001"
down_revision = "w3d7_cleanup_artifacts_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # DEVICE TOKENS — Expo push tokens per device
    # =========================================================================
    op.create_table(
        "device_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("token", sa.String(500), nullable=False),
        sa.Column("platform", sa.String(10), nullable=False),
        sa.Column("device_name", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("user_id", "token", name="uq_user_device_token"),
    )

    # =========================================================================
    # NOTIFICATION PREFERENCES — Per-user toggles
    # =========================================================================
    op.create_table(
        "notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, unique=True, index=True),
        # Master toggle
        sa.Column("enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
        # Category toggles
        sa.Column("social", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("discovery", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("inbox", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("capsule", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("system", sa.Boolean, server_default=sa.text("true"), nullable=False),
        # Quiet hours
        sa.Column("quiet_hours_enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("quiet_hours_start", sa.String(5), server_default=sa.text("'23:00'"), nullable=False),
        sa.Column("quiet_hours_end", sa.String(5), server_default=sa.text("'07:00'"), nullable=False),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )

    # =========================================================================
    # NOTIFICATION HISTORY — Sent notification log
    # =========================================================================
    op.create_table(
        "notification_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("data", postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("is_read", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )

    # Partial index for unread notifications (fast badge count)
    op.create_index(
        "ix_notification_history_user_unread",
        "notification_history",
        ["user_id"],
        postgresql_where=sa.text("is_read = false"),
    )


def downgrade() -> None:
    op.drop_index("ix_notification_history_user_unread", table_name="notification_history")
    op.drop_table("notification_history")
    op.drop_table("notification_preferences")
    op.drop_table("device_tokens")
