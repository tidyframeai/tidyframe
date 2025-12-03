"""
Database utility functions for job management in Celery workers

This module provides sync database operations for Celery workers since
Celery runs in a different context and needs sync database access.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.job import JobStatus, ProcessingJob

logger = structlog.get_logger()

# Create synchronous engine for Celery workers
# Convert async URL to sync URL (replace postgresql+asyncpg with postgresql+psycopg2)
sync_db_url = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)

sync_engine = create_engine(
    sync_db_url,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


def update_job_status(
    job_id: str,
    status: JobStatus,
    error_message: Optional[str] = None,
    processing_results: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Update job status in database (synchronous for Celery workers)

    Args:
        job_id: Job ID to update
        status: New job status
        error_message: Error message if job failed
        processing_results: Results from processing (for completed jobs)

    Returns:
        bool: True if update was successful
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        logger.error("invalid_job_id", job_id=job_id)
        return False

    with SyncSessionLocal() as db:
        try:
            # Find the job
            stmt = select(ProcessingJob).where(ProcessingJob.id == job_uuid)
            result = db.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                logger.error("job_not_found", job_id=job_id)
                return False

            # Update basic status
            job.status = status
            current_time = datetime.now(timezone.utc)

            if status == JobStatus.PROCESSING:
                job.started_at = current_time
                logger.info("job_status_updated", job_id=job_id, status="processing")

            elif status == JobStatus.COMPLETED:
                from datetime import timedelta

                job.completed_at = current_time
                # Set expiry time using configured retention period
                job.expires_at = current_time + timedelta(
                    minutes=settings.POST_PROCESSING_RETENTION_MINUTES
                )

                # Update processing results if provided
                if processing_results:
                    # CRITICAL: Set row_count from total_rows for frontend display
                    job.row_count = processing_results.get("total_rows", 0)
                    job.processed_rows = processing_results.get("processed_rows", 0)
                    # Handle None values - if successful_parses is None, don't update it
                    if (
                        "successful_parses" in processing_results
                        and processing_results["successful_parses"] is not None
                    ):
                        job.successful_parses = processing_results["successful_parses"]
                    job.failed_parses = processing_results.get("failed_parses", 0)
                    job.result_file_path = processing_results.get("results_path")

                    # Store analytics in error_details (repurpose as analytics for completed jobs)
                    analytics = {
                        "entity_stats": processing_results.get("entity_stats", {}),
                        "gender_distribution": processing_results.get(
                            "gender_distribution", {}
                        ),
                        "avg_confidence": processing_results.get("avg_confidence", 0.0),
                        "high_confidence_count": processing_results.get(
                            "high_confidence_count", 0
                        ),
                        "medium_confidence_count": processing_results.get(
                            "medium_confidence_count", 0
                        ),
                        "low_confidence_count": processing_results.get(
                            "low_confidence_count", 0
                        ),
                        "success_rate": processing_results.get("success_rate", 0.0),
                        # Add additional fields that frontend expects
                        "gemini_success_count": processing_results.get(
                            "fallback_stats", {}
                        ).get("gemini_used", 0),
                        "fallback_usage_count": processing_results.get(
                            "fallback_stats", {}
                        ).get("fallback_used", 0),
                    }
                    job.error_details = analytics  # Repurposing for analytics storage

                    # Calculate processing time
                    if job.started_at:
                        processing_time = (
                            current_time - job.started_at
                        ).total_seconds() * 1000
                        job.processing_time_ms = int(processing_time)

                    # CRITICAL: Update user's parse count for authenticated users
                    if job.user_id:
                        from app.models.parse_log import ParseLog
                        from app.models.user import User

                        user_stmt = select(User).where(User.id == job.user_id)
                        user_result = db.execute(user_stmt)
                        user = user_result.scalar_one_or_none()

                        if user:
                            # Increment the user's monthly parse count
                            # Use successful_parses if it was explicitly set in the results, otherwise
                            # use processed_rows
                            if (
                                processing_results
                                and "successful_parses" in processing_results
                                and processing_results["successful_parses"] is not None
                            ):
                                rows_parsed = processing_results["successful_parses"]
                            else:
                                rows_parsed = job.processed_rows
                            if rows_parsed and rows_parsed > 0:
                                # CRITICAL: Calculate overage status BEFORE incrementing counter
                                user_limit = user.monthly_limit
                                parses_before_job = user.parses_this_month or 0
                                is_overage_parse = parses_before_job >= user_limit

                                # Now increment the counter
                                user.parses_this_month = parses_before_job + rows_parsed

                                # Report usage to Stripe for overage billing IMMEDIATELY
                                # Use synchronous Stripe call for immediate reporting
                                if user.stripe_customer_id and not user.is_admin:
                                    try:
                                        import stripe

                                        # Initialize Stripe with API key (settings already imported at module level)
                                        stripe.api_key = settings.STRIPE_SECRET_KEY

                                        # Report usage immediately using Meter Events API v2
                                        meter_event_name = settings.STRIPE_METER_EVENT_NAME or "tidyframe_token"
                                        meter_event = stripe.v2.billing.MeterEvent.create(
                                            event_name=meter_event_name,  # Meter event name from settings
                                            payload={
                                                "value": rows_parsed,
                                                "stripe_customer_id": user.stripe_customer_id,
                                            },
                                        )

                                        logger.info(
                                            f"Immediately reported {rows_parsed} usage to Stripe for customer {user.stripe_customer_id}"
                                        )

                                    except Exception as e:
                                        logger.error(
                                            f"Failed to report usage to Stripe immediately: {e}"
                                        )
                                        # Fallback to queue if immediate reporting fails
                                        from app.services.stripe_service import (
                                            get_usage_service,
                                        )

                                        usage_service = get_usage_service()
                                        usage_service.usage_queue.append(
                                            {
                                                "customer_id": user.stripe_customer_id,
                                                "quantity": rows_parsed,
                                                "timestamp": current_time,
                                                "user_id": str(user.id),
                                            }
                                        )
                                        logger.info(
                                            f"Fallback: Queued {rows_parsed} usage for customer {user.stripe_customer_id}"
                                        )

                                # Create ParseLog entry for tracking with correct overage flag
                                parse_log = ParseLog(
                                    user_id=job.user_id,
                                    job_id=job.id,
                                    row_count=rows_parsed,
                                    timestamp=current_time,
                                    processing_time_ms=job.processing_time_ms or 0,
                                    success=True,
                                    is_overage=is_overage_parse,  # ✅ FIXED: Dynamic flag based on user limit
                                )
                                db.add(parse_log)

                                logger.info(
                                    "user_parse_count_updated",
                                    user_id=str(job.user_id),
                                    rows_parsed=rows_parsed,
                                    new_total=user.parses_this_month,
                                    is_overage=is_overage_parse,  # ✅ ADDED: Log overage status
                                    overage_amount=max(0, user.parses_this_month - user_limit),  # ✅ ADDED: Log overage amount
                                )

                    # Update fallback tracking fields
                    fallback_stats = processing_results.get("fallback_stats", {})
                    if fallback_stats:
                        job.gemini_success_count = fallback_stats.get("gemini_used", 0)
                        job.fallback_usage_count = fallback_stats.get(
                            "fallback_used", 0
                        )
                        job.fallback_reasons = fallback_stats.get(
                            "fallback_reasons", {}
                        )

                    # Update quality metrics
                    warning_stats = processing_results.get("warning_stats", {})
                    if warning_stats:
                        job.warning_count = warning_stats.get("total_warnings", 0)
                        job.low_confidence_count = processing_results.get(
                            "low_confidence_count", 0
                        )

                    # Store overall quality score
                    quality_score = processing_results.get("quality_score", 0)
                    # quality_score should be a float/numeric value for the database
                    if isinstance(quality_score, dict):
                        job.quality_score = float(quality_score.get("score", 0))
                    else:
                        job.quality_score = float(quality_score)

                    # Also update anonymous usage if applicable
                    if job.anonymous_ip:
                        from app.models.anonymous_usage import AnonymousUsage

                        anon_stmt = select(AnonymousUsage).where(
                            AnonymousUsage.ip_address == job.anonymous_ip
                        )
                        anon_result = db.execute(anon_stmt)
                        anon_usage = anon_result.scalar_one_or_none()

                        if anon_usage:
                            # Use successful_parses if it was explicitly set in the results, otherwise
                            # use processed_rows
                            if (
                                processing_results
                                and "successful_parses" in processing_results
                                and processing_results["successful_parses"] is not None
                            ):
                                rows_parsed = processing_results["successful_parses"]
                            else:
                                rows_parsed = job.processed_rows
                            if rows_parsed and rows_parsed > 0:
                                anon_usage.parse_count = (
                                    anon_usage.parse_count or 0
                                ) + rows_parsed
                                anon_usage.last_used = current_time  # Fixed: Column name is last_used, not last_used_at
                                logger.info(
                                    "anonymous_parse_count_updated",
                                    ip=job.anonymous_ip,
                                    rows_parsed=rows_parsed,
                                    new_total=anon_usage.parse_count,
                                )
                        else:
                            # Create AnonymousUsage record if it doesn't exist (defensive fallback)
                            from app.models.anonymous_usage import AnonymousUsage

                            rows_parsed = processing_results.get(
                                "successful_parses", job.processed_rows
                            )
                            if rows_parsed and rows_parsed > 0:
                                anon_usage = AnonymousUsage(
                                    ip_address=job.anonymous_ip, parse_count=rows_parsed
                                )
                                db.add(anon_usage)
                                logger.info(
                                    "anonymous_usage_created_on_completion",
                                    ip=job.anonymous_ip,
                                    rows_parsed=rows_parsed,
                                )

                logger.info(
                    "job_completed_updated",
                    job_id=job_id,
                    processed_rows=job.processed_rows,
                    successful_parses=job.successful_parses,
                    analytics=analytics if "analytics" in locals() else None,
                )

            elif status == JobStatus.FAILED:
                job.completed_at = current_time
                if error_message:
                    job.error_message = error_message[
                        :1000
                    ]  # Limit error message length

                logger.info("job_failed_updated", job_id=job_id, error=error_message)

            # Commit changes
            db.commit()
            return True

        except Exception as e:
            db.rollback()
            logger.error(
                "job_status_update_failed",
                job_id=job_id,
                status=status.value,
                error=str(e),
            )
            return False


def get_job_by_id(job_id: str) -> Optional[ProcessingJob]:
    """
    Get job by ID (synchronous for Celery workers)

    Args:
        job_id: Job ID to retrieve

    Returns:
        ProcessingJob or None if not found
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        logger.error("invalid_job_id", job_id=job_id)
        return None

    with SyncSessionLocal() as db:
        try:
            stmt = select(ProcessingJob).where(ProcessingJob.id == job_uuid)
            result = db.execute(stmt)
            job = result.scalar_one_or_none()
            return job
        except Exception as e:
            logger.error("job_fetch_failed", job_id=job_id, error=str(e))
            return None


def update_job_progress_db(job_id: str, progress: int) -> bool:
    """
    Update job progress in database (in addition to Redis)

    Args:
        job_id: Job ID to update
        progress: Progress percentage (0-100)

    Returns:
        bool: True if update was successful
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        logger.error("invalid_job_id", job_id=job_id)
        return False

    with SyncSessionLocal() as db:
        try:
            # Update progress using a more efficient update statement
            stmt = (
                update(ProcessingJob)
                .where(ProcessingJob.id == job_uuid)
                .values(progress=progress)
            )
            db.execute(stmt)
            db.commit()
            return True

        except Exception as e:
            db.rollback()
            logger.error(
                "job_progress_update_failed",
                job_id=job_id,
                progress=progress,
                error=str(e),
            )
            return False
