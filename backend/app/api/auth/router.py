"""
Authentication API routes
"""

import ipaddress
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.schemas import (
    ChangePassword,
    EmailVerify,
    GoogleAuthURL,
    GoogleCallback,
    PasswordReset,
    PasswordResetConfirm,
    RefreshToken,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import check_user_rate_limit, require_auth
from app.core.security import (
    create_user_tokens,
    generate_reset_token,
    generate_verification_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.user import PlanType, User
from app.services.google_oauth import GoogleOAuthService
from app.utils.client_ip import get_client_ip
from app.workers.email_sender import (
    send_email_verification,
    send_password_reset,
    send_welcome_email,
)

logger = structlog.get_logger()

router = APIRouter()


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_user_rate_limit),
):
    """Register a new user account with legal compliance tracking"""

    # CRITICAL LEGAL COMPLIANCE - Check if user already exists
    existing_user = await db.execute(select(User).where(User.email == user_data.email))

    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # CRITICAL LEGAL VALIDATION - Ensure all consents are provided
    if not user_data.consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Legal consent data is required for registration",
        )

    # GEOGRAPHIC RESTRICTION ENFORCEMENT - US-only service per Terms of Service
    if not user_data.consent.location_confirmed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This service is only available to users located in the United States",
        )

    # AGE VERIFICATION ENFORCEMENT - 18+ requirement per Terms of Service
    if not user_data.consent.age_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users must be at least 18 years old to create an account",
        )

    # MANDATORY ARBITRATION ENFORCEMENT - Required per Terms of Service
    if not user_data.consent.arbitration_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must acknowledge the mandatory arbitration clause to create an account",
        )

    # TERMS AND PRIVACY ACCEPTANCE - Required for legal compliance
    if not user_data.consent.terms_accepted or not user_data.consent.privacy_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must accept both the Terms of Service and Privacy Policy to create an account",
        )

    # Extract client IP address for legal compliance (reads X-Forwarded-For from nginx)
    client_ip = None
    client_ip_str = get_client_ip(request)
    if client_ip_str:
        try:
            client_ip = ipaddress.ip_address(client_ip_str)
        except ValueError:
            logger.warning("Invalid client IP", ip=client_ip_str)

    # Create user
    hashed_password = get_password_hash(user_data.password)
    verification_token = generate_verification_token()
    current_time = datetime.now(timezone.utc)

    user = User(
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        company_name=user_data.company_name,
        plan=PlanType.FREE,
        email_verification_token=verification_token,
        email_verification_sent_at=current_time,
        email_verified=True,  # Auto-verify for now (email verification disabled)
    )

    # Add legal compliance data if provided
    if user_data.consent:
        if user_data.consent.age_verified:
            user.age_verified_at = current_time
        if user_data.consent.terms_accepted:
            user.terms_accepted_at = current_time
        if user_data.consent.privacy_accepted:
            user.privacy_accepted_at = current_time
        if user_data.consent.arbitration_acknowledged:
            user.arbitration_acknowledged_at = current_time
        if user_data.consent.location_confirmed:
            user.location_confirmed_at = current_time

        # Store consent evidence
        user.consent_ip_address = client_ip
        user.consent_user_agent = user_data.consent.user_agent

        # Log critical legal compliance for audit trail
        logger.info(
            "legal_consent_recorded",
            user_id=user.id,
            email=user.email,
            age_verified=user_data.consent.age_verified,
            terms_accepted=user_data.consent.terms_accepted,
            privacy_accepted=user_data.consent.privacy_accepted,
            arbitration_acknowledged=user_data.consent.arbitration_acknowledged,
            location_confirmed=user_data.consent.location_confirmed,
            consent_ip=str(client_ip) if client_ip else None,
            consent_timestamp=user_data.consent.consent_timestamp,
        )
    else:
        logger.warning(
            "registration_without_consent",
            user_id=user.id,
            email=user.email,
            message="User registered without providing legal consent data - COMPLIANCE RISK",
        )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send welcome and verification emails
    send_welcome_email.delay(user.email, user.full_name)
    send_email_verification.delay(user.email, user.full_name, verification_token)

    # Create Stripe customer and checkout session for immediate payment
    checkout_url = None
    try:
        from app.services.stripe_service import StripeService

        stripe_service = StripeService()

        # Create Stripe customer if not exists
        if not user.stripe_customer_id:
            customer_id = await stripe_service.create_customer(
                email=user.email, name=user.full_name
            )
            user.stripe_customer_id = customer_id
            await db.commit()

        # Create checkout session for standard plan (monthly or yearly based on user selection)
        billing_period = getattr(user_data.consent, "billing_period", "monthly")
        price_id = (
            settings.STRIPE_STANDARD_YEARLY_PRICE_ID
            if billing_period == "yearly"
            else settings.STRIPE_STANDARD_MONTHLY_PRICE_ID
        )
        if price_id:
            # Use centralized URL generation from stripe_service (no need to pass URLs)
            checkout_url = await stripe_service.create_checkout_session(
                customer_id=user.stripe_customer_id,
                price_id=price_id,
                metadata={"user_id": str(user.id), "plan": "STANDARD"},
            )
    except Exception as e:
        logger.error(
            "checkout_session_creation_failed_on_registration",
            user_id=user.id,
            error=str(e),
        )
        # Don't fail registration if checkout creation fails

    # Create tokens (including is_admin claim)
    tokens = create_user_tokens(str(user.id), user.email, user.is_admin)

    logger.info(
        "user_registered",
        user_id=user.id,
        email=user.email,
        legal_compliance=(
            user.is_legally_compliant()
            if hasattr(user, "is_legally_compliant")
            else False
        ),
    )

    response = TokenResponse(
        **tokens,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )

    # Add checkout URL to response for frontend redirect
    if checkout_url:
        response_dict = response.dict()
        response_dict["checkout_url"] = checkout_url
        response_dict["requires_payment"] = True
        response_dict["message"] = (
            "Registration successful! Please complete payment to access all features."
        )
        return response_dict

    return response


@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_user_rate_limit),
):
    """Login user with email and password"""

    # Find user
    result = await db.execute(select(User).where(User.email == user_credentials.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Check if account is locked
    if user.is_account_locked():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked due to too many failed login attempts. Try again later.",
        )

    # Verify password
    if not user.password_hash or not verify_password(
        user_credentials.password, user.password_hash
    ):
        # Increment failed attempts
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.LOCKOUT_DURATION_MINUTES
            )
            logger.warning("account_locked", user_id=user.id, email=user.email)

        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
        )

    # Reset failed login attempts and update last login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)

    await db.commit()

    # Create tokens (including is_admin claim)
    tokens = create_user_tokens(str(user.id), user.email, user.is_admin)

    logger.info("user_logged_in", user_id=user.id, email=user.email)

    # Check subscription status for non-admin users
    requires_subscription = False
    checkout_url = None

    if not user.is_admin and not user.stripe_subscription_id:
        requires_subscription = True
        checkout_url = "/api/billing/checkout"
        logger.warning(f"User {user.email} logged in without subscription")

    response = TokenResponse(
        **tokens,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )

    # Add subscription requirement to response
    if requires_subscription:
        response_dict = response.dict()
        response_dict["requires_subscription"] = True
        response_dict["checkout_url"] = checkout_url
        response_dict["message"] = "Please subscribe to access file processing features"
        return response_dict

    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    refresh_data: RefreshToken, db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""

    # Verify refresh token
    payload = verify_token(refresh_data.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    # Find user
    result = await db.execute(select(User).where(User.id == user_id, User.is_active))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens (including is_admin claim)
    tokens = create_user_tokens(str(user.id), user.email, user.is_admin)

    return TokenResponse(
        **tokens,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
async def logout_user(current_user: User = Depends(require_auth)):
    """Logout user (client should discard tokens)"""

    logger.info("user_logged_out", user_id=current_user.id, email=current_user.email)

    return {"message": "Successfully logged out"}


@router.post("/verify-email")
async def verify_email(
    verification_data: EmailVerify, db: AsyncSession = Depends(get_db)
):
    """Verify user email address"""

    # Find user by verification token
    result = await db.execute(
        select(User).where(User.email_verification_token == verification_data.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
        )

    # Check if token is expired
    if user.email_verification_sent_at:
        expires_at = user.email_verification_sent_at + timedelta(
            hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS
        )
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token has expired",
            )

    # Verify email
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_sent_at = None

    await db.commit()

    logger.info("email_verified", user_id=user.id, email=user.email)

    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification_email(
    current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)
):
    """Resend email verification"""

    if current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified"
        )

    # Generate new verification token
    verification_token = generate_verification_token()
    current_user.email_verification_token = verification_token
    current_user.email_verification_sent_at = datetime.now(timezone.utc)

    await db.commit()

    # Send verification email
    send_email_verification.delay(
        current_user.email, current_user.full_name, verification_token
    )

    return {"message": "Verification email sent"}


@router.post("/reset-password")
async def request_password_reset(
    reset_data: PasswordReset,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_user_rate_limit),
):
    """Request password reset"""

    # Find user
    result = await db.execute(select(User).where(User.email == reset_data.email))
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if not user:
        return {"message": "If the email exists, a reset link has been sent"}

    # Generate reset token
    reset_token = generate_reset_token()
    user.password_reset_token = reset_token
    user.password_reset_sent_at = datetime.now(timezone.utc)

    await db.commit()

    # Send reset email
    send_password_reset.delay(user.email, user.full_name, reset_token)

    logger.info("password_reset_requested", user_id=user.id, email=user.email)

    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm, db: AsyncSession = Depends(get_db)
):
    """Confirm password reset with token"""

    # Find user by reset token
    result = await db.execute(
        select(User).where(User.password_reset_token == reset_data.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token"
        )

    # Check if token is expired
    if user.password_reset_sent_at:
        expires_at = user.password_reset_sent_at + timedelta(
            hours=settings.PASSWORD_RESET_EXPIRE_HOURS
        )
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired",
            )

    # Update password
    user.password_hash = get_password_hash(reset_data.password)
    user.password_reset_token = None
    user.password_reset_sent_at = None

    # Reset failed login attempts
    user.failed_login_attempts = 0
    user.locked_until = None

    await db.commit()

    logger.info("password_reset_completed", user_id=user.id, email=user.email)

    return {"message": "Password reset successfully"}


@router.post("/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Change user password"""

    # Verify current password
    if not current_user.password_hash or not verify_password(
        password_data.current_password, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.password_hash = get_password_hash(password_data.new_password)
    await db.commit()

    logger.info("password_changed", user_id=current_user.id, email=current_user.email)

    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(require_auth)):
    """Get current user information"""
    return UserResponse.model_validate(current_user)


# Google OAuth endpoints
@router.get("/google", response_model=GoogleAuthURL)
async def google_auth_url(request: Request):
    """Get Google OAuth authorization URL"""

    oauth_service = GoogleOAuthService()
    auth_url, state = oauth_service.get_authorization_url()

    return GoogleAuthURL(auth_url=auth_url, state=state)


@router.post("/google/callback", response_model=TokenResponse)
async def google_callback(
    callback_data: GoogleCallback, db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback"""

    oauth_service = GoogleOAuthService()

    try:
        # Exchange code for user info
        user_info = await oauth_service.exchange_code_for_token(
            callback_data.code, callback_data.state
        )

        # Find or create user
        result = await db.execute(select(User).where(User.google_id == user_info["id"]))
        user = result.scalar_one_or_none()

        if not user:
            # Check if user exists with same email
            result = await db.execute(
                select(User).where(User.email == user_info["email"])
            )
            user = result.scalar_one_or_none()

            if user:
                # Link Google account to existing user
                user.google_id = user_info["id"]
            else:
                # Create new user
                user = User(
                    email=user_info["email"],
                    google_id=user_info["id"],
                    first_name=user_info.get("given_name"),
                    last_name=user_info.get("family_name"),
                    plan=PlanType.FREE,
                    email_verified=True,  # Google emails are pre-verified
                    last_login_at=datetime.now(timezone.utc),
                )
                db.add(user)
        else:
            # Update last login
            user.last_login_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(user)

        # Create tokens (including is_admin claim)
        tokens = create_user_tokens(str(user.id), user.email, user.is_admin)

        logger.info("google_oauth_login", user_id=user.id, email=user.email)

        return TokenResponse(
            **tokens,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )

    except Exception as e:
        logger.error("google_oauth_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google authentication failed",
        )
