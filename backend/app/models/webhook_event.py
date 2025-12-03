"""
Webhook Event model for Stripe webhooks and other integrations
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.core.database import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Event identification (from external service)
    external_event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    source = Column(
        String(50), nullable=False, default="stripe"
    )  # stripe, resend, etc.

    # Processing status
    processed = Column(Boolean, default=False, nullable=False, index=True)
    processing_attempts = Column(Integer, default=0, nullable=False)

    # Event data
    data = Column(JSONB, nullable=False)  # Store the full webhook payload

    # Error handling
    error_message = Column(String(1000), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<WebhookEvent {self.external_event_id}: {self.event_type}>"

    def mark_processed(self):
        """Mark event as successfully processed"""
        from datetime import datetime, timezone

        self.processed = True
        self.processed_at = datetime.now(timezone.utc)
        self.error_message = None

    def mark_failed(self, error_message: str):
        """Mark event as failed processing"""
        self.processed = False
        self.processing_attempts = (self.processing_attempts or 0) + 1
        self.error_message = error_message
