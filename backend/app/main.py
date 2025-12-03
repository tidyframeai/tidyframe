"""
tidyframe.com FastAPI Main Application
AI-powered name parsing and entity detection SaaS platform
"""

import os
import time
import uuid

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.admin import router as admin_router
from app.api.apikeys import router as apikeys_router
from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.files import router as files_router
from app.api.site_password import router as site_password_router
from app.api.users import router as users_router
from app.core.config import settings
from app.core.database import create_tables, get_db
from app.middleware.billing_middleware import BillingMiddleware
from app.middleware.geolocation import GeolocationMiddleware
from app.middleware.security import RateLimitMiddleware, SecurityMiddleware
from app.middleware.site_password import SitePasswordMiddleware
from app.utils.client_ip import get_client_ip

# Configure structured logging
logger = structlog.get_logger()


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="tidyframe.com API",
        description="AI-powered name parsing and entity detection platform",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Configure CORS with secure headers
    # Build comprehensive list of allowed origins based on environment
    allowed_origins = []

    if settings.ENVIRONMENT == "production":
        # Production domains
        allowed_origins = [
            "https://tidyframe.com",
            "https://www.tidyframe.com",
            "https://api.tidyframe.com",
            "https://app.tidyframe.com",
        ]
    elif settings.ENVIRONMENT == "staging":
        # Staging domains
        allowed_origins = [
            "https://staging.tidyframe.com",
            "https://staging-api.tidyframe.com",
            "https://test.tidyframe.com",
        ]
    else:
        # Development and local testing
        allowed_origins = [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "http://0.0.0.0",
            "http://0.0.0.0:3000",
            "http://0.0.0.0:8000",
            "https://localhost",
            "https://localhost:3000",
            "https://localhost:8000",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-CSRF-Token",
            "X-Correlation-ID",
            "X-API-Key",
            "X-Site-Password",
            "Cache-Control",
            "Pragma",
        ],
        expose_headers=[
            "X-Total-Count",
            "X-Page-Count",
            "X-Correlation-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-Response-Time",
        ],
        max_age=(
            86400 if settings.ENVIRONMENT == "production" else 3600
        ),  # 24h prod, 1h dev
    )

    # Add comprehensive security middleware
    app.add_middleware(
        SecurityMiddleware,
        environment=settings.ENVIRONMENT,
        enable_hsts=settings.ENVIRONMENT == "production",
        enable_csp=True,
        rate_limit_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        api_rate_limit_per_minute=settings.API_RATE_LIMIT_PER_MINUTE,
        max_request_size_mb=settings.MAX_FILE_SIZE_MB,
    )

    # Add trusted host middleware for security
    if settings.ENVIRONMENT == "production":
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

    # Add dedicated rate limiting for additional protection
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        burst_requests=min(20, settings.RATE_LIMIT_PER_MINUTE // 3),
        whitelist_ips=(
            {"127.0.0.1", "::1"} if settings.ENVIRONMENT != "production" else set()
        ),
    )

    # CRITICAL: Add billing middleware to enforce payment requirements
    # This MUST be added to prevent free access to processing
    app.add_middleware(BillingMiddleware)

    # Add site password protection middleware (LAST so it runs FIRST)
    # This ensures site password protection happens before any other auth checks
    logger.info(
        "site_password_middleware_config",
        enabled=settings.ENABLE_SITE_PASSWORD,
        has_password=bool(settings.SITE_PASSWORD),
        password_length=len(settings.SITE_PASSWORD) if settings.SITE_PASSWORD else 0,
    )

    app.add_middleware(
        SitePasswordMiddleware,
        enabled=settings.ENABLE_SITE_PASSWORD,
        password=settings.SITE_PASSWORD,
    )

    # CRITICAL LEGAL COMPLIANCE: Add geolocation middleware for US-only enforcement
    # This enforces Terms of Service Section 10.1 - US-only service requirement
    app.add_middleware(
        GeolocationMiddleware,
        exempt_paths=[
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/health",
            "/api/auth/login",
            "/api/auth/refresh",
            "/api/auth/reset-password",
            "/api/site-password",
            "/api/v1/auth/register",  # Allow registration with legal compliance
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
        ],
    )

    # Request logging middleware
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        # Log request
        start_time = time.time()
        logger.info(
            "request_started",
            method=request.method,
            url=str(request.url),
            correlation_id=correlation_id,
            user_agent=request.headers.get("user-agent"),
            client_ip=get_client_ip(request),
        )

        # Process request
        response = await call_next(request)

        # Log response
        process_time = time.time() - start_time
        logger.info(
            "request_completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=process_time,
            correlation_id=correlation_id,
        )

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    # Exception handlers
    @app.exception_handler(HTTPException)
    async def fastapi_exception_handler(request: Request, exc: HTTPException):
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        # Log authentication errors as warnings, not errors
        if exc.status_code in [401, 403]:
            logger.warning(
                "authentication_exception",
                status_code=exc.status_code,
                detail=exc.detail,
                correlation_id=correlation_id,
            )
        else:
            logger.error(
                "http_exception",
                status_code=exc.status_code,
                detail=exc.detail,
                correlation_id=correlation_id,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "correlation_id": correlation_id},
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(
        request: Request, exc: StarletteHTTPException
    ):
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        logger.error(
            "starlette_exception",
            status_code=exc.status_code,
            detail=exc.detail,
            correlation_id=correlation_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        logger.error(
            "validation_exception", errors=exc.errors(), correlation_id=correlation_id
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "message": "Validation error",
                "details": [
                    {
                        "loc": error.get("loc", []),
                        "msg": str(error.get("msg", "")),
                        "type": error.get("type", ""),
                    }
                    for error in exc.errors()
                ],
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        logger.error(
            "unexpected_exception",
            exception=str(exc),
            exception_type=type(exc).__name__,
            correlation_id=correlation_id,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "message": "Internal server error",
                "correlation_id": correlation_id,
            },
        )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "tidyframe-api"}

    # Include API routers
    app.include_router(
        site_password_router, prefix="/api/site-password", tags=["Site Password"]
    )
    app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(files_router, prefix="/api", tags=["File Processing"])
    app.include_router(users_router, prefix="/api/user", tags=["User Management"])
    app.include_router(billing_router, prefix="/api/billing", tags=["Billing"])
    app.include_router(admin_router, prefix="/api/admin", tags=["Administration"])
    app.include_router(apikeys_router, prefix="/api/apikeys", tags=["API Keys"])

    # Webhook compatibility routes for Stripe dashboard configuration
    # These aliases match the URLs configured in Stripe dashboard
    @app.post("/api/stripe/webhook")
    async def stripe_webhook_alias(
        request: Request, db: AsyncSession = Depends(get_db)
    ):
        """Alias to match Stripe dashboard webhook URL"""
        from app.api.billing.router import stripe_webhook

        return await stripe_webhook(request, db)

    @app.post("/api/stripe/meter/webhook")
    async def stripe_meter_webhook_alias(
        request: Request, db: AsyncSession = Depends(get_db)
    ):
        """Alias to match Stripe meter webhook URL"""
        from app.api.billing.router import stripe_meter_webhook

        return await stripe_meter_webhook(request, db)

    # Catch-all route for SPA - MUST come after API routes but before static mount
    # This serves index.html for all frontend routes (React Router handles client-side routing)
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str, request: Request):
        """
        Catch-all route to serve index.html for React SPA routes.
        Excludes static files which are handled by directly serving them here.
        This ensures frontend routes like /auth/register, /dashboard, /pricing work properly.
        API routes take precedence since they're registered first.
        """
        # If path starts with 'api/', it should have matched an API route above
        # If we're here, it means the API endpoint doesn't exist - return 404
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")

        # Determine static directory (same logic as mount below)
        static_dir = "/app/app/static"
        if settings.ENVIRONMENT != "production":
            frontend_dist = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "..", "frontend", "dist"
            )
            if os.path.exists(frontend_dist):
                static_dir = frontend_dist

        # Check if this is a request for a static file
        static_extensions = {
            ".js",
            ".css",
            ".map",
            ".json",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
            ".webp",
            ".woff",
            ".woff2",
            ".ttf",
            ".eot",
            ".otf",
            ".pdf",
            ".txt",
            ".xml",
        }

        path_lower = full_path.lower()
        is_static_file = any(
            path_lower.endswith(ext) for ext in static_extensions
        ) or full_path.startswith("assets/")

        if is_static_file:
            # Try to serve the static file directly
            file_path = os.path.join(static_dir, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            else:
                # Static file not found
                raise HTTPException(status_code=404, detail="File not found")

        # For all other paths (SPA routes), serve the React SPA index.html
        index_path = os.path.join(static_dir, "index.html")

        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            # If index.html doesn't exist, application hasn't been deployed
            raise HTTPException(
                status_code=500,
                detail="Application not deployed - index.html not found",
            )

    # Mount static files AFTER all middleware and routers
    # This ensures site password middleware protects static files
    # Static files are at /app/app/static in Docker (Dockerfile copies to app/static within /app workdir)
    static_dir = "/app/app/static"
    if settings.ENVIRONMENT == "production":
        # In production, frontend files are copied to backend/app/static by deploy.sh
        # Docker image structure: /app/app/static (workdir is /app, files at app/static)
        static_dir = "/app/app/static"
    else:
        # In development, use local frontend dist directory
        frontend_dist = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "..", "frontend", "dist"
        )
        if os.path.exists(frontend_dist):
            static_dir = frontend_dist

    # Create static directory if it doesn't exist
    os.makedirs(static_dir, exist_ok=True)

    # Mount static files (this will be protected by site password middleware)
    try:
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
        logger.info(f"Mounted static files from: {static_dir}")
    except Exception as e:
        logger.warning(f"Failed to mount static files from {static_dir}: {e}")
        # Create a basic index.html if static directory is empty
        index_path = os.path.join(static_dir, "index.html")
        if not os.path.exists(index_path):
            with open(index_path, "w") as f:
                f.write(
                    """<!DOCTYPE html>
<html>
<head><title>TidyFrame - Loading...</title></head>
<body><h1>TidyFrame is loading...</h1><p>Please wait while the application starts.</p></body>
</html>"""
                )
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


# Create application instance
app = create_application()


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("application_starting", version="1.0.0")

    # Create database tables
    await create_tables()

    # Create/update admin user automatically
    import uuid
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.core.security import get_password_hash
    from app.models.user import PlanType, User

    try:
        admin_email = os.getenv("ADMIN_EMAIL", "admin@tidyframe.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

        async with AsyncSessionLocal() as db:
            # Check if admin exists
            result = await db.execute(select(User).where(User.email == admin_email))
            admin = result.scalar_one_or_none()

            if admin:
                # Update existing admin
                admin.password_hash = get_password_hash(admin_password)
                admin.plan = PlanType.ENTERPRISE
                admin.is_admin = True
                admin.email_verified = True
                admin.is_active = True
                admin.custom_monthly_limit = 10000000
            else:
                # Create new admin
                admin = User(
                    id=uuid.uuid4(),
                    email=admin_email,
                    password_hash=get_password_hash(admin_password),
                    plan=PlanType.ENTERPRISE,
                    is_admin=True,
                    email_verified=True,
                    is_active=True,
                    custom_monthly_limit=10000000,
                    parses_this_month=0,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(admin)

            await db.commit()
            logger.info("admin_user_initialized", email=admin_email)
    except Exception as e:
        logger.error("admin_setup_failed", error=str(e))

    # Start background usage reporting task for Stripe billing
    # This ensures usage gets reported even if batches don't reach threshold
    import asyncio

    from app.services.stripe_service import get_usage_service

    usage_service = get_usage_service()
    asyncio.create_task(usage_service.start_background_reporting())
    logger.info("stripe_usage_reporting_started")

    logger.info("application_started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("application_shutting_down")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
