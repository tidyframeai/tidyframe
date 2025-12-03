"""
User management API routes
"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_auth
from app.core.security import generate_api_key
from app.models.api_key import APIKey
from app.models.user import User
from app.schemas.auth import UserResponse

logger = structlog.get_logger()

router = APIRouter()


class UserProfile(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None


class APIKeyCreate(BaseModel):
    name: str


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key_hint: str
    created_at: str
    last_used_at: Optional[str] = None
    usage_count: int
    is_active: bool


@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(require_auth)):
    """Get user profile - returns data with camelCase fields"""
    return UserResponse.model_validate(current_user)


@router.put("/profile")
async def update_profile(
    profile_data: UserProfile,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update user profile"""

    current_user.first_name = profile_data.first_name
    current_user.last_name = profile_data.last_name
    current_user.company_name = profile_data.company_name

    await db.commit()

    return {"message": "Profile updated successfully"}


@router.post("/api-keys", response_model=dict)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create new API key"""

    # Generate API key
    api_key, key_hash = generate_api_key()
    key_hint = api_key[-4:]  # Last 4 characters

    # Create API key record
    new_key = APIKey(
        user_id=current_user.id,
        key_hash=key_hash,
        key_hint=key_hint,
        name=key_data.name,
    )

    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)

    logger.info("api_key_created", user_id=current_user.id, key_name=key_data.name)

    return {
        "api_key": api_key,  # Only returned once!
        "key_id": str(new_key.id),
        "name": key_data.name,
        "key_hint": key_hint,
        "message": "API key created successfully. Save it now - it won't be shown again!",
    }


@router.get("/api-keys")
async def list_api_keys(
    current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)
):
    """List user's API keys"""

    from sqlalchemy import select

    result = await db.execute(select(APIKey).where(APIKey.user_id == current_user.id))
    api_keys = result.scalars().all()

    return {
        "api_keys": [
            {
                "id": str(key.id),
                "name": key.name,
                "key_hint": f"...{key.key_hint}",
                "created_at": key.created_at.isoformat(),
                "last_used_at": (
                    key.last_used_at.isoformat() if key.last_used_at else None
                ),
                "usage_count": key.usage_count,
                "is_active": key.is_active,
            }
            for key in api_keys
        ]
    }


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delete API key"""

    import uuid

    from sqlalchemy import select

    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid key ID format"
        )

    result = await db.execute(
        select(APIKey).where(APIKey.id == key_uuid, APIKey.user_id == current_user.id)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    await db.delete(api_key)
    await db.commit()

    logger.info("api_key_deleted", user_id=current_user.id, key_id=key_id)

    return {"message": "API key deleted successfully"}
