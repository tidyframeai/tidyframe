"""
Database configuration and session management
SQLAlchemy async setup for PostgreSQL
"""

import structlog
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Configure logger
logger = structlog.get_logger()

# SQLAlchemy setup
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

Base = declarative_base(metadata=metadata)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=settings.DATABASE_POOL_PRE_PING,
    poolclass=NullPool if settings.ENVIRONMENT == "test" else None,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncSession:
    """
    Dependency function to get database session
    Use with FastAPI's Depends()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error("database_session_error", error=str(e))
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all database tables"""
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            pass

            await conn.run_sync(Base.metadata.create_all)
            logger.info("database_tables_created")
    except Exception as e:
        logger.error("database_tables_creation_failed", error=str(e))
        raise


async def drop_tables():
    """Drop all database tables (for testing)"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("database_tables_dropped")
    except Exception as e:
        logger.error("database_tables_drop_failed", error=str(e))
        raise
