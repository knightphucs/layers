"""add campfire game tables (Week 6 Day 5)

Revision ID: w6d5_game_001
Revises: w6d4_spark_001
Create Date: 2026-06-04

FILE: backend/alembic/versions/2026_06_04_0001-w6d5_game_001_add_game_tables.py

⚠️  Before running:
    Verify your Day 4 migration revision is 'w6d4_spark_001'.
    If not, update down_revision below. Find current head:
        cd backend && alembic heads

WHAT THIS MIGRATION DOES:
    Creates 3 tables for Truth-or-Dare:
      - campfire_games            (one per active game per room)
      - campfire_game_rounds      (questions inside a game)
      - campfire_game_answers     (one per user per round, with vote tracking)

    Adds 2 enums (campfiregamestate, campfireroundstate) and 2 unique constraints
    (one active game per room, one answer per user per round).

PURELY ADDITIVE — no existing tables modified.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'w6d5_game_001'
down_revision: Union[str, None] = 'w6d4_spark_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Enums
    # =========================================================================
    game_state = postgresql.ENUM(
        'WAITING', 'IN_PROGRESS', 'COMPLETED',
        name='campfiregamestate', create_type=False,
    )
    game_state.create(op.get_bind(), checkfirst=True)

    round_state = postgresql.ENUM(
        'ANSWERING', 'VOTING', 'REVEALED',
        name='campfireroundstate', create_type=False,
    )
    round_state.create(op.get_bind(), checkfirst=True)

    # =========================================================================
    # campfire_games
    # =========================================================================
    op.create_table(
        'campfire_games',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('room_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('chat_rooms.id', ondelete='CASCADE'), nullable=False),
        sa.Column('starter_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('state',
                  postgresql.ENUM(name='campfiregamestate', create_type=False),
                  nullable=False, server_default='WAITING'),
        # No FK on current_round_id — circular dep: games → rounds → games.
        # App layer is responsible for maintaining consistency.
        sa.Column('current_round_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('round_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_campfire_games_room_id', 'campfire_games', ['room_id'])
    op.create_index('ix_campfire_games_starter_id', 'campfire_games', ['starter_id'])
    op.create_index('ix_campfire_games_state', 'campfire_games', ['state'])
    # Partial unique: at most one active (non-COMPLETED) game per room.
    op.execute("""
        CREATE UNIQUE INDEX uq_campfire_games_active
        ON campfire_games (room_id)
        WHERE state != 'COMPLETED'
    """)

    # =========================================================================
    # campfire_game_rounds
    # =========================================================================
    op.create_table(
        'campfire_game_rounds',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('game_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('campfire_games.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('round_number', sa.Integer, nullable=False),
        sa.Column('question_text', sa.Text, nullable=False),
        sa.Column('state',
                  postgresql.ENUM(name='campfireroundstate', create_type=False),
                  nullable=False, server_default='ANSWERING'),
        sa.Column('winner_user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        # No FK on winning_answer_id — circular dep: rounds → answers → rounds.
        # App layer is responsible for maintaining consistency.
        sa.Column('winning_answer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('revealed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_campfire_game_rounds_game_id', 'campfire_game_rounds', ['game_id'])
    op.create_index('ix_campfire_game_rounds_state', 'campfire_game_rounds', ['state'])
    # Composite for "get round N of game X" queries.
    op.create_index('ix_campfire_game_rounds_game_round',
                    'campfire_game_rounds', ['game_id', 'round_number'])

    # =========================================================================
    # campfire_game_answers
    # =========================================================================
    op.create_table(
        'campfire_game_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('round_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('campfire_game_rounds.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('vote_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('voter_ids', postgresql.JSONB, nullable=False,
                  server_default=sa.text("'[]'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.UniqueConstraint('round_id', 'user_id',
                            name='uq_campfire_game_answer_user'),
    )
    op.create_index('ix_campfire_game_answers_round_id', 'campfire_game_answers', ['round_id'])
    op.create_index('ix_campfire_game_answers_user_id', 'campfire_game_answers', ['user_id'])

    print("✅ Created campfire_games, campfire_game_rounds, campfire_game_answers")


def downgrade() -> None:
    op.drop_table('campfire_game_answers')
    op.drop_index('ix_campfire_game_rounds_game_round', table_name='campfire_game_rounds')
    op.drop_table('campfire_game_rounds')
    op.execute("DROP INDEX IF EXISTS uq_campfire_games_active")
    op.drop_table('campfire_games')
    op.execute("DROP TYPE IF EXISTS campfireroundstate")
    op.execute("DROP TYPE IF EXISTS campfiregamestate")
    print("✅ Dropped all campfire game tables")
