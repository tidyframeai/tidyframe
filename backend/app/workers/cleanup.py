"""
Consolidated cleanup tasks for expired data and maintenance
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict

import structlog
from sqlalchemy import and_, select

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database_sync import SessionLocal
from app.models.anonymous_usage import AnonymousUsage
from app.models.job import JobStatus, ProcessingJob
from app.models.user import User

logger = structlog.get_logger()


@celery_app.task
def cleanup_expired_files() -> Dict[str, int]:
    """
    Clean up expired result files and update database
    Runs hourly to remove files older than their expiration date
    """
    logger.info("cleanup_expired_files_started")

    result = {"cleaned_files": 0, "cleaned_jobs": 0, "cleaned_uploads": 0, "errors": 0}

    try:
        with SessionLocal() as db:
            current_time = datetime.now(timezone.utc)

            # Find all expired jobs
            expired_jobs = (
                db.execute(
                    select(ProcessingJob).where(
                        and_(
                            ProcessingJob.expires_at < current_time,
                            ProcessingJob.result_file_path.isnot(None),
                            ProcessingJob.status == JobStatus.COMPLETED,
                        )
                    )
                )
                .scalars()
                .all()
            )

            for job in expired_jobs:
                try:
                    # Delete result file if it exists
                    if job.result_file_path and os.path.exists(job.result_file_path):
                        os.remove(job.result_file_path)
                        result["cleaned_files"] += 1
                        logger.info(
                            "expired_result_file_removed",
                            job_id=str(job.id),
                            file_path=job.result_file_path,
                        )

                    # Clear paths in database
                    job.result_file_path = None
                    job.result_url = None
                    result["cleaned_jobs"] += 1

                    logger.info(
                        "expired_job_cleaned",
                        job_id=str(job.id),
                        expired_at=(
                            job.expires_at.isoformat() if job.expires_at else None
                        ),
                    )

                except Exception as e:
                    logger.error("cleanup_job_failed", job_id=str(job.id), error=str(e))
                    result["errors"] += 1

            # Clean up orphaned upload files older than 24 hours
            upload_dir = settings.UPLOAD_DIR
            if os.path.exists(upload_dir):
                cutoff_time = current_time - timedelta(hours=24)

                for filename in os.listdir(upload_dir):
                    file_path = os.path.join(upload_dir, filename)

                    if os.path.isfile(file_path):
                        try:
                            file_modified = datetime.fromtimestamp(
                                os.path.getmtime(file_path), tz=timezone.utc
                            )

                            if file_modified < cutoff_time:
                                # Check if file is still referenced in database
                                job_with_file = db.execute(
                                    select(ProcessingJob).where(
                                        ProcessingJob.file_path == file_path
                                    )
                                ).scalar_one_or_none()

                                if not job_with_file:
                                    os.remove(file_path)
                                    result["cleaned_uploads"] += 1
                                    logger.info(
                                        "orphaned_upload_removed", file_path=file_path
                                    )
                        except Exception as e:
                            logger.error(
                                "upload_cleanup_failed",
                                file_path=file_path,
                                error=str(e),
                            )
                            result["errors"] += 1

            db.commit()

    except Exception as e:
        logger.error("cleanup_expired_files_failed", error=str(e))
        result["errors"] += 1

    logger.info("cleanup_expired_files_completed", **result)
    return result


@celery_app.task
def cleanup_failed_jobs() -> Dict[str, int]:
    """
    Clean up failed jobs and their associated files
    Removes files from failed jobs older than 7 days
    """
    logger.info("cleanup_failed_jobs_started")

    result = {"cleaned_files": 0, "deleted_jobs": 0, "errors": 0}

    try:
        with SessionLocal() as db:
            # Find failed jobs older than 7 days
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

            failed_jobs = (
                db.execute(
                    select(ProcessingJob).where(
                        and_(
                            ProcessingJob.status == JobStatus.FAILED,
                            ProcessingJob.created_at < cutoff_date,
                        )
                    )
                )
                .scalars()
                .all()
            )

            for job in failed_jobs:
                try:
                    # Remove upload file if it exists
                    if job.file_path and os.path.exists(job.file_path):
                        os.remove(job.file_path)
                        result["cleaned_files"] += 1
                        logger.info(
                            "failed_job_upload_removed",
                            job_id=str(job.id),
                            file_path=job.file_path,
                        )

                    # Remove result file if it exists (shouldn't exist for failed jobs, but check anyway)
                    if job.result_file_path and os.path.exists(job.result_file_path):
                        os.remove(job.result_file_path)
                        result["cleaned_files"] += 1

                    # Delete job record
                    db.delete(job)
                    result["deleted_jobs"] += 1

                    logger.info("failed_job_deleted", job_id=str(job.id))

                except Exception as e:
                    logger.error(
                        "failed_job_cleanup_error", job_id=str(job.id), error=str(e)
                    )
                    result["errors"] += 1

            db.commit()

    except Exception as e:
        logger.error("cleanup_failed_jobs_failed", error=str(e))
        result["errors"] += 1

    logger.info("cleanup_failed_jobs_completed", **result)
    return result


@celery_app.task
def reset_monthly_usage() -> Dict[str, int]:
    """
    Reset monthly usage counters for users whose billing cycle has reset
    Runs daily to check for users who need their monthly counters reset

    For STANDARD users with Stripe subscriptions: Uses Stripe's actual period_end
    For FREE users without subscriptions: Uses 30-day approximation
    """
    logger.info("reset_monthly_usage_started")

    result = {"users_reset": 0, "errors": 0}

    try:
        with SessionLocal() as db:
            current_time = datetime.now(timezone.utc)

            # Find users whose month_reset_date has passed
            users_to_reset = (
                db.execute(select(User).where(User.month_reset_date <= current_time))
                .scalars()
                .all()
            )

            for user in users_to_reset:
                try:
                    # Reset parse count
                    user.parses_this_month = 0

                    # Determine next reset date based on subscription status
                    if user.stripe_subscription_id:
                        # STANDARD user with Stripe subscription - use Stripe's period_end
                        try:
                            from app.services.stripe_service import StripeService
                            stripe_service = StripeService()
                            subscription = stripe_service.stripe.Subscription.retrieve(
                                user.stripe_subscription_id
                            )
                            # Use Stripe's next period_end for accurate billing alignment
                            user.month_reset_date = datetime.fromtimestamp(
                                subscription["current_period_end"], tz=timezone.utc
                            )
                            logger.info(
                                "user_monthly_usage_reset_stripe",
                                user_id=str(user.id),
                                email=user.email,
                                next_reset=user.month_reset_date.isoformat(),
                                source="stripe_period_end"
                            )
                        except Exception as e:
                            # Fallback to 30 days if Stripe fetch fails
                            user.month_reset_date = current_time + timedelta(days=30)
                            logger.warning(
                                "user_reset_stripe_fallback",
                                user_id=str(user.id),
                                error=str(e),
                                next_reset=user.month_reset_date.isoformat()
                            )
                    else:
                        # FREE user without subscription - use 30-day approximation
                        user.month_reset_date = current_time + timedelta(days=30)
                        logger.info(
                            "user_monthly_usage_reset_free",
                            user_id=str(user.id),
                            email=user.email,
                            next_reset=user.month_reset_date.isoformat(),
                            source="30_day_approximation"
                        )

                    result["users_reset"] += 1

                except Exception as e:
                    logger.error(
                        "user_reset_failed", user_id=str(user.id), error=str(e)
                    )
                    result["errors"] += 1

            db.commit()

    except Exception as e:
        logger.error("reset_monthly_usage_failed", error=str(e))
        result["errors"] += 1

    logger.info("reset_monthly_usage_completed", **result)
    return result


@celery_app.task
def cleanup_anonymous_usage() -> Dict[str, int]:
    """
    Clean up old anonymous usage records
    Removes records older than 30 days to maintain privacy
    """
    logger.info("cleanup_anonymous_usage_started")

    result = {"deleted_records": 0, "errors": 0}

    try:
        with SessionLocal() as db:
            # Delete anonymous usage records older than 30 days
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

            old_records = (
                db.execute(
                    select(AnonymousUsage).where(
                        AnonymousUsage.first_used < cutoff_date
                    )
                )
                .scalars()
                .all()
            )

            for record in old_records:
                try:
                    db.delete(record)
                    result["deleted_records"] += 1
                except Exception as e:
                    logger.error(
                        "anonymous_record_delete_failed",
                        record_id=str(record.id),
                        error=str(e),
                    )
                    result["errors"] += 1

            db.commit()

            logger.info(
                "anonymous_usage_cleaned", deleted_count=result["deleted_records"]
            )

    except Exception as e:
        logger.error("cleanup_anonymous_usage_failed", error=str(e))
        result["errors"] += 1

    logger.info("cleanup_anonymous_usage_completed", **result)
    return result


@celery_app.task
def cleanup_all() -> Dict[str, Dict[str, int]]:
    """
    Run all cleanup tasks in sequence
    This is a convenience task that runs all cleanup operations
    """
    logger.info("cleanup_all_started")

    results = {}

    # Run each cleanup task
    try:
        results["expired_files"] = cleanup_expired_files()
    except Exception as e:
        logger.error("cleanup_expired_files_error", error=str(e))
        results["expired_files"] = {"error": str(e)}

    try:
        results["failed_jobs"] = cleanup_failed_jobs()
    except Exception as e:
        logger.error("cleanup_failed_jobs_error", error=str(e))
        results["failed_jobs"] = {"error": str(e)}

    try:
        results["anonymous_usage"] = cleanup_anonymous_usage()
    except Exception as e:
        logger.error("cleanup_anonymous_usage_error", error=str(e))
        results["anonymous_usage"] = {"error": str(e)}

    logger.info("cleanup_all_completed", results=results)
    return results


@celery_app.task
def cleanup_processed_files_10min() -> Dict[str, int]:
    """
    Clean up processed files after 10 minutes (for all users)
    Runs every 10 minutes to ensure files are deleted promptly after processing
    """
    logger.info("cleanup_processed_files_10min_started")

    result = {"cleaned_files": 0, "cleaned_jobs": 0, "errors": 0}

    try:
        with SessionLocal() as db:
            current_time = datetime.now(timezone.utc)

            # Find all completed jobs with expired files (expired means expires_at < now)
            expired_jobs = (
                db.execute(
                    select(ProcessingJob).where(
                        and_(
                            ProcessingJob.expires_at < current_time,
                            ProcessingJob.result_file_path.isnot(None),
                            ProcessingJob.status == JobStatus.COMPLETED,
                        )
                    )
                )
                .scalars()
                .all()
            )

            for job in expired_jobs:
                try:
                    # Delete result file if it exists
                    if job.result_file_path and os.path.exists(job.result_file_path):
                        os.remove(job.result_file_path)
                        result["cleaned_files"] += 1
                        logger.info(
                            "processed_file_cleaned_10min",
                            job_id=str(job.id),
                            file_path=job.result_file_path,
                            expired_at=(
                                job.expires_at.isoformat() if job.expires_at else None
                            ),
                        )

                    # Clear file paths in database (but keep job record for history)
                    job.result_file_path = None
                    job.result_url = None
                    result["cleaned_jobs"] += 1

                except Exception as e:
                    logger.error(
                        "cleanup_10min_job_failed", job_id=str(job.id), error=str(e)
                    )
                    result["errors"] += 1

            # Also clean up any orphaned upload files that are older than retention period
            upload_dir = settings.UPLOAD_DIR
            if os.path.exists(upload_dir):
                cutoff_time = current_time - timedelta(
                    minutes=settings.POST_PROCESSING_RETENTION_MINUTES
                )

                for filename in os.listdir(upload_dir):
                    file_path = os.path.join(upload_dir, filename)

                    if os.path.isfile(file_path):
                        try:
                            file_modified = datetime.fromtimestamp(
                                os.path.getmtime(file_path), tz=timezone.utc
                            )

                            if file_modified < cutoff_time:
                                # Check if file is still referenced in an active job
                                active_job = db.execute(
                                    select(ProcessingJob).where(
                                        and_(
                                            ProcessingJob.file_path == file_path,
                                            ProcessingJob.status.in_(
                                                [
                                                    JobStatus.PENDING,
                                                    JobStatus.PROCESSING,
                                                ]
                                            ),
                                        )
                                    )
                                ).scalar_one_or_none()

                                if not active_job:
                                    os.remove(file_path)
                                    result["cleaned_files"] += 1
                                    logger.info(
                                        "orphaned_upload_cleaned_10min",
                                        file_path=file_path,
                                    )
                        except Exception as e:
                            logger.error(
                                "upload_cleanup_10min_failed",
                                file_path=file_path,
                                error=str(e),
                            )
                            result["errors"] += 1

            db.commit()

    except Exception as e:
        logger.error("cleanup_processed_files_10min_failed", error=str(e))
        result["errors"] += 1

    logger.info("cleanup_processed_files_10min_completed", **result)
    return result
