"""
LAYERS - Connection Model
User relationships and progressive connection system
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, Integer, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ConnectionStatus(str, Enum):
    """Connection status between users"""
    PENDING = "PENDING"      # Slow Mail mode (5 interactions needed)
    CONNECTED = "CONNECTED"  # Real-time chat unlocked


class Connection(Base):
    """
    Connection between two users.
    
    Progressive Connection System:
    - Level 0 (Stranger): Anonymous, Slow Mail only
    - Level 1 (Signal): After 5 interactions
    - Level 2 (Connected): Both accept → Real-time chat
    """
    __tablename__ = "connections"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    user_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    user_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Count of messages exchanged
    interaction_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    
    status: Mapped[ConnectionStatus] = mapped_column(
        SQLEnum(ConnectionStatus),
        default=ConnectionStatus.PENDING
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    def __repr__(self) -> str:
        return f"<Connection {self.user_a_id} <-> {self.user_b_id} ({self.status.value})>"
    
    def can_upgrade(self) -> bool:
        """Check if connection can be upgraded to CONNECTED"""
        return (
            self.status == ConnectionStatus.PENDING and 
            self.interaction_count >= 5
        )
    
    def add_interaction(self) -> bool:
        """
        Record an interaction between users.
        Returns True if can now upgrade.
        """
        self.interaction_count += 1
        return self.can_upgrade()