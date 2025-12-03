"""
Enhanced Stripe Service with Usage Metering and Overage Billing
Gilfoyle-approved implementation with proper architecture
"""

import asyncio
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List

import stripe
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Load Stripe API key from environment (module-level for global access)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
# API version is set per-instance in StripeService.__init__ for proper encapsulation


class SubscriptionTier(Enum):
    """Subscription tiers with limits"""

    FREE = "FREE"
    STANDARD = "STANDARD"
    ENTERPRISE = "ENTERPRISE"

    @property
    def monthly_limit(self):
        limits = {self.FREE: 1000, self.STANDARD: 100000, self.ENTERPRISE: float("inf")}
        return limits.get(self, 0)


class StripeService:
    """
    Production-ready Stripe integration with usage metering.
    Handles subscriptions, usage tracking, and overage billing.
    """

    def __init__(self):
        """Initialize with environment configuration"""
        self.stripe = stripe
        self.stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        # Ensure we're using the correct API version for flexible billing
        self.stripe.api_version = "2025-06-30.basil"

        # Product and Price IDs
        self.product_id = os.getenv("STRIPE_PRODUCT_ID")
        self.price_monthly = os.getenv("STRIPE_STANDARD_MONTHLY_PRICE_ID")
        self.price_annual = os.getenv("STRIPE_STANDARD_YEARLY_PRICE_ID")
        self.price_overage = os.getenv("STRIPE_OVERAGE_PRICE_ID")

        # Meter configuration - CRITICAL: Separate event name from meter ID
        # Event name is used for REPORTING usage (MeterEvent.create)
        # Meter ID is used for READING summaries (Meter.list_event_summaries)
        self.meter_event_name = os.getenv("STRIPE_METER_EVENT_NAME", "tidyframe_token")
        self.meter_id = os.getenv("STRIPE_METER_ID")

        # Billing configuration
        self.monthly_limit = int(os.getenv("MONTHLY_NAME_LIMIT", "100000"))
        self.overage_price = float(os.getenv("OVERAGE_PRICE_PER_UNIT", "0.01"))

        # Webhook secrets for verification (two separate endpoints)
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        self.meter_webhook_secret = os.getenv("STRIPE_BILLING_METER_WEBHOOK_SECRET")

        # Validate critical Stripe configuration
        self._validate_stripe_config()

        logger.info(f"Stripe service initialized with product {self.product_id}")

    def _validate_stripe_config(self):
        """Validate that required Stripe price IDs are configured"""
        missing_ids = []

        if not self.price_monthly:
            missing_ids.append("STRIPE_STANDARD_MONTHLY_PRICE_ID")
        if not self.price_annual:
            missing_ids.append("STRIPE_STANDARD_YEARLY_PRICE_ID")
        if not self.price_overage:
            missing_ids.append("STRIPE_OVERAGE_PRICE_ID")

        if missing_ids:
            logger.warning(
                f"Stripe price IDs not configured: {', '.join(missing_ids)}. "
                "Billing features may not work correctly. Please configure missing Stripe price IDs."
            )

    def get_checkout_urls(self) -> dict:
        """
        Centralized checkout URL generation - single source of truth

        Returns dict with 'success' and 'cancel' URLs for Stripe checkout sessions.
        Validates that localhost is not used in production.
        """
        from app.core.config import settings

        base_url = settings.FRONTEND_URL

        # CRITICAL: Warn if using localhost in production
        if "localhost" in base_url.lower():
            logger.warning(
                "🚨 Using localhost in Stripe checkout URLs",
                frontend_url=base_url,
                environment=settings.ENVIRONMENT,
            )
            if settings.ENVIRONMENT == "production":
                logger.error(
                    "CRITICAL: localhost URLs will break Stripe redirects in production!"
                )

        success_url = f"{base_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{base_url}/payment/cancelled"

        logger.info(
            "Generated checkout URLs",
            success_url=success_url,
            cancel_url=cancel_url,
            environment=settings.ENVIRONMENT,
        )

        return {"success": success_url, "cancel": cancel_url}

    async def create_customer(
        self, email: str, name: str = None, metadata: Dict[str, str] = None
    ) -> str:
        """Create a Stripe customer"""
        try:
            customer = self.stripe.Customer.create(
                email=email, name=name, metadata=metadata or {}
            )
            logger.info(f"Created Stripe customer {customer.id} for {email}")
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create customer: {e}")
            raise

    async def create_subscription(
        self, customer_id: str, price_id: str = None, trial_days: int = 0, payment_required: bool = True
    ) -> Dict[str, Any]:
        """
        Create a subscription with usage-based billing

        Args:
            customer_id: Stripe customer ID
            price_id: Base subscription price ID (defaults to monthly)
            trial_days: Trial period in days
            payment_required: If False, creates incomplete subscription without payment method
                             WARNING: False should only be used for testing/development
        """
        try:
            # Use monthly as default
            if not price_id:
                price_id = self.price_monthly

            # Create subscription with base plan
            items = [{"price": price_id}]

            # Add usage-based overage item (metered billing)
            if self.price_overage:
                items.append(
                    {
                        "price": self.price_overage
                        # No quantity for metered billing - usage reported separately
                    }
                )

            # Configure payment behavior based on whether payment method is required
            subscription_params = {
                "customer": customer_id,
                "items": items,
                "trial_period_days": trial_days,
                "billing_mode": {"type": "flexible"},  # Required for mixed intervals (monthly + metered)
                "metadata": {
                    "monthly_limit": str(self.monthly_limit),
                    "overage_price": str(self.overage_price),
                },
            }

            # TEST ONLY: Allow incomplete subscriptions without payment method
            # WARNING: This creates subscriptions that won't charge until payment method added
            if not payment_required:
                subscription_params["payment_behavior"] = "default_incomplete"

            subscription = self.stripe.Subscription.create(**subscription_params)

            logger.info(
                f"Created subscription {subscription.id} for customer {customer_id}"
            )
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_end": getattr(subscription, "current_period_end", None),
                "items": subscription.items.data,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {e}")
            raise

    async def report_usage(
        self, customer_id: str, quantity: int, timestamp: datetime = None
    ) -> bool:
        """
        Report usage to Stripe Billing Meter using Meter Events API v2
        This properly reports usage for overage billing
        """
        try:
            timestamp = timestamp or datetime.now(timezone.utc)

            # Use Stripe Meter Events API v2 for usage-based billing
            # This reports to the meter configured in Stripe dashboard
            meter_event = self.stripe.v2.billing.MeterEvent.create(
                event_name=self.meter_event_name,  # Event name (e.g., 'tidyframe_token')
                payload={"value": quantity, "stripe_customer_id": customer_id},
                timestamp=int(timestamp.timestamp()),
            )

            logger.info(
                f"Reported {quantity} usage to meter event '{self.meter_event_name}' for customer {customer_id}"
            )
            return True

        except stripe.error.StripeError as e:
            logger.error(f"Failed to report meter usage: {e}")
            return False

    async def get_current_usage(self, customer_id: str) -> Dict[str, Any]:
        """Get current billing period usage from Meter Events API"""
        try:
            # Get active subscription to determine billing period
            subscriptions = self.stripe.Subscription.list(
                customer=customer_id, status="active", limit=1
            )

            if not subscriptions.data:
                logger.warning(f"No active subscription for customer {customer_id}")
                return {"usage": 0, "limit": 0, "overage": 0}

            subscription = subscriptions.data[0]
            period_start = subscription["current_period_start"]
            period_end = subscription["current_period_end"]

            # Get meter ID for reading summaries
            # CRITICAL: This must be the meter ID (mtr_xxx), NOT the event name
            if not self.meter_id or self.meter_id.startswith("mtr_your-") or not self.meter_id.startswith("mtr_"):
                logger.error(
                    "STRIPE_METER_ID not configured or invalid! "
                    f"Current value: {self.meter_id or 'None'}. "
                    "Cannot read meter data from Stripe. Falling back to local database."
                )
                # Fallback to local database count
                return await self._get_usage_from_local_db(customer_id)

            # Read from Meter Events API (correct approach for v2 billing meters)
            try:
                meter_summaries = self.stripe.billing.Meter.list_event_summaries(
                    self.meter_id,  # Use meter ID (mtr_xxx), not event name
                    customer=customer_id,
                    start_time=period_start,
                    end_time=period_end,
                )

                # Aggregate total usage across all summaries
                current_usage = 0
                for summary in meter_summaries.data:
                    current_usage += summary.get("aggregated_value", 0)

                logger.info(
                    f"Meter usage for customer {customer_id}: {current_usage} "
                    f"(period: {period_start}-{period_end})"
                )

            except stripe.error.StripeError as e:
                logger.error(f"Failed to read meter summaries: {e}")
                # Fallback to local database
                return await self._get_usage_from_local_db(customer_id)

            # Calculate overage
            overage = max(0, current_usage - self.monthly_limit)

            return {
                "usage": current_usage,
                "limit": self.monthly_limit,
                "overage": overage,
                "overage_cost": overage * self.overage_price,
                "period_end": period_end,
                "data_source": "stripe_meter",  # For debugging
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to get usage: {e}")
            return await self._get_usage_from_local_db(customer_id)

    async def _get_usage_from_local_db(self, customer_id: str) -> Dict[str, Any]:
        """Fallback: Get usage from local database when Stripe API fails"""
        try:
            from app.core.database import async_session_maker
            from app.models.user import User
            from sqlalchemy import select

            async with async_session_maker() as db:
                stmt = select(User).where(User.stripe_customer_id == customer_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    return {"usage": 0, "limit": 0, "overage": 0}

                current_usage = user.parses_this_month or 0
                overage = max(0, current_usage - user.monthly_limit)

                logger.warning(
                    f"Using local DB fallback for customer {customer_id}: "
                    f"{current_usage} parses"
                )

                return {
                    "usage": current_usage,
                    "limit": user.monthly_limit,
                    "overage": overage,
                    "overage_cost": overage * settings.OVERAGE_PRICE_PER_UNIT,
                    "period_end": None,
                    "data_source": "local_db_fallback",  # For debugging
                }
        except Exception as e:
            logger.error(f"Local DB fallback failed: {e}")
            return {"usage": 0, "limit": 0, "overage": 0}

    async def create_checkout_session(
        self,
        customer_id: str,
        price_id: str = None,
        success_url: str = None,
        cancel_url: str = None,
        metadata: Dict[str, str] = None,
    ) -> str:
        """Create checkout session for new subscriptions"""
        try:
            price_id = price_id or self.price_monthly

            # Use centralized URL generation if not explicitly provided
            if not success_url or not cancel_url:
                urls = self.get_checkout_urls()
                success_url = success_url or urls["success"]
                cancel_url = cancel_url or urls["cancel"]

            # Build line items - include base subscription + overage metered pricing
            line_items = [
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ]

            # NOTE: Overage price is NOT added here to avoid billing interval conflicts
            # (recurring base + metered overage = Stripe error: "Checkout does not support
            # multiple prices with different billing intervals"). Instead, overage price is
            # added in _handle_subscription_created webhook after subscription is created.

            session = self.stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="subscription",
                customer=customer_id,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {"product": "tidyframe_standard"},
            )

            logger.info(
                f"Created checkout session {session.id} with URLs success={success_url}, cancel={cancel_url}"
            )
            return session.url

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise

    async def create_portal_session(self, customer_id: str, return_url: str) -> str:
        """Create Stripe customer portal session"""
        try:
            session = self.stripe.billing_portal.Session.create(
                customer=customer_id, return_url=return_url
            )

            logger.info(
                f"Created portal session {session.id} for customer {customer_id}"
            )
            return session.url

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            raise

    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription details"""
        try:
            subscription = self.stripe.Subscription.retrieve(subscription_id)

            return {
                "id": subscription.id,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "items": subscription['items']['data'],
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to get subscription: {e}")
            raise

    async def get_customer_invoices(
        self, customer_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get customer invoices"""
        try:
            invoices = self.stripe.Invoice.list(customer=customer_id, limit=limit)

            return [
                {
                    "id": invoice.id,
                    "number": invoice.number,
                    "status": invoice.status,
                    "amount_paid": invoice.amount_paid,
                    "amount_due": invoice.amount_due,
                    "currency": invoice.currency,
                    "created": invoice.created,
                    "invoice_pdf": invoice.invoice_pdf,
                    "hosted_invoice_url": invoice.hosted_invoice_url,
                }
                for invoice in invoices.data
            ]

        except stripe.error.StripeError as e:
            logger.error(f"Failed to get customer invoices: {e}")
            raise

    async def cancel_subscription(
        self, subscription_id: str, at_period_end: bool = True
    ) -> Dict[str, Any]:
        """Cancel a subscription"""
        try:
            if not at_period_end:
                # Cancel immediately
                subscription = self.stripe.Subscription.delete(subscription_id)
            else:
                # Cancel at period end
                subscription = self.stripe.Subscription.modify(
                    subscription_id, cancel_at_period_end=True
                )

            logger.info(f"Cancelled subscription {subscription_id}")
            return {
                "success": True,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "status": subscription.status,
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise

    async def update_subscription(
        self, subscription_id: str, new_price_id: str
    ) -> Dict[str, Any]:
        """Update subscription plan (monthly to annual or vice versa)"""
        try:
            subscription = self.stripe.Subscription.retrieve(subscription_id)

            # Update the subscription item with new price
            self.stripe.Subscription.modify(
                subscription_id,
                items=[
                    {
                        "id": subscription["items"]["data"][0]["id"],
                        "price": new_price_id,
                    }
                ],
                proration_behavior="create_prorations",
            )

            logger.info(
                f"Updated subscription {subscription_id} to price {new_price_id}"
            )
            return {"success": True, "new_price": new_price_id}

        except stripe.error.StripeError as e:
            logger.error(f"Failed to update subscription: {e}")
            raise

    def construct_webhook_event(
        self, payload: bytes, signature: str, webhook_type: str = "main"
    ):
        """Construct and verify webhook event

        Args:
            payload: Raw webhook payload
            signature: Stripe signature header
            webhook_type: 'main' or 'meter' to determine which secret to use
        """
        try:
            # Use appropriate secret based on webhook type
            if webhook_type == "meter":
                secret = (
                    self.meter_webhook_secret
                    or settings.STRIPE_BILLING_METER_WEBHOOK_SECRET
                )
            else:
                secret = self.webhook_secret

            event = stripe.Webhook.construct_event(payload, signature, secret)
            return event
        except ValueError:
            logger.error("Invalid webhook payload")
            raise
        except stripe.error.SignatureVerificationError:
            logger.error(f"Invalid {webhook_type} webhook signature")
            raise

    def verify_webhook_signature(
        self, payload: bytes, signature: str, is_meter_event: bool = False
    ) -> bool:
        """Verify webhook signature for security (legacy method)

        Args:
            payload: Raw webhook payload
            signature: Stripe signature header
            is_meter_event: True for meter events, False for general events
        """
        try:
            webhook_type = "meter" if is_meter_event else "main"
            self.construct_webhook_event(payload, signature, webhook_type)
            return True
        except BaseException:
            return False

    async def handle_webhook_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process webhook events"""
        event_type = event.get("type")

        handlers = {
            # Checkout events
            "checkout.session.completed": self._handle_checkout_completed,
            "checkout.session.async_payment_succeeded": self._handle_checkout_completed,
            "checkout.session.async_payment_failed": self._handle_checkout_failed,
            "checkout.session.expired": self._handle_checkout_expired,
            # Subscription events
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            # Invoice events
            "invoice.created": self._handle_invoice_created,
            "invoice.payment_succeeded": self._handle_payment_succeeded,
            "invoice.payment_failed": self._handle_payment_failed,
            "invoice.payment_action_required": self._handle_payment_action_required,
        }

        handler = handlers.get(event_type)
        if handler:
            return await handler(event)

        logger.info(f"Unhandled webhook event type: {event_type}")
        return {"status": "unhandled"}

    async def _handle_checkout_completed(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful checkout"""
        session = event["data"]["object"]
        customer_id = session["customer"]
        subscription_id = session["subscription"]

        logger.info(
            f"Checkout completed for customer {customer_id}, subscription {subscription_id}"
        )

        return {
            "status": "processed",
            "customer_id": customer_id,
            "subscription_id": subscription_id,
        }

    async def _handle_subscription_created(
        self, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle new subscription creation - add overage price after creation"""
        subscription = event["data"]["object"]
        subscription_id = subscription["id"]

        logger.info(f"Subscription created: {subscription_id}")

        # Add overage price to subscription if not already present
        # NOTE: Checkout flow creates base only, direct creation adds base + overage
        # This handler safely adds overage only if missing (prevents duplicates)
        if self.price_overage:
            try:
                # Check if overage price already exists in subscription items
                existing_items = subscription.get("items", {}).get("data", [])
                has_overage = any(
                    item.get("price", {}).get("id") == self.price_overage
                    for item in existing_items
                )

                if has_overage:
                    logger.info(
                        f"Subscription {subscription_id} already has overage price - skipping"
                    )
                else:
                    # Add overage price only if missing
                    self.stripe.SubscriptionItem.create(
                        subscription=subscription_id,
                        price=self.price_overage,
                    )
                    logger.info(
                        f"Added overage price {self.price_overage} to subscription {subscription_id}"
                    )
            except stripe.error.StripeError as e:
                logger.error(
                    f"Failed to add overage price to subscription {subscription_id}: {e}"
                )
                # Don't fail the webhook - subscription still created successfully

        return {"status": "processed", "subscription_id": subscription_id}

    async def _handle_subscription_updated(
        self, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle subscription updates"""
        subscription = event["data"]["object"]
        logger.info(f"Subscription updated: {subscription['id']}")
        return {"status": "processed", "subscription_id": subscription["id"]}

    async def _handle_subscription_deleted(
        self, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle subscription cancellation"""
        subscription = event["data"]["object"]
        logger.info(f"Subscription cancelled: {subscription['id']}")
        return {"status": "processed", "subscription_id": subscription["id"]}

    async def _handle_payment_succeeded(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful payment"""
        invoice = event["data"]["object"]
        logger.info(f"Payment succeeded for invoice {invoice['id']}")
        return {"status": "processed", "invoice_id": invoice["id"]}

    async def _handle_payment_failed(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment"""
        invoice = event["data"]["object"]
        logger.error(f"Payment failed for invoice {invoice['id']}")
        return {"status": "processed", "invoice_id": invoice["id"]}

    async def _handle_checkout_failed(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed checkout (async payment)"""
        session = event["data"]["object"]
        logger.error(f"Checkout payment failed for session {session['id']}")
        return {"status": "processed", "session_id": session["id"]}

    async def _handle_checkout_expired(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle expired checkout session"""
        session = event["data"]["object"]
        logger.info(f"Checkout session expired: {session['id']}")
        return {"status": "processed", "session_id": session["id"]}

    async def _handle_invoice_created(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle invoice creation"""
        invoice = event["data"]["object"]
        logger.info(
            f"Invoice created: {invoice['id']} for ${invoice['amount_due'] / 100:.2f}"
        )
        return {"status": "processed", "invoice_id": invoice["id"]}

    async def _handle_payment_action_required(
        self, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle payment requiring additional action"""
        invoice = event["data"]["object"]
        logger.warning(f"Payment action required for invoice {invoice['id']}")
        return {
            "status": "processed",
            "invoice_id": invoice["id"],
            "action_required": True,
        }


class UsageMeteringService:
    """
    Service for tracking and reporting usage to Stripe
    This is the CRITICAL component for overage billing
    """

    def __init__(self, stripe_service: StripeService):
        self.stripe_service = stripe_service
        self.usage_queue = []  # In production, use Redis or similar
        self.batch_size = 100
        self.report_interval = 300  # Report every 5 minutes

    async def track_usage(
        self, user_id: str, customer_id: str, quantity: int, is_admin: bool = False
    ) -> bool:
        """Track usage event for billing"""

        # Admin bypass - don't track usage
        if is_admin:
            logger.info(f"Admin user {user_id} - usage not tracked")
            return True

        # Add to queue for batch reporting
        self.usage_queue.append(
            {
                "customer_id": customer_id,
                "quantity": quantity,
                "timestamp": datetime.now(timezone.utc),
                "user_id": user_id,
            }
        )

        # Report if batch size reached
        if len(self.usage_queue) >= self.batch_size:
            await self.report_batch()

        return True

    async def report_batch(self) -> int:
        """Report batched usage to Stripe"""
        if not self.usage_queue:
            return 0

        # Group by customer
        customer_usage = {}
        for event in self.usage_queue:
            customer_id = event["customer_id"]
            if customer_id not in customer_usage:
                customer_usage[customer_id] = 0
            customer_usage[customer_id] += event["quantity"]

        # Report to Stripe
        reported = 0
        for customer_id, total_quantity in customer_usage.items():
            success = await self.stripe_service.report_usage(
                customer_id, total_quantity
            )
            if success:
                reported += 1

        # Clear queue
        self.usage_queue.clear()

        logger.info(f"Reported usage for {reported} customers")
        return reported

    async def start_background_reporting(self):
        """Start background task for periodic usage reporting"""
        while True:
            await asyncio.sleep(self.report_interval)
            await self.report_batch()


class BillingEnforcementService:
    """
    Service for enforcing billing limits and managing access
    """

    def __init__(self, stripe_service: StripeService):
        self.stripe_service = stripe_service

    async def check_access(
        self, user_id: str, customer_id: str, is_admin: bool = False
    ) -> Dict[str, Any]:
        """Check if user has access based on billing status"""

        # Admin bypass
        if is_admin:
            return {
                "has_access": True,
                "reason": "admin_bypass",
                "usage": 0,
                "limit": float("inf"),
            }

        # Check subscription status
        if not customer_id:
            return {
                "has_access": False,
                "reason": "no_subscription",
                "redirect_url": await self._get_checkout_url(user_id),
            }

        # Get current usage
        usage_data = await self.stripe_service.get_current_usage(customer_id)

        # For standard plan, always allow but track overage
        return {
            "has_access": True,
            "usage": usage_data["usage"],
            "limit": usage_data["limit"],
            "overage": usage_data["overage"],
            "overage_cost": usage_data.get("overage_cost", 0),
        }

    async def _get_checkout_url(self, user_id: str) -> str:
        """Get checkout URL for user"""
        # In production, get user email from database
        return "https://tidyframe.com/subscribe"


# Singleton instances
_stripe_service = None
_usage_service = None
_billing_service = None


def get_stripe_service() -> StripeService:
    """Get singleton Stripe service instance"""
    global _stripe_service
    if not _stripe_service:
        _stripe_service = StripeService()
    return _stripe_service


def get_usage_service() -> UsageMeteringService:
    """Get singleton usage metering service"""
    global _usage_service
    if not _usage_service:
        _usage_service = UsageMeteringService(get_stripe_service())
    return _usage_service


def get_billing_service() -> BillingEnforcementService:
    """Get singleton billing enforcement service"""
    global _billing_service
    if not _billing_service:
        _billing_service = BillingEnforcementService(get_stripe_service())
    return _billing_service
