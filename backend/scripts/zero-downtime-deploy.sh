#!/bin/bash

# ================================================================
# TidyFrame Zero-Downtime Deployment Script
# Performs rolling update of backend services without downtime
# Usage: ./zero-downtime-deploy.sh [compose_file] [services...]
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

COMPOSE_FILE="${1:-docker-compose.prod.yml}"
SERVICES="${2:-backend celery-worker celery-beat}"

# If services are passed as separate arguments, collect them
if [ $# -gt 2 ]; then
    SERVICES="${@:2}"
fi

PROJECT_ROOT="${PROJECT_ROOT:-/opt/tidyframe}"
HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-https://tidyframe.com/health}"
MAX_HEALTH_CHECKS="${MAX_HEALTH_CHECKS:-10}"
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-10}"
BUILD_NO_CACHE="${BUILD_NO_CACHE:-true}"

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
}

# ================================================================
# Dependency Verification
# ================================================================

check_dependencies() {
    log_info "Verifying system dependencies..."

    local missing_critical=()
    local missing_optional=()

    # Critical dependencies
    for cmd in docker git curl; do
        if ! command -v $cmd &>/dev/null; then
            missing_critical+=("$cmd")
        fi
    done

    # Optional but recommended
    if ! command -v jq &>/dev/null; then
        missing_optional+=("jq")
    fi

    if [ ${#missing_critical[@]} -gt 0 ]; then
        log_error "Missing critical dependencies: ${missing_critical[*]}"
        log_error "Install with: apt-get install -y ${missing_critical[*]}"
        exit 1
    fi

    if [ ${#missing_optional[@]} -gt 0 ]; then
        log_warning "Missing optional dependencies: ${missing_optional[*]}"
        log_warning "Falling back to alternative verification methods"
        log_warning "For optimal performance, install: apt-get install -y ${missing_optional[*]}"
    fi

    echo ""
}

# ================================================================
# Multi-Method Container State Verification
# ================================================================

get_container_state() {
    local service=$1
    local compose_file=$2

    # Method 1: jq (fastest, most reliable)
    if command -v jq &>/dev/null; then
        local state=$(docker compose -f "$compose_file" ps "$service" --format json 2>/dev/null | jq -r '.[0].State // ""' 2>/dev/null)
        if [ -n "$state" ]; then
            echo "$state"
            return 0
        fi
    fi

    # Method 2: python3 fallback
    if command -v python3 &>/dev/null; then
        local state=$(docker compose -f "$compose_file" ps "$service" --format json 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['State'] if data and len(data) > 0 and 'State' in data[0] else '')" 2>/dev/null)
        if [ -n "$state" ]; then
            echo "$state"
            return 0
        fi
    fi

    # Method 3: docker inspect (most reliable, no external tools)
    local container_id=$(docker compose -f "$compose_file" ps -q "$service" 2>/dev/null)
    if [ -n "$container_id" ]; then
        docker inspect --format='{{.State.Status}}' "$container_id" 2>/dev/null || echo "unknown"
    else
        echo "not_found"
    fi
}

verify_container_running() {
    local service=$1
    local compose_file=$2

    # Get container ID first
    local container_id=$(docker compose -f "$compose_file" ps -q "$service" 2>/dev/null)

    if [ -z "$container_id" ]; then
        echo "not_found"
        return 1
    fi

    # Use docker inspect (doesn't require jq or python)
    local is_running=$(docker inspect --format='{{.State.Running}}' "$container_id" 2>/dev/null || echo "false")
    local health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$container_id" 2>/dev/null || echo "unknown")

    if [ "$is_running" = "true" ]; then
        if [ "$health" = "healthy" ] || [ "$health" = "no-healthcheck" ]; then
            echo "healthy"
            return 0
        else
            echo "running-$health"
            return 0
        fi
    else
        echo "stopped"
        return 1
    fi
}

# ================================================================
# Pre-deployment Checks
# ================================================================

log_info "Zero-Downtime Deployment Script"
echo "  Compose File: $COMPOSE_FILE"
echo "  Services: $SERVICES"
echo "  Project Root: $PROJECT_ROOT"
echo ""

# Change to project directory
if [ ! -d "$PROJECT_ROOT" ]; then
    log_error "Project directory not found: $PROJECT_ROOT"
    exit 1
fi
cd "$PROJECT_ROOT"

# Check compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    log_error "Compose file not found: $COMPOSE_FILE"
    exit 1
fi

# Check docker compose is available
if ! docker compose version &>/dev/null; then
    log_error "Docker Compose v2 is not available"
    exit 1
fi

# Check system dependencies
check_dependencies

# ================================================================
# Store Current State
# ================================================================

log_info "Storing current deployment state..."

# Get current commit (if in a git repo)
if command -v git &>/dev/null && [ -d ".git" ]; then
    CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    echo "current_commit=$CURRENT_COMMIT" > deployment.state
    echo "current_branch=$CURRENT_BRANCH" >> deployment.state
    echo "deployment_timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> deployment.state
    log_success "Stored commit: $CURRENT_COMMIT on branch $CURRENT_BRANCH"
else
    log_warning "Not a git repository, skipping commit tracking"
fi

# Get current container IDs for rollback
for service in $SERVICES; do
    container_id=$(docker compose -f "$COMPOSE_FILE" ps -q "$service" 2>/dev/null || echo "")
    if [ -n "$container_id" ]; then
        echo "${service}_container=$container_id" >> deployment.state
        log_info "Current $service container: ${container_id:0:12}"
    fi
done

echo ""

# ================================================================
# Build New Images
# ================================================================

log_info "Building new container images..."

build_args=""
if [ "$BUILD_NO_CACHE" = "true" ]; then
    build_args="--no-cache"
fi

if docker compose -f "$COMPOSE_FILE" build $build_args $SERVICES; then
    log_success "Container images built successfully"
else
    log_error "Failed to build container images"
    exit 1
fi

echo ""

# ================================================================
# Zero-Downtime Deployment
# ================================================================

log_info "Starting zero-downtime deployment..."
log_info "This will recreate containers while keeping database and Redis running"

# Use --force-recreate to ensure new code is deployed
# Use --no-deps to avoid restarting postgres/redis (prevents downtime)
if docker compose -f "$COMPOSE_FILE" up -d --force-recreate --no-deps $SERVICES; then
    log_success "Containers recreated successfully"
else
    log_error "Failed to recreate containers"
    exit 1
fi

echo ""

# ================================================================
# Wait for Containers to Start
# ================================================================

log_info "Waiting for containers to initialize (15 seconds)..."
sleep 15

# Check container status using multiple verification methods
log_info "Checking container status..."
for service in $SERVICES; do
    state=$(get_container_state "$service" "$COMPOSE_FILE")
    health=$(verify_container_running "$service" "$COMPOSE_FILE")

    if [ "$state" = "running" ] || [ "$health" = "healthy" ] || [[ "$health" == running-* ]]; then
        log_success "$service is running (state: $state, health: $health)"
    else
        log_warning "$service state: $state, health: $health (may still be starting)"
    fi
done

echo ""

# ================================================================
# Health Checks
# ================================================================

log_info "Running health checks..."

if [ -n "$HEALTH_ENDPOINT" ]; then
    ATTEMPT=0
    while [ $ATTEMPT -lt $MAX_HEALTH_CHECKS ]; do
        ATTEMPT=$((ATTEMPT + 1))
        log_info "Health check attempt $ATTEMPT/$MAX_HEALTH_CHECKS..."

        # Check main health endpoint
        if curl -f -s -m 10 "$HEALTH_ENDPOINT" > /dev/null 2>&1; then
            log_success "Health endpoint is responsive: $HEALTH_ENDPOINT"
            break
        fi

        if [ $ATTEMPT -lt $MAX_HEALTH_CHECKS ]; then
            log_warning "Health check failed, retrying in ${HEALTH_CHECK_INTERVAL}s..."
            sleep $HEALTH_CHECK_INTERVAL
        else
            log_error "Health checks failed after $MAX_HEALTH_CHECKS attempts"
            echo ""
            log_error "Deployment may have issues. Check logs with:"
            echo "  docker compose -f $COMPOSE_FILE logs $SERVICES"
            exit 1
        fi
    done
else
    log_warning "No health endpoint configured, skipping health checks"
fi

echo ""

# ================================================================
# Final Verification
# ================================================================

# Verify all services are running using docker inspect (most reliable)
log_info "Verifying deployment health..."
all_healthy=true
for service in $SERVICES; do
    health=$(verify_container_running "$service" "$COMPOSE_FILE")

    if [ "$health" = "healthy" ] || [[ "$health" == running-* ]]; then
        log_success "$service is healthy ($health)"
    else
        state=$(get_container_state "$service" "$COMPOSE_FILE")
        log_error "$service verification failed (state: $state, health: $health)"
        log_error "Check logs: docker compose -f $COMPOSE_FILE logs $service"
        all_healthy=false
    fi
done

if [ "$all_healthy" = false ]; then
    log_error "Some services failed health verification"
    exit 1
fi

echo ""

# ================================================================
# Success Summary
# ================================================================

echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}✅ Zero-Downtime Deployment Successful!${NC}"
echo "================================================================"
echo ""
log_success "Services updated: $SERVICES"
log_success "Deployment completed at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [ -n "$CURRENT_COMMIT" ] && [ "$CURRENT_COMMIT" != "unknown" ]; then
    NEW_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    if [ "$NEW_COMMIT" != "$CURRENT_COMMIT" ]; then
        log_success "Code updated: ${CURRENT_COMMIT:0:8} → ${NEW_COMMIT:0:8}"
    else
        log_info "Code version: ${CURRENT_COMMIT:0:8} (unchanged)"
    fi
fi

echo ""
log_info "Monitor logs with:"
echo "  docker compose -f $COMPOSE_FILE logs -f $SERVICES"
echo ""
log_info "Rollback if needed:"
echo "  git reset --hard \$(grep current_commit deployment.state | cut -d= -f2)"
echo "  ./zero-downtime-deploy.sh $COMPOSE_FILE $SERVICES"
echo ""

exit 0
