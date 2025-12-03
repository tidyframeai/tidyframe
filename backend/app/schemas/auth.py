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


class UserResponse(ResponseModel):
    """User response schema with automatic camelCase conversion"""

    id: str
    email: str
    full_name: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    company_name: Optional[str]
    plan: str
    is_active: bool
    email_verified: bool
    is_admin: bool  # Critical for admin access
    created_at: datetime
    updated_at: Optional[datetime]
    parses_this_month: int
    monthly_limit: int
    month_reset_date: Optional[datetime]
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


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
