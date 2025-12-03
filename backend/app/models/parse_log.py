"""
Parse log model for tracking parsing operations and usage
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ParseLog(Base):
    __tablename__ = "parse_logs"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )  # Nullable for anonymous
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("processing_jobs.id"), nullable=False, index=True
    )

    # Parse operation details
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    row_count = Column(Integer, nullable=False)
    success = Column(Boolean, default=True, nullable=False)
    processing_time_ms = Column(Integer, nullable=False)

    # Usage tracking
    is_overage = Column(
        Boolean, default=False, nullable=False
    )  # Was this beyond user's limit

    # Anonymous tracking
    anonymous_ip = Column(
        String(45), nullable=True, index=True
    )  # For anonymous usage tracking

    # Relationships
    user = relationship("User", back_populates="parse_logs")
    job = relationship("ProcessingJob", back_populates="parse_logs")

    def __repr__(self):
        return f"<ParseLog {self.id}: {self.row_count} rows>"
