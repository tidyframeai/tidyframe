"""
Browser Cache Headers and CDN Configuration
Optimizes client-side caching and reduces server load
"""

from typing import Dict, Optional
from fastapi import Response
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


class CacheHeaders:
    """Browser cache header management"""
    
    # Cache durations in seconds
    STATIC_ASSETS_CACHE = 31536000    # 1 year
    API_DATA_CACHE = 300              # 5 minutes
    USER_DATA_CACHE = 60              # 1 minute
    DASHBOARD_CACHE = 180             # 3 minutes
    PUBLIC_DATA_CACHE = 3600          # 1 hour
    NO_CACHE = 0                      # No caching
    
    @staticmethod
    def add_cache_headers(
        response: Response, 
        max_age: int, 
        public: bool = True,
        must_revalidate: bool = False,
        no_cache: bool = False,
        etag: Optional[str] = None
    ):
        """Add comprehensive cache headers to response"""
        
        if no_cache:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
        
        # Build Cache-Control header
        cache_control_parts = []
        
        if public:
            cache_control_parts.append("public")
        else:
            cache_control_parts.append("private")
            
        cache_control_parts.append(f"max-age={max_age}")
        
        if must_revalidate:
            cache_control_parts.append("must-revalidate")
        
        response.headers["Cache-Control"] = ", ".join(cache_control_parts)
        
        # Add Expires header
        expires_time = datetime.utcnow() + timedelta(seconds=max_age)
        response.headers["Expires"] = expires_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        # Add ETag if provided
        if etag:
            response.headers["ETag"] = f'"{etag}"'
            response.headers["Vary"] = "Accept-Encoding"
        
        # Add Last-Modified
        response.headers["Last-Modified"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        logger.debug("cache_headers_added", max_age=max_age, public=public, etag=etag)
        
        return response
    
    @staticmethod
    def static_asset_headers(response: Response) -> Response:
        """Headers for static assets (CSS, JS, images)"""
        return CacheHeaders.add_cache_headers(
            response, 
            CacheHeaders.STATIC_ASSETS_CACHE,
            public=True,
            etag=None
        )
    
    @staticmethod
    def api_response_headers(response: Response, cache_duration: int = None) -> Response:
        """Headers for API responses"""
        duration = cache_duration or CacheHeaders.API_DATA_CACHE
        return CacheHeaders.add_cache_headers(
            response,
            duration,
            public=False,
            must_revalidate=True
        )
    
    @staticmethod
    def user_data_headers(response: Response) -> Response:
        """Headers for user-specific data"""
        return CacheHeaders.add_cache_headers(
            response,
            CacheHeaders.USER_DATA_CACHE,
            public=False,
            must_revalidate=True
        )
    
    @staticmethod
    def dashboard_headers(response: Response) -> Response:
        """Headers for dashboard data"""
        return CacheHeaders.add_cache_headers(
            response,
            CacheHeaders.DASHBOARD_CACHE,
            public=False,
            must_revalidate=True
        )
    
    @staticmethod
    def no_cache_headers(response: Response) -> Response:
        """Headers to prevent caching"""
        return CacheHeaders.add_cache_headers(
            response,
            CacheHeaders.NO_CACHE,
            no_cache=True
        )


class ConditionalCaching:
    """Implements conditional caching with ETags and Last-Modified"""
    
    @staticmethod
    def generate_etag(content: str) -> str:
        """Generate ETag for content"""
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @staticmethod
    def check_if_modified(
        request_headers: Dict[str, str],
        last_modified: datetime,
        etag: Optional[str] = None
    ) -> bool:
        """Check if content has been modified since last request"""
        
        # Check If-Modified-Since header
        if_modified_since = request_headers.get("if-modified-since")
        if if_modified_since:
            try:
                client_time = datetime.strptime(
                    if_modified_since, 
                    "%a, %d %b %Y %H:%M:%S %Z"
                )
                if last_modified <= client_time:
                    return False  # Not modified
            except ValueError:
                pass
        
        # Check If-None-Match header (ETag)
        if_none_match = request_headers.get("if-none-match")
        if if_none_match and etag:
            # Remove quotes if present
            client_etag = if_none_match.strip('"')
            if client_etag == etag:
                return False  # Not modified
        
        return True  # Content has been modified
    
    @staticmethod
    def create_conditional_response(
        content: Dict,
        last_modified: datetime,
        request_headers: Dict[str, str],
        cache_duration: int = 300
    ) -> JSONResponse:
        """Create response with conditional caching"""
        
        # Generate ETag
        import json
        content_str = json.dumps(content, sort_keys=True)
        etag = ConditionalCaching.generate_etag(content_str)
        
        # Check if content was modified
        if not ConditionalCaching.check_if_modified(request_headers, last_modified, etag):
            # Return 304 Not Modified
            response = JSONResponse(content={}, status_code=304)
            response.headers["ETag"] = f'"{etag}"'
            response.headers["Last-Modified"] = last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")
            return response
        
        # Return full response with cache headers
        response = JSONResponse(content=content)
        CacheHeaders.add_cache_headers(
            response,
            cache_duration,
            public=False,
            etag=etag,
            must_revalidate=True
        )
        
        return response


class CDNConfiguration:
    """CDN optimization settings and recommendations"""
    
    @staticmethod
    def get_cdn_headers() -> Dict[str, str]:
        """Get recommended CDN headers"""
        return {
            # CloudFlare specific headers
            "CF-Cache-Status": "HIT",  # Will be set by CloudFlare
            "CF-RAY": "",              # Will be set by CloudFlare
            
            # Generic CDN headers
            "X-Cache": "HIT",          # Cache status
            "X-Cache-Expires": "",     # Cache expiration
            "X-Served-By": "CDN",      # Served by CDN
            
            # Optimization headers
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            
            # Compression
            "Content-Encoding": "gzip",
            "Vary": "Accept-Encoding, User-Agent",
        }
    
    @staticmethod
    def get_asset_optimization_config() -> Dict[str, Dict]:
        """Get asset optimization configuration for CDN"""
        return {
            "css": {
                "cache_duration": CacheHeaders.STATIC_ASSETS_CACHE,
                "compress": True,
                "minify": True,
                "content_type": "text/css"
            },
            "js": {
                "cache_duration": CacheHeaders.STATIC_ASSETS_CACHE,
                "compress": True,
                "minify": True,
                "content_type": "application/javascript"
            },
            "images": {
                "cache_duration": CacheHeaders.STATIC_ASSETS_CACHE,
                "compress": True,
                "optimize": True,
                "webp_conversion": True
            },
            "fonts": {
                "cache_duration": CacheHeaders.STATIC_ASSETS_CACHE,
                "compress": True,
                "preload": True
            },
            "api": {
                "cache_duration": CacheHeaders.API_DATA_CACHE,
                "compress": True,
                "edge_cache": False  # Don't cache API responses at edge
            }
        }
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get security headers for CDN"""
        return {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' https://apis.google.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:;",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }


# FastAPI middleware for automatic cache headers
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically add cache headers based on route"""
    
    def __init__(self, app):
        super().__init__(app)
        self.route_cache_config = {
            # Static assets - long cache
            "/static/": CacheHeaders.STATIC_ASSETS_CACHE,
            "/assets/": CacheHeaders.STATIC_ASSETS_CACHE,
            "/favicon.ico": CacheHeaders.STATIC_ASSETS_CACHE,
            
            # API routes - short cache
            "/api/v1/users/me": CacheHeaders.USER_DATA_CACHE,
            "/api/v1/dashboard": CacheHeaders.DASHBOARD_CACHE,
            "/api/v1/jobs": CacheHeaders.API_DATA_CACHE,
            
            # Public data - medium cache
            "/api/v1/public/": CacheHeaders.PUBLIC_DATA_CACHE,
            
            # No cache routes
            "/api/v1/auth/": CacheHeaders.NO_CACHE,
            "/api/v1/admin/": CacheHeaders.NO_CACHE,
        }
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Skip if response already has cache headers
        if "Cache-Control" in response.headers:
            return response
        
        # Determine cache duration based on route
        cache_duration = self._get_cache_duration(request.url.path)
        
        if cache_duration is not None:
            # Add appropriate cache headers
            if cache_duration == CacheHeaders.NO_CACHE:
                CacheHeaders.no_cache_headers(response)
            elif request.url.path.startswith("/static/") or request.url.path.startswith("/assets/"):
                CacheHeaders.static_asset_headers(response)
            else:
                CacheHeaders.api_response_headers(response, cache_duration)
        
        return response
    
    def _get_cache_duration(self, path: str) -> Optional[int]:
        """Get cache duration for path"""
        for route_prefix, duration in self.route_cache_config.items():
            if path.startswith(route_prefix):
                return duration
        
        # Default for API routes
        if path.startswith("/api/"):
            return CacheHeaders.API_DATA_CACHE
        
        return None


# Utility functions
def create_cacheable_response(
    content: Dict,
    cache_duration: int = CacheHeaders.API_DATA_CACHE,
    public: bool = False
) -> JSONResponse:
    """Create a JSONResponse with optimal cache headers"""
    response = JSONResponse(content=content)
    
    CacheHeaders.add_cache_headers(
        response,
        cache_duration,
        public=public,
        must_revalidate=True
    )
    
    return response


def create_static_response(
    content: str,
    content_type: str = "text/plain"
) -> StarletteResponse:
    """Create a static asset response with long cache"""
    response = StarletteResponse(content=content, media_type=content_type)
    CacheHeaders.static_asset_headers(response)
    return response