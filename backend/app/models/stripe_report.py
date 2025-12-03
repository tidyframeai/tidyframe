"""
Failed Stripe Report model for retry queue - CRITICAL revenue protection
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class FailedStripeReport(Base):
    __tablename__ = "failed_stripe_reports"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User association
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # Stripe customer info
    customer_id = Column(String(255), nullable=False, index=True)

    # Usage data to report
    quantity = Column(Integer, nullable=False)  # Number of parses to report

    # Retry metadata
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=10, nullable=False)

    # Error tracking
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    timestamp = Column(DateTime(timezone=True), nullable=False)  # Original parse timestamp
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)
    succeeded_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="failed_stripe_reports")

    def __repr__(self):
        return f"<FailedStripeReport {self.id}: {self.customer_id} - {self.quantity} parses (attempt {self.retry_count}/{self.max_retries})>"

    def increment_retry(self, error_message: str):
        """Increment retry count and update error message"""
        from datetime import datetime, timedelta, timezone

        self.retry_count += 1
        self.last_error = error_message[:5000]  # Limit error message length

        # Exponential backoff: 5 min, 10 min, 20 min, 40 min, 80 min, etc.
        backoff_minutes = 5 * (2 ** (self.retry_count - 1))
        self.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=min(backoff_minutes, 1440))  # Max 24 hours

    def mark_succeeded(self):
        """Mark report as successfully sent to Stripe"""
        from datetime import datetime, timezone

        self.succeeded_at = datetime.now(timezone.utc)
