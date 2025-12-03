"""
Redis connection and utilities
Used for caching, session storage, and Celery broker
"""

import json
from typing import Any, Optional, Union

import redis.asyncio as redis
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class RedisClient:
    """Redis client wrapper with async support"""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.connected = False

    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.redis = redis.from_url(
                settings.REDIS_URL, encoding="utf-8", decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            self.connected = True
            logger.info("redis_connected", url=settings.REDIS_URL)
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            self.connected = False
            raise

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            self.connected = False
            logger.info("redis_disconnected")

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        if not self.connected:
            await self.connect()

        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error("redis_get_failed", key=key, error=str(e))
            return None

    async def set(
        self, key: str, value: Union[str, dict, list], expire: Optional[int] = None
    ) -> bool:
        """Set value in Redis with optional expiration"""
        if not self.connected:
            await self.connect()

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            if expire:
                return await self.redis.setex(key, expire, value)
            else:
                return await self.redis.set(key, value)
        except Exception as e:
            logger.error("redis_set_failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.connected:
            await self.connect()

        try:
            result = await self.redis.delete(key)
            return bool(result)
        except Exception as e:
            logger.error("redis_delete_failed", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self.connected:
            await self.connect()

        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error("redis_exists_failed", key=key, error=str(e))
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter in Redis"""
        if not self.connected:
            await self.connect()

        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error("redis_increment_failed", key=key, error=str(e))
            return None

    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value from Redis"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error("redis_json_decode_failed", key=key, error=str(e))
        return None

    async def set_json(
        self, key: str, value: Any, expire: Optional[int] = None
    ) -> bool:
        """Set JSON value in Redis"""
        return await self.set(key, value, expire)

    async def cache_with_ttl(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Cache value with default TTL"""
        if ttl is None:
            ttl = settings.REDIS_CACHE_TTL
        return await self.set_json(key, value, ttl)


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency function for getting Redis client"""
    if not redis_client.connected:
        await redis_client.connect()
    return redis_client


# Rate limiting utilities
async def check_rate_limit(
    identifier: str, limit: int, window_seconds: int = 60
) -> tuple[bool, int]:
    """
    Check if rate limit is exceeded
    Returns (allowed, current_count)
    """
    key = f"rate_limit:{identifier}"

    try:
        if not redis_client.connected:
            await redis_client.connect()

        current = await redis_client.redis.get(key)
        if current is None:
            # First request in window
            await redis_client.redis.setex(key, window_seconds, 1)
            return True, 1

        current = int(current)
        if current >= limit:
            return False, current

        # Increment counter
        await redis_client.redis.incr(key)
        return True, current + 1

    except Exception as e:
        logger.error("rate_limit_check_failed", identifier=identifier, error=str(e))
        # Allow request if Redis fails
        return True, 0


# Session management
async def store_session(session_id: str, data: dict, expire: int = 3600):
    """Store session data in Redis"""
    key = f"session:{session_id}"
    return await redis_client.set_json(key, data, expire)


async def get_session(session_id: str) -> Optional[dict]:
    """Get session data from Redis"""
    key = f"session:{session_id}"
    return await redis_client.get_json(key)


async def delete_session(session_id: str) -> bool:
    """Delete session from Redis"""
    key = f"session:{session_id}"
    return await redis_client.delete(key)


# Job progress tracking
async def set_job_progress(job_id: str, progress: int):
    """Store job progress in Redis"""
    key = f"job_progress:{job_id}"
    await redis_client.set(key, str(progress), expire=3600)


async def get_job_progress(job_id: str) -> Optional[int]:
    """Get job progress from Redis"""
    key = f"job_progress:{job_id}"
    progress = await redis_client.get(key)
    return int(progress) if progress else None
