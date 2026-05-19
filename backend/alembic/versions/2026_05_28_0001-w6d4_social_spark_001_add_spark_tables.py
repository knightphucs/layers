"""add social spark tables (Week 6 Day 4)

Revision ID: w6d4_spark_001
Revises: w6d3_campfire_001
Create Date: 2026-05-28

FILE: backend/alembic/versions/2026_05_28_0001-w6d4_social_spark_001_add_spark_tables.py

⚠️  Before running:
    Verify your Day 3 migration revision is 'w6d3_campfire_001'.
    If not, update down_revision below. Find current head:
        cd backend && alembic heads

WHAT THIS MIGRATION DOES:
    Creates 4 tables for the social-spark trio:
      - artifact_boosts        (📡 amplify an artifact 24h)
      - waves                  (👋 anonymous ephemeral ping, PostGIS)
      - artifact_discoveries   (idempotent unlock ledger)
      - synchronicity_events   (✨ two strangers, same artifact, 30 min)

PURELY ADDITIVE — no existing tables touched.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql


revision: str = 'w6d4_spark_001'
down_revision: Union[str, None] = 'w6d3_campfire_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # artifact_boosts  📡
    # =========================================================================
    op.create_table(
        'artifact_boosts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('artifacts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('booster_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('boost_radius_meters', sa.Integer, nullable=False,
                  server_default='2000'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_artifact_boosts_artifact_id', 'artifact_boosts', ['artifact_id'])
    op.create_index('ix_artifact_boosts_booster_id', 'artifact_boosts', ['booster_id'])
    op.create_index('ix_artifact_boosts_created_at', 'artifact_boosts', ['created_at'])
    op.create_index('ix_artifact_boosts_expires_at', 'artifact_boosts', ['expires_at'])

    # =========================================================================
    # waves  👋
    # =========================================================================
    op.create_table(
        'waves',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('geom',
                  geoalchemy2.types.Geography(
                      geometry_type='POINT', srid=4326, spatial_index=False),
                  nullable=False),
        sa.Column('latitude', sa.Float, nullable=False),
        sa.Column('longitude', sa.Float, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_waves_sender_id', 'waves', ['sender_id'])
    op.create_index('ix_waves_created_at', 'waves', ['created_at'])
    op.create_index('ix_waves_expires_at', 'waves', ['expires_at'])
    op.create_index('ix_waves_geom', 'waves', ['geom'], postgresql_using='gist')

    # =========================================================================
    # artifact_discoveries  (idempotent ledger)
    # =========================================================================
    op.create_table(
        'artifact_discoveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('artifacts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.UniqueConstraint('artifact_id', 'user_id',
                            name='uq_artifact_discovery_user'),
    )
    op.create_index('ix_artifact_discoveries_artifact_id',
                    'artifact_discoveries', ['artifact_id'])
    op.create_index('ix_artifact_discoveries_user_id',
                    'artifact_discoveries', ['user_id'])
    op.create_index('ix_artifact_discoveries_discovered_at',
                    'artifact_discoveries', ['discovered_at'])

    # =========================================================================
    # synchronicity_events  ✨
    # =========================================================================
    op.create_table(
        'synchronicity_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('artifacts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_a_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_b_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.UniqueConstraint('artifact_id', 'user_a_id', 'user_b_id',
                            name='uq_synchronicity_pair_per_artifact'),
    )
    op.create_index('ix_synchronicity_events_artifact_id',
                    'synchronicity_events', ['artifact_id'])
    op.create_index('ix_synchronicity_events_user_a_id',
                    'synchronicity_events', ['user_a_id'])
    op.create_index('ix_synchronicity_events_user_b_id',
                    'synchronicity_events', ['user_b_id'])
    op.create_index('ix_synchronicity_events_created_at',
                    'synchronicity_events', ['created_at'])

    print("✅ Created artifact_boosts, waves, artifact_discoveries, synchronicity_events")


def downgrade() -> None:
    op.drop_table('synchronicity_events')
    op.drop_table('artifact_discoveries')
    op.execute("DROP INDEX IF EXISTS ix_waves_geom")
    op.drop_table('waves')
    op.drop_table('artifact_boosts')
    print("✅ Dropped all social spark tables")
