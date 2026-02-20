"""initial_schema

Revision ID: 8023060b27a5
Revises: 
Create Date: 2026-01-26 00:41:25.288708

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8023060b27a5'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # USERS TABLE
    # =========================================================================
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text('uuid_generate_v4()')),
        
        # Authentication
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('username', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        
        # Profile
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('bio', sa.Text, nullable=True),
        
        # Gamification
        sa.Column('experience_points', sa.Integer, default=0, nullable=False),
        sa.Column('reputation_score', sa.Integer, default=100, nullable=False),
        sa.Column('level', sa.Integer, default=1, nullable=False),
        
        # Status
        sa.Column('role', sa.Enum('USER', 'ADMIN', 'PARTNER', name='userrole'), 
                  default='USER', nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('is_verified', sa.Boolean, default=False, nullable=False),
        sa.Column('is_banned', sa.Boolean, default=False, nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # =========================================================================
    # LOCATIONS TABLE (with PostGIS)
    # =========================================================================
    op.create_table(
        'locations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        
        # Geographic data (PostGIS GEOGRAPHY for accurate distance calculations)
        sa.Column('geom', geoalchemy2.Geography(geometry_type='POINT', srid=4326, spatial_index=False),
                  nullable=False),
        sa.Column('latitude', sa.Float, nullable=False),
        sa.Column('longitude', sa.Float, nullable=False),
        
        # Categorization
        sa.Column('layer', sa.Enum('LIGHT', 'SHADOW', name='layertype'),
                  default='LIGHT', nullable=False),
        sa.Column('category', sa.Enum('CAFE', 'PARK', 'RESTAURANT', 'LANDMARK', 
                                       'STREET', 'GHOST', 'VOUCHER', 'CUSTOM',
                                       name='locationcategory'),
                  default='CUSTOM', nullable=False),
        
        # Display info
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        
        # Flexible metadata (JSONB for flexible data)
        sa.Column('metadata', postgresql.JSONB, default={}, nullable=False),
        
        # Stats
        sa.Column('artifact_count', sa.Integer, default=0, nullable=False),
        sa.Column('visit_count', sa.Integer, default=0, nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
    )
    
    # Create spatial index for geo queries
    op.create_index('idx_locations_geom', 'locations', ['geom'],
                    postgresql_using='gist')
    
    # =========================================================================
    # ARTIFACTS TABLE (The heart of the app!)
    # =========================================================================
    op.create_table(
        'artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        
        # Relationships
        sa.Column('location_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('locations.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True, index=True),
        
        # Content
        sa.Column('content_type', sa.Enum('LETTER', 'VOICE', 'PHOTO', 'PAPER_PLANE',
                                          'VOUCHER', 'TIME_CAPSULE', 'NOTEBOOK',
                                          name='contenttype'),
                  nullable=False, index=True),
        sa.Column('payload', postgresql.JSONB, default={}, nullable=False),
        
        # Privacy
        sa.Column('visibility', sa.Enum('PUBLIC', 'TARGETED', 'PASSCODE',
                                        name='visibility'),
                  default='PUBLIC', nullable=False),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('secret_code_hash', sa.String(255), nullable=True),
        
        # Unlock conditions
        sa.Column('unlock_conditions', postgresql.JSONB, nullable=True),
        sa.Column('layer', sa.String(20), default='LIGHT', nullable=False),
        
        # Status
        sa.Column('status', sa.Enum('ACTIVE', 'PENDING', 'HIDDEN', 'DELETED',
                                    name='artifactstatus'),
                  default='ACTIVE', nullable=False),
        sa.Column('report_count', sa.Integer, default=0, nullable=False),
        
        # Engagement
        sa.Column('view_count', sa.Integer, default=0, nullable=False),
        sa.Column('reply_count', sa.Integer, default=0, nullable=False),
        sa.Column('save_count', sa.Integer, default=0, nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('unlock_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # =========================================================================
    # ARTIFACT REPLIES TABLE (Slow Mail)
    # =========================================================================
    op.create_table(
        'artifact_replies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('artifacts.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('deliver_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_delivered', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
    )
    
    # =========================================================================
    # EXPLORED CHUNKS TABLE (Fog of War)
    # =========================================================================
    op.create_table(
        'explored_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('chunk_x', sa.Integer, nullable=False),
        sa.Column('chunk_y', sa.Integer, nullable=False),
        sa.Column('explored_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
    )
    
    # Unique constraint: user can only explore each chunk once
    op.create_unique_constraint(
        'uq_explored_chunks_user_chunk',
        'explored_chunks',
        ['user_id', 'chunk_x', 'chunk_y']
    )
    
    # =========================================================================
    # CONNECTIONS TABLE (Social)
    # =========================================================================
    op.create_table(
        'connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_a_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('user_b_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('interaction_count', sa.Integer, default=0, nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'CONNECTED', name='connectionstatus'),
                  default='PENDING', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('connected_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Unique constraint: only one connection per pair
    op.create_unique_constraint(
        'uq_connections_users',
        'connections',
        ['user_a_id', 'user_b_id']
    )
    
    # =========================================================================
    # INVENTORY TABLE (User's saved items)
    # =========================================================================
    op.create_table(
        'inventory',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('artifacts.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('saved_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_used', sa.Boolean, default=False, nullable=False),
    )
    
    # Unique: can't save same artifact twice
    op.create_unique_constraint(
        'uq_inventory_user_artifact',
        'inventory',
        ['user_id', 'artifact_id']
    )
    
    # =========================================================================
    # MAIL QUEUE TABLE (Slow Mail delivery)
    # =========================================================================
    op.create_table(
        'mail_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('receiver_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('artifacts.id', ondelete='CASCADE'), nullable=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('deliver_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('status', sa.Enum('PENDING', 'SENT', 'FAILED', name='mailstatus'),
                  default='PENDING', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
    )
    
    # =========================================================================
    # REPORTS TABLE (Content moderation)
    # =========================================================================
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('reporter_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('artifacts.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('reason', sa.Enum('SPAM', 'INAPPROPRIATE', 'HARASSMENT', 
                                     'MISINFORMATION', 'OTHER', name='reportreason'),
                  nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'REVIEWED', 'RESOLVED', 
                                     name='reportstatus'),
                  default='PENDING', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
    )
    
    print("✅ All tables created successfully!")


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('reports')
    op.drop_table('mail_queue')
    op.drop_table('inventory')
    op.drop_table('connections')
    op.drop_table('explored_chunks')
    op.drop_table('artifact_replies')
    op.drop_table('artifacts')
    op.drop_index('idx_locations_geom', 'locations')
    op.drop_table('locations')
    op.drop_table('users')
    
    # Drop custom types
    op.execute('DROP TYPE IF EXISTS reportstatus')
    op.execute('DROP TYPE IF EXISTS reportreason')
    op.execute('DROP TYPE IF EXISTS mailstatus')
    op.execute('DROP TYPE IF EXISTS connectionstatus')
    op.execute('DROP TYPE IF EXISTS artifactstatus')
    op.execute('DROP TYPE IF EXISTS visibility')
    op.execute('DROP TYPE IF EXISTS contenttype')
    op.execute('DROP TYPE IF EXISTS locationcategory')
    op.execute('DROP TYPE IF EXISTS layertype')
    op.execute('DROP TYPE IF EXISTS userrole')
    
    print("✅ All tables dropped successfully!")
