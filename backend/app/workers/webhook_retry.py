"""
Webhook retry worker for processing failed webhook events
Ensures reliable webhook processing with exponential backoff
"""

import structlog
from datetime import datetime, timedelta, timezone

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.webhook_event import WebhookEvent
from app.services.stripe_service import StripeService

logger = structlog.get_logger()

# Create async database engine for Celery tasks
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_pre_ping=True,
)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


class WebhookRetryTask(Task):
    """Custom task class with retry configuration"""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 5}
    retry_backoff = True  # Exponential backoff
    retry_backoff_max = 600  # Max 10 minutes between retries
    retry_jitter = True  # Add random jitter to prevent thundering herd


@celery_app.task(
    bind=True,
    base=WebhookRetryTask,
    name="app.workers.webhook_retry.retry_failed_webhooks",
)
def retry_failed_webhooks(self):
    """
    Periodic task to retry failed webhook events
    Runs every 5 minutes via beat scheduler
    """
    import asyncio

    return asyncio.run(_retry_failed_webhooks_async())


async def _retry_failed_webhooks_async():
    """Async implementation of webhook retry logic"""
    from app.api.billing.router import process_stripe_event

    logger.info("webhook_retry_started", task="retry_failed_webhooks")

    async with AsyncSessionLocal() as db:
        # Find failed webhooks older than 5 minutes that haven't exceeded max attempts
        five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)

        result = await db.execute(
            select(WebhookEvent)
            .where(
                WebhookEvent.processed == False,  # noqa: E712
                WebhookEvent.processing_attempts < 5,
                WebhookEvent.created_at < five_minutes_ago,
            )
            .order_by(WebhookEvent.created_at.asc())
            .limit(50)  # Process up to 50 failed webhooks per run
        )
        failed_events = result.scalars().all()

        retry_count = 0
        success_count = 0
        failed_count = 0

        for event in failed_events:
            try:
                logger.info(
                    "webhook_retry_attempt",
                    event_id=event.external_event_id,
                    event_type=event.event_type,
                    attempt=event.processing_attempts + 1,
                )

                # Reconstruct Stripe event object
                stripe_event = {
                    "id": event.external_event_id,
                    "type": event.event_type,
                    "data": event.data,
                }

                # Retry processing
                result = await process_stripe_event(stripe_event, db)

                if result.get("processed"):
                    event.mark_processed()
                    success_count += 1
                    logger.info(
                        "webhook_retry_success",
                        event_id=event.external_event_id,
                        event_type=event.event_type,
                    )
                else:
                    event.mark_failed(result.get("error", "Retry failed"))
                    failed_count += 1

                retry_count += 1

            except Exception as e:
                logger.error(
                    "webhook_retry_error",
                    event_id=event.external_event_id,
                    event_type=event.event_type,
                    error=str(e),
                )
                event.mark_failed(str(e))
                failed_count += 1

        await db.commit()

        logger.info(
            "webhook_retry_completed",
            total_attempted=retry_count,
            successful=success_count,
            failed=failed_count,
        )

        return {
            "total_attempted": retry_count,
            "successful": success_count,
            "failed": failed_count,
        }


@celery_app.task(
    bind=True,
    base=WebhookRetryTask,
    name="app.workers.webhook_retry.sync_subscription_status",
)
def sync_subscription_status(self):
    """
    Background job to sync subscription status from Stripe
    Catches any missed webhooks by directly querying Stripe API
    Runs hourly via beat scheduler
    """
    import asyncio

    return asyncio.run(_sync_subscription_status_async())


async def _sync_subscription_status_async():
    """Async implementation of subscription sync"""
    from app.models.user import PlanType, User

    logger.info("subscription_sync_started")

    stripe_service = StripeService()
    sync_count = 0
    error_count = 0

    async with AsyncSessionLocal() as db:
        # Get all users with active paid plans and Stripe subscriptions
        result = await db.execute(
            select(User).where(
                User.plan.in_([PlanType.STANDARD, PlanType.ENTERPRISE]),
                User.stripe_subscription_id.isnot(None),
            )
        )
        users = result.scalars().all()

        for user in users:
            try:
                # Get subscription from Stripe
                subscription = await stripe_service.get_subscription(
                    user.stripe_subscription_id
                )

                # Check if subscription status is active
                if subscription["status"] not in ["active", "trialing"]:
                    logger.warning(
                        "subscription_status_mismatch",
                        user_id=user.id,
                        user_plan=user.plan.value,
                        stripe_status=subscription["status"],
                        message="User plan doesn't match Stripe subscription status",
                    )

                    # If subscription is canceled or past_due, downgrade to free
                    if subscription["status"] in ["canceled", "unpaid"]:
                        user.plan = PlanType.FREE
                        user.stripe_subscription_id = None
                        logger.info(
                            "subscription_auto_downgraded",
                            user_id=user.id,
                            reason=subscription["status"],
                        )

                sync_count += 1

            except Exception as e:
                logger.error(
                    "subscription_sync_error",
                    user_id=user.id,
                    subscription_id=user.stripe_subscription_id,
                    error=str(e),
                )
                error_count += 1

        await db.commit()

        logger.info(
            "subscription_sync_completed", synced=sync_count, errors=error_count
        )

        return {"synced": sync_count, "errors": error_count}
