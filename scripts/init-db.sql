-- =============================================================================
-- TidyFrame Database Initialization Script
-- Creates database, user, and initial schema setup
-- =============================================================================

-- Create application database if it doesn't exist
-- This is handled by the POSTGRES_DB environment variable in Docker

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Note: pg_stat_statements requires shared_preload_libraries to be set first
-- It will be created after restart with proper configuration
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for performance
-- These will be created by Alembic migrations, but we can add some basic ones here

-- Performance and monitoring setup
-- The pg_stat_statements_reset() will be called after the extension is properly loaded

-- Create a function to clean old data based on retention policies
CREATE OR REPLACE FUNCTION cleanup_expired_data()
RETURNS void AS $$
BEGIN
    -- This function will be implemented by the application
    -- It's just a placeholder for now
    RAISE NOTICE 'Cleanup function placeholder - implement in application code';
END;
$$ LANGUAGE plpgsql;

-- Create a scheduled job to run cleanup (requires pg_cron extension if available)
-- This is typically handled by the application's Celery beat scheduler

-- Database performance settings are handled via docker-compose environment variables
-- or postgresql.conf in production environments
