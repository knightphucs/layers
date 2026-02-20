"""create locations table with PostGIS

Revision ID: w3d1_locations_001
Revises: [YOUR_PREVIOUS_REVISION_ID]
Create Date: 2026-02-13

FILE: backend/migrations/versions/w3d1_locations_001.py

HOW TO USE:
1. Replace [YOUR_PREVIOUS_REVISION_ID] with your actual latest revision
   (run: alembic history | head -5)
2. Place this file in: backend/migrations/versions/
3. Run: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

revision = 'w3d1_locations_001'
down_revision = '920296b3321a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop any existing tables (created by Base.metadata.create_all())
    op.execute("DROP TABLE IF EXISTS explored_chunks CASCADE")
    op.execute("DROP TABLE IF EXISTS locations CASCADE")

    # Ensure PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # Create enum types
    layer_type = postgresql.ENUM('LIGHT', 'SHADOW', name='layer_type', create_type=False)
    layer_type.create(op.get_bind(), checkfirst=True)

    location_category = postgresql.ENUM(
        'CAFE', 'PARK', 'MONUMENT', 'SCHOOL', 'MARKET', 'RESTAURANT',
        'GENERAL', 'GHOST', 'URBAN_LEGEND', 'MIDNIGHT', 'CHALLENGE',
        'VOUCHER', 'HIDDEN_GEM',
        name='location_category', create_type=False
    )
    location_category.create(op.get_bind(), checkfirst=True)

    # Create locations table
    op.create_table(
        'locations',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),

        # PostGIS GEOGRAPHY column
        sa.Column('geom', geoalchemy2.Geography(
            geometry_type='POINT', srid=4326, spatial_index=False
        ), nullable=False),

        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),

        sa.Column('layer', layer_type, nullable=False, server_default='LIGHT'),
        sa.Column('category', location_category, nullable=False, server_default='GENERAL'),

        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default='{}'),

        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('visit_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('artifact_count', sa.Integer(), server_default='0', nullable=False),

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.PrimaryKeyConstraint('id'),
    )

    # Spatial index (GiST) — makes ST_DWithin O(log n)
    op.create_index('idx_locations_geom', 'locations', ['geom'], postgresql_using='gist')
    op.create_index('idx_locations_layer_active', 'locations', ['layer', 'is_active'])
    op.create_index('idx_locations_category', 'locations', ['category'])
    op.create_index('idx_locations_created_by', 'locations', ['created_by'])
    op.create_index('idx_locations_created_at', 'locations', ['created_at'])

    # Create explored_chunks table (Fog of War)
    op.create_table(
        'explored_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_x', sa.Integer(), nullable=False),
        sa.Column('chunk_y', sa.Integer(), nullable=False),
        sa.Column('explored_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'chunk_x', 'chunk_y', name='uq_explored_chunk_user_coords'),
    )

    op.create_index('ix_explored_chunks_user_id', 'explored_chunks', ['user_id'])


def downgrade() -> None:
    op.drop_table('explored_chunks')
    op.drop_table('locations')
    op.execute("DROP TYPE IF EXISTS location_category")
    op.execute("DROP TYPE IF EXISTS layer_type")
