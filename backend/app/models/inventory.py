"""
LAYERS - Inventory Model
User's saved items (vouchers, memorable letters, badges)
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class InventoryItem(Base):
    """
    Items saved in user's inventory.
    
    Users can save:
    - Vouchers (to use later)
    - Memorable letters/memories
    - Collected badges
    """
    __tablename__ = "inventory"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False
    )
    
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    
    # For vouchers: track if used
    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    
    def __repr__(self) -> str:
        return f"<InventoryItem user={self.user_id} artifact={self.artifact_id}>"


class MailQueue(Base):
    """
    Queue for Slow Mail delivery.
    
    Messages are held here and delivered after random delay (6-12 hours).
    Background worker processes this queue.
    """
    __tablename__ = "mail_queue"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    receiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=True
    )
    
    content: Mapped[str] = mapped_column(
        nullable=False
    )
    
    # When to deliver (random 6-12 hours from creation)
    deliver_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    status: Mapped[str] = mapped_column(
        default="PENDING"  # PENDING, SENT, FAILED
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    
    def __repr__(self) -> str:
        return f"<MailQueue {self.sender_id} -> {self.receiver_id} @ {self.deliver_at}>"