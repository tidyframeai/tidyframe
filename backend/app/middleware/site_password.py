"""
Site Password Protection Middleware
Provides temporary password protection for the entire site before public launch
"""

import hashlib
from typing import Optional

import structlog
from fastapi import Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.client_ip import get_client_ip

logger = structlog.get_logger()


class SitePasswordMiddleware(BaseHTTPMiddleware):
    """
    Middleware to protect the entire site with a password during pre-launch phase.

    Features:
    - Session-based authentication (once authenticated, user stays authenticated)
    - Configurable via environment variables
    - Easy to enable/disable
    - Secure password hashing
    - Proper error handling and logging
    """

    def __init__(self, app, enabled: bool = False, password: Optional[str] = None):
        super().__init__(app)
        self.enabled = enabled
        self.password_hash = self._hash_password(password) if password else None
        self.session_cookie_name = "site_password_authenticated"

        # Paths that should be excluded from password protection
        self.excluded_paths = {
            "/health",
            "/api/site-password/status",
            "/api/site-password/check",
            "/api/site-password/authenticate",
            "/favicon.ico",
        }

        # Allow static assets only (needed for password form to render)
        # SECURITY: ALL auth endpoints now require site password for total lockdown
        self.excluded_prefixes = [
            "/static/",  # Password form assets
            "/assets/",  # Password form assets
        ]

        if self.enabled and not password:
            logger.warning(
                "Site password protection is enabled but no password is configured!"
            )

        logger.info(
            "site_password_middleware_initialized",
            enabled=self.enabled,
            has_password=bool(self.password_hash),
        )

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256 for comparison"""
        return hashlib.sha256(password.encode()).hexdigest()

    def _is_path_excluded(self, path: str) -> bool:
        """Check if the path should be excluded from password protection"""
        if path in self.excluded_paths:
            return True

        for prefix in self.excluded_prefixes:
            if path.startswith(prefix):
                return True

        return False

    def _is_authenticated(self, request: Request) -> bool:
        """Check if the user is already authenticated via session cookie or header"""
        # Check header first (for API requests)
        site_password_header = request.headers.get("x-site-password")
        if site_password_header and self.verify_password(site_password_header):
            return True

        # Check cookie (for browser sessions)
        auth_cookie = request.cookies.get(self.session_cookie_name)
        if not auth_cookie:
            return False

        # Verify the cookie value (simple hash of password)
        expected_cookie_value = hashlib.sha256(
            f"authenticated_{self.password_hash}".encode()
        ).hexdigest()

        return auth_cookie == expected_cookie_value

    def _create_auth_cookie_value(self) -> str:
        """Create the authentication cookie value"""
        return hashlib.sha256(
            f"authenticated_{self.password_hash}".encode()
        ).hexdigest()

    def _has_valid_api_key_format(self, request: Request) -> bool:
        """Check if request has a valid API key format (bypass site password for API clients)"""
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return False

        # Check for Bearer token that looks like an API key
        if auth_header.startswith("Bearer ") and len(auth_header) > 7:
            token = auth_header[7:]  # Remove "Bearer " prefix
            # API keys start with "tf_" - let the authentication system validate the actual key
            return token.startswith("tf_")

        return False

    def _is_admin_user(self, request: Request) -> bool:
        """Check if the request is from an admin user via JWT token

        Note: We decode the JWT to check the is_admin claim that was set during login.
        The actual auth middleware validates the token properly.
        """
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return False

        try:
            token = auth_header[7:]  # Remove "Bearer " prefix

            # Import jwt and settings locally to avoid import issues
            from jose import jwt

            from app.core.config import settings

            # Properly verify JWT token
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            except jwt.InvalidTokenError:
                # Invalid token, not an admin
                return False

            # Check the is_admin claim in the JWT
            # This claim is set during login based on the database is_admin column
            is_admin = payload.get("is_admin", False)

            if is_admin:
                email = payload.get("email", "unknown")
                logger.info(f"Admin user {email} bypassing site password")
                return True

        except Exception:
            # Silently fail - the actual auth middleware will handle JWT validation
            pass

        return False

    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method"""

        # Skip if middleware is disabled
        if not self.enabled:
            return await call_next(request)

        # Skip if no password is configured
        if not self.password_hash:
            logger.warning(
                "Site password middleware enabled but no password configured"
            )
            return await call_next(request)

        # Always allow OPTIONS requests for CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path

        # Skip excluded paths
        if self._is_path_excluded(path):
            return await call_next(request)

        # Check if user is already authenticated
        if self._is_authenticated(request):
            return await call_next(request)

        # Check for API key authentication (bypass site password for API clients)
        if self._has_valid_api_key_format(request):
            return await call_next(request)

        # Check if user is admin (bypass site password for admin users)
        if self._is_admin_user(request):
            return await call_next(request)

        # User is not authenticated, deny access
        logger.info(
            "site_password_access_denied",
            path=path,
            client_ip=get_client_ip(request),
            user_agent=request.headers.get("user-agent", "unknown"),
        )

        # Return 401 for API endpoints (keep as JSON)
        if path.startswith("/api/"):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": True,
                    "message": "Site password required",
                    "code": "SITE_PASSWORD_REQUIRED",
                },
            )

        # For non-API requests (HTML pages), serve password form
        return self._serve_password_form(request)

    def _serve_password_form(self, request: Request) -> HTMLResponse:
        """Serve a beautiful HTML password form"""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Access Required - TidyFrame</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 24px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 48px;
            max-width: 440px;
            width: 100%;
        }
        .icon {
            width: 64px;
            height: 64px;
            background: #667eea;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
        }
        .icon svg {
            width: 32px;
            height: 32px;
            fill: white;
        }
        h1 {
            text-align: center;
            color: #1a202c;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 12px;
        }
        .subtitle {
            text-align: center;
            color: #718096;
            font-size: 16px;
            margin-bottom: 32px;
            line-height: 1.5;
        }
        .form-group {
            margin-bottom: 24px;
        }
        label {
            display: block;
            color: #4a5568;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        input[type="password"] {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 16px;
            transition: all 0.2s;
            outline: none;
        }
        input[type="password"]:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .button {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
        }
        .button:active {
            transform: translateY(0);
        }
        .error {
            background: #fed7d7;
            color: #c53030;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
            font-size: 14px;
        }
        .error.show {
            display: block;
        }
        .footer {
            text-align: center;
            margin-top: 24px;
            color: #718096;
            font-size: 14px;
        }
        .footer a {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }
        .footer a:hover {
            text-decoration: underline;
        }
        .copyright {
            text-align: center;
            color: rgba(255,255,255,0.9);
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="container">
            <div class="icon">
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 1C8.676 1 6 3.676 6 7v2H5c-1.105 0-2 .895-2 2v10c0 1.105.895 2 2 2h14c1.105 0 2-.895 2-2V11c0-1.105-.895-2-2-2h-1V7c0-3.324-2.676-6-6-6zm0 2c2.276 0 4 1.724 4 4v2H8V7c0-2.276 1.724-4 4-4zm0 10c1.105 0 2 .895 2 2s-.895 2-2 2-2-.895-2-2 .895-2 2-2z"/>
                </svg>
            </div>

            <h1>Welcome to TidyFrame</h1>
            <p class="subtitle">This site is currently in pre-launch mode.<br>Please enter the access password to continue.</p>

            <div id="error" class="error"></div>

            <form id="passwordForm" action="/api/site-password/authenticate" method="POST">
                <div class="form-group">
                    <label for="password">Access Password</label>
                    <input
                        type="password"
                        id="password"
                        name="password"
                        placeholder="Enter password"
                        required
                        autofocus
                    >
                </div>

                <button type="submit" class="button">Access Site</button>
            </form>

            <div class="footer">
                Need help? Contact <a href="mailto:tidyframeai@gmail.com">tidyframeai@gmail.com</a>
            </div>
        </div>

        <div class="copyright">
            © 2025 TidyFrame. All rights reserved.
        </div>
    </div>

    <script>
        const form = document.getElementById('passwordForm');
        const errorDiv = document.getElementById('error');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            errorDiv.classList.remove('show');

            const password = document.getElementById('password').value;

            try {
                const response = await fetch('/api/site-password/authenticate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ password })
                });

                const data = await response.json();

                if (data.success) {
                    // Reload the page to get the site content
                    window.location.reload();
                } else {
                    errorDiv.textContent = data.message || 'Invalid password. Please try again.';
                    errorDiv.classList.add('show');
                }
            } catch (error) {
                errorDiv.textContent = 'Authentication failed. Please try again.';
                errorDiv.classList.add('show');
            }
        });
    </script>
</body>
</html>
        """
        return HTMLResponse(content=html_content, status_code=401)

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash"""
        if not self.password_hash:
            return False
        return self._hash_password(password) == self.password_hash

    def create_authenticated_response(self, response: Response) -> Response:
        """Add authentication cookie to response"""
        if self.password_hash:
            cookie_value = self._create_auth_cookie_value()
            from app.core.config import settings

            response.set_cookie(
                key=self.session_cookie_name,
                value=cookie_value,
                httponly=True,
                secure=settings.ENVIRONMENT == "production",  # HTTPS only in production
                samesite="lax",
                max_age=86400 * 7,  # 7 days
            )
        return response
