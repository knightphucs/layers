"""Fix schema gaps: artifacts FK, geo indexes, notification partial index

Revision ID: w7d6_schema_gaps
Revises: w7d5_badges
Create Date: 2026-06-12

WHAT THIS MIGRATION DOES:
  1. Add missing FK fk_artifacts_location_id_locations
  2. Create GiST index idx_chat_rooms_center_geom (PostGIS campfire queries)
  3. Create GiST index idx_waves_geom (PostGIS wave proximity queries)
  4. Fix ix_notification_history_user_unread: drop old (user_id only) index,
     create correct partial compound index on (user_id, is_read) WHERE NOT is_read

PURELY ADDITIVE on the FK and indexes.
"""
from alembic import op
import sqlalchemy as sa

revision = "w7d6_schema_gaps"
down_revision = "w7d5_badges"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Missing FK on artifacts.location_id → locations.id
    op.create_foreign_key(
        "fk_artifacts_location_id_locations",
        "artifacts",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 2. GiST index for campfire center_geom (PostGIS spatial queries)
    op.create_index(
        "idx_chat_rooms_center_geom",
        "chat_rooms",
        ["center_geom"],
        postgresql_using="gist",
    )

    # 3. GiST index for wave geom (PostGIS wave proximity queries)
    op.create_index(
        "idx_waves_geom",
        "waves",
        ["geom"],
        postgresql_using="gist",
    )

    # 4. Fix notification_history unread index:
    #    old index only covered user_id; replace with partial compound index
    op.drop_index(
        "ix_notification_history_user_unread",
        table_name="notification_history",
    )
    op.create_index(
        "ix_notification_history_user_unread",
        "notification_history",
        ["user_id", "is_read"],
        postgresql_where=sa.text("NOT is_read"),
    )


def downgrade() -> None:
    # Restore old single-column unread index
    op.drop_index(
        "ix_notification_history_user_unread",
        table_name="notification_history",
    )
    op.create_index(
        "ix_notification_history_user_unread",
        "notification_history",
        ["user_id"],
    )

    op.drop_index("idx_waves_geom", table_name="waves")
    op.drop_index("idx_chat_rooms_center_geom", table_name="chat_rooms")
    op.drop_constraint(
        "fk_artifacts_location_id_locations", "artifacts", type_="foreignkey"
    )
