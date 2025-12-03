"""
FastAPI dependency functions for authentication and database access
"""

from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import check_rate_limit
from app.core.security import verify_api_key, verify_token
from app.models.api_key import APIKey
from app.models.user import User
from app.utils.client_ip import get_client_ip

logger = structlog.get_logger()

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current authenticated user from JWT token or API key

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        User object or None if not authenticated

    Raises:
        HTTPException: If token is invalid
    """

    if not credentials:
        logger.debug("No credentials provided in request")
        return None

    token = credentials.credentials

    if not token:
        logger.debug("Empty token in credentials")
        return None

    # First try JWT token
    payload = verify_token(token)
    if payload:
        user_id = payload.get("sub")
        if user_id:
            result = await db.execute(
                select(User).where(User.id == user_id, User.is_active)
            )
            user = result.scalar_one_or_none()

            if user and not user.is_account_locked():
                logger.debug(
                    f"Authenticated user: {user.email}, is_admin: {user.is_admin}"
                )
                return user
            elif user:
                logger.warning(f"User {user.email} account is locked")
        else:
            logger.debug("No user_id in JWT payload")

    # Then try API key
    if token.startswith("tf_"):
        result = await db.execute(
            select(APIKey).join(User).where(APIKey.is_active, User.is_active)
        )

        for api_key in result.scalars():
            if verify_api_key(token, api_key.key_hash):
                if api_key.can_use():
                    # Update usage statistics
                    api_key.usage_count += 1
                    api_key.last_used_at = datetime.now(timezone.utc)
                    await db.commit()

                    return api_key.user

    return None


async def require_auth(
    current_user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Require authentication - raises exception if not authenticated

    Args:
        current_user: Current user from get_current_user

    Returns:
        User object

    Raises:
        HTTPException: If user is not authenticated
    """

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return current_user


async def require_premium_user(current_user: User = Depends(require_auth)) -> User:
    """
    Require premium (paid) user

    Args:
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        HTTPException: If user doesn't have premium access
    """

    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required",
        )

    return current_user


async def require_enterprise_user(current_user: User = Depends(require_auth)) -> User:
    """
    Require enterprise user

    Args:
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        HTTPException: If user doesn't have enterprise access
    """

    from app.models.user import PlanType

    if current_user.plan != PlanType.ENTERPRISE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enterprise subscription required",
        )

    return current_user


async def check_user_rate_limit(
    request: Request, current_user: Optional[User] = Depends(get_current_user)
) -> None:
    """
    Check rate limiting for API requests

    Args:
        request: FastAPI request object
        current_user: Current user (if authenticated)

    Raises:
        HTTPException: If rate limit exceeded
    """

    # Determine rate limit based on user status
    if current_user:
        identifier = f"user:{current_user.id}"
        limit = settings.API_RATE_LIMIT_PER_MINUTE
    else:
        # Use IP for anonymous users
        client_ip = get_client_ip(request)
        identifier = f"ip:{client_ip}"
        limit = settings.RATE_LIMIT_PER_MINUTE

    # Check rate limit
    allowed, current_count = await check_rate_limit(identifier, limit)

    if not allowed:
        logger.warning(
            "rate_limit_exceeded",
            identifier=identifier,
            current_count=current_count,
            limit=limit,
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "60"},
        )


async def get_anonymous_or_user(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[Optional[User], Optional[str]]:
    """
    Get current user or IP for anonymous access
    Used for endpoints that support both authenticated and anonymous access

    Args:
        request: FastAPI request object
        current_user: Current user (if authenticated)
        db: Database session

    Returns:
        Tuple of (user, ip_address)
    """

    if current_user:
        return current_user, None
    else:
        # Anonymous user - track by IP (reads X-Forwarded-For from nginx)
        client_ip = get_client_ip(request)
        return None, client_ip


async def check_parsing_quota(
    current_user: Optional[User],
    client_ip: Optional[str],
    rows_to_parse: int,
    db: AsyncSession = Depends(get_db),
) -> bool:
    """
    Check if user/IP has remaining parsing quota

    Args:
        current_user: Authenticated user or None
        client_ip: Client IP address for anonymous users
        rows_to_parse: Number of rows to be parsed
        db: Database session

    Returns:
        True if quota is available

    Raises:
        HTTPException: If quota exceeded
    """

    if current_user:
        # Check authenticated user quota
        if not current_user.can_parse(rows_to_parse):
            remaining = max(
                0, current_user.monthly_limit - current_user.parses_this_month
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Monthly parse limit exceeded. Remaining: {remaining} parses. Upgrade your plan for more capacity.",
            )

        return True

    elif client_ip:
        # Check anonymous user quota
        from app.models.anonymous_usage import AnonymousUsage

        result = await db.execute(
            select(AnonymousUsage).where(AnonymousUsage.ip_address == client_ip)
        )

        anonymous_usage = result.scalar_one_or_none()

        if anonymous_usage:
            if not anonymous_usage.can_parse(rows_to_parse):
                remaining = max(
                    0, settings.ANONYMOUS_LIFETIME_LIMIT - anonymous_usage.parse_count
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Anonymous usage limit exceeded. Remaining: {remaining} parses. Please sign up for more capacity.",
                )
        else:
            # First time anonymous user - check if within limit
            if rows_to_parse > settings.ANONYMOUS_LIFETIME_LIMIT:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"File too large for anonymous usage. Maximum: {settings.ANONYMOUS_LIFETIME_LIMIT} parses. Please sign up for more capacity.",
                )

            # Create AnonymousUsage record for tracking
            new_anon_user = AnonymousUsage(
                ip_address=client_ip,
                parse_count=0,  # Will be incremented after processing completes
            )
            db.add(new_anon_user)
            await db.flush()  # Ensure record exists before job processing starts

            logger.info(
                "anonymous_user_initialized",
                ip=client_ip,
                initial_parse_count=0,
                lifetime_limit=settings.ANONYMOUS_LIFETIME_LIMIT,
            )

        return True

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to identify user or IP address",
        )


# Admin-only dependency
async def require_admin_user(current_user: User = Depends(require_auth)) -> User:
    """
    Require admin user (for admin endpoints)

    Args:
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        HTTPException: If user is not admin
    """

    # Check the proper is_admin column
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    return current_user
