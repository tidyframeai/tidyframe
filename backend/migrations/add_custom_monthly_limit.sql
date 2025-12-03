-- Add custom_monthly_limit column to users table
-- This allows admins to set custom limits that override plan defaults

ALTER TABLE users ADD COLUMN IF NOT EXISTS custom_monthly_limit INTEGER;

-- Add comment to explain the column
COMMENT ON COLUMN users.custom_monthly_limit IS 'Admin-configurable custom monthly parse limit that overrides plan defaults';

-- Index for faster queries when filtering by custom limits
CREATE INDEX IF NOT EXISTS idx_users_custom_monthly_limit ON users(custom_monthly_limit) WHERE custom_monthly_limit IS NOT NULL;