"""
Geolocation middleware for enforcing geographic restrictions per Terms of Service
CRITICAL FOR LEGAL COMPLIANCE - US-only service requirement
"""

from datetime import datetime, timezone
from typing import Optional

import httpx
import structlog
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.client_ip import get_client_ip

logger = structlog.get_logger()


class GeolocationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce geographic restrictions

    Per Terms of Service Section 10.1:
    "The Services are intended solely for users located in the United States"
    """

    def __init__(self, app, exempt_paths: Optional[list] = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/auth/login",
            "/api/auth/refresh",  # Allow existing users to login
            "/api/v1/auth/register",  # Allow registration (handled with consent validation)
            "/api/v1/auth/login",  # Allow v1 API login
            "/api/v1/auth/refresh",  # Allow v1 API refresh
            "/api/site-password",  # Allow site password protection check and auth
        ]

    async def dispatch(self, request: Request, call_next):
        # Skip geolocation check for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # Skip for registration endpoints - handled in router with consent validation
        if request.url.path in ["/api/auth/register", "/api/v1/auth/register"]:
            return await call_next(request)

        # Get client IP (reads X-Forwarded-For from nginx)
        client_ip = get_client_ip(request)

        if not client_ip:
            logger.warning("geolocation_no_ip", path=request.url.path)
            return await call_next(request)

        # Skip geolocation check for localhost/development and Docker networks
        if self._is_localhost_or_docker_network(client_ip):
            return await call_next(request)

        # Check if IP is from US
        is_us_ip = await self._is_us_ip(client_ip)

        if not is_us_ip:
            logger.warning(
                "geolocation_blocked",
                ip=client_ip,
                path=request.url.path,
                user_agent=request.headers.get("user-agent", ""),
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This service is only available to users located in the United States. Please see our Terms of Service for more information.",
            )

        # Add geolocation info to request state for logging
        request.state.client_ip = client_ip
        request.state.is_verified_us = True

        return await call_next(request)

    def _is_localhost_or_docker_network(self, ip: str) -> bool:
        """Check if IP is localhost or from Docker network ranges"""
        # Standard localhost IPs
        localhost_ips = ["127.0.0.1", "::1", "localhost"]
        if ip in localhost_ips:
            return True

        try:
            # Convert IP to check Docker network ranges
            parts = ip.split(".")
            if len(parts) != 4:
                return False

            # Convert to integer for range checks
            ip_int = sum(int(part) << (8 * (3 - i)) for i, part in enumerate(parts))

            # Docker default bridge network ranges
            docker_ranges = [
                (0xAC110000, 0xAC11FFFF),  # 172.17.0.0/16 - default bridge
                (0xAC120000, 0xAC12FFFF),  # 172.18.0.0/16 - custom networks
                (0xAC130000, 0xAC13FFFF),  # 172.19.0.0/16 - custom networks
                (0xAC140000, 0xAC1FFFFF),  # 172.20.0.0/12 - Docker range
                (0xC0A80000, 0xC0A8FFFF),  # 192.168.0.0/16 - private range
                (0x0A000000, 0x0AFFFFFF),  # 10.0.0.0/8 - private range
            ]

            for start, end in docker_ranges:
                if start <= ip_int <= end:
                    logger.info(
                        "geolocation_docker_bypass",
                        ip=ip,
                        reason="Docker network or localhost detected",
                    )
                    return True

            return False

        except Exception as e:
            logger.warning("geolocation_localhost_check_error", error=str(e), ip=ip)
            # If we can't determine, treat as non-localhost for security
            return False

    async def _is_us_ip(self, ip: str) -> bool:
        """
        Check if IP address is from United States

        Uses multiple fallback methods:
        1. ip-api.com (free, reliable)
        2. ipinfo.io (backup)
        3. Local IP range checks for common US ranges
        """
        try:
            # Method 1: ip-api.com (free tier, good for compliance)
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"http://ip-api.com/json/{ip}?fields=status,country,countryCode"
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        country_code = data.get("countryCode", "").upper()

                        logger.info(
                            "geolocation_check",
                            ip=ip,
                            country=data.get("country"),
                            country_code=country_code,
                            service="ip-api",
                        )

                        return country_code == "US"

        except Exception as e:
            logger.warning("geolocation_api_error", error=str(e), service="ip-api")

        try:
            # Method 2: ipinfo.io backup
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"https://ipinfo.io/{ip}/json")

                if response.status_code == 200:
                    data = response.json()
                    country_code = data.get("country", "").upper()

                    logger.info(
                        "geolocation_check",
                        ip=ip,
                        country_code=country_code,
                        service="ipinfo",
                    )

                    return country_code == "US"

        except Exception as e:
            logger.warning("geolocation_api_error", error=str(e), service="ipinfo")

        # Method 3: Basic IP range checks for known US ranges
        # This is a fallback - not comprehensive but covers major US providers
        return self._is_likely_us_ip(ip)

    def _is_likely_us_ip(self, ip: str) -> bool:
        """
        Basic check for common US IP ranges
        This is not comprehensive - just a fallback when APIs fail
        """
        try:
            # Convert IP to integer for range checks
            parts = ip.split(".")
            if len(parts) != 4:
                return False

            ip_int = sum(int(part) << (8 * (3 - i)) for i, part in enumerate(parts))

            # Some major US IP ranges (not exhaustive - just common ones)
            us_ranges = [
                (0x08000000, 0x08FFFFFF),  # 8.0.0.0/8 - Level3/CenturyLink
                (0x4C000000, 0x4CFFFFFF),  # 76.0.0.0/8 - Comcast
                (0x18000000, 0x18FFFFFF),  # 24.0.0.0/8 - Various US ISPs
                (0x40000000, 0x4FFFFFFF),  # 64.0.0.0/6 - Various US providers
            ]

            for start, end in us_ranges:
                if start <= ip_int <= end:
                    logger.info("geolocation_fallback_match", ip=ip, method="ip_range")
                    return True

            # If we can't determine, err on the side of caution and allow
            # This prevents legitimate US users from being blocked due to API issues
            logger.warning(
                "geolocation_fallback_allow",
                ip=ip,
                reason="Could not determine location, allowing access",
            )
            return True

        except Exception as e:
            logger.error("geolocation_fallback_error", error=str(e), ip=ip)
            # If all else fails, allow access to avoid blocking legitimate users
            return True


class IPGeolocationService:
    """Service for IP geolocation queries with caching"""

    def __init__(self):
        self._cache = {}  # Simple in-memory cache

    async def get_country_code(self, ip: str) -> Optional[str]:
        """Get country code for IP address with caching"""

        # Check cache first (cache for 1 hour)
        cached = self._cache.get(ip)
        if cached:
            cache_time, country_code = cached
            if (datetime.now(timezone.utc) - cache_time).seconds < 3600:
                return country_code

        # Fetch from API
        country_code = await self._fetch_country_code(ip)

        # Cache result
        if country_code:
            self._cache[ip] = (datetime.now(timezone.utc), country_code)

        return country_code

    async def _fetch_country_code(self, ip: str) -> Optional[str]:
        """Fetch country code from geolocation API"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"http://ip-api.com/json/{ip}?fields=status,countryCode"
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        return data.get("countryCode", "").upper()

        except Exception as e:
            logger.warning("geolocation_fetch_error", error=str(e), ip=ip)

        return None


# Global service instance
geolocation_service = IPGeolocationService()
