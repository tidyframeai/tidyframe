"""
Security utilities for authentication and password handling
"""

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import structlog
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = structlog.get_logger()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    SECURITY-ENHANCED: Create JWT access token with proper validation

    Args:
        data: Data to encode in token
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    # SECURITY: Validate input data
    if not data or not isinstance(data, dict):
        raise ValueError("Invalid token data")

    # SECURITY: Ensure required fields are present
    if "sub" not in data:
        raise ValueError("Token data must include 'sub' (user ID)")

    to_encode = data.copy()
    current_time = datetime.now(timezone.utc)

    if expires_delta:
        expire = current_time + expires_delta
    else:
        expire = current_time + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # SECURITY: Add comprehensive token claims
    to_encode.update(
        {
            "exp": expire,
            "iat": current_time,  # Issued at
            "nbf": current_time,  # Not before
            "type": "access",
            "jti": secrets.token_urlsafe(16),  # JWT ID for revocation support
        }
    )

    # SECURITY: Validate SECRET_KEY before encoding
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters long")

    try:
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error("token_creation_failed", error=str(e))
        raise ValueError(f"Failed to create token: {str(e)}")


def create_refresh_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token

    Args:
        data: Data to encode in token
        expires_delta: Token expiration time

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    SECURITY-ENHANCED: Verify and decode JWT token with strict validation

    Args:
        token: JWT token to verify

    Returns:
        Decoded token payload or None if invalid
    """
    if not token or len(token) < 10:
        logger.warning("jwt_verification_failed", reason="invalid_token_format")
        return None

    # SECURITY: Check for obviously malicious tokens
    if "../" in token or "<script" in token.lower():
        logger.warning("jwt_verification_failed", reason="malicious_token_detected")
        return None

    try:
        # SECURITY: Strict algorithm validation
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": False,  # We don't use audience
                "verify_iss": False,  # We don't use issuer
            },
        )

        # SECURITY: Validate required claims
        required_claims = ["sub", "exp", "type"]
        for claim in required_claims:
            if claim not in payload:
                logger.warning(
                    "jwt_verification_failed", reason=f"missing_claim_{claim}"
                )
                return None

        # SECURITY: Validate token type
        token_type = payload.get("type")
        if token_type not in ["access", "refresh"]:
            logger.warning(
                "jwt_verification_failed", reason="invalid_token_type", type=token_type
            )
            return None

        # SECURITY: Validate expiration (double-check)
        exp = payload.get("exp")
        if exp is None:
            logger.warning("jwt_verification_failed", reason="missing_expiration")
            return None

        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        if exp_datetime < datetime.now(timezone.utc):
            logger.warning("jwt_verification_failed", reason="token_expired")
            return None

        # SECURITY: Check not-before claim if present
        nbf = payload.get("nbf")
        if nbf is not None:
            nbf_datetime = datetime.fromtimestamp(nbf, tz=timezone.utc)
            if nbf_datetime > datetime.now(timezone.utc):
                logger.warning("jwt_verification_failed", reason="token_not_yet_valid")
                return None

        # SECURITY: Validate user ID format
        user_id = payload.get("sub")
        if not user_id or not isinstance(user_id, str):
            logger.warning("jwt_verification_failed", reason="invalid_user_id")
            return None

        # SECURITY: Additional validation for email if present
        email = payload.get("email")
        if email and ("@" not in email or len(email) > 254):
            logger.warning("jwt_verification_failed", reason="invalid_email_format")
            return None

        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("jwt_verification_failed", reason="signature_expired")
        return None
    except jwt.JWTError as e:
        # JWTError is the parent class that covers all JWT-related errors
        error_type = type(e).__name__
        logger.warning(
            "jwt_verification_failed",
            reason="jwt_error",
            error_type=error_type,
            error=str(e),
        )
        return None
    except Exception as e:
        logger.error("jwt_verification_error", reason="unexpected_error", error=str(e))
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password strength requirements

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(
            f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long"
        )

    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")

    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        errors.append("Password must contain at least one special character")

    return len(errors) == 0, errors


def generate_api_key() -> tuple[str, str]:
    """
    Generate API key and its hash

    Returns:
        Tuple of (api_key, api_key_hash)
    """
    # Generate API key with format: tf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    key_length = 32
    key_chars = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(key_chars) for _ in range(key_length))
    api_key = f"tf_{random_part}"

    # Hash the API key for storage
    api_key_hash = get_password_hash(api_key)

    return api_key, api_key_hash


def generate_secure_token(length: int = 32) -> str:
    """
    Generate cryptographically secure random token

    Args:
        length: Token length

    Returns:
        Secure random token
    """
    return secrets.token_urlsafe(length)


def generate_verification_token() -> str:
    """
    Generate email verification token

    Returns:
        Verification token
    """
    return generate_secure_token(48)


def generate_reset_token() -> str:
    """
    Generate password reset token

    Returns:
        Password reset token
    """
    return generate_secure_token(48)


def hash_api_key(api_key: str) -> str:
    """
    Hash API key for comparison

    Args:
        api_key: Plain API key

    Returns:
        Hashed API key
    """
    return get_password_hash(api_key)


def verify_api_key(api_key: str, hashed_api_key: str) -> bool:
    """
    Verify API key against hash

    Args:
        api_key: Plain API key
        hashed_api_key: Hashed API key from database

    Returns:
        True if API key matches
    """
    return verify_password(api_key, hashed_api_key)


def create_user_tokens(
    user_id: str, email: str, is_admin: bool = False
) -> Dict[str, str]:
    """
    Create both access and refresh tokens for user

    Args:
        user_id: User ID
        email: User email
        is_admin: Whether user is admin

    Returns:
        Dict containing access_token and refresh_token
    """
    access_token_data = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "is_admin": is_admin,  # Include admin status
    }

    refresh_token_data = {
        "sub": str(user_id),
        "email": email,
        "type": "refresh",
        "is_admin": is_admin,  # Include admin status
    }

    access_token = create_access_token(access_token_data)
    refresh_token = create_refresh_token(refresh_token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
