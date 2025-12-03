#!/bin/bash

# =============================================================================
# TidyFrame Unified Control Script
# Single control point for development, production, and deployment
# Usage: ./tidyframe.sh [command] [options]
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default to development mode
MODE="${1:-dev}"
shift || true

# Functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

print_usage() {
    cat << EOF
TidyFrame Control Script
========================

Usage: ./tidyframe.sh [command] [options]

Commands:
  dev, development    Start development environment
  prod, production    Start production environment locally
  stop               Stop all services
  restart            Restart all services
  status             Show service status
  logs [service]     Show logs (optionally for specific service)
  admin              Create/update admin user
  backup             Backup database
  restore [file]     Restore database from backup
  deploy             Deploy to production server
  clean              Clean up Docker resources
  help               Show this help message

Environment Selection:
  The script automatically uses the appropriate .env file:
  - Development: .env.development
  - Production: .env.production

Examples:
  ./tidyframe.sh dev           # Start development
  ./tidyframe.sh prod          # Start production locally
  ./tidyframe.sh logs backend  # View backend logs
  ./tidyframe.sh admin         # Create admin user
  ./tidyframe.sh deploy        # Deploy to production

EOF
}

# Setup environment based on mode
setup_environment() {
    local env_mode=$1
    
    if [ "$env_mode" = "prod" ] || [ "$env_mode" = "production" ]; then
        ENV_FILE=".env.production"
        COMPOSE_FILE="docker compose.prod.yml"
        ENV_NAME="PRODUCTION"
    else
        ENV_FILE=".env.development"
        COMPOSE_FILE="docker compose.yml"
        ENV_NAME="DEVELOPMENT"
    fi
    
    # Check if environment file exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error "$ENV_FILE not found!"
        if [ "$ENV_FILE" = ".env.development" ]; then
            log_info "Creating .env.development from template..."
            # .env.development should already exist from our previous step
            exit 1
        else
            log_error "Please ensure .env.production exists with production values"
            exit 1
        fi
    fi
    
    # Copy to .env for Docker Compose
    cp "$ENV_FILE" .env
    log_info "Using $ENV_NAME environment ($ENV_FILE)"
    
    # Export for use in commands
    export COMPOSE_FILE
    export ENV_FILE
    export ENV_NAME
}

# Start services
start_services() {
    setup_environment "$1"
    
    log_info "Starting $ENV_NAME services..."
    
    # Create necessary directories
    mkdir -p backend/uploads backend/results backend/logs
    
    # Start services
    docker compose -f "$COMPOSE_FILE" up -d --build
    
    log_success "$ENV_NAME services started!"
    log_info "View logs with: ./tidyframe.sh logs"
    
    # Get base URL from environment or use localhost default
    BASE_URL="${BASE_URL:-http://localhost}"
    
    if [ "$ENV_NAME" = "DEVELOPMENT" ]; then
        log_info "Access the application at: $BASE_URL"
        log_info "API documentation at: $BASE_URL/api/docs"
    else
        log_info "Production mode started locally"
        log_info "Access at: $BASE_URL"
    fi
}

# Stop services
stop_services() {
    log_info "Stopping all services..."
    
    # Try both compose files to ensure everything stops
    docker compose -f docker compose.yml down 2>/dev/null || true
    docker compose -f docker compose.prod.yml down 2>/dev/null || true
    
    log_success "All services stopped"
}

# Show status
show_status() {
    log_info "Service Status:"
    docker compose ps
    
    echo ""
    log_info "Resource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# Show logs
show_logs() {
    local service="$1"
    
    # Determine which compose file is active
    if docker compose -f docker compose.prod.yml ps 2>/dev/null | grep -q "Up"; then
        COMPOSE_FILE="docker compose.prod.yml"
    else
        COMPOSE_FILE="docker compose.yml"
    fi
    
    if [ -z "$service" ]; then
        docker compose -f "$COMPOSE_FILE" logs -f --tail=100
    else
        docker compose -f "$COMPOSE_FILE" logs -f --tail=100 "$service"
    fi
}

# Admin management
manage_admin() {
    # Determine which compose file is active
    if docker compose -f docker compose.prod.yml ps 2>/dev/null | grep -q "backend.*Up"; then
        COMPOSE_FILE="docker compose.prod.yml"
    else
        COMPOSE_FILE="docker compose.yml"
    fi
    
    log_info "Creating/updating admin user..."
    docker compose -f "$COMPOSE_FILE" exec backend python scripts/setup_admin.py
}

# Backup database
backup_database() {
    log_info "Creating database backup..."
    
    local backup_dir="backups"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$backup_dir/backup_${timestamp}.sql"
    
    mkdir -p "$backup_dir"
    
    # Determine which postgres container is running
    if [ "$ENV_NAME" = "PRODUCTION" ] || docker ps | grep -q "postgres-prod"; then
        CONTAINER="tidyframe-postgres-prod"
        DB_PASS="${POSTGRES_PASSWORD}"
    else
        CONTAINER="tidyframe-postgres-1"
        DB_PASS="${POSTGRES_PASSWORD:-devpassword123}"
    fi
    
    docker exec "$CONTAINER" pg_dump -U tidyframe tidyframe > "$backup_file"
    
    if [ $? -eq 0 ]; then
        log_success "Backup created: $backup_file"
        ls -lh "$backup_file"
    else
        log_error "Backup failed"
        exit 1
    fi
}

# Restore database
restore_database() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        log_error "Please specify backup file to restore"
        log_info "Available backups:"
        ls -la backups/*.sql 2>/dev/null || echo "No backups found"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log_warning "This will overwrite the current database. Continue? (y/n)"
    read -r confirm
    if [ "$confirm" != "y" ]; then
        log_info "Restore cancelled"
        exit 0
    fi
    
    log_info "Restoring database from: $backup_file"
    
    # Determine which postgres container is running
    if [ "$ENV_NAME" = "PRODUCTION" ] || docker ps | grep -q "postgres-prod"; then
        CONTAINER="tidyframe-postgres-prod"
    else
        CONTAINER="tidyframe-postgres-1"
    fi
    
    docker exec -i "$CONTAINER" psql -U tidyframe tidyframe < "$backup_file"
    
    if [ $? -eq 0 ]; then
        log_success "Database restored successfully"
    else
        log_error "Restore failed"
        exit 1
    fi
}

# Deploy to production
deploy_production() {
    log_info "Starting production deployment..."
    
    if [ ! -f "backend/scripts/deploy.sh" ]; then
        log_error "Deployment script not found at backend/scripts/deploy.sh"
        exit 1
    fi
    
    # Run the deployment script
    bash backend/scripts/deploy.sh "$@"
}

# Clean Docker resources
clean_docker() {
    log_warning "This will remove stopped containers, unused images, and volumes. Continue? (y/n)"
    read -r confirm
    if [ "$confirm" != "y" ]; then
        log_info "Clean cancelled"
        exit 0
    fi
    
    log_info "Cleaning Docker resources..."
    
    # Stop all services first
    stop_services
    
    # Clean up
    docker system prune -a --volumes -f
    
    log_success "Docker resources cleaned"
}

# Main execution
main() {
    case "$MODE" in
        dev|development)
            start_services "dev"
            ;;
        prod|production)
            start_services "prod"
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 2
            start_services "${1:-dev}"
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$1"
            ;;
        admin)
            manage_admin
            ;;
        backup)
            backup_database
            ;;
        restore)
            restore_database "$1"
            ;;
        deploy)
            deploy_production "$@"
            ;;
        clean)
            clean_docker
            ;;
        help|--help|-h)
            print_usage
            ;;
        *)
            log_error "Unknown command: $MODE"
            print_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"