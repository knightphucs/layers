"""
LAYERS - Glitch Zone Model
=========================================
A Glitch Zone is a circular Shadow-Layer area where the city "glitches" — the
rules bend. Walking inside an ACTIVE zone grants an effect:

  XP_SURGE       artifacts created/explored here are worth more XP
  SHADOW_REVEAL  Shadow-layer artifacts that are normally hidden show up
  ANONYMOUS      content you drop here is authored anonymously

Zones are usually nocturnal — they wake at night (default 23:00–03:00 local)
and sleep by day, which is what makes the Shadow Layer feel alive and mysterious.
A zone with no window (active_start/end NULL) is always on.

GEO STORAGE CHOICE
We store center_lat/center_lng + radius_m as plain columns and test membership
with haversine in Python, instead of a PostGIS GEOGRAPHY column. Reason: there
will be a small, curated number of zones (tens, not millions), so a spatial
index buys nothing, and this keeps the model dependency-free and easy to seed.
(Artifacts/locations, which ARE numerous, keep using PostGIS.)
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, Float, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class GlitchZone(Base):
    __tablename__ = "glitch_zones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Circular area
    center_lat: Mapped[float] = mapped_column(Float, nullable=False)
    center_lng: Mapped[float] = mapped_column(Float, nullable=False)
    radius_m: Mapped[int] = mapped_column(Integer, default=150, nullable=False)

    # "XP_SURGE" | "SHADOW_REVEAL" | "ANONYMOUS" (validated in shadow_service)
    glitch_type: Mapped[str] = mapped_column(
        String(20), default="XP_SURGE", nullable=False
    )
    # Effect strength. For XP_SURGE this is the XP multiplier (e.g. 2.0).
    intensity: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)

    # Local-time activation window ("HH:MM"); NULL/NULL = always active.
    active_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    active_end: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_glitch_zones_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<GlitchZone {self.name} {self.glitch_type} r={self.radius_m}m>"
