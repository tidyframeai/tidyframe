#!/bin/bash

# =============================================================================
# TidyFrame Production Deployment Script - Digital Ocean
# =============================================================================
# This script handles the complete deployment process including:
# - Prerequisites checking
# - Environment setup
# - Database initialization
# - Docker services startup
# - SSL/HTTPS configuration
# - Health checks and validation
# =============================================================================

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

# =============================================================================
# Utility Functions (MUST BE DEFINED FIRST)
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] [$level] $message"
}

log_info() {
    log "INFO" "${BLUE}$*${NC}"
}

log_success() {
    log "SUCCESS" "${GREEN}$*${NC}"
}

log_warning() {
    log "WARNING" "${YELLOW}$*${NC}"
}

log_error() {
    log "ERROR" "${RED}$*${NC}"
}

print_banner() {
    echo -e "${GREEN}"
    echo "================================================================="
    echo "  TidyFrame Production Deployment - Digital Ocean"
    echo "  Environment: $DEPLOY_ENV"
    echo "  Domain: $DOMAIN"
    echo "  Timestamp: $(date)"
    echo "================================================================="
    echo -e "${NC}"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "Required command '$1' is not installed"
        return 1
    fi
}

wait_for_service() {
    local service_name=$1
    local check_command=$2
    local timeout=${3:-60}
    local interval=${4:-5}

    log_info "Waiting for $service_name to be ready..."
    local elapsed=0
    local last_error=""

    while [ $elapsed -lt $timeout ]; do
        if last_error=$(eval "$check_command" 2>&1); then
            log_success "$service_name is ready"
            return 0
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
        printf "."

        # Log progress every 30 seconds
        if [ $((elapsed % 30)) -eq 0 ]; then
            echo ""
            log_info "$service_name still starting... (${elapsed}s/${timeout}s)"
        fi
    done

    echo ""
    log_error "$service_name failed to start within $timeout seconds"
    if [ -n "$last_error" ]; then
        log_error "Last error: $last_error"
    fi

    return 1
}

retry_command() {
    local max_attempts=$1
    local delay=$2
    shift 2
    local command="$*"

    for attempt in $(seq 1 $max_attempts); do
        if eval "$command"; then
            return 0
        fi

        if [ $attempt -lt $max_attempts ]; then
            log_warning "Command failed (attempt $attempt/$max_attempts), retrying in ${delay}s..."
            sleep $delay
        fi
    done

    log_error "Command failed after $max_attempts attempts: $command"
    return 1
}

# =============================================================================
# Configuration & Constants
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# =============================================================================
# DEPLOYMENT CONFIGURATION - All values configurable via environment/CLI
# =============================================================================

# Mode Flags
QUICK_MODE="${QUICK_MODE:-false}"

# Project Structure
PROJECT_NAME="${PROJECT_NAME:-tidyframe}"
PROJECT_ROOT="${PROJECT_ROOT:-/opt/tidyframe}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKEND_DIR="${BACKEND_DIR:-backend}"
FRONTEND_DIR="${FRONTEND_DIR:-frontend}"

# Domain & SSL
DOMAIN="${DOMAIN:-tidyframe.com}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-tidyframeai@gmail.com}"
DEPLOY_ENV="${DEPLOY_ENV:-production}"
SKIP_SSL="${SKIP_SSL:-false}"

# Service Configuration
BACKEND_PORT="${BACKEND_PORT:-8000}"
BACKEND_HOST="${BACKEND_HOST:-localhost}"
HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-/health}"

# Container Names (Docker Compose v2 naming)
CONTAINER_PREFIX="${CONTAINER_PREFIX:-tidyframe}"
CONTAINER_SUFFIX="${CONTAINER_SUFFIX:--1}"
POSTGRES_CONTAINER="${CONTAINER_PREFIX}-postgres${CONTAINER_SUFFIX}"
REDIS_CONTAINER="${CONTAINER_PREFIX}-redis${CONTAINER_SUFFIX}"
BACKEND_CONTAINER="${CONTAINER_PREFIX}-backend${CONTAINER_SUFFIX}"
NGINX_CONTAINER="${CONTAINER_PREFIX}-nginx${CONTAINER_SUFFIX}"

# Timeout Configuration (Normal Mode)
POSTGRES_WAIT_TIMEOUT="${POSTGRES_WAIT_TIMEOUT:-120}"
POSTGRES_WAIT_INTERVAL="${POSTGRES_WAIT_INTERVAL:-10}"
REDIS_WAIT_TIMEOUT="${REDIS_WAIT_TIMEOUT:-60}"
REDIS_WAIT_INTERVAL="${REDIS_WAIT_INTERVAL:-5}"
BACKEND_WAIT_TIMEOUT="${BACKEND_WAIT_TIMEOUT:-180}"
BACKEND_WAIT_INTERVAL="${BACKEND_WAIT_INTERVAL:-10}"
NGINX_WAIT_TIMEOUT="${NGINX_WAIT_TIMEOUT:-60}"
NGINX_WAIT_INTERVAL="${NGINX_WAIT_INTERVAL:-5}"

# Quick Mode Overrides (applied in main() after CLI parsing)

# Build Configuration
SKIP_BACKUP="${SKIP_BACKUP:-false}"
FORCE_REBUILD="${FORCE_REBUILD:-false}"
SKIP_FRONTEND_BUILD="${SKIP_FRONTEND_BUILD:-false}"
SKIP_BUILD="${SKIP_BUILD:-false}"
FRONTEND_BUILD_CMD="${FRONTEND_BUILD_CMD:-npm run build}"
FRONTEND_INSTALL_CMD="${FRONTEND_INSTALL_CMD:-npm install}"

# Static Files Paths
FRONTEND_DIST_DIR="${FRONTEND_DIST_DIR:-dist}"
BACKEND_STATIC_DIR="${BACKEND_STATIC_DIR:-app/static}"

# Directories
LOG_DIR="${LOG_DIR:-$PROJECT_ROOT/logs}"
BACKUP_DIR_BASE="${BACKUP_DIR_BASE:-$PROJECT_ROOT/backups}"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"
DEPLOY_LOG="$LOG_DIR/deploy-$(date +%Y%m%d_%H%M%S).log"
BACKUP_DIR="$BACKUP_DIR_BASE/$(date +%Y%m%d_%H%M%S)"

# =============================================================================
# Prerequisites Check
# =============================================================================

check_prerequisites() {
    log_info "Checking deployment prerequisites..."

    # Ensure we're in the right directory
    if [ ! -d "$PROJECT_ROOT" ]; then
        log_error "Project directory not found: $PROJECT_ROOT"
        exit 1
    fi
    cd "$PROJECT_ROOT"

    # Create necessary directories
    mkdir -p "$PROJECT_ROOT/logs" "$PROJECT_ROOT/backups" "$PROJECT_ROOT/data"
    mkdir -p "$PROJECT_ROOT/backend/uploads" "$PROJECT_ROOT/backend/results" "$PROJECT_ROOT/backend/logs"
    mkdir -p "$PROJECT_ROOT/certbot/conf" "$PROJECT_ROOT/certbot/www"

    # Check required commands
    local required_commands=("docker" "curl")
    for cmd in "${required_commands[@]}"; do
        if ! check_command "$cmd"; then
            log_error "Missing required command: $cmd"
            exit 1
        fi
    done

    # Check Docker daemon
    if ! docker info &>/dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi

    # Check Docker Compose version
    local compose_version=$(docker compose version --short 2>/dev/null || echo "2.0.0")
    log_info "Docker Compose version: $compose_version"

    # Check available disk space (minimum 5GB)
    local available_space=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5242880 ]; then  # 5GB in KB
        log_error "Insufficient disk space: $(($available_space / 1024 / 1024))GB available (5GB required)"
        exit 1
    fi

    # Check memory (minimum 1GB available)
    local available_memory=$(free -m | awk 'NR==2{print $7}')
    if [ "$available_memory" -lt 1024 ]; then
        log_warning "Low memory: ${available_memory}MB available (1GB recommended)"
    fi

    log_success "Prerequisites check completed"
}

# =============================================================================
# Environment Setup
# =============================================================================

setup_environment() {
    log_info "Setting up environment configuration..."

    cd "$PROJECT_ROOT"

    # Check for production environment file
    if [ ! -f ".env.production" ]; then
        log_error ".env.production file not found!"
        log_info "Please create .env.production with all required production values"
        exit 1
    fi

    # Copy production env to .env for Docker Compose
    log_info "Setting up production environment..."
    cp .env.production .env

    # Load environment variables
    set -a
    source .env
    set +a

    # Validate critical environment variables
    local required_vars=(
        "SECRET_KEY"
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
        "GEMINI_API_KEY"
        "ADMIN_EMAIL"
        "ADMIN_PASSWORD"
    )

    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Required environment variable $var is not set in .env.production"
            exit 1
        fi
    done

    # Validate admin credentials are properly set
    if [ "$ADMIN_EMAIL" = "admin@tidyframe.com" ] || [ "$ADMIN_PASSWORD" = "admin123" ]; then
        log_error "ADMIN_EMAIL or ADMIN_PASSWORD still has default value - please update .env.production"
        exit 1
    fi

    log_info "Environment validation passed (all required variables set)"

    # Update environment variables for production
    if [ "$DEPLOY_ENV" = "production" ]; then
        log_info "Updating environment for production domain: $DOMAIN"

        # Update API URL in .env
        sed -i.bak "s|VITE_API_URL=.*|VITE_API_URL=https://$DOMAIN|g" .env
        sed -i "s|ALLOWED_HOSTS_STR=.*|ALLOWED_HOSTS_STR=$DOMAIN,www.$DOMAIN|g" .env

        # Remove any localhost references
        if grep -q "localhost" .env; then
            log_warning "Found localhost references in .env - updating for production"
            sed -i "s|http://localhost|https://$DOMAIN|g" .env
            sed -i "s|https://localhost|https://$DOMAIN|g" .env
        fi
    fi

    # Export important variables for docker compose
    export DOMAIN
    export CERTBOT_EMAIL
    export ENV_FILE=".env"

    log_success "Environment setup completed"
}

# =============================================================================
# Configuration Summary
# =============================================================================

apply_quick_mode() {
    if [ "$QUICK_MODE" = "true" ]; then
        log_info "⚡ Applying quick mode overrides..."
        POSTGRES_WAIT_TIMEOUT=30
        REDIS_WAIT_TIMEOUT=20
        BACKEND_WAIT_TIMEOUT=40
        NGINX_WAIT_TIMEOUT=20
        SKIP_BACKUP=true
        SKIP_SSL=true
    fi
}

print_config_summary() {
    echo ""
    log_info "=== Deployment Configuration ==="
    log_info "Mode:              $([ "$QUICK_MODE" = "true" ] && echo "⚡ QUICK" || echo "🔧 FULL")"
    log_info "Project:           $PROJECT_NAME"
    log_info "Root:              $PROJECT_ROOT"
    log_info "Compose File:      $COMPOSE_FILE"
    log_info "Environment:       $DEPLOY_ENV"
    log_info "Domain:            $DOMAIN"
    log_info "SSL:               $([ "$SKIP_SSL" = "false" ] && echo "✅ Enabled" || echo "⏭️  Skipped")"
    log_info "Backup:            $([ "$SKIP_BACKUP" = "false" ] && echo "✅ Enabled" || echo "⏭️  Skipped")"
    log_info "Frontend Build:    $([ "$SKIP_FRONTEND_BUILD" = "false" ] && echo "✅ Enabled" || echo "⏭️  Skipped")"
    log_info "Docker Build:      $([ "$SKIP_BUILD" = "false" ] && echo "✅ Rebuild" || echo "⏭️  Use Existing")"
    log_info "Force Rebuild:     $([ "$FORCE_REBUILD" = "true" ] && echo "✅ Yes (--no-cache)" || echo "No")"
    log_info "Backend Timeout:   ${BACKEND_WAIT_TIMEOUT}s"
    log_info "================================"
    echo ""
}

# =============================================================================
# Create Backup
# =============================================================================

create_backup() {
    if [ "$SKIP_BACKUP" = "true" ]; then
        if [ "$QUICK_MODE" = "true" ]; then
            log_info "⚡ Quick mode: Skipping backup"
        else
            log_info "Skipping backup (SKIP_BACKUP=true)"
        fi
        return 0
    fi

    log_info "Creating deployment backup..."

    mkdir -p "$BACKUP_DIR"

    # Check if this is a fresh deployment or update
    if docker ps --format "table {{.Names}}" | grep -q "$CONTAINER_PREFIX"; then
        log_info "Existing deployment detected - creating full backup"

        # Backup database if it exists
        if docker ps | grep -q "$POSTGRES_CONTAINER"; then
            log_info "Backing up database..."
            docker exec "$POSTGRES_CONTAINER" pg_dump -U tidyframe tidyframe > "$BACKUP_DIR/database.sql" 2>/dev/null || {
                log_warning "Database backup skipped (container might not be fully ready)"
            }
        fi

        # Backup data directories
        if [ -d "$PROJECT_ROOT/data" ]; then
            log_info "Backing up data directory..."
            tar -czf "$BACKUP_DIR/data.tar.gz" -C "$PROJECT_ROOT" data 2>/dev/null || log_warning "Data backup failed"
        fi
    else
        log_info "Fresh deployment - no existing data to backup"
    fi

    # Always backup configuration
    cp "$PROJECT_ROOT/.env" "$BACKUP_DIR/env.backup" 2>/dev/null || true

    log_success "Backup created at $BACKUP_DIR"
}

# =============================================================================
# Build Frontend
# =============================================================================

build_frontend() {
    log_info "Building frontend application..."

    cd "$PROJECT_ROOT/frontend"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        log_info "Installing frontend dependencies..."
        npm install || {
            log_error "Failed to install frontend dependencies"
            exit 1
        }
    fi

    # Build frontend
    log_info "Running frontend build (vite build)..."
    npm run build || {
        log_error "Frontend build failed"
        exit 1
    }

    # Verify build output exists
    if [ ! -d "dist" ] || [ ! -f "dist/index.html" ]; then
        log_error "Frontend build did not produce expected output (dist/index.html missing)"
        exit 1
    fi

    # Copy to backend static directory
    log_info "Copying built files to backend static directory..."
    mkdir -p "$PROJECT_ROOT/backend/app/static"
    rm -rf "$PROJECT_ROOT/backend/app/static"/*
    cp -r dist/* "$PROJECT_ROOT/backend/app/static/"

    # Verify static files were copied
    if [ ! -f "$PROJECT_ROOT/backend/app/static/index.html" ]; then
        log_error "Failed to copy static files to backend"
        exit 1
    fi

    local static_size=$(du -sh "$PROJECT_ROOT/backend/app/static" | cut -f1)
    log_success "Frontend built and copied to backend/app/static/ (${static_size})"

    cd "$PROJECT_ROOT"
}

# =============================================================================
# Initialize Database
# =============================================================================

initialize_database() {
    log_info "Initializing database..."

    cd "$PROJECT_ROOT"

    # Ensure database directories exist with correct permissions
    mkdir -p "$PROJECT_ROOT/data/postgres" "$PROJECT_ROOT/data/redis"

    # Start database services first
    log_info "Starting database services..."
    docker compose -f "$COMPOSE_FILE" up -d postgres redis

    # Wait for PostgreSQL
    wait_for_service "PostgreSQL" \
        "docker exec \"$POSTGRES_CONTAINER\" pg_isready -U tidyframe" \
        "$POSTGRES_WAIT_TIMEOUT" "$POSTGRES_WAIT_INTERVAL"

    # Wait for Redis with password
    wait_for_service "Redis" \
        "docker exec \"$REDIS_CONTAINER\" redis-cli -a '$REDIS_PASSWORD' ping | grep -q PONG" \
        "$REDIS_WAIT_TIMEOUT" "$REDIS_WAIT_INTERVAL"

    log_success "Database initialization completed"
}

# =============================================================================
# Start Docker Services
# =============================================================================

start_docker_services() {
    log_info "Starting Docker services..."

    cd "$PROJECT_ROOT"

    # Stop any existing services first (for clean restart)
    log_info "Stopping any existing services..."
    docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true

    # Clean up any dangling volumes
    docker volume prune -f 2>/dev/null || true

    # Build or rebuild images
    if [ "$SKIP_BUILD" = "true" ]; then
        log_info "Skipping Docker build (using existing images)..."
    elif [ "$FORCE_REBUILD" = "true" ]; then
        log_info "Force rebuilding all images..."
        docker compose -f "$COMPOSE_FILE" build --no-cache --pull
    else
        log_info "Building images (using cache if available)..."
        docker compose -f "$COMPOSE_FILE" build
    fi

    # Start all services with proper order
    log_info "Starting core services..."
    docker compose -f "$COMPOSE_FILE" up -d postgres redis

    # Wait for databases
    sleep 10

    log_info "Starting application services..."
    docker compose -f "$COMPOSE_FILE" up -d backend celery-worker celery-beat

    # Wait for backend to be ready (check from inside container since port not exposed to host)
    wait_for_service "Backend API" \
        "docker exec \"$BACKEND_CONTAINER\" curl -f -s http://localhost:$BACKEND_PORT$HEALTH_ENDPOINT" \
        "$BACKEND_WAIT_TIMEOUT" "$BACKEND_WAIT_INTERVAL"

    # Frontend is now built into backend Docker image - no frontend-builder needed
    log_info "Frontend static files included in backend image"

    # Start nginx and certbot last
    log_info "Starting nginx reverse proxy and certbot..."
    docker compose -f "$COMPOSE_FILE" up -d nginx certbot

    # Final wait for nginx (check from host since it exposes port 80)
    wait_for_service "Nginx" \
        "curl -f -s http://localhost$HEALTH_ENDPOINT" \
        "$NGINX_WAIT_TIMEOUT" "$NGINX_WAIT_INTERVAL"

    log_success "All Docker services started successfully"
}

# =============================================================================
# Create Admin User
# =============================================================================

create_admin_user() {
    if [ "$QUICK_MODE" = "true" ]; then
        log_info "⚡ Quick mode: Skipping admin user creation"
        return 0
    fi

    log_info "Setting up admin user..."

    # Check if setup_admin.py exists
    if [ ! -f "$PROJECT_ROOT/$BACKEND_DIR/scripts/setup_admin.py" ]; then
        log_warning "Admin setup script not found - skipping admin creation"
        return 0
    fi

    # Wait for backend to be fully ready
    sleep 10

    # Run admin setup
    log_info "Creating admin user (tidyframeai@gmail.com)..."
    docker compose -f "$COMPOSE_FILE" exec -T backend python scripts/setup_admin.py 2>&1 | tail -5 || {
        log_warning "Admin user might already exist"
    }

    log_success "Admin setup completed"
}

# =============================================================================
# Configure SSL
# =============================================================================

configure_ssl() {
    if [ "$SKIP_SSL" = "true" ]; then
        if [ "$QUICK_MODE" = "true" ]; then
            log_info "⚡ Quick mode: Skipping SSL configuration"
        else
            log_info "Skipping SSL configuration (SKIP_SSL=true)"
        fi
        log_warning "Site is running on HTTP only - not recommended for production!"
        return 0
    fi

    log_info "Configuring SSL/HTTPS..."

    # Check if setup-ssl.sh exists and run it
    if [ -f "$PROJECT_ROOT/$BACKEND_DIR/scripts/setup-ssl.sh" ]; then
        log_info "Running SSL setup script for Let's Encrypt..."
        cd "$PROJECT_ROOT"
        bash "$BACKEND_DIR/scripts/setup-ssl.sh" "$DOMAIN" "$CERTBOT_EMAIL" "$DEPLOY_ENV"
    else
        log_error "SSL setup script not found at $BACKEND_DIR/scripts/setup-ssl.sh"
        log_warning "Please run SSL setup manually"
    fi

    log_success "SSL configuration completed"
}

# =============================================================================
# Health Checks & Validation
# =============================================================================

run_health_checks() {
    log_info "Running comprehensive health checks..."

    cd "$PROJECT_ROOT"
    local health_check_failed=0

    # Check Docker services status
    log_info "Checking Docker services..."
    local services=("postgres" "redis" "backend" "celery-worker" "celery-beat" "nginx")

    for service in "${services[@]}"; do
        if docker compose -f "$COMPOSE_FILE" ps | grep -q "${service}.*Up"; then
            log_success "✅ Service $service is running"
        else
            log_error "❌ Service $service is not running"
            health_check_failed=1
            # Show logs for failed service
            docker compose -f "$COMPOSE_FILE" logs --tail=10 "$service" 2>/dev/null || true
        fi
    done

    # Check API Health (from inside container since port not exposed to host)
    log_info "Checking API health..."
    if docker exec "$BACKEND_CONTAINER" curl -f -s -m 10 "http://localhost:$BACKEND_PORT$HEALTH_ENDPOINT" > /dev/null 2>&1; then
        log_success "✅ API health check passed"
    else
        log_error "❌ API health check failed"
        docker compose -f "$COMPOSE_FILE" logs --tail=20 backend 2>/dev/null || true
        health_check_failed=1
    fi

    # Check Database connectivity
    log_info "Checking database connectivity..."
    if docker exec "$POSTGRES_CONTAINER" pg_isready -U tidyframe > /dev/null 2>&1; then
        log_success "✅ Database connectivity check passed"
    else
        log_error "❌ Database connectivity check failed"
        health_check_failed=1
    fi

    # Check Redis connectivity
    log_info "Checking Redis connectivity..."
    if docker exec "$REDIS_CONTAINER" redis-cli -a "$REDIS_PASSWORD" ping 2>/dev/null | grep -q PONG; then
        log_success "✅ Redis connectivity check passed"
    else
        log_error "❌ Redis connectivity check failed"
        health_check_failed=1
    fi

    # Check Nginx
    log_info "Checking Nginx..."
    if curl -f -s -m 10 "http://localhost$HEALTH_ENDPOINT" > /dev/null; then
        log_success "✅ Nginx health check passed"
    else
        log_error "❌ Nginx health check failed"
        docker compose -f "$COMPOSE_FILE" logs --tail=20 nginx 2>/dev/null || true
        health_check_failed=1
    fi

    # Check external access
    log_info "Checking external access..."
    if [ "$SKIP_SSL" = "true" ]; then
        if curl -f -s -m 10 "http://$DOMAIN/health" > /dev/null 2>&1; then
            log_success "✅ External HTTP access working"
        else
            log_warning "⚠️ External access not yet available (DNS may be propagating)"
        fi
    else
        if curl -f -s -m 10 "https://$DOMAIN/health" > /dev/null 2>&1; then
            log_success "✅ External HTTPS access working"
        else
            log_warning "⚠️ HTTPS not yet accessible (certificates may still be generating)"
        fi
    fi

    # System resource check
    log_info "Checking system resources..."
    local disk_usage=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $5}' | sed 's/%//')
    local memory_usage=$(free | awk 'NR==2{printf "%.1f", $3/$2*100}')

    if [ "$disk_usage" -gt 90 ]; then
        log_warning "⚠️ High disk usage: ${disk_usage}%"
    else
        log_success "✅ Disk usage: ${disk_usage}%"
    fi

    log_info "Memory usage: ${memory_usage}%"

    # Final result
    if [ $health_check_failed -eq 0 ]; then
        log_success "🎉 All health checks passed!"
        return 0
    else
        log_error "⚠️ Some health checks failed - review logs above"
        return 1
    fi
}

# =============================================================================
# Generate Deployment Report
# =============================================================================

generate_deployment_report() {
    local report_file="$PROJECT_ROOT/logs/deployment-report-$(date +%Y%m%d_%H%M%S).txt"

    {
        echo "====================================="
        echo "TidyFrame Deployment Report"
        echo "====================================="
        echo "Date: $(date)"
        echo "Environment: $DEPLOY_ENV"
        echo "Domain: $DOMAIN"
        echo "SSL Enabled: $([ "$SKIP_SSL" = "false" ] && echo "Yes" || echo "No")"
        echo ""
        echo "Service Status:"
        docker compose -f "$COMPOSE_FILE" ps
        echo ""
        echo "Access URLs:"
        if [ "$SKIP_SSL" = "false" ]; then
            echo "  Frontend: https://$DOMAIN"
            echo "  API: https://$DOMAIN/api"
            echo "  Health: https://$DOMAIN$HEALTH_ENDPOINT"
            echo "  Admin: https://$DOMAIN/admin"
        else
            echo "  Frontend: http://$DOMAIN"
            echo "  API: http://$DOMAIN/api"
            echo "  Health: http://$DOMAIN$HEALTH_ENDPOINT"
            echo "  Admin: http://$DOMAIN/admin"
        fi
        echo ""
        echo "Credentials:"
        echo "  See .env.production file for admin credentials"
        echo "  ADMIN_EMAIL and ADMIN_PASSWORD are configured in environment"
        echo "  SITE_PASSWORD is configured in environment (if enabled)"
        echo ""
        echo "Commands:"
        echo "  View logs: docker compose -f $COMPOSE_FILE logs -f"
        echo "  Restart: docker compose -f $COMPOSE_FILE restart"
        echo "  Stop: docker compose -f $COMPOSE_FILE down"
    } | tee "$report_file"

    log_info "Report saved to: $report_file"
}

# =============================================================================
# Main Deployment Function
# =============================================================================

main() {
    # Redirect all output to log file while still showing on screen
    exec 1> >(tee -a "$DEPLOY_LOG")
    exec 2>&1

    print_banner

    # Apply quick mode settings if enabled
    apply_quick_mode

    print_config_summary

    local start_time=$(date +%s)

    # =============================================================================
    # PRE-DEPLOYMENT VALIDATION (CRITICAL - Prevent deployment errors)
    # =============================================================================
    log_info "Running pre-deployment validation..."
    if [ -f "$PROJECT_ROOT/$BACKEND_DIR/scripts/validate-deployment.sh" ]; then
        if bash "$PROJECT_ROOT/$BACKEND_DIR/scripts/validate-deployment.sh"; then
            log_success "Pre-deployment validation passed"
        else
            log_error "Pre-deployment validation failed - aborting deployment"
            log_error "Please fix the errors above before deploying"
            exit 1
        fi
    else
        log_warning "Validation script not found - skipping pre-deployment checks"
    fi

    # Execute deployment steps
    check_prerequisites
    setup_environment
    create_backup

    # Build frontend BEFORE Docker services (so static files are fresh)
    if [ "$SKIP_FRONTEND_BUILD" = "false" ]; then
        build_frontend
    else
        log_info "Skipping frontend build (SKIP_FRONTEND_BUILD=true)"
    fi

    initialize_database
    start_docker_services
    create_admin_user

    # Run initial health check before SSL
    if run_health_checks; then
        log_success "Initial deployment successful"
    else
        log_warning "Some services may need more time to stabilize"
    fi

    # Configure SSL if not skipped
    if [ "$SKIP_SSL" = "false" ]; then
        configure_ssl
        # Run health check again after SSL
        run_health_checks
    fi

    generate_deployment_report

    # =============================================================================
    # POST-DEPLOYMENT SMOKE TESTS
    # =============================================================================
    log_info "Running post-deployment smoke tests..."
    if [ -f "$PROJECT_ROOT/$BACKEND_DIR/scripts/smoke-test.sh" ]; then
        if bash "$PROJECT_ROOT/$BACKEND_DIR/scripts/smoke-test.sh" "$DOMAIN" "$COMPOSE_FILE"; then
            log_success "Post-deployment smoke tests passed"
        else
            log_warning "Some smoke tests failed - review output above"
        fi
    else
        log_warning "Smoke test script not found - skipping post-deployment tests"
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo ""
    log_success "🎉 Deployment completed in ${duration} seconds!"
    echo ""
    echo -e "${GREEN}=================================================================${NC}"
    echo -e "${GREEN}  TidyFrame is now deployed!${NC}"
    echo ""
    if [ "$SKIP_SSL" = "false" ]; then
        echo -e "  🌐 Frontend: ${BLUE}https://$DOMAIN${NC}"
        echo -e "  🔧 API: ${BLUE}https://$DOMAIN/api${NC}"
        echo -e "  ❤️  Health: ${BLUE}https://$DOMAIN$HEALTH_ENDPOINT${NC}"
    else
        echo -e "  🌐 Frontend: ${BLUE}http://$DOMAIN${NC}"
        echo -e "  🔧 API: ${BLUE}http://$DOMAIN/api${NC}"
        echo -e "  ❤️  Health: ${BLUE}http://$DOMAIN$HEALTH_ENDPOINT${NC}"
        echo ""
        echo -e "  ${YELLOW}⚠️  SSL not configured - run with SSL for production${NC}"
    fi
    echo ""
    echo -e "  📊 View logs: ${BLUE}docker compose -f $COMPOSE_FILE logs -f${NC}"
    echo -e "  📋 Status: ${BLUE}docker compose -f $COMPOSE_FILE ps${NC}"
    echo ""
    echo -e "  📝 Full log: ${BLUE}$DEPLOY_LOG${NC}"
    echo -e "${GREEN}=================================================================${NC}"
}

# =============================================================================
# Script Entry Point
# =============================================================================

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --email)
            CERTBOT_EMAIL="$2"
            shift 2
            ;;
        --env)
            DEPLOY_ENV="$2"
            shift 2
            ;;
        --skip-ssl)
            SKIP_SSL=true
            shift
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-frontend)
            SKIP_FRONTEND_BUILD=true
            shift
            ;;
        --force-rebuild)
            FORCE_REBUILD=true
            shift
            ;;
        --backend-port)
            BACKEND_PORT="$2"
            shift 2
            ;;
        --backend-timeout)
            BACKEND_WAIT_TIMEOUT="$2"
            shift 2
            ;;
        --project-root)
            PROJECT_ROOT="$2"
            shift 2
            ;;
        --compose-file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --help)
            echo "TidyFrame Production Deployment Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Mode Options:"
            echo "  --quick                 Quick deployment mode (skips backup, SSL, admin, shorter timeouts)"
            echo ""
            echo "Configuration Options:"
            echo "  --domain DOMAIN         Domain name (default: tidyframe.com)"
            echo "  --email EMAIL           Email for Let's Encrypt (default: tidyframeai@gmail.com)"
            echo "  --env ENV               Environment (default: production)"
            echo "  --project-root PATH     Project root directory (default: /opt/tidyframe)"
            echo "  --compose-file FILE     Docker Compose file (default: docker-compose.prod.yml)"
            echo ""
            echo "Build Options:"
            echo "  --skip-ssl              Skip SSL/HTTPS configuration"
            echo "  --skip-backup           Skip backup creation"
            echo "  --skip-build            Skip Docker image build (use existing images)"
            echo "  --skip-frontend         Skip frontend build step"
            echo "  --force-rebuild         Force rebuild all images with --no-cache"
            echo ""
            echo "Advanced Options:"
            echo "  --backend-port PORT     Backend port (default: 8000)"
            echo "  --backend-timeout SEC   Backend startup timeout (default: 180s, quick: 40s)"
            echo ""
            echo "Help:"
            echo "  --help                  Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                  # Full production deployment"
            echo "  $0 --quick                          # Quick deployment (dev/testing)"
            echo "  $0 --skip-ssl                       # Deploy without SSL (HTTP only)"
            echo "  $0 --skip-build --skip-frontend     # Deploy without rebuilding anything"
            echo "  $0 --force-rebuild                  # Force rebuild all images from scratch"
            echo "  $0 --backend-timeout 300            # Increase backend startup timeout"
            echo ""
            echo "Quick Mode Details:"
            echo "  Automatically enables: --skip-backup --skip-ssl"
            echo "  Reduced timeouts: Postgres 30s, Redis 20s, Backend 40s, Nginx 20s"
            echo "  Skips: Admin user creation"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main function
main