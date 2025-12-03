"""
Admin API routes
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin_user
from app.models.job import ProcessingJob
from app.models.parse_log import ParseLog
from app.models.user import PlanType, User
from app.models.webhook_event import WebhookEvent

logger = structlog.get_logger()

router = APIRouter()


class UserSummary(BaseModel):
    id: str
    email: str
    plan: str
    parses_this_month: int
    monthly_limit: int
    custom_monthly_limit: Optional[int] = None
    is_active: bool
    email_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SystemStats(BaseModel):
    total_users: int
    active_users: int
    total_jobs: int
    jobs_today: int
    total_parses: int
    parses_today: int
    storage_used_gb: float


class UsageResetRequest(BaseModel):
    user_id: str
    reset_count: Optional[int] = 0


class UserLimitUpdate(BaseModel):
    custom_monthly_limit: Optional[int] = None


class UserPlanUpdate(BaseModel):
    plan: str


class SetParseCountRequest(BaseModel):
    """Request to manually set user's parse count - for testing threshold behavior"""

    parse_count: int = Field(
        ge=0, le=10_000_000, description="Parse count to set (0-10M)"
    )
    reason: str = Field(min_length=10, description="Reason for manual adjustment")


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    current_user: User = Depends(require_admin_user), db: AsyncSession = Depends(get_db)
):
    """Get system statistics"""

    today = datetime.now(timezone.utc).date()
    today_start = datetime.combine(today, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )

    # Count users
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar()

    active_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_active)
    )
    active_users = active_users_result.scalar()

    # Count jobs
    total_jobs_result = await db.execute(select(func.count(ProcessingJob.id)))
    total_jobs = total_jobs_result.scalar()

    jobs_today_result = await db.execute(
        select(func.count(ProcessingJob.id)).where(
            ProcessingJob.created_at >= today_start
        )
    )
    jobs_today = jobs_today_result.scalar()

    # Count parses
    total_parses_result = await db.execute(select(func.sum(ParseLog.row_count)))
    total_parses = total_parses_result.scalar() or 0

    parses_today_result = await db.execute(
        select(func.sum(ParseLog.row_count)).where(ParseLog.timestamp >= today_start)
    )
    parses_today = parses_today_result.scalar() or 0

    # Estimate storage usage (rough calculation)
    storage_used_gb = 0.0  # Would need to implement actual disk usage calculation

    return SystemStats(
        total_users=total_users,
        active_users=active_users,
        total_jobs=total_jobs,
        jobs_today=jobs_today,
        total_parses=total_parses,
        parses_today=parses_today,
        storage_used_gb=storage_used_gb,
    )


@router.get("/users", response_model=List[UserSummary])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    plan_filter: Optional[str] = Query(None),
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List users with pagination and filtering"""

    # Build query
    query = select(User)

    if search:
        query = query.where(User.email.ilike(f"%{search}%"))

    if plan_filter:
        query = query.where(User.plan == plan_filter)

    # Add pagination
    offset = (page - 1) * page_size
    query = query.order_by(desc(User.created_at)).offset(offset).limit(page_size)

    result = await db.execute(query)
    users = result.scalars().all()

    return [
        UserSummary(
            id=str(user.id),
            email=user.email,
            plan=user.plan.value,
            parses_this_month=user.parses_this_month,
            monthly_limit=user.monthly_limit,
            custom_monthly_limit=user.custom_monthly_limit,
            is_active=user.is_active,
            email_verified=user.email_verified,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
        for user in users
    ]


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed user information"""

    import uuid

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format"
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Get user's job statistics
    jobs_count_result = await db.execute(
        select(func.count(ProcessingJob.id)).where(ProcessingJob.user_id == user.id)
    )
    jobs_count = jobs_count_result.scalar()

    parses_count_result = await db.execute(
        select(func.sum(ParseLog.row_count)).where(ParseLog.user_id == user.id)
    )
    parses_count = parses_count_result.scalar() or 0

    return {
        "user": UserSummary(
            id=str(user.id),
            email=user.email,
            plan=user.plan.value,
            parses_this_month=user.parses_this_month,
            monthly_limit=user.monthly_limit,
            custom_monthly_limit=user.custom_monthly_limit,
            is_active=user.is_active,
            email_verified=user.email_verified,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        ),
        "statistics": {
            "total_jobs": jobs_count,
            "total_parses": parses_count,
            "current_month_parses": user.parses_this_month,
        },
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    update_data: dict,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user information"""

    import uuid

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format"
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update allowed fields
    allowed_fields = ["is_active", "plan", "email_verified", "custom_monthly_limit"]

    for field, value in update_data.items():
        if field in allowed_fields:
            if field == "plan":
                # Validate plan
                try:
                    plan_enum = PlanType(value)
                    setattr(user, field, plan_enum)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid plan: {value}",
                    )
            else:
                setattr(user, field, value)

    await db.commit()

    logger.info(
        "user_updated_by_admin",
        admin_id=current_user.id,
        target_user_id=user.id,
        updates=update_data,
    )

    return {"message": "User updated successfully"}


@router.post("/users/{user_id}/reset-usage")
async def reset_user_usage(
    user_id: str,
    reset_data: UsageResetRequest,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset user's monthly usage"""

    import uuid

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format"
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    old_count = user.parses_this_month
    user.parses_this_month = reset_data.reset_count

    # Set next reset date based on subscription status
    if user.stripe_subscription_id:
        # Use Stripe's next period_end for STANDARD users
        try:
            from app.services.stripe_service import StripeService

            stripe_service = StripeService()
            subscription = await stripe_service.get_subscription(user.stripe_subscription_id)
            user.month_reset_date = datetime.fromtimestamp(
                subscription["current_period_end"], tz=timezone.utc
            )
        except Exception:
            # Fallback if Stripe fetch fails
            user.month_reset_date = datetime.now(timezone.utc) + timedelta(days=30)
    else:
        # FREE user - use 30-day approximation
        user.month_reset_date = datetime.now(timezone.utc) + timedelta(days=30)

    await db.commit()

    logger.info(
        "user_usage_reset_by_admin",
        admin_id=current_user.id,
        target_user_id=user.id,
        old_count=old_count,
        new_count=reset_data.reset_count,
    )

    return {
        "message": "Usage reset successfully",
        "old_count": old_count,
        "new_count": reset_data.reset_count,
    }


@router.post("/users/{user_id}/set-parse-count")
async def set_user_parse_count(
    user_id: str,
    request_data: SetParseCountRequest,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Set user's parse count to a specific value - for testing overage threshold behavior.

    Use cases:
    - Set to 99,999 to test 100K threshold behavior
    - Set to 150,000 to test overage billing calculation
    - Set to 0 for clean testing runs

    This endpoint requires a reason for audit trail purposes.
    """

    import uuid

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format"
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Validate parse count against user's limit
    if request_data.parse_count > user.monthly_limit * 2:
        logger.warning(
            "parse_count_set_exceeds_2x_limit",
            admin_id=current_user.id,
            user_id=user.id,
            parse_count=request_data.parse_count,
            limit=user.monthly_limit,
        )

    old_count = user.parses_this_month
    user.parses_this_month = request_data.parse_count

    await db.commit()

    # Calculate overage status
    overage_amount = max(0, request_data.parse_count - user.monthly_limit)
    is_overage = request_data.parse_count >= user.monthly_limit

    logger.info(
        "parse_count_set_by_admin",
        admin_id=str(current_user.id),
        admin_email=current_user.email,
        target_user_id=str(user.id),
        target_user_email=user.email,
        old_count=old_count,
        new_count=request_data.parse_count,
        user_limit=user.monthly_limit,
        is_overage=is_overage,
        overage_amount=overage_amount,
        reason=request_data.reason,
    )

    return {
        "message": "Parse count set successfully",
        "user_email": user.email,
        "old_count": old_count,
        "new_count": request_data.parse_count,
        "monthly_limit": user.monthly_limit,
        "is_overage": is_overage,
        "overage_amount": overage_amount,
        "overage_cost_usd": overage_amount * 0.01,  # $0.01 per parse
        "reason": request_data.reason,
    }


@router.patch("/users/{user_id}/limits")
async def update_user_limits(
    user_id: str,
    limit_update: UserLimitUpdate,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user's monthly limits"""

    import uuid

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format"
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    old_limit = user.custom_monthly_limit
    user.custom_monthly_limit = limit_update.custom_monthly_limit

    await db.commit()

    logger.info(
        "user_limits_updated_by_admin",
        admin_id=current_user.id,
        target_user_id=user.id,
        old_limit=old_limit,
        new_limit=limit_update.custom_monthly_limit,
    )

    return {
        "message": "User limits updated successfully",
        "old_limit": old_limit,
        "new_limit": limit_update.custom_monthly_limit,
        "monthly_limit": user.monthly_limit,  # This will use the new custom limit
    }


@router.patch("/users/{user_id}/plan")
async def update_user_plan(
    user_id: str,
    plan_update: UserPlanUpdate,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user's plan"""

    import uuid

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format"
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Validate plan
    try:
        plan_enum = PlanType(plan_update.plan)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan: {plan_update.plan}",
        )

    old_plan = user.plan.value
    user.plan = plan_enum

    await db.commit()

    logger.info(
        "user_plan_updated_by_admin",
        admin_id=current_user.id,
        target_user_id=user.id,
        old_plan=old_plan,
        new_plan=plan_update.plan,
    )

    return {
        "message": "User plan updated successfully",
        "old_plan": old_plan,
        "new_plan": plan_update.plan,
        "monthly_limit": user.monthly_limit,
    }


@router.get("/jobs")
async def list_all_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    user_email: Optional[str] = Query(None),
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all processing jobs with filtering"""

    # Build query
    query = select(ProcessingJob).join(
        User, ProcessingJob.user_id == User.id, isouter=True
    )

    if status_filter:
        query = query.where(ProcessingJob.status == status_filter)

    if user_email:
        query = query.where(User.email.ilike(f"%{user_email}%"))

    # Add pagination
    offset = (page - 1) * page_size
    query = (
        query.order_by(desc(ProcessingJob.created_at)).offset(offset).limit(page_size)
    )

    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "jobs": [
            {
                "id": str(job.id),
                "filename": job.filename,
                "status": job.status.value,
                "user_email": job.user.email if job.user else "anonymous",
                "created_at": job.created_at,
                "row_count": job.row_count,
                "progress": job.progress,
            }
            for job in jobs
        ]
    }


@router.get("/logs")
async def get_system_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    level: Optional[str] = Query(None),
    current_user: User = Depends(require_admin_user),
):
    """Get system logs (placeholder - would integrate with logging system)"""

    # This would integrate with your logging system
    # For now, return placeholder data

    return {"logs": [], "message": "Log integration not implemented yet"}


@router.get("/webhooks")
async def list_webhook_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    processed: Optional[bool] = Query(None),
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List webhook events"""

    query = select(WebhookEvent)

    if processed is not None:
        query = query.where(WebhookEvent.processed == processed)

    # Add pagination
    offset = (page - 1) * page_size
    query = (
        query.order_by(desc(WebhookEvent.created_at)).offset(offset).limit(page_size)
    )

    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "events": [
            {
                "id": str(event.id),
                "external_event_id": event.external_event_id,
                "event_type": event.event_type,
                "source": event.source,
                "processed": event.processed,
                "created_at": event.created_at,
                "error_message": event.error_message,
            }
            for event in events
        ]
    }
