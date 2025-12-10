"""
Authentication schemas
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.core.schemas import ResponseModel


class Token(BaseModel):
    """JWT token response"""

    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    """Token payload data"""

    user_id: Optional[str] = None


class ConsentData(BaseModel):
    """Legal consent data schema for user registration"""

    age_verified: bool
    terms_accepted: bool
    privacy_accepted: bool
    arbitration_acknowledged: bool
    location_confirmed: bool
    consent_timestamp: str
    user_agent: Optional[str] = None


class UserCreate(BaseModel):
    """User creation schema"""

    email: EmailStr
    password: str
    full_name: Optional[str] = None
    company: Optional[str] = None
    consent: Optional[ConsentData] = None


class PasswordResetRequest(BaseModel):
    """Password reset request schema"""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema"""

    token: str
    new_password: str


class EmailVerification(BaseModel):
    """Email verification schema"""

    token: str
