"""
Site Password API Router
Handles authentication and status checking for site password protection
"""

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.utils.client_ip import get_client_ip

from .schemas import (
    SitePasswordRequest,
    SitePasswordResponse,
    SitePasswordStatusResponse,
)

logger = structlog.get_logger()

router = APIRouter()


def get_site_password_middleware(request: Request):
    """Get the site password middleware instance from the app"""
    # Look for the middleware in the app's middleware stack
    for middleware in request.app.middleware_stack:
        if (
            hasattr(middleware, "cls")
            and middleware.cls.__name__ == "SitePasswordMiddleware"
        ):
            return middleware.kwargs.get("middleware_instance") or middleware.kwargs
        # Handle the case where middleware is wrapped
        if hasattr(middleware, "app") and hasattr(middleware.app, "enabled"):
            return middleware.app
    return None


@router.options("/authenticate")
async def authenticate_options():
    """Handle OPTIONS request for CORS preflight"""
    logger.info("OPTIONS request received for /authenticate")
    return JSONResponse(content={})


@router.options("/status")
async def status_options():
    """Handle OPTIONS request for CORS preflight"""
    return JSONResponse(content={})


@router.get("/status", response_model=SitePasswordStatusResponse)
async def get_site_password_status(request: Request):
    """
    Get the current site password protection status

    Returns:
    - enabled: Whether site password protection is enabled
    - authenticated: Whether the current session is authenticated
    """

    # Check if site password is enabled
    enabled = getattr(settings, "ENABLE_SITE_PASSWORD", False)

    if not enabled:
        return SitePasswordStatusResponse(
            enabled=False,
            authenticated=True,  # If disabled, consider everyone authenticated
        )

    # Check if user is authenticated via cookie
    auth_cookie = request.cookies.get("site_password_authenticated")
    authenticated = bool(auth_cookie)  # Simple check for now

    logger.info(
        "site_password_status_check",
        enabled=enabled,
        authenticated=authenticated,
        client_ip=get_client_ip(request),
    )

    return SitePasswordStatusResponse(enabled=enabled, authenticated=authenticated)


@router.post("/authenticate", response_model=SitePasswordResponse)
async def authenticate_site_password(
    password_request: SitePasswordRequest, request: Request
):
    """
    Authenticate with site password

    Sets authentication cookie on successful authentication
    """

    # Check if site password protection is enabled
    enabled = getattr(settings, "ENABLE_SITE_PASSWORD", False)

    if not enabled:
        return JSONResponse(
            content={"success": True, "message": "Site password protection is disabled"}
        )

    # Get the configured site password
    site_password = getattr(settings, "SITE_PASSWORD", "")

    if not site_password:
        logger.error(
            "Site password authentication attempted but no password configured"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Site password not configured",
        )

    # Verify the password
    logger.info(
        "site_password_authentication_attempt",
        received_password_length=len(password_request.password),
        expected_password_length=len(site_password),
        first_char_match=(
            password_request.password[0] == site_password[0]
            if password_request.password and site_password
            else False
        ),
        last_char_match=(
            password_request.password[-1] == site_password[-1]
            if password_request.password and site_password
            else False
        ),
        match=password_request.password == site_password,
    )

    if password_request.password != site_password:
        logger.warning(
            "site_password_authentication_failed",
            client_ip=get_client_ip(request),
            user_agent=request.headers.get("user-agent", "unknown"),
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
        )

    # Password is correct, create success response with cookie
    logger.info(
        "site_password_authentication_success",
        client_ip=get_client_ip(request),
        user_agent=request.headers.get("user-agent", "unknown"),
    )

    # Create the response
    response = JSONResponse(
        content={"success": True, "message": "Authentication successful"}
    )

    # Set authentication cookie
    import hashlib

    password_hash = hashlib.sha256(site_password.encode()).hexdigest()
    cookie_value = hashlib.sha256(f"authenticated_{password_hash}".encode()).hexdigest()

    response.set_cookie(
        key="site_password_authenticated",
        value=cookie_value,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",  # Secure in production
        samesite="lax",
        max_age=86400 * 7,  # 7 days
    )

    return response


@router.post("/check", response_model=SitePasswordResponse)
async def check_site_password(password_request: SitePasswordRequest, request: Request):
    """
    Check if provided password is correct without setting cookies
    Useful for validation before setting permanent authentication
    """

    # Check if site password protection is enabled
    enabled = getattr(settings, "ENABLE_SITE_PASSWORD", False)

    if not enabled:
        return SitePasswordResponse(
            success=True, message="Site password protection is disabled"
        )

    # Get the configured site password
    site_password = getattr(settings, "SITE_PASSWORD", "")

    if not site_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Site password not configured",
        )

    # Verify the password
    is_valid = password_request.password == site_password

    logger.info("site_password_check", valid=is_valid, client_ip=get_client_ip(request))

    if is_valid:
        return SitePasswordResponse(success=True, message="Password is valid")
    else:
        return SitePasswordResponse(success=False, message="Invalid password")
