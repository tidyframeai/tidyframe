/**
 * Centralized constants for the TidyFrame application
 * Eliminates hardcoded values and provides single source of truth
 */

// File size limits per plan (in bytes)
export const FILE_SIZE_LIMITS = {
  ANONYMOUS: 1 * 1024 * 1024,      // 1MB
  STANDARD: 50 * 1024 * 1024,      // 50MB
  ENTERPRISE: 200 * 1024 * 1024,   // 200MB
} as const;

// Monthly parse limits per plan
export const PARSE_LIMITS = {
  ANONYMOUS: 5,                     // 5 total lifetime for anonymous
  STANDARD: 100_000,                // 100k per month
  ENTERPRISE: 10_000_000,           // 10M per month (effectively unlimited)
} as const;

// Plan configuration
export const PLAN_CONFIG = {
  anonymous: {
    maxFileSize: FILE_SIZE_LIMITS.ANONYMOUS,
    maxParses: PARSE_LIMITS.ANONYMOUS,
    planName: 'Anonymous Trial',
    planColor: 'bg-muted',
  },
  standard: {
    maxFileSize: FILE_SIZE_LIMITS.STANDARD,
    maxParses: PARSE_LIMITS.STANDARD,
    planName: 'Standard',
    planColor: 'bg-primary',
  },
  enterprise: {
    maxFileSize: FILE_SIZE_LIMITS.ENTERPRISE,
    maxParses: PARSE_LIMITS.ENTERPRISE,
    planName: 'Enterprise',
    planColor: 'bg-secondary',
  },
} as const;

// Polling and timing intervals (in milliseconds)
export const INTERVALS = {
  JOB_POLL: 3000,                   // Poll job status every 3 seconds
  FILE_EXPIRY: 10 * 60 * 1000,      // Files expire after 10 minutes
  SESSION_TIMEOUT: 30 * 60 * 1000,  // Session timeout after 30 minutes
} as const;

// Processing estimates
export const PROCESSING = {
  MS_PER_ROW: 50,                   // Estimated 50ms per row for processing
  DANGER_ZONE_PERCENT: 80,          // Show warning at 80% usage
  HIGH_CONFIDENCE_THRESHOLD: 0.8,   // 80% confidence is considered high
  LOW_CONFIDENCE_THRESHOLD: 0.3,    // Below 30% triggers warnings
} as const;

// Billing cycle configuration
export const BILLING = {
  DEFAULT_CYCLE_DAYS: 30,           // Default billing cycle length
  GRACE_PERIOD_DAYS: 3,             // Grace period after failed payment
} as const;

// UI Configuration
export const UI = {
  MAX_RECENT_JOBS: 5,               // Show 5 recent jobs on dashboard
  DEFAULT_PAGE_SIZE: 100,           // Default pagination size
  COUNTDOWN_WARNING_MINUTES: 2,     // Show warning 2 minutes before expiry
  TOAST_DURATION: 4000,             // Toast notification duration
} as const;

// API Configuration
export const API = {
  DEFAULT_TIMEOUT: 30000,           // 30 second timeout for API calls
  UPLOAD_TIMEOUT: 120000,           // 2 minute timeout for file uploads
  MAX_RETRIES: 3,                   // Retry failed requests 3 times
} as const;

// Validation patterns
export const VALIDATION = {
  EMAIL_REGEX: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  PASSWORD_MIN_LENGTH: 8,
  NAME_MAX_LENGTH: 255,
  COLUMN_NAMES: ['name', 'parse_string'] as const,
} as const;

// File types configuration
export const FILE_TYPES = {
  ACCEPTED: {
    'text/csv': ['.csv'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'application/vnd.ms-excel': ['.xls'],
    'text/plain': ['.txt']
  },
} as const;

// Entity types
export const ENTITY_TYPES = {
  PERSON: 'person',
  COMPANY: 'company',
  TRUST: 'trust',
  UNKNOWN: 'unknown',
} as const;

// Job statuses
export const JOB_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const;

// Payment statuses
export const PAYMENT_STATUS = {
  PAID: 'paid',
  PENDING: 'pending',
  FAILED: 'failed',
} as const;

// Plan types
export const PLAN_TYPES = {
  ANONYMOUS: 'ANONYMOUS',
  STANDARD: 'STANDARD',
  ENTERPRISE: 'ENTERPRISE',
} as const;

// Pricing configuration
export const PRICING = {
  STANDARD_MONTHLY: 80,
  STANDARD_YEARLY: 768,
  OVERAGE_PER_NAME: 0.01,          // $0.01 per name over limit
  OVERAGE_PER_THOUSAND: 10,        // $10 per 1,000 names
} as const;

// Contact information
export const CONTACT = {
  EMAIL: import.meta.env.VITE_ADMIN_EMAIL || 'tidyframeai@gmail.com',
  COMPANY_NAME: 'TidyFrame',
  WEBSITE: 'tidyframe.com',
} as const;

// Date formatting options
export const DATE_FORMAT = {
  SHORT: 'MMM dd',
  LONG: 'MMM dd, yyyy',
  DATETIME: 'MMM dd, yyyy HH:mm',
  TIME: 'HH:mm:ss',
} as const;