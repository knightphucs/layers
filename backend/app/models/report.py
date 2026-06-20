"""
LAYERS - Report Model
============================================
One row per (reporter, artifact). This is the fix for report-bombing:
the old code did `artifact.report_count += 1` on every call, so a single
malicious user could hide any artifact by reporting it 5 times. Now a
UNIQUE constraint guarantees one report per user per artifact, and
report_count reflects DISTINCT reporters.

status starts "OPEN"; admin review (moderation approve/remove) closes it:
RESOLVED_REMOVED (report was valid — reporter gets a reputation reward)
or RESOLVED_DISMISSED (false alarm — no reward). See report_service.py.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Short category code: "SPAM" | "INAPPROPRIATE" | "HARASSMENT" |
    # "MISINFORMATION" | "OTHER" — validated in report_service.py
    reason: Mapped[str] = mapped_column(String(30), nullable=False)

    # Optional free-text the reporter adds
    detail: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # "OPEN" | "RESOLVED_REMOVED" | "RESOLVED_DISMISSED"
    status: Mapped[str] = mapped_column(
        String(20), default="OPEN", nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        # The anti-report-bombing guarantee.
        UniqueConstraint("artifact_id", "reporter_id", name="uq_report_once_per_user"),
        Index("ix_reports_artifact_status", "artifact_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Report {self.reason} artifact={self.artifact_id} status={self.status}>"
