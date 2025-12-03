"""
Pydantic schemas for authentication endpoints
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, validator


class ConsentData(BaseModel):
    """Legal consent data for GDPR/CCPA compliance"""

    age_verified: bool
    terms_accepted: bool
    privacy_accepted: bool
    arbitration_acknowledged: bool
    location_confirmed: bool
    consent_timestamp: str
    user_agent: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    consent: Optional[ConsentData] = None

    @validator("password")
    def validate_password(cls, v):
        from app.core.security import validate_password_strength

        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            raise ValueError("; ".join(errors))

        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    company_name: Optional[str]
    plan: str
    parsesThisMonth: int = Field(
        alias="parses_this_month", serialization_alias="parsesThisMonth"
    )
    monthlyLimit: int = Field(alias="monthly_limit", serialization_alias="monthlyLimit")
    is_premium: bool
    email_verified: bool
    is_admin: bool  # Critical for admin access
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "alias_generator": None,
    }


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshToken(BaseModel):
    refresh_token: str


class PasswordReset(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str

    @validator("password")
    def validate_password(cls, v):
        from app.core.security import validate_password_strength

        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            raise ValueError("; ".join(errors))

        return v


class EmailVerify(BaseModel):
    token: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str

    @validator("new_password")
    def validate_new_password(cls, v):
        from app.core.security import validate_password_strength

        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            raise ValueError("; ".join(errors))

        return v


class GoogleAuthURL(BaseModel):
    auth_url: str
    state: str


class GoogleCallback(BaseModel):
    code: str
    state: str
