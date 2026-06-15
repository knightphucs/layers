"""w8d1 moderation 001 — moderation_logs table

Revision ID: w8d1_moderation_001
Revises: w7d6_schema_gaps
Create Date: 2026-06-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "w8d1_moderation_001"
down_revision = "w7d6_schema_gaps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "moderation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True, index=True),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("artifacts.id", ondelete="SET NULL"),
                  nullable=True, index=True),
        sa.Column("context", sa.String(30), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False, index=True),
        sa.Column("reasons", postgresql.JSONB, nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("excerpt", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_moderation_logs_created_at", "moderation_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_moderation_logs_created_at", table_name="moderation_logs")
    op.drop_table("moderation_logs")
