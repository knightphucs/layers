"""create chat tables

Revision ID: w6d1_chat_001
Revises: w5d4_conn_upgrade_001
Create Date: 2026-04-28

WHAT THIS MIGRATION DOES:
    1. Creates `chatroomtype` enum (DIRECT, CAMPFIRE)
    2. Creates `chatroomstatus` enum (ACTIVE, CLOSED)
    3. Creates `chat_rooms` table
    4. Creates `messages` table
    5. Adds unique constraint on (user_a_id, user_b_id) for DIRECT pairs
    6. Adds composite index on (room_id, created_at DESC) for fast pagination

NOTHING IS DROPPED — purely additive.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'w6d1_chat_001'
down_revision: Union[str, None] = 'w5d4_conn_upgrade_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # ENUMS
    # =========================================================================
    chat_room_type = postgresql.ENUM(
        'DIRECT', 'CAMPFIRE',
        name='chatroomtype',
        create_type=False,
    )
    chat_room_type.create(op.get_bind(), checkfirst=True)

    chat_room_status = postgresql.ENUM(
        'ACTIVE', 'CLOSED',
        name='chatroomstatus',
        create_type=False,
    )
    chat_room_status.create(op.get_bind(), checkfirst=True)

    # =========================================================================
    # CHAT_ROOMS TABLE
    # =========================================================================
    op.create_table(
        'chat_rooms',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('uuid_generate_v4()'),
        ),
        sa.Column(
            'room_type',
            postgresql.ENUM('DIRECT', 'CAMPFIRE', name='chatroomtype', create_type=False),
            nullable=False,
        ),
        sa.Column(
            'status',
            postgresql.ENUM('ACTIVE', 'CLOSED', name='chatroomstatus', create_type=False),
            nullable=False,
            server_default='ACTIVE',
        ),

        # DIRECT room members (NULL for CAMPFIRE — Day 3 will add geo columns)
        sa.Column(
            'user_a_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=True,
        ),
        sa.Column(
            'user_b_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=True,
        ),

        # Stats / Lifecycle
        sa.Column('message_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column(
            'last_activity_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
        ),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Indexes for chat_rooms
    op.create_index('ix_chat_rooms_room_type', 'chat_rooms', ['room_type'])
    op.create_index('ix_chat_rooms_status', 'chat_rooms', ['status'])
    op.create_index('ix_chat_rooms_user_a_id', 'chat_rooms', ['user_a_id'])
    op.create_index('ix_chat_rooms_user_b_id', 'chat_rooms', ['user_b_id'])
    op.create_index(
        'ix_chat_rooms_last_activity_at',
        'chat_rooms',
        ['last_activity_at'],
    )

    # Unique pair (canonical ordering enforced in service layer)
    op.create_unique_constraint(
        'uq_chat_rooms_direct_pair',
        'chat_rooms',
        ['user_a_id', 'user_b_id'],
    )

    # =========================================================================
    # MESSAGES TABLE
    # =========================================================================
    op.create_table(
        'messages',
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
            'sender_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
        ),
    )

    # Indexes for messages
    op.create_index('ix_messages_room_id', 'messages', ['room_id'])
    op.create_index('ix_messages_sender_id', 'messages', ['sender_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])

    # Composite index for cursor pagination — newest-first per room
    op.create_index(
        'ix_messages_room_created_desc',
        'messages',
        ['room_id', sa.text('created_at DESC')],
    )

    print("✅ Created chat_rooms + messages tables")


def downgrade() -> None:
    # Drop indexes (some implicit, some explicit)
    op.drop_index('ix_messages_room_created_desc', table_name='messages')
    op.drop_index('ix_messages_created_at', table_name='messages')
    op.drop_index('ix_messages_sender_id', table_name='messages')
    op.drop_index('ix_messages_room_id', table_name='messages')

    op.drop_table('messages')

    op.drop_constraint('uq_chat_rooms_direct_pair', 'chat_rooms', type_='unique')
    op.drop_index('ix_chat_rooms_last_activity_at', table_name='chat_rooms')
    op.drop_index('ix_chat_rooms_user_b_id', table_name='chat_rooms')
    op.drop_index('ix_chat_rooms_user_a_id', table_name='chat_rooms')
    op.drop_index('ix_chat_rooms_status', table_name='chat_rooms')
    op.drop_index('ix_chat_rooms_room_type', table_name='chat_rooms')

    op.drop_table('chat_rooms')

    # Drop enums LAST (after all references are gone)
    sa.Enum(name='chatroomstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='chatroomtype').drop(op.get_bind(), checkfirst=True)

    print("✅ Dropped chat_rooms + messages tables")
