"""
Schemas for site password API
"""

from pydantic import BaseModel, Field


class SitePasswordRequest(BaseModel):
    """Request model for site password authentication"""

    password: str = Field(
        ..., min_length=1, max_length=100, description="Site password"
    )


class SitePasswordResponse(BaseModel):
    """Response model for site password operations"""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Success or error message")


class SitePasswordStatusResponse(BaseModel):
    """Response model for site password status check"""

    enabled: bool = Field(
        ..., description="Whether site password protection is enabled"
    )
    authenticated: bool = Field(
        ..., description="Whether the current session is authenticated"
    )
