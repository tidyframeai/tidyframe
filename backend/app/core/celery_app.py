"""
Celery application setup for background task processing
"""

from celery import Celery

from app.core.config import settings

# Import all models to ensure they're registered with SQLAlchemy

# Create Celery app
celery_app = Celery(
    "tidyframe",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.file_processor",
        "app.workers.email_sender",
        "app.workers.cleanup",
        "app.workers.webhook_retry",
    ],
)

# Configure Celery
celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=settings.CELERY_ENABLE_UTC,
    # Task routing - temporarily disabled for debugging
    # task_routes={
    #     "app.workers.file_processor.process_file": {"queue": "file_processing"},
    #     "app.workers.email_sender.*": {"queue": "email"},
    #     "app.workers.cleanup.*": {"queue": "cleanup"},
    # },
    # Task configuration
    task_time_limit=60 * settings.PROCESSING_TIMEOUT_MINUTES,  # Hard time limit
    task_soft_time_limit=60
    * (settings.PROCESSING_TIMEOUT_MINUTES - 5),  # Soft time limit
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Result backend configuration
    result_expires=3600,  # Results expire after 1 hour
    # Beat scheduler configuration (for periodic tasks)
    beat_schedule={
        "cleanup-processed-files-10min": {
            "task": "app.workers.cleanup.cleanup_processed_files_10min",
            "schedule": 60.0 * 10.0,  # Every 10 minutes - prompt file cleanup
        },
        "cleanup-expired-files": {
            "task": "app.workers.cleanup.cleanup_expired_files",
            "schedule": 60.0 * 60.0,  # Every hour - safety net cleanup
        },
        "reset-monthly-usage": {
            "task": "app.workers.cleanup.reset_monthly_usage",
            "schedule": 60.0 * 60.0 * 24.0,  # Daily check
        },
        "cleanup-failed-jobs": {
            "task": "app.workers.cleanup.cleanup_failed_jobs",
            "schedule": 60.0 * 60.0 * 24.0,  # Daily
        },
        "cleanup-anonymous-usage": {
            "task": "app.workers.cleanup.cleanup_anonymous_usage",
            "schedule": 60.0 * 60.0 * 24.0,  # Daily
        },
        "retry-failed-webhooks": {
            "task": "app.workers.webhook_retry.retry_failed_webhooks",
            "schedule": 60.0 * 5.0,  # Every 5 minutes - retry failed webhooks
        },
        "sync-subscription-status": {
            "task": "app.workers.webhook_retry.sync_subscription_status",
            "schedule": 60.0 * 60.0,  # Every hour - sync subscription status from Stripe
        },
    },
)

if __name__ == "__main__":
    celery_app.start()
