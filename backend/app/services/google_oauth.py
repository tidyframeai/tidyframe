"""
Google OAuth service for authentication
"""

import secrets
from typing import Dict, Tuple

import structlog
from authlib.integrations.httpx_client import AsyncOAuth2Client

from app.core.config import settings

logger = structlog.get_logger()


class GoogleOAuthService:
    """Google OAuth authentication service"""

    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = "https://app.tidyframe.com/auth/google/callback"  # Update with your actual domain

        # Google OAuth endpoints
        self.authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_endpoint = "https://oauth2.googleapis.com/token"
        self.userinfo_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"

        # OAuth scopes
        self.scopes = ["openid", "email", "profile"]

    def get_authorization_url(self) -> Tuple[str, str]:
        """
        Generate Google OAuth authorization URL

        Returns:
            Tuple of (authorization_url, state)
        """

        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured")

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Build authorization URL
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "response_type": "code",
            "state": state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
        }

        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        auth_url = f"{self.authorization_endpoint}?{query_string}"

        return auth_url, state

    async def exchange_code_for_token(self, code: str, state: str) -> Dict[str, any]:
        """
        Exchange authorization code for access token and user info

        Args:
            code: Authorization code from Google
            state: State parameter for CSRF protection

        Returns:
            Dict with user information
        """

        # Create OAuth client
        client = AsyncOAuth2Client(
            client_id=self.client_id, client_secret=self.client_secret
        )

        try:
            # Exchange code for token
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            token_response = await client.post(self.token_endpoint, data=token_data)
            token_response.raise_for_status()
            token_info = token_response.json()

            access_token = token_info.get("access_token")
            if not access_token:
                raise ValueError("No access token received from Google")

            # Get user info
            headers = {"Authorization": f"Bearer {access_token}"}
            user_response = await client.get(self.userinfo_endpoint, headers=headers)
            user_response.raise_for_status()
            user_info = user_response.json()

            # Validate required fields
            if not user_info.get("email"):
                raise ValueError("No email received from Google")

            logger.info(
                "google_oauth_token_exchange_successful",
                email=user_info.get("email"),
                user_id=user_info.get("id"),
            )

            return user_info

        except Exception as e:
            logger.error("google_oauth_token_exchange_failed", error=str(e))
            raise

    async def refresh_token(self, refresh_token: str) -> Dict[str, any]:
        """
        Refresh Google access token

        Args:
            refresh_token: Google refresh token

        Returns:
            New token information
        """

        client = AsyncOAuth2Client(
            client_id=self.client_id, client_secret=self.client_secret
        )

        try:
            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            response = await client.post(self.token_endpoint, data=refresh_data)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error("google_token_refresh_failed", error=str(e))
            raise
