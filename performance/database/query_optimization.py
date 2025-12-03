"""
Database Query Optimization Module
Identifies and fixes N+1 queries, adds indexes, and optimizes database operations
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from sqlalchemy.orm import selectinload, joinedload
import structlog
import asyncio
from contextlib import asynccontextmanager
import time

from app.core.database import engine
from app.models.user import User
from app.models.job import ProcessingJob
from app.models.parse_log import ParseLog

logger = structlog.get_logger()


class QueryOptimizer:
    """Database query optimization utilities"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
    @asynccontextmanager
    async def query_profiler(self, query_name: str):
        """Context manager to profile query execution time"""
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            logger.info(
                "query_profiled",
                query_name=query_name,
                execution_time_ms=round(execution_time * 1000, 2)
            )
    
    async def get_user_with_jobs_optimized(self, user_id: str) -> Optional[User]:
        """
        Optimized version that eagerly loads jobs to avoid N+1 queries
        Uses selectinload for one-to-many relationships
        """
        async with self.query_profiler("get_user_with_jobs_optimized"):
            stmt = select(User).options(
                selectinload(User.jobs).selectinload(ProcessingJob.parse_logs)
            ).where(User.id == user_id)
            
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_user_jobs_with_stats(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Optimized query to get user jobs with aggregated statistics
        Avoids multiple queries by using SQL aggregations
        """
        async with self.query_profiler("get_user_jobs_with_stats"):
            stmt = text("""
                SELECT 
                    j.id,
                    j.filename,
                    j.status,
                    j.progress,
                    j.created_at,
                    j.completed_at,
                    j.row_count,
                    j.successful_parses,
                    j.failed_parses,
                    COUNT(pl.id) as log_count,
                    AVG(CASE WHEN pl.confidence_score IS NOT NULL 
                        THEN pl.confidence_score ELSE 0 END) as avg_confidence
                FROM processing_jobs j
                LEFT JOIN parse_logs pl ON j.id = pl.job_id
                WHERE j.user_id = :user_id
                GROUP BY j.id, j.filename, j.status, j.progress, 
                         j.created_at, j.completed_at, j.row_count,
                         j.successful_parses, j.failed_parses
                ORDER BY j.created_at DESC
            """)
            
            result = await self.db.execute(stmt, {"user_id": user_id})
            return [dict(row._mapping) for row in result.fetchall()]
    
    async def get_dashboard_stats_optimized(self, user_id: str) -> Dict[str, Any]:
        """
        Single optimized query for dashboard statistics
        Replaces multiple separate queries
        """
        async with self.query_profiler("get_dashboard_stats_optimized"):
            stmt = text("""
                WITH job_stats AS (
                    SELECT 
                        COUNT(*) as total_jobs,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_jobs,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs,
                        COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_jobs,
                        SUM(COALESCE(successful_parses, 0)) as total_successful_parses,
                        SUM(COALESCE(failed_parses, 0)) as total_failed_parses,
                        AVG(CASE WHEN processing_time_ms IS NOT NULL 
                            THEN processing_time_ms ELSE 0 END) as avg_processing_time
                    FROM processing_jobs 
                    WHERE user_id = :user_id
                        AND created_at >= NOW() - INTERVAL '30 days'
                ),
                recent_activity AS (
                    SELECT COUNT(*) as recent_jobs
                    FROM processing_jobs 
                    WHERE user_id = :user_id
                        AND created_at >= NOW() - INTERVAL '7 days'
                )
                SELECT 
                    js.total_jobs,
                    js.completed_jobs,
                    js.failed_jobs,
                    js.processing_jobs,
                    js.total_successful_parses,
                    js.total_failed_parses,
                    ROUND(js.avg_processing_time, 2) as avg_processing_time_ms,
                    ra.recent_jobs,
                    CASE WHEN js.total_successful_parses + js.total_failed_parses > 0
                        THEN ROUND(
                            (js.total_successful_parses::float / 
                            (js.total_successful_parses + js.total_failed_parses)) * 100, 2
                        )
                        ELSE 0
                    END as success_rate_percentage
                FROM job_stats js
                CROSS JOIN recent_activity ra
            """)
            
            result = await self.db.execute(stmt, {"user_id": user_id})
            row = result.fetchone()
            return dict(row._mapping) if row else {}
    
    async def get_top_users_by_usage(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Optimized query for admin dashboard - top users by usage
        Single query with joins instead of N+1
        """
        async with self.query_profiler("get_top_users_by_usage"):
            stmt = text("""
                SELECT 
                    u.id,
                    u.email,
                    u.first_name,
                    u.last_name,
                    u.plan,
                    u.parses_this_month,
                    COUNT(j.id) as total_jobs,
                    SUM(COALESCE(j.successful_parses, 0)) as total_parses,
                    MAX(j.created_at) as last_job_date
                FROM users u
                LEFT JOIN processing_jobs j ON u.id = j.user_id
                WHERE u.plan != 'anonymous'
                GROUP BY u.id, u.email, u.first_name, u.last_name, u.plan, u.parses_this_month
                ORDER BY total_parses DESC NULLS LAST
                LIMIT :limit
            """)
            
            result = await self.db.execute(stmt, {"limit": limit})
            return [dict(row._mapping) for row in result.fetchall()]


async def add_missing_indexes():
    """
    Add missing database indexes for frequently queried columns
    This significantly improves query performance
    """
    indexes_to_create = [
        # User table indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_active ON users(email) WHERE is_active = true;",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_plan_active ON users(plan) WHERE is_active = true;",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_login ON users(last_login_at);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_stripe_customer ON users(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;",
        
        # Processing jobs indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_user_created ON processing_jobs(user_id, created_at DESC);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_status_created ON processing_jobs(status, created_at DESC);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_user_status ON processing_jobs(user_id, status);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_expires_at ON processing_jobs(expires_at) WHERE expires_at IS NOT NULL;",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_completed_at ON processing_jobs(completed_at) WHERE completed_at IS NOT NULL;",
        
        # Parse logs indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_parse_logs_job_created ON parse_logs(job_id, created_at);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_parse_logs_confidence ON parse_logs(confidence_score) WHERE confidence_score IS NOT NULL;",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_parse_logs_user_created ON parse_logs(user_id, created_at) WHERE user_id IS NOT NULL;",
        
        # Composite indexes for common queries
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_user_status_created ON processing_jobs(user_id, status, created_at DESC);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_verified_active ON users(email, email_verified, is_active);",
        
        # API key indexes (if api_key model exists)
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_keys_user_active ON api_keys(user_id, is_active) WHERE is_active = true;",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash) WHERE is_active = true;",
    ]
    
    async with engine.begin() as conn:
        for index_sql in indexes_to_create:
            try:
                await conn.execute(text(index_sql))
                logger.info("index_created", sql=index_sql)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning("index_creation_failed", sql=index_sql, error=str(e))


async def analyze_slow_queries():
    """
    Analyze and identify slow queries in the database
    Returns recommendations for optimization
    """
    slow_query_analysis = text("""
        SELECT 
            query,
            calls,
            total_time,
            mean_time,
            max_time,
            stddev_time,
            rows
        FROM pg_stat_statements 
        WHERE mean_time > 100  -- Queries slower than 100ms
        ORDER BY total_time DESC
        LIMIT 20;
    """)
    
    try:
        async with engine.begin() as conn:
            # Enable pg_stat_statements if not enabled
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"))
            
            result = await conn.execute(slow_query_analysis)
            slow_queries = [dict(row._mapping) for row in result.fetchall()]
            
            logger.info("slow_queries_analyzed", count=len(slow_queries))
            return slow_queries
            
    except Exception as e:
        logger.error("slow_query_analysis_failed", error=str(e))
        return []


async def optimize_database_settings():
    """
    Apply database optimization settings for better performance
    """
    optimization_settings = [
        # Memory settings
        "ALTER SYSTEM SET shared_buffers = '256MB';",
        "ALTER SYSTEM SET effective_cache_size = '1GB';",
        "ALTER SYSTEM SET maintenance_work_mem = '64MB';",
        "ALTER SYSTEM SET work_mem = '16MB';",
        
        # Query optimization
        "ALTER SYSTEM SET random_page_cost = 1.1;",  # For SSD storage
        "ALTER SYSTEM SET effective_io_concurrency = 200;",  # For SSD
        
        # Logging for performance monitoring
        "ALTER SYSTEM SET log_min_duration_statement = 1000;",  # Log queries > 1s
        "ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';",
        
        # Checkpoint settings
        "ALTER SYSTEM SET checkpoint_completion_target = 0.9;",
        "ALTER SYSTEM SET wal_buffers = '16MB';",
        
        # Connection settings
        "ALTER SYSTEM SET max_connections = 200;",
    ]
    
    try:
        async with engine.begin() as conn:
            for setting in optimization_settings:
                await conn.execute(text(setting))
            
            # Reload configuration
            await conn.execute(text("SELECT pg_reload_conf();"))
            
            logger.info("database_settings_optimized")
            
    except Exception as e:
        logger.error("database_optimization_failed", error=str(e))


class QueryBatcher:
    """Batch multiple queries to reduce database round trips"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._batch = []
        
    def add_query(self, query, params=None):
        """Add query to batch"""
        self._batch.append((query, params or {}))
        
    async def execute_batch(self) -> List[Any]:
        """Execute all batched queries"""
        if not self._batch:
            return []
            
        results = []
        async with self.db.begin():
            for query, params in self._batch:
                result = await self.db.execute(query, params)
                results.append(result)
                
        self._batch.clear()
        return results
        

async def setup_database_optimizations():
    """
    Setup all database optimizations
    Should be called during application startup
    """
    logger.info("starting_database_optimizations")
    
    try:
        # Add missing indexes
        await add_missing_indexes()
        
        # Optimize database settings
        await optimize_database_settings()
        
        # Analyze slow queries
        slow_queries = await analyze_slow_queries()
        if slow_queries:
            logger.warning("slow_queries_detected", count=len(slow_queries))
        
        logger.info("database_optimizations_completed")
        
    except Exception as e:
        logger.error("database_optimizations_failed", error=str(e))
        raise