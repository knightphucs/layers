"""add user_badges table (Week 7 Day 5)

Revision ID: w7d5_badges
Revises: w7d4_quests
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "w7d5_badges"
down_revision = "w7d4_quests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("badge_id", sa.String(length=50), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_user_badge", "user_badges", ["user_id", "badge_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_user_badge", "user_badges", type_="unique")
    op.drop_table("user_badges")
