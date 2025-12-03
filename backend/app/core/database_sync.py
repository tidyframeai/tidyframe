"""
Synchronous database configuration for Celery workers
Uses the same models but with synchronous engine
"""

import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Configure logger
logger = structlog.get_logger()

# Convert async URL to sync URL for Celery
sync_database_url = settings.DATABASE_URL.replace("+asyncpg", "")

# Create synchronous engine for Celery workers
sync_engine = create_engine(
    sync_database_url,
    echo=False,  # Don't echo in Celery workers
    pool_size=5,  # Smaller pool for workers
    max_overflow=10,
    pool_pre_ping=True,
)

# Synchronous session for Celery workers
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
)


def get_sync_db():
    """
    Get synchronous database session for Celery workers
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
