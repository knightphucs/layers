"""w9d3 add user_blocks table

Revision ID: w9d3_user_blocks_001
Revises: w8d4_shadow_001
Create Date: 2026-07-07

LAYERS Week 9 Day 3 — user-level blocking for Privacy & Safety.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "w9d3_user_blocks_001"
down_revision = "w8d4_shadow_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_blocks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "blocker_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "blocked_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_user_blocks_pair"),
    )
    op.create_index("ix_user_blocks_blocker", "user_blocks", ["blocker_id"])
    op.create_index("ix_user_blocks_blocked", "user_blocks", ["blocked_id"])


def downgrade() -> None:
    op.drop_index("ix_user_blocks_blocked", table_name="user_blocks")
    op.drop_index("ix_user_blocks_blocker", table_name="user_blocks")
    op.drop_table("user_blocks")
