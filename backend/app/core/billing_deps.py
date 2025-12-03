"""
Billing Dependencies for Enforcing Payment Requirements
Gilfoyle-approved: No free rides
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.stripe_service import get_billing_service

logger = logging.getLogger(__name__)


async def require_subscription(
    current_user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    SECURITY-ENHANCED: Enforce subscription requirement for API access.
    This is the CRITICAL dependency that prevents free access.
    """

    # SECURITY: Strict authentication requirement
    if not current_user:
        logger.warning("Unauthorized access attempt - no authenticated user")
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # SECURITY: Verify account is active and email verified
    if not current_user.is_active:
        logger.warning(f"Inactive account access attempt: {current_user.email}")
        raise HTTPException(
            status_code=403, detail="Account is inactive. Please contact support."
        )

    # Email verification temporarily disabled for MVP testing
    # if not current_user.email_verified:
    #     logger.warning(f"Unverified email access attempt: {current_user.email}")
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Email verification required. Please verify your email before using the service."
    #     )

    # SECURITY: Check for account locks
    if current_user.is_account_locked():
        logger.warning(f"Locked account access attempt: {current_user.email}")
        raise HTTPException(
            status_code=423,  # Locked
            detail="Account is temporarily locked due to security concerns. Please contact support.",
        )

    # Admin bypass - but still log for audit
    if current_user.is_admin:
        logger.info(
            f"Admin user {current_user.email} bypassed billing check",
            user_id=current_user.id,
            admin_bypass=True,
        )
        return current_user

    # SECURITY: Verify Stripe customer exists
    if not current_user.stripe_customer_id:
        logger.warning(f"User {current_user.email} missing Stripe customer ID")
        raise HTTPException(
            status_code=402,  # Payment Required
            detail={
                "error": "Payment setup required",
                "message": "Your payment information needs to be configured",
                "checkout_url": "/api/billing/checkout",
                "action_required": "setup_payment",
            },
        )

    # SECURITY: Check if user has active subscription ID
    if not current_user.stripe_subscription_id:
        logger.warning(
            f"User {current_user.email} attempted access without subscription",
            user_id=current_user.id,
            stripe_customer_id=current_user.stripe_customer_id,
        )
        raise HTTPException(
            status_code=402,  # Payment Required
            detail={
                "error": "Subscription required",
                "message": "You must have an active subscription to use this service",
                "checkout_url": "/api/billing/checkout",
                "action_required": "subscribe",
            },
        )

    # SECURITY: Verify subscription is actually active with Stripe
    try:
        billing_service = get_billing_service()
        access_check = await billing_service.check_access(
            user_id=str(current_user.id),
            customer_id=current_user.stripe_customer_id,
            is_admin=current_user.is_admin,
        )

        if not access_check["has_access"]:
            reason = access_check.get("reason", "Your subscription is not active")
            logger.warning(
                f"User {current_user.email} subscription access denied: {reason}",
                user_id=current_user.id,
                subscription_id=current_user.stripe_subscription_id,
                access_check=access_check,
            )
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Subscription not active",
                    "message": reason,
                    "checkout_url": access_check.get(
                        "redirect_url", "/api/billing/checkout"
                    ),
                    "action_required": "renew_subscription",
                },
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log unexpected errors but deny access
        logger.error(
            f"Billing service error for user {current_user.email}: {str(e)}",
            user_id=current_user.id,
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="Billing verification temporarily unavailable. Please try again later.",
        )

    # Success - log for audit trail
    logger.info(
        f"User {current_user.email} subscription validated successfully",
        user_id=current_user.id,
        subscription_id=current_user.stripe_subscription_id,
    )

    return current_user


async def check_usage_limits(
    current_user: User = Depends(require_subscription),
) -> User:
    """
    Check if user has remaining usage within their limits.
    Returns user if they can proceed, raises 402 if over limit.
    """

    # Admin bypass
    if current_user.is_admin:
        return current_user

    # Check usage vs limits
    billing_service = get_billing_service()

    if current_user.stripe_customer_id:
        usage_data = await billing_service.stripe_service.get_current_usage(
            current_user.stripe_customer_id
        )

        # Log usage for monitoring
        logger.info(
            f"User {current_user.email} usage: {usage_data['usage']}/{usage_data['limit']} "
            f"(overage: {usage_data['overage']})"
        )

        # We allow overage but track it for billing
        # If you want to hard-stop at limit, uncomment this:
        # if usage_data['usage'] >= usage_data['limit']:
        #     raise HTTPException(
        #         status_code=402,
        #         detail={
        #             "error": "Usage limit exceeded",
        #             "message": f"You have reached your monthly limit of {usage_data['limit']} names",
        #             "usage": usage_data['usage'],
        #             "limit": usage_data['limit'],
        #             "overage_cost": usage_data.get('overage_cost', 0)
        #         }
        #     )

    return current_user


# Alias for clarity
require_premium_user = require_subscription
require_paid_user = require_subscription
