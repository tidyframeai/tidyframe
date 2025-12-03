"""
API Key model for programmatic access
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.user import User


class APIKey(Base):
    __tablename__ = "api_keys"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # Key information
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_hint = Column(String(20), nullable=False)  # Last 4 characters for display
    name = Column(String(100), nullable=False)  # User-defined name for the key

    # Status and permissions
    is_active = Column(Boolean, default=True, nullable=False)

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_used_ip = Column(String(45), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey {self.name} for {self.user.email}>"

    def is_expired(self) -> bool:
        """Check if API key is expired"""
        from datetime import datetime, timezone

        if self.expires_at is None:
            return False

        return datetime.now(timezone.utc) > self.expires_at

    def can_use(self) -> bool:
        """Check if API key can be used"""
        return self.is_active and not self.is_expired()


# Add relationship to User model

User.api_keys = relationship("APIKey", back_populates="user", lazy="dynamic")
