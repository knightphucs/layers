"""w8d4 shadow 001 — glitch_zones table

Revision ID: w8d4_shadow_001
Revises: w8d2_reports_001
Create Date: 2026-06-27

No PostGIS geom column here, intentionally: the GlitchZone model and
ShadowService deliberately use plain center_lat/center_lng + haversine
(small, curated zone count — a spatial index buys nothing). See the
docstring in app/models/glitch_zone.py.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "w8d4_shadow_001"
down_revision = "w8d2_reports_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "glitch_zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("center_lat", sa.Float, nullable=False),
        sa.Column("center_lng", sa.Float, nullable=False),
        sa.Column("radius_m", sa.Integer, nullable=False, server_default="150"),
        sa.Column("glitch_type", sa.String(20), nullable=False,
                  server_default="XP_SURGE"),
        sa.Column("intensity", sa.Float, nullable=False, server_default="2.0"),
        sa.Column("active_start", sa.String(5), nullable=True),
        sa.Column("active_end", sa.String(5), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False,
                  server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_glitch_zones_is_active", "glitch_zones", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_glitch_zones_is_active", table_name="glitch_zones")
    op.drop_table("glitch_zones")
