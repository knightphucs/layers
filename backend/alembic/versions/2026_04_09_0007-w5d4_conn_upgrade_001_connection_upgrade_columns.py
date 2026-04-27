"""
Migration: w5d4_conn_upgrade_001
Adds upgrade request tracking to the existing connections table.

Run: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "w5d4_conn_upgrade_001"
down_revision = "w5d2_notif_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "connections",
        sa.Column(
            "upgrade_requested_by_a",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment="User A has requested Level 2 upgrade",
        ),
    )
    op.add_column(
        "connections",
        sa.Column(
            "upgrade_requested_by_b",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment="User B has requested Level 2 upgrade",
        ),
    )
    op.add_column(
        "connections",
        sa.Column(
            "last_interaction_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("NOW()"),
            comment="Most recent interaction timestamp",
        ),
    )

    # Keep existing and future rows sortable by activity time.
    op.execute(
        "UPDATE connections SET last_interaction_at = created_at WHERE last_interaction_at IS NULL"
    )
    op.alter_column("connections", "last_interaction_at", nullable=False)

    op.create_index(
        "ix_connections_last_interaction_at",
        "connections",
        ["last_interaction_at"],
        postgresql_using="btree",
    )


def downgrade() -> None:
    op.drop_index("ix_connections_last_interaction_at", table_name="connections")
    op.drop_column("connections", "last_interaction_at")
    op.drop_column("connections", "upgrade_requested_by_b")
    op.drop_column("connections", "upgrade_requested_by_a")
