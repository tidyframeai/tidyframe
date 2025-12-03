"""
API Keys management router
Handles API key creation, listing, and revocation for authenticated users
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_auth
from app.core.security import generate_api_key
from app.models.api_key import APIKey
from app.models.user import User

logger = structlog.get_logger()

router = APIRouter()


# Pydantic models for API responses


class APIKeyRequest(BaseModel):
    """Request model for creating API key"""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Name for the API key"
    )
    expires_days: Optional[int] = Field(
        None, ge=1, le=365, description="Days until expiration (optional)"
    )


class APIKeyResponse(BaseModel):
    """Response model for API key (without the actual key)"""

    id: UUID
    name: str
    key_hint: str
    is_active: bool
    usage_count: int
    last_used_at: Optional[datetime]
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeyCreatedResponse(BaseModel):
    """Response model when API key is created (includes the actual key)"""

    id: UUID
    name: str
    api_key: str  # Full API key - only shown once
    key_hint: str
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)
):
    """
    List all API keys for the current user
    """
    try:
        result = await db.execute(
            select(APIKey)
            .where(APIKey.user_id == current_user.id)
            .order_by(APIKey.created_at.desc())
        )

        api_keys = result.scalars().all()

        logger.info(
            "api_keys_listed", user_id=str(current_user.id), key_count=len(api_keys)
        )

        return api_keys

    except Exception as e:
        logger.error("api_keys_list_failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API keys",
        )


@router.post(
    "/", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    request: APIKeyRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new API key for the current user
    """
    try:
        # Check if user already has too many API keys
        result = await db.execute(
            select(APIKey).where(APIKey.user_id == current_user.id, APIKey.is_active)
        )

        active_keys = result.scalars().all()
        max_keys = 10  # Limit to 10 active keys per user

        if len(active_keys) >= max_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum number of active API keys reached ({max_keys})",
            )

        # Check if name already exists for this user
        result = await db.execute(
            select(APIKey).where(
                APIKey.user_id == current_user.id,
                APIKey.name == request.name,
                APIKey.is_active,
            )
        )

        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API key with this name already exists",
            )

        # Generate API key and hash
        api_key, api_key_hash = generate_api_key()
        key_hint = f"...{api_key[-4:]}"  # Last 4 characters for display

        # Calculate expiration date
        expires_at = None
        if request.expires_days:
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=request.expires_days
            )

        # Create API key record
        new_api_key = APIKey(
            user_id=current_user.id,
            key_hash=api_key_hash,
            key_hint=key_hint,
            name=request.name,
            expires_at=expires_at,
        )

        db.add(new_api_key)
        await db.commit()
        await db.refresh(new_api_key)

        logger.info(
            "api_key_created",
            user_id=str(current_user.id),
            key_id=str(new_api_key.id),
            key_name=request.name,
            expires_at=expires_at.isoformat() if expires_at else None,
        )

        # Return response with the actual API key (only time it's shown)
        return APIKeyCreatedResponse(
            id=new_api_key.id,
            name=new_api_key.name,
            api_key=api_key,  # Full key - only returned once
            key_hint=new_api_key.key_hint,
            expires_at=new_api_key.expires_at,
            created_at=new_api_key.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "api_key_creation_failed",
            user_id=str(current_user.id),
            key_name=request.name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key",
        )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke (delete) an API key
    """
    try:
        # Find the API key belonging to the current user
        result = await db.execute(
            select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
        )

        api_key = result.scalar_one_or_none()

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )

        # Delete the API key
        await db.delete(api_key)
        await db.commit()

        logger.info(
            "api_key_revoked",
            user_id=str(current_user.id),
            key_id=str(key_id),
            key_name=api_key.name,
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "api_key_revocation_failed",
            user_id=str(current_user.id),
            key_id=str(key_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key",
        )


@router.patch("/{key_id}/toggle", response_model=APIKeyResponse)
async def toggle_api_key_status(
    key_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Toggle API key active/inactive status
    """
    try:
        # Find the API key belonging to the current user
        result = await db.execute(
            select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
        )

        api_key = result.scalar_one_or_none()

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )

        # Toggle the active status
        api_key.is_active = not api_key.is_active
        await db.commit()
        await db.refresh(api_key)

        logger.info(
            "api_key_toggled",
            user_id=str(current_user.id),
            key_id=str(key_id),
            key_name=api_key.name,
            new_status=api_key.is_active,
        )

        return api_key

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "api_key_toggle_failed",
            user_id=str(current_user.id),
            key_id=str(key_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle API key status",
        )
