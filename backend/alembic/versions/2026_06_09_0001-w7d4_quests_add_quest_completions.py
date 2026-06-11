"""add quest_completions + user streak columns

Revision ID: w7d4_quests
Revises: w7d3_xp_events
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "w7d4_quests"
down_revision = "w7d3_xp_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Streak columns on users
    op.add_column("users", sa.Column("current_streak", sa.Integer(),
                                     nullable=False, server_default="0"))
    op.add_column("users", sa.Column("longest_streak", sa.Integer(),
                                     nullable=False, server_default="0"))
    op.add_column("users", sa.Column("last_quest_date", sa.Date(), nullable=True))

    # Quest completions table
    op.create_table(
        "quest_completions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("quest_id", sa.String(length=50), nullable=False),
        sa.Column("quest_date", sa.Date(), nullable=False, index=True),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_quest_completion_user_quest_date",
        "quest_completions", ["user_id", "quest_id", "quest_date"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_quest_completion_user_quest_date",
                       "quest_completions", type_="unique")
    op.drop_table("quest_completions")
    op.drop_column("users", "last_quest_date")
    op.drop_column("users", "longest_streak")
    op.drop_column("users", "current_streak")
