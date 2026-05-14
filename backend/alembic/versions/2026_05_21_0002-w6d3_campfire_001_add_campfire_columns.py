"""add campfire columns and campfire_members table (Week 6 Day 3)

Revision ID: w6d3_campfire_001
Revises: w6d1_chat_001
Create Date: 2026-05-21

WHAT THIS MIGRATION DOES:
    1. Adds campfire columns to chat_rooms (center_geom, center_latitude,
       center_longitude, radius_meters, expires_at, name, creator_id)
    2. Creates campfire_members table
    3. Adds GIST index on center_geom for PostGIS proximity queries
    4. Adds partial unique index: at most one ACTIVE membership per (room, user)

PURELY ADDITIVE -- no tables modified, no data lost.
"""
from typing import Sequence, Union

from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'w6d3_campfire_001'
down_revision: Union[str, None] = 'w6d1_chat_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # 1. Add campfire columns to chat_rooms
    # =========================================================================
    op.add_column(
        'chat_rooms',
        sa.Column(
            'center_geom',
            geoalchemy2.types.Geography(
                geometry_type='POINT',
                srid=4326,
                spatial_index=False,
            ),
            nullable=True,
            comment='PostGIS POINT for campfire center (NULL for DIRECT)',
        ),
    )
    op.add_column(
        'chat_rooms',
        sa.Column('center_latitude', sa.Float, nullable=True),
    )
    op.add_column(
        'chat_rooms',
        sa.Column('center_longitude', sa.Float, nullable=True),
    )
    op.add_column(
        'chat_rooms',
        sa.Column(
            'radius_meters',
            sa.Integer,
            nullable=True,
            comment='Geo-fence radius in meters (default 50)',
        ),
    )
    op.add_column(
        'chat_rooms',
        sa.Column(
            'expires_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='When the campfire auto-closes',
        ),
    )
    op.add_column(
        'chat_rooms',
        sa.Column(
            'name',
            sa.String(100),
            nullable=True,
            comment='Optional campfire title',
        ),
    )
    op.add_column(
        'chat_rooms',
        sa.Column(
            'creator_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )

    # GIST index for PostGIS proximity queries.
    op.create_index(
        'ix_chat_rooms_center_geom',
        'chat_rooms',
        ['center_geom'],
        postgresql_using='gist',
    )

    # Partial index for the periodic cleanup job; DIRECT rooms have no expiry.
    op.create_index(
        'ix_chat_rooms_expires_at',
        'chat_rooms',
        ['expires_at'],
        postgresql_where=sa.text('expires_at IS NOT NULL'),
    )

    # =========================================================================
    # 2. campfire_members table
    # =========================================================================
    op.create_table(
        'campfire_members',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('uuid_generate_v4()'),
        ),
        sa.Column(
            'room_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('chat_rooms.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'joined_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
        ),
        sa.Column(
            'left_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index('ix_campfire_members_room_id', 'campfire_members', ['room_id'])
    op.create_index('ix_campfire_members_user_id', 'campfire_members', ['user_id'])
    op.create_index('ix_campfire_members_left_at', 'campfire_members', ['left_at'])

    # Only enforce uniqueness for active memberships.
    op.create_index(
        'uq_campfire_members_active',
        'campfire_members',
        ['room_id', 'user_id'],
        unique=True,
        postgresql_where=sa.text('left_at IS NULL'),
    )

    # Composite index for the get_active_members query.
    op.create_index(
        'ix_campfire_members_active_lookup',
        'campfire_members',
        ['room_id', 'left_at', 'joined_at'],
    )

    print("Added campfire columns to chat_rooms")
    print("Created campfire_members table with partial unique index")


def downgrade() -> None:
    # Drop campfire_members first (FK to chat_rooms).
    op.drop_index('ix_campfire_members_active_lookup', table_name='campfire_members')
    op.drop_index('uq_campfire_members_active', table_name='campfire_members')
    op.drop_index('ix_campfire_members_left_at', table_name='campfire_members')
    op.drop_index('ix_campfire_members_user_id', table_name='campfire_members')
    op.drop_index('ix_campfire_members_room_id', table_name='campfire_members')
    op.drop_table('campfire_members')

    # Drop campfire columns from chat_rooms.
    op.drop_index('ix_chat_rooms_expires_at', table_name='chat_rooms')
    op.drop_index('ix_chat_rooms_center_geom', table_name='chat_rooms')
    op.drop_column('chat_rooms', 'creator_id')
    op.drop_column('chat_rooms', 'name')
    op.drop_column('chat_rooms', 'expires_at')
    op.drop_column('chat_rooms', 'radius_meters')
    op.drop_column('chat_rooms', 'center_longitude')
    op.drop_column('chat_rooms', 'center_latitude')
    op.drop_column('chat_rooms', 'center_geom')

    print("Dropped campfire columns + campfire_members table")
