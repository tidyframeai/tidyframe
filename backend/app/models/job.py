"""
Processing job model for file upload and parsing tasks
"""

import enum
import uuid

from sqlalchemy import (
    Column,
    DateTime,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )  # Nullable for anonymous

    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_path = Column(String(500), nullable=False)  # Local file path
    content_type = Column(String(100), nullable=True)

    # Processing status
    status = Column(
        SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True
    )
    progress = Column(Integer, default=0, nullable=False)  # 0-100

    # Results
    result_file_path = Column(String(500), nullable=True)
    result_url = Column(String(500), nullable=True)
    download_count = Column(Integer, default=0, nullable=False)

    # Metadata
    row_count = Column(Integer, nullable=True)
    processed_rows = Column(Integer, default=0, nullable=False)
    successful_parses = Column(Integer, default=0, nullable=False)
    failed_parses = Column(Integer, default=0, nullable=False)

    # Processing configuration
    parsing_config = Column(JSONB, nullable=True)  # Store parsing parameters

    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)  # Structured error information

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # When results expire

    # Processing metadata
    processing_time_ms = Column(Integer, nullable=True)
    worker_id = Column(String(255), nullable=True)  # Celery worker that processed
    retry_count = Column(Integer, default=0, nullable=False)

    # Fallback tracking
    gemini_success_count = Column(
        Integer, default=0, nullable=False
    )  # Rows parsed with Gemini
    fallback_usage_count = Column(
        Integer, default=0, nullable=False
    )  # Rows that used fallback
    fallback_reasons = Column(JSONB, nullable=True)  # Detailed fallback reasons

    # Quality metrics
    low_confidence_count = Column(
        Integer, default=0, nullable=False
    )  # Results with confidence < 0.7
    warning_count = Column(
        Integer, default=0, nullable=False
    )  # Total warnings generated
    quality_score = Column(JSONB, nullable=True)  # Overall processing quality metrics

    # Anonymous processing
    anonymous_ip = Column(String(45), nullable=True)  # IP address for anonymous users

    # Relationships
    user = relationship("User", back_populates="jobs")
    parse_logs = relationship(
        "ParseLog", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ProcessingJob {self.id}: {self.filename} ({self.status})>"

    @property
    def is_completed(self) -> bool:
        """Check if job is in completed state"""
        return self.status == JobStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if job failed"""
        return self.status == JobStatus.FAILED

    @property
    def is_processing(self) -> bool:
        """Check if job is currently processing"""
        return self.status in [JobStatus.PENDING, JobStatus.PROCESSING]

    @property
    def success_rate(self) -> float:
        """Calculate parsing success rate"""
        if self.processed_rows == 0:
            return 0.0
        return (self.successful_parses / self.processed_rows) * 100

    @property
    def gemini_usage_rate(self) -> float:
        """Calculate rate of successful Gemini API usage"""
        if self.processed_rows == 0:
            return 0.0
        return (self.gemini_success_count / self.processed_rows) * 100

    @property
    def fallback_rate(self) -> float:
        """Calculate rate of fallback usage"""
        if self.processed_rows == 0:
            return 0.0
        return (self.fallback_usage_count / self.processed_rows) * 100

    @property
    def has_quality_concerns(self) -> bool:
        """Check if job has quality concerns that need attention"""
        if self.processed_rows == 0:
            return False

        # Quality concerns if:
        # - More than 10% fallback usage
        # - More than 20% low confidence results
        # - More than 30% results with warnings
        fallback_rate = self.fallback_rate
        low_confidence_rate = (self.low_confidence_count / self.processed_rows) * 100
        warning_rate = (self.warning_count / self.processed_rows) * 100

        return fallback_rate > 10 or low_confidence_rate > 20 or warning_rate > 30

    def can_download(self) -> bool:
        """Check if results are available for download"""
        from datetime import datetime, timezone

        if not self.is_completed or not self.result_file_path:
            return False

        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False

        return True

    def get_estimated_completion_time(self) -> int:
        """Estimate completion time in seconds based on progress"""
        if self.progress == 0 or not self.started_at:
            return None

        from datetime import datetime, timezone

        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        if self.progress == 100:
            return 0

        # Estimate based on current progress
        estimated_total = elapsed * (100 / self.progress)
        remaining = estimated_total - elapsed
        return max(0, int(remaining))


# Alias for backward compatibility
Job = ProcessingJob
