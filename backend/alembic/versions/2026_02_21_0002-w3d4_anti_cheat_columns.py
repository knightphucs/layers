"""Add anti-cheat columns to users table

Revision ID: w3d4_anti_cheat_001
Revises: (set to your latest revision)
Create Date: 2026-02-20

Adds cheat_strikes, banned_until, ban_reason columns
for the anti-cheat strike & ban system.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = 'w3d4_anti_cheat_001'
down_revision = 'w3d1_locations_001'  # ← SET THIS to your latest migration revision!
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add anti-cheat columns to users table
    op.add_column('users', sa.Column(
        'cheat_strikes', sa.Integer(),
        nullable=False, server_default='0',
        comment='Number of anti-cheat violations (3 = perm ban)'
    ))
    op.add_column('users', sa.Column(
        'banned_until', sa.DateTime(timezone=True),
        nullable=True,
        comment='Temporary ban expiry timestamp (NULL = not temp banned)'
    ))
    op.add_column('users', sa.Column(
        'ban_reason', sa.String(500),
        nullable=True,
        comment='Reason for ban (displayed to user)'
    ))

    # Index for quick ban-check queries
    op.create_index('idx_users_banned_until', 'users', ['banned_until'])
    op.create_index('idx_users_is_banned', 'users', ['is_banned'])


def downgrade() -> None:
    op.drop_index('idx_users_is_banned', table_name='users')
    op.drop_index('idx_users_banned_until', table_name='users')
    op.drop_column('users', 'ban_reason')
    op.drop_column('users', 'banned_until')
    op.drop_column('users', 'cheat_strikes')
