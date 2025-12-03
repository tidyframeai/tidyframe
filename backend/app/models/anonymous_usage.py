"""
Anonymous Usage model for tracking free tier usage by IP
"""

import uuid

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class AnonymousUsage(Base):
    __tablename__ = "anonymous_usage"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address = Column(
        String(45), unique=True, nullable=False, index=True
    )  # Support IPv6

    # Usage tracking
    parse_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    first_used = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return f"<AnonymousUsage {self.ip_address}: {self.parse_count} parses>"

    def can_parse(self, count: int = 1) -> bool:
        """Check if IP can perform additional parses"""
        from app.core.config import settings

        return (self.parse_count + count) <= settings.ANONYMOUS_LIFETIME_LIMIT

    def increment_usage(self, count: int = 1):
        """Increment parse count"""
        from datetime import datetime, timezone

        self.parse_count += count
        self.last_used = datetime.now(timezone.utc)
