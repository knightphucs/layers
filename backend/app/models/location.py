"""
LAYERS - Location Model
========================
This is the GEO ENGINE of LAYERS. Every artifact lives at a location.
Every location has a PostGIS GEOGRAPHY point for precise geo-queries.

KEY CONCEPT: We use GEOGRAPHY (not GEOMETRY) because:
- GEOGRAPHY works in meters on a sphere (Earth)
- ST_DWithin(geog, geog, meters) gives real-world distance
- Perfect for "find things within 50m" (Proof of Presence)

From Masterplan:
- geom (GEOGRAPHY Point): GPS coordinates WGS84
- layer: LIGHT / SHADOW
- category: CAFE, PARK, GHOST, VOUCHER...
- metadata (JSONB): flexible extra data
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Float, Enum as SQLEnum,
    ForeignKey, Index, Text, Boolean, Integer, UniqueConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from geoalchemy2 import Geography
from sqlalchemy.orm import relationship
import enum

# Import your Base from wherever you defined it in Week 1
# Adjust this import to match YOUR project structure
from app.core.database import Base


# ============================================================
# ENUMS
# ============================================================

class LayerType(str, enum.Enum):
    """Which layer does this location belong to?"""
    LIGHT = "LIGHT"     # Daytime - healing, memories, slow connections
    SHADOW = "SHADOW"   # Nighttime - mysteries, challenges, urban legends


class LocationCategory(str, enum.Enum):
    """What kind of place is this?"""
    # Light Layer categories
    CAFE = "CAFE"
    PARK = "PARK"
    MONUMENT = "MONUMENT"
    SCHOOL = "SCHOOL"
    MARKET = "MARKET"
    RESTAURANT = "RESTAURANT"
    GENERAL = "GENERAL"

    # Shadow Layer categories
    GHOST = "GHOST"             # Glitch Zone - haunted/eerie spots
    URBAN_LEGEND = "URBAN_LEGEND"  # Urban mystery locations
    MIDNIGHT = "MIDNIGHT"       # Only visible 23:00-03:00
    CHALLENGE = "CHALLENGE"     # Dare/challenge spots

    # Commerce
    VOUCHER = "VOUCHER"         # Partner business with voucher drops
    HIDDEN_GEM = "HIDDEN_GEM"   # User-discovered cool spots


# ============================================================
# MODEL
# ============================================================

class Location(Base):
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # === GEO DATA (PostGIS) ===
    # GEOGRAPHY type with SRID 4326 (WGS84 = standard GPS coordinates)
    # This enables ST_DWithin queries in METERS
    geom = Column(
        Geography(geometry_type='POINT', srid=4326),
        nullable=False,
        comment="GPS coordinates as PostGIS GEOGRAPHY point"
    )

    # Convenience columns for quick access without PostGIS functions
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # === LAYER & CATEGORY ===
    layer = Column(
        SQLEnum(LayerType, name="layer_type"),
        nullable=False,
        default=LayerType.LIGHT,
        comment="LIGHT (daytime/healing) or SHADOW (nighttime/mystery)"
    )
    category = Column(
        SQLEnum(LocationCategory, name="location_category"),
        nullable=False,
        default=LocationCategory.GENERAL,
    )

    # === INFO ===
    name = Column(String(200), nullable=True, comment="Optional name: 'Ben Thanh Market'")
    description = Column(Text, nullable=True)
    address = Column(String(500), nullable=True)

    # === METADATA (JSONB) - Flexible extra data ===
    # Examples:
    #   { "tree_level": 5, "vibe_tag": "chill" }           -- Light Layer
    #   { "sound_url": "s3://glitch.mp3", "scare_level": 3 } -- Shadow Layer
    #   { "business_name": "Cafe XYZ", "voucher_count": 10 } -- Commerce
    location_meta = Column('metadata', JSONB, nullable=True, default={})

    # === OWNERSHIP ===
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created this location (null for system/seeded)"
    )

    # === STATUS ===
    is_active = Column(Boolean, default=True, server_default=text('true'), comment="Soft delete / moderation hide")
    is_verified = Column(Boolean, default=False, server_default=text('false'), comment="Verified by admin or system")

    # === STATS ===
    visit_count = Column(Integer, default=0, server_default=text('0'), comment="How many users have been here")
    artifact_count = Column(Integer, default=0, server_default=text('0'), comment="Number of artifacts at this location")

    # === TIMESTAMPS ===
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text('now()'))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text('now()'))

    # === RELATIONSHIPS ===
    artifacts = relationship("Artifact", back_populates="location", lazy="selectin")
    creator = relationship("User", foreign_keys=[created_by], lazy="selectin")

    def __repr__(self):
        return f"<Location {self.id} [{self.layer.value}] ({self.latitude}, {self.longitude})>"

    @classmethod
    def create_point_wkt(cls, latitude: float, longitude: float) -> str:
        """
        Create WKT (Well-Known Text) for a point.
        PostGIS uses longitude first!
        """
        return f"SRID=4326;POINT({longitude} {latitude})"


# ============================================================
# INDEXES - Critical for geo-query performance!
# ============================================================

# PostGIS spatial index on geography column
# This makes ST_DWithin queries O(log n) instead of O(n)
Index("idx_locations_geom", Location.geom, postgresql_using="gist")

# Composite index: layer + active (most common filter combo)
Index("idx_locations_layer_active", Location.layer, Location.is_active)

# Category index for filtering
Index("idx_locations_category", Location.category)

# Creator index for "my locations" queries
Index("idx_locations_created_by", Location.created_by)

# Created at index for sorting by newest
Index("idx_locations_created_at", Location.created_at)


class ExploredChunk(Base):
    """
    Tracks which map chunks a user has explored (Fog of War).

    Uses a grid system where each chunk is ~100m x 100m.
    """
    __tablename__ = "explored_chunks"

    __table_args__ = (
        UniqueConstraint('user_id', 'chunk_x', 'chunk_y', name='uq_explored_chunk_user_coords'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Grid coordinates (calculated from lat/lng)
    chunk_x = Column(Integer, nullable=False)
    chunk_y = Column(Integer, nullable=False)

    # When first explored
    explored_at = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def calculate_chunk(latitude: float, longitude: float, chunk_size_meters: int = 100) -> tuple:
        """
        Calculate chunk coordinates from lat/lng.

        Uses simple approximation:
        - 1 degree latitude ≈ 111km
        - 1 degree longitude ≈ 111km * cos(latitude)
        """
        import math

        # Convert chunk size to degrees
        lat_per_chunk = chunk_size_meters / 111000  # ~0.0009 degrees
        lng_per_chunk = chunk_size_meters / (111000 * math.cos(math.radians(latitude)))

        chunk_x = int(longitude / lng_per_chunk)
        chunk_y = int(latitude / lat_per_chunk)

        return chunk_x, chunk_y
