"""
LAYERS - Social Spark Models
============================================
The "social spark" trio — lightweight ways strangers brush against each other:

  - ArtifactBoost      : amplify an artifact so it reaches a wider radius (24h)
  - Wave               : anonymous one-tap "I'm here too" ping (15-min ephemeral)
  - ArtifactDiscovery  : ledger of who first unlocked which artifact (idempotent)
  - SynchronicityEvent : two people unlocked the same artifact within 30 min ✨

Synchronicity is the soul feature: it turns a shared moment at a place into a
real connection (it calls ConnectionService.record_interaction under the hood).
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Float,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geography

from app.core.database import Base


# ============================================================
# ARTIFACT BOOST  📡
# ============================================================

class ArtifactBoost(Base):
    """
    A user boosts an artifact they've discovered, so it surfaces to people
    much further away (BOOST_DISCOVERY_RADIUS_M) for BOOST_DURATION_HOURS.

    Rate-limited: BOOST_DAILY_LIMIT per user per day (counted from this table).
    """
    __tablename__ = "artifact_boosts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    booster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    boost_radius_meters: Mapped[int] = mapped_column(
        Integer, default=2000, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<ArtifactBoost artifact={self.artifact_id} by={self.booster_id}>"


# ============================================================
# WAVE  👋  (anonymous, ephemeral)
# ============================================================

class Wave(Base):
    """
    An anonymous "I'm here too" ping dropped at a location.

    The sender_id is stored ONLY for rate-limiting and self-exclusion —
    it is NEVER returned by any endpoint. Waves expire after WAVE_EXPIRY_MIN.
    """
    __tablename__ = "waves"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="NEVER exposed via API — rate-limit + self-exclusion only",
    )
    geom: Mapped[str] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False,
        comment="Where the wave was dropped (WGS84)",
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<Wave @ ({self.latitude:.4f},{self.longitude:.4f})>"


# ============================================================
# ARTIFACT DISCOVERY  (idempotent ledger)
# ============================================================

class ArtifactDiscovery(Base):
    """
    Records the FIRST time a user unlocks/discovers an artifact.

    Unique on (artifact_id, user_id) — re-discovering is a no-op, so
    synchronicity never double-fires for the same person on the same artifact.
    """
    __tablename__ = "artifact_discoveries"

    __table_args__ = (
        UniqueConstraint(
            "artifact_id", "user_id", name="uq_artifact_discovery_user"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<ArtifactDiscovery artifact={self.artifact_id} user={self.user_id}>"


# ============================================================
# SYNCHRONICITY EVENT  ✨
# ============================================================

class SynchronicityEvent(Base):
    """
    Two users unlocked the same artifact within SYNC_WINDOW_MIN of each other.

    user_a_id / user_b_id are stored in canonical order (smaller UUID first)
    to match ConnectionService's pair convention and de-dupe symmetric events.
    """
    __tablename__ = "synchronicity_events"

    __table_args__ = (
        UniqueConstraint(
            "artifact_id",
            "user_a_id",
            "user_b_id",
            name="uq_synchronicity_pair_per_artifact",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<SynchronicityEvent ✨ {self.user_a_id} ~ {self.user_b_id} "
            f"@ artifact={self.artifact_id}>"
        )
