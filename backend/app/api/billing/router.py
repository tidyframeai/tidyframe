"""
Billing and subscription API routes
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_auth
from app.models.job import ProcessingJob
from app.models.parse_log import ParseLog
from app.models.user import PlanType, User
from app.models.webhook_event import WebhookEvent
from app.services.stripe_service import StripeService

logger = structlog.get_logger()

router = APIRouter()


class CheckoutRequest(BaseModel):
    plan: str  # "STANDARD" or "ENTERPRISE"
    billing_period: str = "monthly"  # "monthly" or "yearly"


class PortalRequest(BaseModel):
    return_url: str


class SubscriptionResponse(BaseModel):
    id: Optional[str] = None
    status: Optional[str] = None
    plan: str
    current_period_start: Optional[int] = None
    current_period_end: Optional[int] = None
    cancel_at_period_end: Optional[bool] = None
    # Usage and billing info
    current_usage: Optional[int] = None
    usage_limit: Optional[int] = None
    usage_percentage: Optional[float] = None
    overage: Optional[int] = None
    overage_cost: Optional[int] = None  # in cents
    estimated_next_invoice: Optional[int] = None  # in cents
    days_until_renewal: Optional[int] = None


class InvoiceResponse(BaseModel):
    id: str
    number: Optional[str] = None
    status: str
    amount_paid: int
    amount_due: int
    currency: str
    created: int
    invoice_pdf: Optional[str] = None
    hosted_invoice_url: Optional[str] = None


class UsageMonth(BaseModel):
    parses: int
    limit: int
    percentage: float
    overage: int
    overage_cost: int  # in cents
    period_start: str
    period_end: str


class PeakDay(BaseModel):
    date: str
    parses: int


class UsageStatsResponse(BaseModel):
    current_month: UsageMonth
    previous_month: UsageMonth
    all_time_parses: int
    average_parse_size: int
    peak_usage_day: PeakDay


class BillingHistoryItem(BaseModel):
    id: str
    amount: int
    currency: str
    status: str
    description: str
    invoice_url: Optional[str] = None
    invoice_pdf: Optional[str] = None
    created_at: str
    paid_at: Optional[str] = None
    line_items: Dict[str, int]


class PricingPlanResponse(BaseModel):
    id: str
    name: str
    description: str
    amount: Optional[int]
    currency: str
    interval: str
    price_id: Optional[str]
    popular: bool
    features: List[str]


class BillingConfigResponse(BaseModel):
    """Billing configuration for frontend display"""

    monthly_price: float  # In dollars
    yearly_price: float  # In dollars
    overage_rate: float  # Per unit in dollars
    standard_limit: int  # Monthly parse limit
    enterprise_limit: int  # Monthly parse limit
    currency: str
    standard_features: List[str]
    standard_yearly_features: List[str]
    enterprise_features: List[str]


@router.post("/create-checkout")
async def create_checkout_session(
    checkout_data: CheckoutRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create Stripe checkout session"""

    stripe_service = StripeService()

    # Log incoming request for debugging
    logger.info(
        "checkout_session_requested",
        user_id=current_user.id,
        plan=checkout_data.plan,
        billing_period=checkout_data.billing_period,
        plan_type=type(checkout_data.plan).__name__,
    )

    # Validate plan
    if checkout_data.plan not in ["STANDARD", "ENTERPRISE"]:
        logger.error(
            "invalid_plan_validation_failed",
            user_id=current_user.id,
            plan_received=checkout_data.plan,
            plan_type=type(checkout_data.plan).__name__,
            expected_plans=["STANDARD", "ENTERPRISE"],
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan selected"
        )

    # Validate billing period
    if checkout_data.billing_period not in ["monthly", "yearly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid billing period. Must be 'monthly' or 'yearly'",
        )

    # Get price ID based on plan and billing period
    if checkout_data.plan == "STANDARD":
        if checkout_data.billing_period == "yearly":
            price_id = settings.STRIPE_STANDARD_YEARLY_PRICE_ID
        else:
            price_id = settings.STRIPE_STANDARD_MONTHLY_PRICE_ID
    else:
        # Enterprise plan
        if checkout_data.billing_period == "yearly":
            price_id = settings.STRIPE_ENTERPRISE_YEARLY_PRICE_ID
        else:
            price_id = settings.STRIPE_ENTERPRISE_MONTHLY_PRICE_ID

    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Price ID not configured for {checkout_data.plan} plan",
        )

    # Create or get Stripe customer
    if not current_user.stripe_customer_id:
        try:
            customer_id = await stripe_service.create_customer(
                email=current_user.email, name=current_user.full_name
            )

            current_user.stripe_customer_id = customer_id
            await db.commit()

        except Exception as e:
            logger.error(
                "stripe_customer_creation_failed", user_id=current_user.id, error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create customer",
            )

    # Create checkout session - uses centralized URL generation
    try:
        checkout_url = await stripe_service.create_checkout_session(
            customer_id=current_user.stripe_customer_id,
            price_id=price_id,
            metadata={"user_id": str(current_user.id), "plan": checkout_data.plan},
        )

        return {"checkout_url": checkout_url}

    except Exception as e:
        logger.error(
            "checkout_session_creation_failed", user_id=current_user.id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        )


@router.post("/portal")
async def create_portal_session(
    portal_data: PortalRequest, current_user: User = Depends(require_auth)
):
    """Create Stripe customer portal session"""

    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Stripe customer found. Please subscribe first.",
        )

    stripe_service = StripeService()

    try:
        portal_url = await stripe_service.create_portal_session(
            customer_id=current_user.stripe_customer_id,
            return_url=portal_data.return_url,
        )

        return {"portal_url": portal_url}

    except Exception as e:
        logger.error(
            "portal_session_creation_failed", user_id=current_user.id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create portal session",
        )


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(current_user: User = Depends(require_auth)):
    """Get user's subscription details with usage and overage information"""

    if not current_user.stripe_subscription_id:
        # Data consistency check: User has paid plan but no Stripe subscription ID
        if current_user.plan in [PlanType.STANDARD, PlanType.ENTERPRISE]:
            logger.error(
                "subscription_data_inconsistency",
                user_id=current_user.id,
                user_plan=current_user.plan.value,
                stripe_subscription_id=None,
                stripe_customer_id=current_user.stripe_customer_id,
                message="User has paid plan but no subscription ID - data inconsistency",
            )
            # Return with warning status to alert frontend
            return SubscriptionResponse(
                plan=current_user.plan.value,
                status="error",  # Special status to indicate data issue
            )

        return SubscriptionResponse(plan=current_user.plan.value, status="inactive")

    stripe_service = StripeService()

    try:
        # Get subscription from Stripe
        subscription = await stripe_service.get_subscription(
            current_user.stripe_subscription_id
        )

        # Get usage data with overage calculations
        usage_data = {}
        if current_user.stripe_customer_id:
            try:
                usage_data = await stripe_service.get_current_usage(
                    current_user.stripe_customer_id
                )
            except Exception as e:
                logger.warning(
                    "usage_fetch_failed", user_id=current_user.id, error=str(e)
                )

        # Calculate days until renewal
        period_end = subscription["current_period_end"]
        days_until_renewal = (
            datetime.fromtimestamp(period_end, tz=timezone.utc)
            - datetime.now(timezone.utc)
        ).days

        # Get subscription base amount
        base_amount = 0
        if subscription.get("items") and subscription["items"]:
            price = subscription["items"][0].get("price", {})
            base_amount = price.get("unit_amount", 0)

        # Calculate usage percentage and estimated invoice
        current_usage = usage_data.get("usage", 0)
        limit = usage_data.get("limit", current_user.monthly_limit)
        overage = usage_data.get("overage", 0)
        overage_cost = int(
            overage * settings.OVERAGE_PRICE_PER_UNIT * 100
        )  # Convert to cents
        usage_percentage = (current_usage / limit * 100) if limit > 0 else 0
        estimated_invoice = base_amount + overage_cost

        return SubscriptionResponse(
            id=subscription["id"],
            status=subscription["status"],
            plan=current_user.plan.value,
            current_period_start=subscription["current_period_start"],
            current_period_end=subscription["current_period_end"],
            cancel_at_period_end=subscription["cancel_at_period_end"],
            current_usage=current_usage,
            usage_limit=limit,
            usage_percentage=round(usage_percentage, 2),
            overage=overage,
            overage_cost=overage_cost,
            estimated_next_invoice=estimated_invoice,
            days_until_renewal=days_until_renewal,
        )

    except Exception as e:
        logger.error(
            "subscription_retrieval_failed",
            user_id=current_user.id,
            subscription_id=current_user.stripe_subscription_id,
            error=str(e),
        )

        # Return basic info if Stripe call fails
        return SubscriptionResponse(plan=current_user.plan.value, status="unknown")


@router.post("/cancel")
async def cancel_subscription(current_user: User = Depends(require_auth)):
    """Cancel user's subscription"""

    if not current_user.stripe_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription found",
        )

    stripe_service = StripeService()

    try:
        result = await stripe_service.cancel_subscription(
            current_user.stripe_subscription_id, at_period_end=True
        )

        return {
            "message": "Subscription will be cancelled at the end of the current billing period",
            "cancel_at_period_end": result["cancel_at_period_end"],
        }

    except Exception as e:
        logger.error(
            "subscription_cancellation_failed",
            user_id=current_user.id,
            subscription_id=current_user.stripe_subscription_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription",
        )


@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(current_user: User = Depends(require_auth)):
    """Get user's invoices"""

    if not current_user.stripe_customer_id:
        return []

    stripe_service = StripeService()

    try:
        invoices = await stripe_service.get_customer_invoices(
            current_user.stripe_customer_id
        )

        return [InvoiceResponse(**invoice) for invoice in invoices]

    except Exception as e:
        logger.error(
            "invoices_retrieval_failed",
            user_id=current_user.id,
            customer_id=current_user.stripe_customer_id,
            error=str(e),
        )
        return []


@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)
):
    """Get comprehensive usage statistics with overage calculations"""

    stripe_service = StripeService()

    # Get current period usage from Stripe (source of truth for billing)
    stripe_usage = {}
    if current_user.stripe_customer_id:
        try:
            stripe_usage = await stripe_service.get_current_usage(
                current_user.stripe_customer_id
            )
        except Exception as e:
            logger.warning(
                "stripe_usage_fetch_failed", user_id=current_user.id, error=str(e)
            )

    # Get current month period from subscription or default
    subscription = None
    if current_user.stripe_subscription_id:
        try:
            subscription = await stripe_service.get_subscription(
                current_user.stripe_subscription_id
            )
            period_start = datetime.fromtimestamp(
                subscription["current_period_start"], tz=timezone.utc
            )
            period_end = datetime.fromtimestamp(
                subscription["current_period_end"], tz=timezone.utc
            )
        except Exception:
            period_start = current_user.month_reset_date
            period_end = period_start + timedelta(days=30)
    else:
        # Fallback to user's month_reset_date
        period_start = current_user.month_reset_date
        period_end = period_start + timedelta(days=30)

    # Use user's parses_this_month as the source of truth for billing
    # This field is incremented during processing and reset monthly via webhooks
    # parse_logs is kept for audit/debugging but not used for billing calculations
    local_current_count = current_user.parses_this_month

    # Get previous month usage
    prev_month_start = period_start - timedelta(days=30)
    prev_month_result = await db.execute(
        select(func.sum(ParseLog.row_count))
        .where(ParseLog.user_id == current_user.id)
        .where(ParseLog.timestamp >= prev_month_start)
        .where(ParseLog.timestamp < period_start)
    )
    prev_month_count = prev_month_result.scalar() or 0

    # Get all-time usage
    all_time_result = await db.execute(
        select(func.sum(ParseLog.row_count)).where(ParseLog.user_id == current_user.id)
    )
    all_time_count = all_time_result.scalar() or 0

    # Get peak usage day (last 30 days)
    peak_day_result = await db.execute(
        select(
            func.date(ParseLog.timestamp).label("date"),
            func.sum(ParseLog.row_count).label("count"),
        )
        .where(ParseLog.user_id == current_user.id)
        .where(ParseLog.timestamp >= period_start)
        .group_by(func.date(ParseLog.timestamp))
        .order_by(func.sum(ParseLog.row_count).desc())
        .limit(1)
    )
    peak_day = peak_day_result.first()

    # Get average file size
    avg_size_result = await db.execute(
        select(func.avg(ProcessingJob.file_size)).where(
            ProcessingJob.user_id == current_user.id
        )
    )
    avg_size = int(avg_size_result.scalar() or 0)

    # Calculate overage (prefer Stripe data for billing)
    current_usage = stripe_usage.get("usage", local_current_count)
    limit = current_user.monthly_limit
    overage = max(0, current_usage - limit)
    overage_cost = int(
        overage * settings.OVERAGE_PRICE_PER_UNIT * 100
    )  # Convert to cents

    # Calculate previous month overage
    prev_overage = max(0, prev_month_count - limit)
    prev_overage_cost = int(prev_overage * settings.OVERAGE_PRICE_PER_UNIT * 100)

    return UsageStatsResponse(
        current_month=UsageMonth(
            parses=current_usage,
            limit=limit,
            percentage=(current_usage / limit * 100) if limit > 0 else 0,
            overage=overage,
            overage_cost=overage_cost,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
        ),
        previous_month=UsageMonth(
            parses=prev_month_count,
            limit=limit,
            percentage=(prev_month_count / limit * 100) if limit > 0 else 0,
            overage=prev_overage,
            overage_cost=prev_overage_cost,
            period_start=prev_month_start.isoformat(),
            period_end=period_start.isoformat(),
        ),
        all_time_parses=all_time_count,
        average_parse_size=avg_size,
        peak_usage_day=PeakDay(
            date=(
                peak_day.date.isoformat()
                if peak_day
                else period_start.date().isoformat()
            ),
            parses=int(peak_day.count) if peak_day else 0,
        ),
    )


@router.get("/history", response_model=List[BillingHistoryItem])
async def get_billing_history(
    limit: int = Query(default=10, le=50), current_user: User = Depends(require_auth)
):
    """Get billing history with overage line items separated"""

    if not current_user.stripe_customer_id:
        return []

    stripe_service = StripeService()

    try:
        # Get invoices with expanded line items
        invoices_raw = stripe_service.stripe.Invoice.list(
            customer=current_user.stripe_customer_id, limit=limit, expand=["data.lines"]
        )

        history = []
        for invoice in invoices_raw.data:
            # Parse line items to separate subscription from overage
            subscription_amount = 0
            overage_amount = 0
            other_amount = 0

            for line in invoice.lines.data:
                description = line.description or ""
                amount = line.amount

                # Identify line item type
                if "overage" in description.lower() or (
                    line.price and line.price.id == settings.STRIPE_OVERAGE_PRICE_ID
                ):
                    overage_amount += amount
                elif line.price and line.price.id in [
                    settings.STRIPE_STANDARD_MONTHLY_PRICE_ID,
                    settings.STRIPE_STANDARD_YEARLY_PRICE_ID,
                    settings.STRIPE_ENTERPRISE_MONTHLY_PRICE_ID,
                    settings.STRIPE_ENTERPRISE_YEARLY_PRICE_ID,
                ]:
                    subscription_amount += amount
                else:
                    other_amount += amount

            history.append(
                BillingHistoryItem(
                    id=invoice.id,
                    amount=invoice.amount_paid,
                    currency=invoice.currency,
                    status=invoice.status,
                    description=f"Invoice {invoice.number or invoice.id}",
                    invoice_url=invoice.hosted_invoice_url,
                    invoice_pdf=invoice.invoice_pdf,
                    created_at=datetime.fromtimestamp(
                        invoice.created, tz=timezone.utc
                    ).isoformat(),
                    paid_at=(
                        datetime.fromtimestamp(
                            invoice.status_transitions.paid_at, tz=timezone.utc
                        ).isoformat()
                        if invoice.status_transitions.paid_at
                        else None
                    ),
                    line_items={
                        "subscription": subscription_amount,
                        "overage": overage_amount,
                        "other": other_amount,
                    },
                )
            )

        return history

    except Exception as e:
        logger.error(
            "billing_history_retrieval_failed",
            user_id=current_user.id,
            customer_id=current_user.stripe_customer_id,
            error=str(e),
        )
        return []


@router.get("/plans", response_model=List[PricingPlanResponse])
async def get_pricing_plans():
    """Get available pricing plans"""

    plans = [
        PricingPlanResponse(
            id="standard-monthly",
            name="Standard",
            description="Professional name parsing for businesses",
            amount=int(settings.STANDARD_MONTHLY_PRICE * 100),  # Convert to cents
            currency="usd",
            interval="month",
            price_id=settings.STRIPE_STANDARD_MONTHLY_PRICE_ID,
            popular=True,
            features=settings.STANDARD_PLAN_FEATURES,
        ),
        PricingPlanResponse(
            id="standard-yearly",
            name="Standard (Yearly)",
            description="Save 20% with annual billing",
            amount=int(settings.STANDARD_YEARLY_PRICE * 100),  # Convert to cents
            currency="usd",
            interval="year",
            price_id=settings.STRIPE_STANDARD_YEARLY_PRICE_ID,
            popular=False,
            features=settings.STANDARD_YEARLY_FEATURES,
        ),
        PricingPlanResponse(
            id="enterprise",
            name="Enterprise",
            description="Custom solutions for large-scale operations",
            amount=None,
            currency="usd",
            interval="month",
            price_id=None,
            popular=False,
            features=settings.ENTERPRISE_PLAN_FEATURES,
        ),
    ]

    return plans


@router.get("/config", response_model=BillingConfigResponse)
async def get_billing_config():
    """Get billing configuration for frontend"""

    return BillingConfigResponse(
        monthly_price=settings.STANDARD_MONTHLY_PRICE,
        yearly_price=settings.STANDARD_YEARLY_PRICE,
        overage_rate=settings.OVERAGE_PRICE_PER_UNIT,
        standard_limit=settings.MONTHLY_NAME_LIMIT,
        enterprise_limit=settings.ENTERPRISE_TIER_MONTHLY_LIMIT,
        currency="usd",
        standard_features=settings.STANDARD_PLAN_FEATURES,
        standard_yearly_features=settings.STANDARD_YEARLY_FEATURES,
        enterprise_features=settings.ENTERPRISE_PLAN_FEATURES,
    )


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle main Stripe webhooks"""

    # Get request body
    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe signature"
        )

    stripe_service = StripeService()

    try:
        # Verify webhook with main webhook secret
        event = stripe_service.construct_webhook_event(
            payload, signature, webhook_type="main"
        )

        # Check if we've already processed this event
        from sqlalchemy import select

        existing_event = await db.execute(
            select(WebhookEvent).where(WebhookEvent.external_event_id == event.id)
        )

        if existing_event.scalar_one_or_none():
            logger.info("webhook_event_already_processed", event_id=event.id)
            return {"status": "already_processed"}

        # Create webhook event record
        webhook_event = WebhookEvent(
            external_event_id=event.id,
            event_type=event.type,
            source="stripe",
            data=event.data,
        )
        db.add(webhook_event)

        # Process the event
        result = await process_stripe_event(event, db)

        if result.get("processed"):
            webhook_event.mark_processed()
        else:
            webhook_event.mark_failed(result.get("error", "Unknown error"))

        await db.commit()

        return {"status": "processed"}

    except Exception as e:
        logger.error(
            "webhook_processing_failed",
            event_type=event.type if "event" in locals() else "unknown",
            error=str(e),
        )

        if "webhook_event" in locals():
            webhook_event.mark_failed(str(e))
            await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed",
        )


@router.post("/stripe/meter/webhook")
async def stripe_meter_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe billing meter webhooks"""

    # Get request body
    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe signature"
        )

    stripe_service = StripeService()

    try:
        # Verify webhook with meter webhook secret
        event = stripe_service.construct_webhook_event(
            payload, signature, webhook_type="meter"
        )

        # Process meter-specific events
        if event.type == "v1.billing.meter.error_report_triggered":
            logger.error(
                "billing_meter_error_report", event_data=event.data, event_id=event.id
            )
            # Handle meter error reports
            return {"status": "acknowledged"}

        logger.info("meter_webhook_received", event_type=event.type)
        return {"status": "processed"}

    except Exception as e:
        logger.error("meter_webhook_processing_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Meter webhook processing failed",
        )


async def process_stripe_event(event, db: AsyncSession) -> dict:
    """Process individual Stripe webhook events"""

    StripeService()
    event_type = event.type
    data = event.data.object

    try:
        if event_type == "checkout.session.completed":
            return await handle_checkout_completed(data, db)
        elif event_type == "checkout.session.expired":
            return await handle_checkout_expired(data, db)
        elif event_type == "customer.subscription.created":
            return await handle_subscription_created(data, db)
        elif event_type == "customer.subscription.updated":
            return await handle_subscription_updated(data, db)
        elif event_type == "customer.subscription.deleted":
            return await handle_subscription_deleted(data, db)
        elif event_type == "invoice.payment_succeeded":
            return await handle_payment_succeeded(data, db)
        elif event_type == "invoice.payment_failed":
            return await handle_payment_failed(data, db)
        else:
            logger.info("webhook_event_ignored", event_type=event_type)
            return {"processed": False, "reason": "Event type not handled"}

    except Exception as e:
        logger.error("event_processing_failed", event_type=event_type, error=str(e))
        return {"processed": False, "error": str(e)}


async def handle_checkout_completed(session_data: dict, db: AsyncSession) -> dict:
    """Handle successful checkout session completion - upgrade user from FREE to STANDARD"""

    customer_id = session_data["customer"]
    subscription_id = session_data.get("subscription")
    metadata = session_data.get("metadata", {})
    plan = metadata.get("plan", "STANDARD")

    # Find user by Stripe customer ID with row-level locking to prevent race conditions
    from sqlalchemy import select

    result = await db.execute(
        select(User)
        .where(User.stripe_customer_id == customer_id)
        .with_for_update()  # Row-level lock prevents concurrent webhook updates
    )
    user = result.scalar_one_or_none()

    if user:
        # Update user's subscription and plan
        if subscription_id:
            user.stripe_subscription_id = subscription_id

        # Upgrade from FREE to the appropriate paid plan
        if plan == "enterprise":
            user.plan = PlanType.ENTERPRISE
        else:
            user.plan = PlanType.STANDARD

        await db.commit()

        logger.info(
            "checkout_completed_processed",
            user_id=user.id,
            subscription_id=subscription_id,
            plan=plan,
            upgraded_from="FREE",
        )
    else:
        logger.error("checkout_completed_user_not_found", customer_id=customer_id)

    return {"processed": True}


async def handle_checkout_expired(session_data: dict, db: AsyncSession) -> dict:
    """Handle checkout session expiration - reset user plan to FREE if payment was cancelled"""

    customer_id = session_data.get("customer")
    session_data.get("metadata", {})

    if not customer_id:
        logger.warning(
            "checkout_expired_no_customer", session_id=session_data.get("id")
        )
        return {"processed": False, "reason": "No customer ID in session"}

    # Find user by Stripe customer ID
    from sqlalchemy import select

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # If user still has FREE plan (webhook from completed never fired), keep it FREE
        # If user somehow got upgraded before expiry, reset back to FREE
        original_plan = str(user.plan)
        user.plan = PlanType.FREE
        user.stripe_subscription_id = None  # Clear any pending subscription

        await db.commit()

        logger.info(
            "checkout_expired_processed",
            user_id=user.id,
            user_email=user.email,
            original_plan=original_plan,
            reset_to="FREE",
            session_id=session_data.get("id"),
        )
    else:
        logger.warning("checkout_expired_user_not_found", customer_id=customer_id)

    return {"processed": True}


async def handle_subscription_created(
    subscription_data: dict, db: AsyncSession
) -> dict:
    """Handle subscription creation"""

    customer_id = subscription_data["customer"]
    subscription_id = subscription_data["id"]

    # Find user by Stripe customer ID with row-level locking
    from sqlalchemy import select

    result = await db.execute(
        select(User)
        .where(User.stripe_customer_id == customer_id)
        .with_for_update()  # Row-level lock prevents concurrent updates
    )
    user = result.scalar_one_or_none()

    if user:
        user.stripe_subscription_id = subscription_id
        # Plan will be updated based on price ID in subscription.updated
        await db.commit()

        logger.info(
            "subscription_created_processed",
            user_id=user.id,
            subscription_id=subscription_id,
        )

    return {"processed": True}


async def handle_subscription_updated(
    subscription_data: dict, db: AsyncSession
) -> dict:
    """Handle subscription updates"""

    customer_id = subscription_data["customer"]
    subscription_id = subscription_data["id"]
    status = subscription_data["status"]

    # Find user with row-level locking
    from sqlalchemy import select

    result = await db.execute(
        select(User)
        .where(User.stripe_customer_id == customer_id)
        .with_for_update()  # Row-level lock prevents concurrent updates
    )
    user = result.scalar_one_or_none()

    if user:
        # Update subscription status and plan based on price ID
        items = subscription_data.get("items", {}).get("data", [])
        if items:
            price_id = items[0].get("price", {}).get("id")

            if price_id in [
                settings.STRIPE_STANDARD_MONTHLY_PRICE_ID,
                settings.STRIPE_STANDARD_YEARLY_PRICE_ID,
            ]:
                user.plan = PlanType.STANDARD
            elif price_id in [
                settings.STRIPE_ENTERPRISE_MONTHLY_PRICE_ID,
                settings.STRIPE_ENTERPRISE_YEARLY_PRICE_ID,
            ]:
                user.plan = PlanType.ENTERPRISE

        # If subscription is cancelled or past due, might want to handle differently
        if status in ["canceled", "past_due"]:
            # Could downgrade to free tier or mark account as limited
            pass

        await db.commit()

        logger.info(
            "subscription_updated_processed",
            user_id=user.id,
            subscription_id=subscription_id,
            status=status,
        )

    return {"processed": True}


async def handle_subscription_deleted(
    subscription_data: dict, db: AsyncSession
) -> dict:
    """Handle subscription deletion - downgrade to FREE plan"""

    customer_id = subscription_data["customer"]
    subscription_id = subscription_data["id"]

    # Find user with row-level locking
    from sqlalchemy import select

    result = await db.execute(
        select(User)
        .where(User.stripe_customer_id == customer_id)
        .with_for_update()  # Row-level lock prevents concurrent updates
    )
    user = result.scalar_one_or_none()

    if user:
        user.stripe_subscription_id = None
        # Downgrade to free tier
        user.plan = PlanType.FREE
        await db.commit()

        logger.info(
            "subscription_deleted_processed",
            user_id=user.id,
            subscription_id=subscription_id,
            downgraded_to="FREE",
        )

    return {"processed": True}


async def handle_payment_succeeded(invoice_data: dict, db: AsyncSession) -> dict:
    """Handle successful payment and reset usage based on Stripe billing period"""

    customer_id = invoice_data["customer"]

    # Find user and reset usage if it's a new billing period
    from sqlalchemy import select

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Reset monthly usage for new billing period
        from datetime import datetime, timezone

        user.parses_this_month = 0

        # Use Stripe's actual billing period end (handles monthly/yearly correctly)
        # Extract period_end from invoice data - supports multiple Stripe webhook formats
        period_end_timestamp = None

        # Try direct period_end field
        if "period_end" in invoice_data:
            period_end_timestamp = invoice_data["period_end"]
        # Try lines.data[0].period.end (standard invoice format)
        elif "lines" in invoice_data and "data" in invoice_data["lines"]:
            lines_data = invoice_data["lines"]["data"]
            if lines_data and len(lines_data) > 0:
                period_data = lines_data[0].get("period", {})
                period_end_timestamp = period_data.get("end")

        if period_end_timestamp:
            # Convert Stripe timestamp to datetime
            user.month_reset_date = datetime.fromtimestamp(
                period_end_timestamp, tz=timezone.utc
            )
            logger.info(
                "payment_succeeded_processed",
                user_id=user.id,
                next_reset=user.month_reset_date.isoformat(),
                period_end_timestamp=period_end_timestamp,
            )
        else:
            # Fallback: fetch subscription data from Stripe if timestamp not in invoice
            try:
                from app.services.stripe_service import StripeService

                stripe_service = StripeService()
                subscription = await stripe_service.get_subscription(
                    user.stripe_subscription_id
                )
                user.month_reset_date = datetime.fromtimestamp(
                    subscription["current_period_end"], tz=timezone.utc
                )
                logger.info(
                    "payment_succeeded_fallback_used",
                    user_id=user.id,
                    next_reset=user.month_reset_date.isoformat(),
                )
            except Exception as e:
                # Last resort: 30 days (better than nothing, but logs warning)
                from datetime import timedelta

                user.month_reset_date = datetime.now(timezone.utc) + timedelta(days=30)
                logger.warning(
                    "payment_succeeded_fallback_failed",
                    user_id=user.id,
                    error=str(e),
                    using_30day_fallback=True,
                )

        await db.commit()

    return {"processed": True}


async def handle_payment_failed(invoice_data: dict, db: AsyncSession) -> dict:
    """Handle failed payment"""

    customer_id = invoice_data["customer"]

    # Could send email notification or limit account access
    logger.warning("payment_failed", customer_id=customer_id)

    return {"processed": True}
