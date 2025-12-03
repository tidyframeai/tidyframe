#!/bin/bash

# ================================================================
# TidyFrame Environment Validation Script
# Validates environment variables and service connections
# Usage: ./validate-env.sh [env_file] [environment]
# ================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ================================================================
# Configuration
# ================================================================

ENV_FILE="${1:-.env}"
TARGET_ENV="${2:-production}"  # production or development
VALIDATION_FAILED=0

# ================================================================
# Helper Functions
# ================================================================

log_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
    VALIDATION_FAILED=1
}

check_var_exists() {
    local var_name=$1
    local var_value=$(grep "^${var_name}=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'")

    if [ -z "$var_value" ]; then
        log_error "Required variable $var_name is not set in $ENV_FILE"
        return 1
    fi

    echo "$var_value"
    return 0
}

check_var_not_placeholder() {
    local var_name=$1
    local var_value=$2
    local placeholder_patterns=("your-" "example" "changeme" "password-here" "key-here" "secret-here")

    for pattern in "${placeholder_patterns[@]}"; do
        if [[ "$var_value" == *"$pattern"* ]]; then
            log_error "$var_name contains placeholder value: $var_value"
            return 1
        fi
    done

    return 0
}

# ================================================================
# Main Validation
# ================================================================

echo ""
echo "🔍 ================================================================"
echo "   TidyFrame Environment Validation"
echo "   Target Environment: $TARGET_ENV"
echo "   Environment File: $ENV_FILE"
echo "================================================================"
echo ""

# ================================================================
# Check 1: Environment file exists
# ================================================================

log_info "Checking environment file existence..."
if [ ! -f "$ENV_FILE" ]; then
    log_error "Environment file not found: $ENV_FILE"
    echo ""
    echo "Please create $ENV_FILE from the template:"
    echo "  cp backend/.env.example $ENV_FILE"
    exit 1
fi
log_success "Environment file exists: $ENV_FILE"
echo ""

# ================================================================
# Check 2: Required variables (All Environments)
# ================================================================

log_info "Validating required environment variables..."

# Critical security variables
SECRET_KEY=$(check_var_exists "SECRET_KEY") || true
GEMINI_API_KEY=$(check_var_exists "GEMINI_API_KEY") || true
DATABASE_URL=$(check_var_exists "DATABASE_URL") || true
REDIS_URL=$(check_var_exists "REDIS_URL") || true

# Docker-specific password variables (for production)
if [ "$TARGET_ENV" = "production" ]; then
    POSTGRES_PASSWORD=$(check_var_exists "POSTGRES_PASSWORD") || true
    REDIS_PASSWORD=$(check_var_exists "REDIS_PASSWORD") || true
fi

# Frontend configuration
FRONTEND_URL=$(check_var_exists "FRONTEND_URL") || true

# Stripe configuration (warn if missing, not critical in dev)
STRIPE_SECRET_KEY=$(check_var_exists "STRIPE_SECRET_KEY") || log_warning "STRIPE_SECRET_KEY not set (required for payments)"
STRIPE_PUBLISHABLE_KEY=$(check_var_exists "STRIPE_PUBLISHABLE_KEY") || log_warning "STRIPE_PUBLISHABLE_KEY not set"

echo ""

# ================================================================
# Check 3: Validate variable values are not placeholders
# ================================================================

log_info "Validating environment variable values..."

if [ -n "$SECRET_KEY" ]; then
    check_var_not_placeholder "SECRET_KEY" "$SECRET_KEY" || true

    # Check minimum length
    if [ ${#SECRET_KEY} -lt 32 ]; then
        log_error "SECRET_KEY is too short (minimum 32 characters, current: ${#SECRET_KEY})"
    else
        log_success "SECRET_KEY length is sufficient (${#SECRET_KEY} characters)"
    fi
fi

if [ -n "$GEMINI_API_KEY" ]; then
    check_var_not_placeholder "GEMINI_API_KEY" "$GEMINI_API_KEY" || true
fi

if [ -n "$STRIPE_SECRET_KEY" ]; then
    # Validate Stripe key format
    if [[ "$STRIPE_SECRET_KEY" == sk_test_* ]]; then
        if [ "$TARGET_ENV" = "production" ]; then
            log_warning "Using Stripe TEST key in PRODUCTION environment"
        else
            log_success "Using Stripe test key (appropriate for $TARGET_ENV)"
        fi
    elif [[ "$STRIPE_SECRET_KEY" == sk_live_* ]]; then
        if [ "$TARGET_ENV" = "production" ]; then
            log_success "Using Stripe live key (production)"
        else
            log_warning "Using Stripe LIVE key in DEVELOPMENT environment"
        fi
    else
        check_var_not_placeholder "STRIPE_SECRET_KEY" "$STRIPE_SECRET_KEY" || true
    fi
fi

echo ""

# ================================================================
# Check 4: Production-specific validations
# ================================================================

if [ "$TARGET_ENV" = "production" ]; then
    log_info "Running production-specific validations..."

    # Validate FRONTEND_URL format
    if [ -n "$FRONTEND_URL" ]; then
        if [[ "$FRONTEND_URL" == https://* ]]; then
            log_success "FRONTEND_URL uses HTTPS: $FRONTEND_URL"
        elif [[ "$FRONTEND_URL" == http://localhost* ]] || [[ "$FRONTEND_URL" == http://127.0.0.1* ]]; then
            log_error "FRONTEND_URL uses localhost in production: $FRONTEND_URL"
            echo "   Production FRONTEND_URL must use HTTPS (e.g., https://tidyframe.com)"
        else
            log_warning "FRONTEND_URL does not use HTTPS: $FRONTEND_URL"
        fi
    fi

    # Check DEBUG is disabled
    DEBUG=$(grep "^DEBUG=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 | tr -d ' "' | tr '[:upper:]' '[:lower:]')
    if [ "$DEBUG" = "true" ] || [ "$DEBUG" = "1" ]; then
        log_error "DEBUG is enabled in production (must be False)"
    else
        log_success "DEBUG is disabled"
    fi

    # Check ENVIRONMENT variable
    ENVIRONMENT=$(grep "^ENVIRONMENT=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 | tr -d ' "')
    if [ "$ENVIRONMENT" != "production" ]; then
        log_warning "ENVIRONMENT is set to '$ENVIRONMENT' (expected 'production')"
    else
        log_success "ENVIRONMENT is set to production"
    fi

    # Check ENABLE_SITE_PASSWORD is disabled for public access
    ENABLE_SITE_PASSWORD=$(grep "^ENABLE_SITE_PASSWORD=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 | tr -d ' "' | tr '[:upper:]' '[:lower:]')
    if [ "$ENABLE_SITE_PASSWORD" = "true" ] || [ "$ENABLE_SITE_PASSWORD" = "1" ]; then
        log_warning "ENABLE_SITE_PASSWORD is enabled (site will require password)"
    fi

    # Validate password variables for Docker Compose
    if [ -n "$POSTGRES_PASSWORD" ]; then
        if [ ${#POSTGRES_PASSWORD} -lt 16 ]; then
            log_warning "POSTGRES_PASSWORD is short (recommended: 16+ characters, current: ${#POSTGRES_PASSWORD})"
        else
            log_success "POSTGRES_PASSWORD is sufficiently strong (${#POSTGRES_PASSWORD} characters)"
        fi
    fi

    if [ -n "$REDIS_PASSWORD" ]; then
        if [ ${#REDIS_PASSWORD} -lt 16 ]; then
            log_warning "REDIS_PASSWORD is short (recommended: 16+ characters, current: ${#REDIS_PASSWORD})"
        else
            log_success "REDIS_PASSWORD is sufficiently strong (${#REDIS_PASSWORD} characters)"
        fi
    fi

    echo ""
fi

# ================================================================
# Check 5: Database URL format validation
# ================================================================

log_info "Validating database connection string..."

if [ -n "$DATABASE_URL" ]; then
    # Check if it's using asyncpg driver
    if [[ "$DATABASE_URL" == postgresql+asyncpg://* ]]; then
        log_success "DATABASE_URL uses correct asyncpg driver"
    elif [[ "$DATABASE_URL" == postgresql://* ]]; then
        log_warning "DATABASE_URL uses psycopg driver (should be postgresql+asyncpg://)"
    else
        log_error "DATABASE_URL has invalid format: $DATABASE_URL"
    fi

    # Extract host from DATABASE_URL
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    if [ -n "$DB_HOST" ]; then
        if [ "$TARGET_ENV" = "production" ] && [ "$DB_HOST" = "localhost" ]; then
            log_warning "DATABASE_URL uses localhost in production (should use 'postgres' service name)"
        fi
    fi
fi

echo ""

# ================================================================
# Check 6: Redis URL format validation
# ================================================================

log_info "Validating Redis connection string..."

if [ -n "$REDIS_URL" ]; then
    if [[ "$REDIS_URL" == redis://* ]]; then
        log_success "REDIS_URL format is valid"
    else
        log_error "REDIS_URL has invalid format: $REDIS_URL"
    fi

    # Extract host from REDIS_URL
    REDIS_HOST=$(echo "$REDIS_URL" | sed -n 's|redis://[^@]*@\?\([^:]*\):.*|\1|p')
    if [ -n "$REDIS_HOST" ] && [ "$REDIS_HOST" != ":" ]; then
        if [ "$TARGET_ENV" = "production" ] && [ "$REDIS_HOST" = "localhost" ]; then
            log_warning "REDIS_URL uses localhost in production (should use 'redis' service name)"
        fi
    fi
fi

echo ""

# ================================================================
# Check 7: Optional service connectivity tests
# ================================================================

if command -v docker &> /dev/null && [ "$TARGET_ENV" = "production" ]; then
    log_info "Testing service connectivity (Docker available)..."

    # Test PostgreSQL connectivity
    if command -v psql &> /dev/null && [ -n "$POSTGRES_PASSWORD" ]; then
        PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U tidyframe -d tidyframe -c "SELECT 1;" > /dev/null 2>&1 && \
            log_success "PostgreSQL connection successful" || \
            log_warning "PostgreSQL connection test failed (service may not be running)"
    fi

    # Test Redis connectivity
    if command -v redis-cli &> /dev/null && [ -n "$REDIS_PASSWORD" ]; then
        redis-cli -a "$REDIS_PASSWORD" ping > /dev/null 2>&1 && \
            log_success "Redis connection successful" || \
            log_warning "Redis connection test failed (service may not be running)"
    fi

    echo ""
fi

# ================================================================
# Check 8: Email configuration (warnings only)
# ================================================================

log_info "Checking email configuration..."

RESEND_API_KEY=$(check_var_exists "RESEND_API_KEY") || log_warning "RESEND_API_KEY not set (email notifications will fail)"
FROM_EMAIL=$(check_var_exists "FROM_EMAIL") || log_warning "FROM_EMAIL not set"

echo ""

# ================================================================
# Final Summary
# ================================================================

echo "================================================================"
if [ $VALIDATION_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All critical validation checks passed!${NC}"
    echo "================================================================"
    echo ""
    log_success "Environment is properly configured for $TARGET_ENV"
    exit 0
else
    echo -e "${RED}❌ Validation failed!${NC}"
    echo "================================================================"
    echo ""
    log_error "Please fix the errors above before deploying to $TARGET_ENV"
    echo ""
    echo "Common fixes:"
    echo "  1. Generate SECRET_KEY:"
    echo "     python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    echo ""
    echo "  2. Set FRONTEND_URL to HTTPS in production:"
    echo "     FRONTEND_URL=https://tidyframe.com"
    echo ""
    echo "  3. Ensure DEBUG=False in production"
    echo ""
    echo "  4. Generate strong database passwords:"
    echo "     python backend/scripts/generate_secure_password.py"
    echo ""
    exit 1
fi
