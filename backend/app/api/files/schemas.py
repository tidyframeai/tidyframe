"""
Pydantic schemas for file processing endpoints
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, validator

from app.core.schemas import ResponseModel


class FileUploadResponse(ResponseModel):
    job_id: str
    message: str
    estimated_processing_time: Optional[int] = None  # seconds


class AnalyticsData(ResponseModel):
    """Strongly typed analytics data"""

    entity_stats: Dict[str, int]
    confidence_distribution: Dict[str, int]
    gender_distribution: Dict[str, int]
    processing_statistics: Dict[str, Any]


class JobStatus(ResponseModel):
    id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    filename: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None  # When results file will be deleted
    estimated_completion_time: Optional[int] = None  # seconds remaining

    # Results (when completed)
    total_rows: Optional[int] = Field(None, validation_alias="row_count")
    processed_rows: Optional[int] = None
    successful_parses: Optional[int] = None
    failed_parses: Optional[int] = None
    success_rate: Optional[float] = None

    # Quality metrics
    gemini_success_count: Optional[int] = None
    fallback_usage_count: Optional[int] = None
    low_confidence_count: Optional[int] = None
    warning_count: Optional[int] = None
    quality_score: Optional[float] = None

    # Analytics (when completed) - now strongly typed
    analytics: Optional[AnalyticsData] = None

    # Error info (when failed)
    error_message: Optional[str] = None

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    # model_config inherited from ResponseModel (includes from_attributes + alias_generator)


class JobList(ResponseModel):
    jobs: List[JobStatus]
    total: int
    page: int
    page_size: int


class FilePreview(ResponseModel):
    filename: str
    columns: List[str]
    data: List[Dict[str, Any]]
    row_count: int
    name_columns: List[str]
    file_size: int
    mime_type: str


class ProcessingConfig(BaseModel):
    """Configuration options for file processing"""

    # Column selection - user can specify which column to process
    name_columns: Optional[List[str]] = None  # Override auto-detection
    primary_name_column: Optional[str] = (
        None  # Primary column to process (user-selected)
    )

    # Name parsing options
    prioritize_male_names: bool = (
        True  # Always prioritize male names in joint ownership
    )
    detect_joint_names: bool = True  # Detect &, and, AND patterns
    detect_companies: bool = True  # Detect business entities
    detect_trusts: bool = True  # Detect trusts and estates

    # Processing options
    skip_empty_rows: bool = True
    batch_size: int = 100

    # Output options
    include_confidence_scores: bool = True
    include_original_text: bool = True
    preserve_joint_indicators: bool = True  # Keep &, and, AND in output

    @validator("batch_size")
    def validate_batch_size(cls, v):
        if v < 1 or v > 1000:
            raise ValueError("Batch size must be between 1 and 1000")
        return v


class DownloadInfo(BaseModel):
    download_url: str
    filename: str
    file_size: int
    expires_at: datetime
    download_count: int


class ParseResult(BaseModel):
    """Single parsing result"""

    original_text: str
    first_name: str
    last_name: str
    entity_type: str  # person, company, trust, unknown
    gender: str  # male, female, unknown
    gender_confidence: float
    parsing_confidence: float
    is_agricultural: bool
    warnings: List[str]
    row_index: int


class ProcessingSummary(ResponseModel):
    """Summary of processing results"""

    total_rows: int
    successful_parses: int
    failed_parses: int
    success_rate: float
    processing_time_ms: int

    entity_types: Dict[str, int]
    gender_distribution: Dict[str, int]
    average_confidence: float
    agricultural_entities: int
    total_warnings: int


class UsageStats(ResponseModel):
    """User usage statistics"""

    parses_this_month: int
    monthly_limit: int
    remaining_parses: int
    usage_percentage: float
    days_until_reset: int
