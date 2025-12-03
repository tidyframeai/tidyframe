"""
Email service for sending emails using Resend via Celery
"""

from typing import Optional

import structlog

from app.core.config import settings
from app.workers.email_sender import send_email

logger = structlog.get_logger()


class EmailService:
    """Email service class that wraps Celery email tasks"""

    def __init__(self):
        self.from_email = settings.FROM_EMAIL

    def send_verification_email(self, to_email: str, verification_token: str) -> bool:
        """Send email verification email"""
        try:
            verification_url = (
                f"{settings.FRONTEND_URL}/auth/verify-email?token={verification_token}"
            )

            html_content = f"""
            <h2>Verify your email address</h2>
            <p>Please click the link below to verify your email address:</p>
            <a href="{verification_url}">Verify Email</a>
            <p>If you didn't create an account, you can safely ignore this email.</p>
            """

            text_content = f"""
            Verify your email address

            Please visit the following URL to verify your email address:
            {verification_url}

            If you didn't create an account, you can safely ignore this email.
            """

            # Send via Celery
            task = send_email.delay(
                to_email=to_email,
                subject="Verify your email address",
                html_content=html_content,
                text_content=text_content,
                from_email=self.from_email,
            )

            logger.info("verification_email_queued", email=to_email, task_id=task.id)
            return True

        except Exception as e:
            logger.error("verification_email_failed", email=to_email, error=str(e))
            return False

    def send_password_reset_email(self, to_email: str, reset_token: str) -> bool:
        """Send password reset email"""
        try:
            reset_url = (
                f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"
            )

            html_content = f"""
            <h2>Reset your password</h2>
            <p>You requested a password reset. Click the link below to reset your password:</p>
            <a href="{reset_url}">Reset Password</a>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this reset, you can safely ignore this email.</p>
            """

            text_content = f"""
            Reset your password

            You requested a password reset. Please visit the following URL to reset your password:
            {reset_url}

            This link will expire in 1 hour.

            If you didn't request this reset, you can safely ignore this email.
            """

            # Send via Celery
            task = send_email.delay(
                to_email=to_email,
                subject="Password Reset Request",
                html_content=html_content,
                text_content=text_content,
                from_email=self.from_email,
            )

            logger.info("password_reset_email_queued", email=to_email, task_id=task.id)
            return True

        except Exception as e:
            logger.error("password_reset_email_failed", email=to_email, error=str(e))
            return False

    def send_welcome_email(self, to_email: str, user_name: str) -> bool:
        """Send welcome email to new users"""
        try:
            html_content = f"""
            <h2>Welcome to TidyFrame!</h2>
            <p>Hello {user_name},</p>
            <p>Welcome to TidyFrame! We're excited to have you on board.</p>
            <p>You can now start uploading and processing your data files.</p>
            <p><a href="{settings.FRONTEND_URL}/dashboard">Get Started</a></p>
            """

            text_content = f"""
            Welcome to TidyFrame!

            Hello {user_name},

            Welcome to TidyFrame! We're excited to have you on board.

            You can now start uploading and processing your data files.

            Get Started: {settings.FRONTEND_URL}/dashboard
            """

            # Send via Celery
            task = send_email.delay(
                to_email=to_email,
                subject="Welcome to TidyFrame!",
                html_content=html_content,
                text_content=text_content,
                from_email=self.from_email,
            )

            logger.info("welcome_email_queued", email=to_email, task_id=task.id)
            return True

        except Exception as e:
            logger.error("welcome_email_failed", email=to_email, error=str(e))
            return False

    def send_custom_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send custom email"""
        try:
            # Send via Celery
            task = send_email.delay(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                from_email=self.from_email,
            )

            logger.info("custom_email_queued", email=to_email, task_id=task.id)
            return True

        except Exception as e:
            logger.error("custom_email_failed", email=to_email, error=str(e))
            return False
