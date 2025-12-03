"""
Enhanced Security Middleware for tidyframe.com
Provides comprehensive security headers, rate limiting, and protection mechanisms
"""

import re
import time
from collections import defaultdict, deque
from typing import Dict, Optional, Set

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.client_ip import get_client_ip

logger = structlog.get_logger()


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware providing:
    - Security headers (HSTS, X-Frame-Options, X-Content-Type-Options, etc.)
    - Content Security Policy (CSP)
    - Rate limiting per IP
    - Request size limiting
    - XSS protection
    - CSRF protection enhancements
    """

    def __init__(
        self,
        app,
        environment: str = "development",
        enable_hsts: bool = True,
        enable_csp: bool = True,
        rate_limit_per_minute: int = 60,
        api_rate_limit_per_minute: int = 1000,
        max_request_size_mb: int = 200,
    ):
        super().__init__(app)
        self.environment = environment
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp
        self.rate_limit_per_minute = rate_limit_per_minute
        self.api_rate_limit_per_minute = api_rate_limit_per_minute
        self.max_request_size_bytes = max_request_size_mb * 1024 * 1024

        # Rate limiting storage (in-memory for simplicity, use Redis for production clustering)
        self.rate_limit_storage: Dict[str, deque] = defaultdict(deque)
        self.api_rate_limit_storage: Dict[str, deque] = defaultdict(deque)

        # Suspicious patterns for basic attack detection
        self.suspicious_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"onload\s*=",
            r"onerror\s*=",
            r"eval\s*\(",
            r"document\.cookie",
            r"\.\./",
            r"union\s+select",
            r"drop\s+table",
        ]
        self.suspicious_regex = re.compile(
            "|".join(self.suspicious_patterns), re.IGNORECASE
        )

        # Safe paths that don't need strict rate limiting
        self.safe_paths = {"/health", "/favicon.ico", "/robots.txt", "/sitemap.xml"}

        logger.info(
            "security_middleware_initialized",
            environment=environment,
            hsts_enabled=enable_hsts,
            csp_enabled=enable_csp,
            rate_limit=rate_limit_per_minute,
            api_rate_limit=api_rate_limit_per_minute,
            max_request_size_mb=max_request_size_mb,
        )

    def _is_rate_limited(self, ip: str, path: str) -> bool:
        """Check if the IP is rate limited"""
        if path in self.safe_paths:
            return False

        current_time = time.time()
        window_start = current_time - 60  # 1 minute window

        # Choose rate limit based on path
        if path.startswith("/api/"):
            storage = self.api_rate_limit_storage[ip]
            limit = self.api_rate_limit_per_minute
        else:
            storage = self.rate_limit_storage[ip]
            limit = self.rate_limit_per_minute

        # Clean old requests outside the window
        while storage and storage[0] < window_start:
            storage.popleft()

        # Check if limit exceeded
        if len(storage) >= limit:
            logger.warning(
                "rate_limit_exceeded",
                ip=ip,
                path=path,
                requests_in_window=len(storage),
                limit=limit,
            )
            return True

        # Add current request
        storage.append(current_time)
        return False

    def _detect_suspicious_content(self, content: str) -> Optional[str]:
        """Detect potentially malicious content"""
        if self.suspicious_regex.search(content):
            return "Suspicious patterns detected"
        return None

    def _add_security_headers(self, response: Response) -> None:
        """Add comprehensive security headers"""

        # X-Frame-Options - Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options - Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection - Enable XSS filtering (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy - Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy - Control browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=(), "
            "accelerometer=(), ambient-light-sensor=()"
        )

        # HSTS - Force HTTPS connections (production only)
        if self.enable_hsts and self.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy
        if self.enable_csp:
            if self.environment == "production":
                # Strict CSP for production
                csp_policy = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com https://accounts.google.com; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                    "font-src 'self' https://fonts.gstatic.com; "
                    "img-src 'self' data: https:; "
                    "connect-src 'self' https://api.stripe.com https://accounts.google.com https://api.tidyframe.com; "
                    "frame-src 'self' https://js.stripe.com https://accounts.google.com; "
                    "object-src 'none'; "
                    "base-uri 'self'; "
                    "form-action 'self'; "
                    "upgrade-insecure-requests"
                )
            else:
                # Relaxed CSP for development
                csp_policy = (
                    "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com https://accounts.google.com; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                    "font-src 'self' https://fonts.gstatic.com; "
                    "img-src 'self' data: https: http:; "
                    "connect-src 'self' https://api.stripe.com https://accounts.google.com ws: wss:; "
                    "frame-src 'self' https://js.stripe.com https://accounts.google.com; "
                    "object-src 'none'"
                )

            response.headers["Content-Security-Policy"] = csp_policy

        # Cross-Origin-Embedder-Policy and Cross-Origin-Opener-Policy for additional isolation
        if self.environment == "production":
            response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        # Server header removal (hide server information)
        if "server" in response.headers:
            del response.headers["server"]

    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method"""

        client_ip = get_client_ip(request)
        path = request.url.path

        # Request size limiting
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size_bytes:
            logger.warning(
                "request_too_large",
                ip=client_ip,
                path=path,
                content_length=int(content_length),
                max_allowed=self.max_request_size_bytes,
            )
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": True,
                    "message": "Request entity too large",
                    "max_size_mb": self.max_request_size_bytes / (1024 * 1024),
                },
            )

        # Rate limiting check
        if self._is_rate_limited(client_ip, path):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": True,
                    "message": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60,
                },
                headers={"Retry-After": "60"},
            )

        # Basic suspicious content detection for query parameters
        query_string = str(request.url.query)
        if query_string:
            suspicious_reason = self._detect_suspicious_content(query_string)
            if suspicious_reason:
                logger.warning(
                    "suspicious_request_blocked",
                    ip=client_ip,
                    path=path,
                    query=query_string[:200],  # Limit log size
                    reason=suspicious_reason,
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": True,
                        "message": "Request blocked for security reasons",
                    },
                )

        # Process the request
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(
                "request_processing_error", ip=client_ip, path=path, error=str(e)
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": True, "message": "Internal server error"},
            )

        # Add security headers to response
        self._add_security_headers(response)

        # Add timing header for monitoring (non-sensitive paths only)
        if not path.startswith("/api/auth/") and not path.startswith("/api/admin/"):
            response.headers["X-Response-Time"] = str(int(time.time() * 1000))

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Dedicated rate limiting middleware with more sophisticated features
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_requests: int = 10,
        whitelist_ips: Optional[Set[str]] = None,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_requests = burst_requests
        self.whitelist_ips = whitelist_ips or set()

        # Storage for rate limiting
        self.request_times: Dict[str, deque] = defaultdict(deque)
        self.burst_counts: Dict[str, int] = defaultdict(int)
        self.last_reset: Dict[str, float] = defaultdict(float)

        logger.info(
            "rate_limit_middleware_initialized",
            requests_per_minute=requests_per_minute,
            burst_requests=burst_requests,
            whitelisted_ips=len(self.whitelist_ips),
        )

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique client identifier (IP + User Agent hash for better accuracy)"""
        ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        return f"{ip}:{hash(user_agent) % 10000}"

    def _is_rate_limited(self, identifier: str) -> bool:
        """Check if client is rate limited"""
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window

        # Clean old requests
        requests = self.request_times[identifier]
        while requests and requests[0] < window_start:
            requests.popleft()

        # Check minute-based rate limit
        if len(requests) >= self.requests_per_minute:
            return True

        # Check burst protection (too many requests in short time)
        recent_requests = sum(
            1 for req_time in requests if req_time > current_time - 10
        )  # Last 10 seconds
        if recent_requests >= self.burst_requests:
            return True

        # Add current request
        requests.append(current_time)
        return False

    async def dispatch(self, request: Request, call_next):
        """Rate limiting dispatch"""
        client_ip = request.client.host

        # Skip rate limiting for whitelisted IPs
        if client_ip in self.whitelist_ips:
            return await call_next(request)

        # Skip for health checks and static assets
        if request.url.path in ["/health", "/favicon.ico", "/robots.txt"]:
            return await call_next(request)

        client_id = self._get_client_identifier(request)

        if self._is_rate_limited(client_id):
            logger.warning(
                "rate_limit_exceeded_detailed",
                client_ip=client_ip,
                path=request.url.path,
                method=request.method,
                user_agent=request.headers.get("user-agent", "unknown")[:100],
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": True,
                    "message": "Too many requests. Please slow down.",
                    "retry_after": 60,
                    "limit": self.requests_per_minute,
                    "window": "1 minute",
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + 60),
                },
            )

        # Add rate limit headers to successful responses
        response = await call_next(request)

        remaining_requests = max(
            0, self.requests_per_minute - len(self.request_times[client_id])
        )
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining_requests)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)

        return response
