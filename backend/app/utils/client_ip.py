"""
Utility for extracting real client IP from requests behind reverse proxy

In production, FastAPI receives requests through nginx reverse proxy.
The direct connection IP (request.client.host) is the nginx container IP (172.x.x.x),
not the real client IP. We must read X-Forwarded-For or X-Real-IP headers.
"""

import structlog
from fastapi import Request

logger = structlog.get_logger()


def get_client_ip(request: Request) -> str:
    """
    Get real client IP from request, accounting for nginx reverse proxy

    Priority order:
    1. X-Forwarded-For header (first IP in chain) - Standard for proxies/load balancers
    2. X-Real-IP header - Alternative nginx header
    3. Direct connection IP - Fallback for development environment

    Args:
        request: FastAPI Request object

    Returns:
        str: Client IP address

    Example:
        >>> # In production with nginx:
        >>> # X-Forwarded-For: "203.0.113.1, 198.51.100.2"
        >>> # Returns: "203.0.113.1" (real client)
        >>>
        >>> # Without proxy (development):
        >>> # Returns: "127.0.0.1" (direct connection)
    """
    # Check X-Forwarded-For first (standard header set by nginx/cloudflare/etc)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take first IP in chain (real client IP before any proxies)
        # Example: "client_ip, proxy1_ip, proxy2_ip" -> "client_ip"
        client_ip = forwarded_for.split(",")[0].strip()
        logger.debug("ip_from_x_forwarded_for", ip=client_ip, full_chain=forwarded_for)
        return client_ip

    # Check X-Real-IP as fallback (alternative nginx header)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        logger.debug("ip_from_x_real_ip", ip=real_ip)
        return real_ip.strip()

    # Fallback to direct connection IP (dev environment only)
    # In production, this will be nginx container IP (172.x.x.x)
    direct_ip = request.client.host if request.client else "unknown"
    logger.debug(
        "ip_from_direct_connection",
        ip=direct_ip,
        warning="Using direct IP - proxy headers not found",
    )
    return direct_ip
