"""add xp_events table (Week 7 Day 3)

Revision ID: w7d3_xp_events
Revises: w6d5_game_001
Create Date: 2026-06-06

WHAT THIS MIGRATION DOES:
    Creates xp_events table for auditing XP grant/deduct operations.
    Stores before/after snapshots of XP and level per event, plus an
    optional idempotency_key to deduplicate concurrent award requests.

PURELY ADDITIVE — no existing tables modified.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "w7d3_xp_events"
down_revision = "w6d5_game_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "xp_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("event_type", sa.String(length=40), nullable=False, index=True),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("ref_id", postgresql.UUID(as_uuid=True)),
        sa.Column("idempotency_key", sa.String(length=120)),
        sa.Column("xp_before", sa.Integer, nullable=False, server_default="0"),
        sa.Column("xp_after", sa.Integer, nullable=False, server_default="0"),
        sa.Column("level_before", sa.Integer, nullable=False, server_default="1"),
        sa.Column("level_after", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False, index=True),
    )
    op.create_unique_constraint(
        "uq_xp_events_idempotency_key", "xp_events", ["idempotency_key"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_xp_events_idempotency_key", "xp_events", type_="unique")
    op.drop_table("xp_events")
