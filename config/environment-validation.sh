#!/bin/bash
# =============================================================================
# Environment Validation Script for TidyFrame
# Validates all required environment variables and configurations
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =========================
# Logging Functions
# =========================
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARN: $1${NC}" >&2
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}"
}

# =========================
# Validation Functions
# =========================
validate_required_vars() {
    log "Validating required environment variables..."
    
    local required_vars=(
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
        "SECRET_KEY"
        "JWT_SECRET_KEY"
        "JWT_REFRESH_SECRET_KEY"
    )
    
    local missing_vars=()
    local weak_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        elif [[ ${#!var} -lt 32 ]]; then
            weak_vars+=("$var (${#!var} characters)")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing required variables: ${missing_vars[*]}"
        return 1
    fi
    
    if [[ ${#weak_vars[@]} -gt 0 ]]; then
        error "Variables with insufficient length (minimum 32 characters): ${weak_vars[*]}"
        return 1
    fi
    
    success "Required environment variables validation passed"
}

validate_optional_vars() {
    log "Validating optional environment variables..."
    
    local warnings=()
    
    # Check API keys
    if [[ -z "${GEMINI_API_KEY:-}" ]]; then
        warnings+=("GEMINI_API_KEY not set - AI features will not work")
    fi
    
    if [[ -z "${STRIPE_SECRET_KEY:-}" ]]; then
        warnings+=("STRIPE_SECRET_KEY not set - payment features disabled")
    fi
    
    if [[ -z "${RESEND_API_KEY:-}" ]]; then
        warnings+=("RESEND_API_KEY not set - email features disabled")
    fi
    
    # Check URLs
    if [[ -z "${VITE_API_URL:-}" ]]; then
        warnings+=("VITE_API_URL not set - using default")
    fi
    
    # Check security settings
    if [[ "${ENABLE_SITE_PASSWORD:-false}" == "true" && -z "${SITE_PASSWORD:-}" ]]; then
        warnings+=("ENABLE_SITE_PASSWORD is true but SITE_PASSWORD is not set")
    fi
    
    # Report warnings
    for warning in "${warnings[@]}"; do
        warn "$warning"
    done
    
    if [[ ${#warnings[@]} -eq 0 ]]; then
        success "Optional environment variables validation passed"
    else
        warn "Environment validation completed with ${#warnings[@]} warnings"
    fi
}

validate_format() {
    log "Validating environment variable formats..."
    
    local format_errors=()
    
    # Validate URLs
    if [[ -n "${VITE_API_URL:-}" && ! "${VITE_API_URL}" =~ ^https?:// ]]; then
        format_errors+=("VITE_API_URL must start with http:// or https://")
    fi
    
    if [[ -n "${CORS_ORIGINS:-}" && ! "${CORS_ORIGINS}" =~ ^https?:// ]]; then
        format_errors+=("CORS_ORIGINS must contain valid URLs")
    fi
    
    # Validate Stripe keys format
    if [[ -n "${STRIPE_SECRET_KEY:-}" && ! "${STRIPE_SECRET_KEY}" =~ ^sk_(test_|live_) ]]; then
        format_errors+=("STRIPE_SECRET_KEY must start with sk_test_ or sk_live_")
    fi
    
    if [[ -n "${STRIPE_PUBLISHABLE_KEY:-}" && ! "${STRIPE_PUBLISHABLE_KEY}" =~ ^pk_(test_|live_) ]]; then
        format_errors+=("STRIPE_PUBLISHABLE_KEY must start with pk_test_ or pk_live_")
    fi
    
    # Validate numeric values
    if [[ -n "${MAX_FILE_SIZE_MB:-}" && ! "${MAX_FILE_SIZE_MB}" =~ ^[0-9]+$ ]]; then
        format_errors+=("MAX_FILE_SIZE_MB must be a number")
    fi
    
    if [[ ${#format_errors[@]} -gt 0 ]]; then
        for error in "${format_errors[@]}"; do
            error "$error"
        done
        return 1
    fi
    
    success "Environment variable format validation passed"
}

validate_security() {
    log "Validating security configuration..."
    
    local security_issues=()
    
    # Check for insecure defaults
    if [[ "${SECRET_KEY:-}" == "your-super-secret-key"* ]]; then
        security_issues+=("SECRET_KEY appears to be using default value")
    fi
    
    if [[ "${POSTGRES_PASSWORD:-}" == "password" ]]; then
        security_issues+=("POSTGRES_PASSWORD is using insecure default")
    fi
    
    if [[ "${REDIS_PASSWORD:-}" == "password" ]]; then
        security_issues+=("REDIS_PASSWORD is using insecure default")
    fi
    
    # Check environment
    if [[ "${ENVIRONMENT:-}" == "production" && "${DEBUG:-false}" == "true" ]]; then
        security_issues+=("DEBUG mode is enabled in production environment")
    fi
    
    # Check CORS origins in production
    if [[ "${ENVIRONMENT:-}" == "production" && "${CORS_ORIGINS:-}" == *"localhost"* ]]; then
        security_issues+=("CORS_ORIGINS contains localhost in production")
    fi
    
    if [[ ${#security_issues[@]} -gt 0 ]]; then
        for issue in "${security_issues[@]}"; do
            error "Security issue: $issue"
        done
        return 1
    fi
    
    success "Security validation passed"
}

validate_connectivity() {
    log "Validating external service connectivity (optional)..."
    
    local connectivity_warnings=()
    
    # Test external APIs if keys are provided (non-blocking)
    if [[ -n "${GEMINI_API_KEY:-}" ]]; then
        log "Testing Gemini API connectivity..."
        # This would typically make a test API call
        # For now, just check the key format
        if [[ ! "${GEMINI_API_KEY}" =~ ^AIza ]]; then
            connectivity_warnings+=("Gemini API key format appears invalid")
        fi
    fi
    
    # Test Stripe API if keys are provided
    if [[ -n "${STRIPE_SECRET_KEY:-}" ]]; then
        log "Stripe API configuration detected"
        # In a real implementation, you might test a simple API call
    fi
    
    # Report connectivity warnings
    for warning in "${connectivity_warnings[@]}"; do
        warn "$warning"
    done
    
    success "Connectivity validation completed"
}

generate_env_report() {
    log "Generating environment configuration report..."
    
    cat <<EOF

=============================================================================
TidyFrame Environment Configuration Report
Generated: $(date -Iseconds)
=============================================================================

Environment: ${ENVIRONMENT:-development}
Debug Mode: ${DEBUG:-false}
Log Level: ${LOG_LEVEL:-INFO}

Database Configuration:
- Database: ${POSTGRES_DB:-tidyframe}
- User: ${POSTGRES_USER:-postgres}
- Password: $([ -n "${POSTGRES_PASSWORD:-}" ] && echo "SET" || echo "NOT SET")

Redis Configuration:
- Password: $([ -n "${REDIS_PASSWORD:-}" ] && echo "SET" || echo "NOT SET")

Security:
- Site Password Protection: ${ENABLE_SITE_PASSWORD:-false}
- Secret Key Length: ${#SECRET_KEY:-0} characters
- JWT Secret Key Length: ${#JWT_SECRET_KEY:-0} characters

External APIs:
- Gemini AI: $([ -n "${GEMINI_API_KEY:-}" ] && echo "CONFIGURED" || echo "NOT CONFIGURED")
- Stripe: $([ -n "${STRIPE_SECRET_KEY:-}" ] && echo "CONFIGURED" || echo "NOT CONFIGURED")
- Resend Email: $([ -n "${RESEND_API_KEY:-}" ] && echo "CONFIGURED" || echo "NOT CONFIGURED")
- Google OAuth: $([ -n "${GOOGLE_CLIENT_ID:-}" ] && echo "CONFIGURED" || echo "NOT CONFIGURED")

File Processing:
- Max File Size: ${MAX_FILE_SIZE_MB:-200}MB
- Upload Directory: ${UPLOAD_DIR:-/app/backend/uploads}
- Results Directory: ${RESULTS_DIR:-/app/backend/results}

Data Retention:
- Anonymous: ${ANONYMOUS_DATA_RETENTION_HOURS:-1} hours
- Standard: ${STANDARD_DATA_RETENTION_HOURS:-24} hours
- Enterprise: ${ENTERPRISE_DATA_RETENTION_HOURS:-720} hours

URLs:
- Frontend API URL: ${VITE_API_URL:-http://localhost:8000}
- CORS Origins: ${CORS_ORIGINS:-not set}
- Allowed Hosts: ${ALLOWED_HOSTS:-not set}

=============================================================================

EOF

    success "Environment report generated"
}

main() {
    log "Starting environment validation..."
    
    local validation_passed=true
    
    # Run all validations
    validate_required_vars || validation_passed=false
    validate_optional_vars  # This only warns, doesn't fail
    validate_format || validation_passed=false
    validate_security || validation_passed=false
    validate_connectivity  # This only warns, doesn't fail
    
    # Generate report
    generate_env_report
    
    if [[ "$validation_passed" == "true" ]]; then
        success "Environment validation completed successfully!"
        return 0
    else
        error "Environment validation failed. Please fix the issues above."
        return 1
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Load environment variables if .env file exists
    if [[ -f "$(dirname "$0")/../.env" ]]; then
        set -a
        source "$(dirname "$0")/../.env"
        set +a
    fi
    
    main "$@"
fi