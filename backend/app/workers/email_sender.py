"""
Celery worker for sending emails
"""

from typing import Dict, Optional

import resend
import structlog

from app.core.celery_app import celery_app
from app.core.config import settings

logger = structlog.get_logger()

# Configure Resend
resend.api_key = settings.RESEND_API_KEY


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_email(
    self,
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    from_email: Optional[str] = None,
) -> Dict[str, any]:
    """
    Send email using Resend service

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of email
        text_content: Plain text content (optional)
        from_email: Sender email (optional, defaults to settings.FROM_EMAIL)

    Returns:
        Dict with sending results
    """

    if not settings.RESEND_API_KEY:
        logger.warning("resend_api_key_not_configured")
        return {"success": False, "error": "Email service not configured"}

    try:
        email_data = {
            "from": from_email or settings.FROM_EMAIL,
            "to": to_email,
            "subject": subject,
            "html": html_content,
        }

        if text_content:
            email_data["text"] = text_content

        response = resend.Emails.send(email_data)

        logger.info(
            "email_sent_successfully",
            to=to_email,
            subject=subject,
            email_id=response.get("id"),
        )

        return {"success": True, "email_id": response.get("id"), "to": to_email}

    except Exception as e:
        logger.error("email_send_failed", to=to_email, subject=subject, error=str(e))

        # Retry for transient errors
        if self.request.retries < self.max_retries:
            logger.info("retrying_email_send", retry_count=self.request.retries + 1)
            raise self.retry(exc=e)

        return {"success": False, "error": str(e), "to": to_email}


@celery_app.task
def send_welcome_email(user_email: str, user_name: str) -> Dict[str, any]:
    """Send welcome email to new user"""

    subject = f"Welcome to {settings.PROJECT_NAME}!"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #2563eb;">Welcome to {settings.PROJECT_NAME}!</h1>

            <p>Hi {user_name},</p>

            <p>Thank you for signing up for {settings.PROJECT_NAME}. We're excited to help you with AI-powered name parsing and entity detection.</p>

            <h2 style="color: #2563eb;">Getting Started</h2>
            <ul>
                <li>Upload your CSV or Excel files for parsing</li>
                <li>Get accurate first/last name extraction</li>
                <li>Detect entity types (Person/Company/Trust)</li>
                <li>Gender detection with confidence scoring</li>
            </ul>

            <h2 style="color: #2563eb;">Your Plan</h2>
            <p>You're on our Standard plan with 2,000 parses per month. Need more? <a href="mailto:{settings.SUPPORT_EMAIL}">Contact us</a> about our Enterprise options.</p>

            <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #2563eb;">Need Help?</h3>
                <p style="margin-bottom: 0;">
                    Check out our <a href="#" style="color: #2563eb;">documentation</a> or
                    contact our support team at <a href="mailto:{settings.SUPPORT_EMAIL}" style="color: #2563eb;">{settings.SUPPORT_EMAIL}</a>
                </p>
            </div>

            <p>Best regards,<br>The {settings.PROJECT_NAME} Team</p>

            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            <p style="font-size: 12px; color: #6b7280;">
                This email was sent to {user_email}. If you didn't create this account, please ignore this email.
            </p>
        </div>
    </body>
    </html>
    """

    text_content = f"""
    Welcome to {settings.PROJECT_NAME}!

    Hi {user_name},

    Thank you for signing up for {settings.PROJECT_NAME}. We're excited to help you with AI-powered name parsing and entity detection.

    Getting Started:
    - Upload your CSV or Excel files for parsing
    - Get accurate first/last name extraction
    - Detect entity types (Person/Company/Trust)
    - Gender detection with confidence scoring

    Your Plan:
    You're on our Standard plan with 2,000 parses per month. Need more? Contact us at {settings.SUPPORT_EMAIL} about our Enterprise options.

    Need Help?
    Contact our support team at {settings.SUPPORT_EMAIL}

    Best regards,
    The {settings.PROJECT_NAME} Team
    """

    return send_email(user_email, subject, html_content, text_content)


@celery_app.task
def send_email_verification(
    user_email: str, user_name: str, verification_token: str
) -> Dict[str, any]:
    """Send email verification email"""

    subject = f"Verify your {settings.PROJECT_NAME} email address"

    # This would typically include your frontend URL
    verification_url = (
        f"https://app.tidyframe.com/verify-email?token={verification_token}"
    )

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #2563eb;">Verify Your Email Address</h1>

            <p>Hi {user_name},</p>

            <p>Please click the button below to verify your email address and complete your {settings.PROJECT_NAME} account setup.</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}"
                   style="display: inline-block; background-color: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Verify Email Address
                </a>
            </div>

            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #6b7280;">{verification_url}</p>

            <p style="color: #6b7280; font-size: 14px;">This verification link will expire in 24 hours.</p>

            <p>Best regards,<br>The {settings.PROJECT_NAME} Team</p>
        </div>
    </body>
    </html>
    """

    return send_email(user_email, subject, html_content)


@celery_app.task
def send_password_reset(
    user_email: str, user_name: str, reset_token: str
) -> Dict[str, any]:
    """Send password reset email"""

    subject = f"Reset your {settings.PROJECT_NAME} password"

    reset_url = f"https://app.tidyframe.com/reset-password?token={reset_token}"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #2563eb;">Reset Your Password</h1>

            <p>Hi {user_name},</p>

            <p>You requested to reset your password for your {settings.PROJECT_NAME} account. Click the button below to set a new password.</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}"
                   style="display: inline-block; background-color: #dc2626; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Reset Password
                </a>
            </div>

            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #6b7280;">{reset_url}</p>

            <p style="color: #6b7280; font-size: 14px;">This reset link will expire in 1 hour.</p>

            <p>If you didn't request this password reset, please ignore this email.</p>

            <p>Best regards,<br>The {settings.PROJECT_NAME} Team</p>
        </div>
    </body>
    </html>
    """

    return send_email(user_email, subject, html_content)


@celery_app.task
def send_processing_complete_email(
    user_email: str, user_name: str, job_id: str, filename: str, results_summary: Dict
) -> Dict[str, any]:
    """Send email when file processing is complete"""

    subject = f"Your {settings.PROJECT_NAME} file processing is complete"

    download_url = f"https://app.tidyframe.com/download/{job_id}"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #2563eb;">Processing Complete!</h1>

            <p>Hi {user_name},</p>

            <p>Great news! Your file "<strong>{filename}</strong>" has been successfully processed.</p>

            <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #2563eb;">Processing Summary</h3>
                <ul style="margin-bottom: 0;">
                    <li><strong>Total Rows:</strong> {results_summary.get('total_rows', 0)}</li>
                    <li><strong>Successful Parses:</strong> {results_summary.get('successful_parses', 0)}</li>
                    <li><strong>Success Rate:</strong> {results_summary.get('success_rate', 0):.1f}%</li>
                </ul>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{download_url}"
                   style="display: inline-block; background-color: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Download Results
                </a>
            </div>

            <p style="color: #6b7280; font-size: 14px;">Your results will be available for download for the next 30 days.</p>

            <p>Best regards,<br>The {settings.PROJECT_NAME} Team</p>
        </div>
    </body>
    </html>
    """

    return send_email(user_email, subject, html_content)
