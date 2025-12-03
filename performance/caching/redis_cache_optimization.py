"""
Redis Cache Optimization Module
Advanced caching strategies for improved performance
"""

import json
import hashlib
import time
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
from contextlib import asynccontextmanager
import asyncio
import structlog

from app.core.redis import redis_client, get_redis
from app.core.config import settings

logger = structlog.get_logger()


class CacheKeyGenerator:
    """Intelligent cache key generation"""
    
    @staticmethod
    def user_profile(user_id: str) -> str:
        return f"user:profile:{user_id}"
    
    @staticmethod
    def user_jobs(user_id: str, limit: int = 50, offset: int = 0) -> str:
        return f"user:jobs:{user_id}:limit:{limit}:offset:{offset}"
    
    @staticmethod
    def user_stats(user_id: str) -> str:
        return f"user:stats:{user_id}"
    
    @staticmethod
    def job_details(job_id: str) -> str:
        return f"job:details:{job_id}"
    
    @staticmethod
    def job_progress(job_id: str) -> str:
        return f"job:progress:{job_id}"
    
    @staticmethod
    def api_response(endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key for API responses"""
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        return f"api:{endpoint}:{params_hash}"
    
    @staticmethod
    def dashboard_data(user_id: str) -> str:
        return f"dashboard:{user_id}"
    
    @staticmethod
    def admin_stats() -> str:
        return "admin:stats:global"


class CacheManager:
    """Advanced cache management with invalidation strategies"""
    
    def __init__(self):
        self.redis = redis_client
        self.default_ttl = settings.REDIS_CACHE_TTL
        self._cache_tags = {}  # For tag-based invalidation
        
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value with error handling"""
        try:
            data = await self.redis.get_json(key)
            if data:
                logger.debug("cache_hit", key=key)
                return data
            logger.debug("cache_miss", key=key)
            return None
        except Exception as e:
            logger.error("cache_get_error", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: List[str] = None) -> bool:
        """Set cached value with optional tags for invalidation"""
        try:
            ttl = ttl or self.default_ttl
            success = await self.redis.set_json(key, value, ttl)
            
            # Store tags for invalidation
            if tags and success:
                for tag in tags:
                    if tag not in self._cache_tags:
                        self._cache_tags[tag] = set()
                    self._cache_tags[tag].add(key)
            
            if success:
                logger.debug("cache_set", key=key, ttl=ttl, tags=tags)
            
            return success
        except Exception as e:
            logger.error("cache_set_error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete cached value"""
        try:
            success = await self.redis.delete(key)
            if success:
                logger.debug("cache_delete", key=key)
                # Remove from tag mappings
                for tag_keys in self._cache_tags.values():
                    tag_keys.discard(key)
            return success
        except Exception as e:
            logger.error("cache_delete_error", key=key, error=str(e))
            return False
    
    async def invalidate_by_tags(self, tags: List[str]) -> int:
        """Invalidate all cache entries with specified tags"""
        keys_to_delete = set()
        
        for tag in tags:
            if tag in self._cache_tags:
                keys_to_delete.update(self._cache_tags[tag])
                del self._cache_tags[tag]
        
        if keys_to_delete:
            deleted_count = 0
            for key in keys_to_delete:
                if await self.delete(key):
                    deleted_count += 1
            
            logger.info("cache_tag_invalidation", tags=tags, deleted_count=deleted_count)
            return deleted_count
        
        return 0
    
    async def warm_cache(self, warm_functions: List[Callable]) -> None:
        """Pre-warm cache with frequently accessed data"""
        logger.info("cache_warming_started")
        
        for func in warm_functions:
            try:
                await func()
            except Exception as e:
                logger.error("cache_warming_error", function=func.__name__, error=str(e))
        
        logger.info("cache_warming_completed")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and health metrics"""
        try:
            info = await self.redis.redis.info()
            
            return {
                'redis_version': info.get('redis_version'),
                'used_memory': info.get('used_memory_human'),
                'used_memory_peak': info.get('used_memory_peak_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                ),
                'cached_tags_count': len(self._cache_tags),
                'total_tagged_keys': sum(len(keys) for keys in self._cache_tags.values())
            }
        except Exception as e:
            logger.error("cache_stats_error", error=str(e))
            return {}
    
    @staticmethod
    def _calculate_hit_rate(hits: int, misses: int) -> float:
        """Calculate cache hit rate"""
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0


# Global cache manager instance
cache_manager = CacheManager()


def cached(key_generator: Callable, ttl: Optional[int] = None, tags: List[str] = None):
    """
    Decorator for caching function results
    
    Args:
        key_generator: Function to generate cache key
        ttl: Time to live in seconds
        tags: Tags for cache invalidation
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = key_generator(*args, **kwargs)
            
            # Try to get from cache first
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            if result is not None:
                await cache_manager.set(cache_key, result, ttl, tags)
            
            return result
        return wrapper
    return decorator


class CacheInvalidator:
    """Handles cache invalidation strategies"""
    
    @staticmethod
    async def invalidate_user_caches(user_id: str):
        """Invalidate all user-related caches"""
        tags_to_invalidate = [f"user:{user_id}", f"dashboard:{user_id}"]
        await cache_manager.invalidate_by_tags(tags_to_invalidate)
    
    @staticmethod
    async def invalidate_job_caches(job_id: str, user_id: str):
        """Invalidate job-related caches"""
        # Delete specific job cache
        await cache_manager.delete(CacheKeyGenerator.job_details(job_id))
        await cache_manager.delete(CacheKeyGenerator.job_progress(job_id))
        
        # Invalidate user caches that might include this job
        await CacheInvalidator.invalidate_user_caches(user_id)
    
    @staticmethod
    async def invalidate_admin_caches():
        """Invalidate admin dashboard caches"""
        await cache_manager.delete(CacheKeyGenerator.admin_stats())


class SessionCacheManager:
    """Specialized session management with Redis"""
    
    def __init__(self):
        self.session_prefix = "session:"
        self.session_ttl = 24 * 3600  # 24 hours
    
    async def create_session(self, user_id: str, session_data: Dict[str, Any]) -> str:
        """Create new user session"""
        session_id = hashlib.sha256(f"{user_id}:{time.time()}".encode()).hexdigest()
        session_key = f"{self.session_prefix}{session_id}"
        
        session_data.update({
            'user_id': user_id,
            'created_at': time.time(),
            'last_activity': time.time()
        })
        
        await cache_manager.set(session_key, session_data, self.session_ttl)
        logger.info("session_created", user_id=user_id, session_id=session_id)
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        session_key = f"{self.session_prefix}{session_id}"
        return await cache_manager.get(session_key)
    
    async def update_session_activity(self, session_id: str):
        """Update session last activity timestamp"""
        session_data = await self.get_session(session_id)
        if session_data:
            session_data['last_activity'] = time.time()
            session_key = f"{self.session_prefix}{session_id}"
            await cache_manager.set(session_key, session_data, self.session_ttl)
    
    async def destroy_session(self, session_id: str):
        """Destroy user session"""
        session_key = f"{self.session_prefix}{session_id}"
        await cache_manager.delete(session_key)
        logger.info("session_destroyed", session_id=session_id)


# API Response Cache Middleware
class APICacheMiddleware:
    """Middleware for caching API responses"""
    
    CACHEABLE_METHODS = {'GET'}
    DEFAULT_CACHE_TTL = 300  # 5 minutes
    
    ENDPOINT_TTL_MAPPING = {
        '/api/v1/users/me': 600,  # 10 minutes
        '/api/v1/jobs': 120,      # 2 minutes
        '/api/v1/dashboard/stats': 180,  # 3 minutes
        '/api/v1/admin/stats': 600,      # 10 minutes
    }
    
    @staticmethod
    def get_cache_key(request) -> str:
        """Generate cache key for request"""
        path = request.url.path
        query_params = dict(request.query_params)
        user_id = getattr(request.state, 'user_id', 'anonymous')
        
        return CacheKeyGenerator.api_response(
            f"{user_id}:{path}",
            query_params
        )
    
    @staticmethod
    def get_cache_ttl(path: str) -> int:
        """Get cache TTL for endpoint"""
        return APICacheMiddleware.ENDPOINT_TTL_MAPPING.get(
            path, 
            APICacheMiddleware.DEFAULT_CACHE_TTL
        )
    
    @staticmethod
    async def get_cached_response(request) -> Optional[Dict[str, Any]]:
        """Get cached API response"""
        if request.method not in APICacheMiddleware.CACHEABLE_METHODS:
            return None
            
        cache_key = APICacheMiddleware.get_cache_key(request)
        return await cache_manager.get(cache_key)
    
    @staticmethod
    async def cache_response(request, response_data: Any):
        """Cache API response"""
        if request.method not in APICacheMiddleware.CACHEABLE_METHODS:
            return
            
        cache_key = APICacheMiddleware.get_cache_key(request)
        ttl = APICacheMiddleware.get_cache_ttl(request.url.path)
        
        # Add user-specific tags for invalidation
        user_id = getattr(request.state, 'user_id', None)
        tags = [f"user:{user_id}"] if user_id else []
        
        await cache_manager.set(cache_key, response_data, ttl, tags)


# Cache warming functions
async def warm_user_cache(user_id: str):
    """Pre-warm cache for user data"""
    # This would be called by actual service functions
    # to pre-populate frequently accessed data
    pass


async def warm_admin_cache():
    """Pre-warm cache for admin dashboard"""
    # Pre-populate admin statistics
    pass


# Cache health check
async def check_cache_health() -> Dict[str, Any]:
    """Check Redis cache health and performance"""
    try:
        start_time = time.time()
        
        # Test basic operations
        test_key = "health_check_test"
        test_value = {"timestamp": time.time()}
        
        # Test set
        await cache_manager.set(test_key, test_value, 60)
        
        # Test get
        retrieved = await cache_manager.get(test_key)
        
        # Test delete
        await cache_manager.delete(test_key)
        
        operation_time = time.time() - start_time
        
        # Get cache stats
        stats = await cache_manager.get_cache_stats()
        
        return {
            'status': 'healthy',
            'operation_time_ms': round(operation_time * 1000, 2),
            'test_passed': retrieved == test_value,
            'stats': stats
        }
        
    except Exception as e:
        logger.error("cache_health_check_failed", error=str(e))
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


# Export cache instances
session_cache = SessionCacheManager()