#!/bin/bash

# =============================================================================
# TidyFrame Backup Script - Production Environment
# =============================================================================
# This script creates comprehensive backups including:
# - Database dump with compression
# - Application data directory
# - Configuration files
# - SSL certificates
# - Docker volumes (optional)
# - Backup verification and integrity checks
# =============================================================================

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

# =============================================================================
# Configuration & Constants
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BACKUP_LOG="$PROJECT_ROOT/logs/backup-$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
BACKUP_NAME=${BACKUP_NAME:-"backup-$(date +%Y%m%d_%H%M%S)"}
BACKUP_DIR=${BACKUP_DIR:-"$PROJECT_ROOT/backups/$BACKUP_NAME"}
COMPRESS_BACKUP=${COMPRESS_BACKUP:-true}
INCLUDE_DOCKER_VOLUMES=${INCLUDE_DOCKER_VOLUMES:-false}
RETENTION_DAYS=${RETENTION_DAYS:-30}
VERIFY_BACKUP=${VERIFY_BACKUP:-true}

# =============================================================================
# Utility Functions
# =============================================================================

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] [$level] $message" | tee -a "$BACKUP_LOG"
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
    echo "  TidyFrame Backup - Production Environment"
    echo "  Creating backup: $BACKUP_NAME"
    echo "  Timestamp: $(date)"
    echo "================================================================="
    echo -e "${NC}"
}

get_file_size() {
    local file_path=$1
    if [ -f "$file_path" ]; then
        du -sh "$file_path" | cut -f1
    elif [ -d "$file_path" ]; then
        du -sh "$file_path" | cut -f1
    else
        echo "0B"
    fi
}

# =============================================================================
# Backup Functions
# =============================================================================

create_backup_directory() {
    log_info "Creating backup directory: $BACKUP_DIR"
    
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Set proper permissions
    chmod 755 "$BACKUP_DIR"
    chmod 755 "$PROJECT_ROOT/logs"
    
    log_success "Backup directory created"
}

backup_database() {
    log_info "Backing up PostgreSQL database..."
    
    # Check if database container is running
    if ! docker ps | grep -q "tidyframe-postgres-prod"; then
        log_error "PostgreSQL container is not running"
        return 1
    fi
    
    # Create database dump with compression
    local db_backup_file="$BACKUP_DIR/database.sql"
    local db_compressed_file="$BACKUP_DIR/database.sql.gz"
    
    # Dump database
    docker exec tidyframe-postgres-prod pg_dump \
        -U tidyframe \
        -h localhost \
        --verbose \
        --clean \
        --no-owner \
        --no-privileges \
        tidyframe > "$db_backup_file" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        local db_size=$(get_file_size "$db_backup_file")
        log_success "Database dump created (size: $db_size)"
        
        # Compress database dump
        if [ "$COMPRESS_BACKUP" = "true" ]; then
            log_info "Compressing database dump..."
            gzip "$db_backup_file"
            local compressed_size=$(get_file_size "$db_compressed_file")
            log_success "Database dump compressed (size: $compressed_size)"
        fi
    else
        log_error "Database dump failed"
        return 1
    fi
    
    # Create database info file
    docker exec tidyframe-postgres-prod psql -U tidyframe -c "
        SELECT 
            'Database: ' || current_database() ||
            ', Size: ' || pg_size_pretty(pg_database_size(current_database())) ||
            ', Tables: ' || count(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'public';
    " > "$BACKUP_DIR/database_info.txt" 2>/dev/null || true
    
    return 0
}

backup_redis() {
    log_info "Backing up Redis data..."
    
    # Check if Redis container is running
    if ! docker ps | grep -q "tidyframe-redis-prod"; then
        log_warning "Redis container is not running, skipping Redis backup"
        return 0
    fi
    
    # Create Redis dump
    docker exec tidyframe-redis-prod redis-cli -a "$REDIS_PASSWORD" BGSAVE >/dev/null 2>&1 || {
        log_warning "Redis backup failed or Redis password not set"
        return 0
    }
    
    # Wait for background save to complete
    local save_complete=false
    local wait_count=0
    local max_wait=30
    
    while [ $wait_count -lt $max_wait ] && [ "$save_complete" = false ]; do
        local last_save=$(docker exec tidyframe-redis-prod redis-cli -a "$REDIS_PASSWORD" LASTSAVE 2>/dev/null || echo "0")
        local save_in_progress=$(docker exec tidyframe-redis-prod redis-cli -a "$REDIS_PASSWORD" INFO persistence 2>/dev/null | grep "rdb_bgsave_in_progress:1" || echo "")
        
        if [ -z "$save_in_progress" ]; then
            save_complete=true
        else
            sleep 2
            wait_count=$((wait_count + 1))
        fi
    done
    
    # Copy Redis dump file
    if docker cp tidyframe-redis-prod:/data/dump.rdb "$BACKUP_DIR/redis-dump.rdb" 2>/dev/null; then
        local redis_size=$(get_file_size "$BACKUP_DIR/redis-dump.rdb")
        log_success "Redis backup created (size: $redis_size)"
    else
        log_warning "Redis dump file copy failed"
    fi
    
    return 0
}

backup_application_data() {
    log_info "Backing up application data..."
    
    if [ -d "$PROJECT_ROOT/data" ]; then
        cp -r "$PROJECT_ROOT/data" "$BACKUP_DIR/"
        local data_size=$(get_file_size "$BACKUP_DIR/data")
        log_success "Application data backed up (size: $data_size)"
    else
        log_warning "Data directory not found: $PROJECT_ROOT/data"
    fi
    
    return 0
}

backup_configuration() {
    log_info "Backing up configuration files..."
    
    # Backup environment file
    if [ -f "$PROJECT_ROOT/.env" ]; then
        cp "$PROJECT_ROOT/.env" "$BACKUP_DIR/env.backup"
        log_success "Environment configuration backed up"
    else
        log_warning "Environment file not found: $PROJECT_ROOT/.env"
    fi
    
    # Backup config directory
    if [ -d "$PROJECT_ROOT/config" ]; then
        cp -r "$PROJECT_ROOT/config" "$BACKUP_DIR/"
        log_success "Configuration directory backed up"
    fi
    
    # Backup Docker Compose files
    local compose_files=("docker-compose.prod.yml" "docker-compose.yml" "docker-compose.override.yml")
    for compose_file in "${compose_files[@]}"; do
        if [ -f "$PROJECT_ROOT/$compose_file" ]; then
            cp "$PROJECT_ROOT/$compose_file" "$BACKUP_DIR/"
            log_success "Docker Compose file backed up: $compose_file"
        fi
    done
    
    # Backup nginx configuration
    if [ -d "$PROJECT_ROOT/nginx" ]; then
        cp -r "$PROJECT_ROOT/nginx" "$BACKUP_DIR/"
        log_success "Nginx configuration backed up"
    fi
    
    return 0
}

backup_ssl_certificates() {
    log_info "Backing up SSL certificates..."
    
    if [ -d "$PROJECT_ROOT/data/ssl" ]; then
        mkdir -p "$BACKUP_DIR/ssl"
        cp -r "$PROJECT_ROOT/data/ssl/"* "$BACKUP_DIR/ssl/" 2>/dev/null || {
            log_warning "SSL certificate backup failed or no certificates found"
        }
        
        # Create certificate info
        if [ -f "$PROJECT_ROOT/data/ssl/fullchain.pem" ]; then
            openssl x509 -in "$PROJECT_ROOT/data/ssl/fullchain.pem" -text -noout > "$BACKUP_DIR/ssl/certificate_info.txt" 2>/dev/null || true
            log_success "SSL certificates backed up"
        fi
    else
        log_info "No SSL certificates found to backup"
    fi
    
    return 0
}

backup_docker_volumes() {
    if [ "$INCLUDE_DOCKER_VOLUMES" != "true" ]; then
        log_info "Skipping Docker volumes backup (INCLUDE_DOCKER_VOLUMES=false)"
        return 0
    fi
    
    log_info "Backing up Docker volumes..."
    
    # Get list of TidyFrame-related volumes
    local volumes=$(docker volume ls --filter name=tidyframe --format "{{.Name}}" 2>/dev/null || echo "")
    
    if [ -n "$volumes" ]; then
        mkdir -p "$BACKUP_DIR/volumes"
        
        for volume in $volumes; do
            log_info "Backing up volume: $volume"
            docker run --rm \
                -v "$volume:/source:ro" \
                -v "$BACKUP_DIR/volumes:/backup" \
                alpine:latest \
                tar czf "/backup/${volume}.tar.gz" -C /source . 2>/dev/null || {
                log_warning "Failed to backup volume: $volume"
            }
        done
        
        log_success "Docker volumes backed up"
    else
        log_info "No TidyFrame Docker volumes found"
    fi
    
    return 0
}

create_backup_manifest() {
    log_info "Creating backup manifest..."
    
    local manifest_file="$BACKUP_DIR/backup_manifest.txt"
    
    cat > "$manifest_file" << EOF
TidyFrame Production Backup Manifest
====================================

Backup Information:
  Name: $BACKUP_NAME
  Created: $(date)
  Server: $(hostname)
  User: $(whoami)
  Project Root: $PROJECT_ROOT
  Backup Directory: $BACKUP_DIR

System Information:
  OS: $(uname -a)
  Docker Version: $(docker --version 2>/dev/null || echo "Not available")
  Docker Compose Version: $(docker compose --version 2>/dev/null || echo "Not available")

TidyFrame Version:
  Git Commit: $(cd "$PROJECT_ROOT" && git rev-parse HEAD 2>/dev/null || echo "Not available")
  Git Branch: $(cd "$PROJECT_ROOT" && git branch --show-current 2>/dev/null || echo "Not available")
  Git Tag: $(cd "$PROJECT_ROOT" && git describe --tags 2>/dev/null || echo "Not available")

Backup Contents:
$(find "$BACKUP_DIR" -type f -exec basename {} \; | sort | sed 's/^/  - /')

File Sizes:
$(find "$BACKUP_DIR" -type f -exec du -sh {} \; | sort -k1,1h | sed 's/^/  /')

Docker Services Status:
$(docker compose -f "$PROJECT_ROOT/docker-compose.prod.yml" ps 2>/dev/null || echo "  Docker Compose not available")

Total Backup Size: $(get_file_size "$BACKUP_DIR")
EOF
    
    log_success "Backup manifest created"
}

verify_backup() {
    if [ "$VERIFY_BACKUP" != "true" ]; then
        log_info "Skipping backup verification (VERIFY_BACKUP=false)"
        return 0
    fi
    
    log_info "Verifying backup integrity..."
    
    local verification_failed=0
    
    # Verify database backup
    if [ -f "$BACKUP_DIR/database.sql" ]; then
        if head -n 10 "$BACKUP_DIR/database.sql" | grep -q "PostgreSQL database dump"; then
            log_success "✅ Database backup verified"
        else
            log_error "❌ Database backup appears corrupted"
            verification_failed=1
        fi
    elif [ -f "$BACKUP_DIR/database.sql.gz" ]; then
        if gunzip -t "$BACKUP_DIR/database.sql.gz" 2>/dev/null; then
            log_success "✅ Compressed database backup verified"
        else
            log_error "❌ Compressed database backup appears corrupted"
            verification_failed=1
        fi
    else
        log_warning "⚠️  No database backup found to verify"
    fi
    
    # Verify configuration backup
    if [ -f "$BACKUP_DIR/env.backup" ]; then
        if [ -s "$BACKUP_DIR/env.backup" ]; then
            log_success "✅ Environment configuration backup verified"
        else
            log_error "❌ Environment configuration backup is empty"
            verification_failed=1
        fi
    else
        log_warning "⚠️  No environment configuration backup found"
    fi
    
    # Verify data directory backup
    if [ -d "$BACKUP_DIR/data" ]; then
        local data_file_count=$(find "$BACKUP_DIR/data" -type f | wc -l)
        log_success "✅ Data directory backup verified ($data_file_count files)"
    else
        log_warning "⚠️  No data directory backup found"
    fi
    
    # Verify backup manifest
    if [ -f "$BACKUP_DIR/backup_manifest.txt" ]; then
        if [ -s "$BACKUP_DIR/backup_manifest.txt" ]; then
            log_success "✅ Backup manifest verified"
        else
            log_error "❌ Backup manifest is empty"
            verification_failed=1
        fi
    else
        log_error "❌ Backup manifest missing"
        verification_failed=1
    fi
    
    if [ $verification_failed -eq 0 ]; then
        log_success "🎉 Backup verification passed"
        return 0
    else
        log_error "💥 Backup verification failed"
        return 1
    fi
}

cleanup_old_backups() {
    log_info "Cleaning up old backups (retention: ${RETENTION_DAYS} days)..."
    
    local backups_dir="$PROJECT_ROOT/backups"
    local deleted_count=0
    
    if [ -d "$backups_dir" ]; then
        # Find and delete backups older than retention period
        while IFS= read -r -d '' old_backup; do
            log_info "Deleting old backup: $(basename "$old_backup")"
            rm -rf "$old_backup"
            deleted_count=$((deleted_count + 1))
        done < <(find "$backups_dir" -maxdepth 1 -type d -name "backup-*" -mtime +$RETENTION_DAYS -print0 2>/dev/null)
        
        # Also clean up pre-rollback backups older than 7 days
        while IFS= read -r -d '' old_backup; do
            log_info "Deleting old pre-rollback backup: $(basename "$old_backup")"
            rm -rf "$old_backup"
            deleted_count=$((deleted_count + 1))
        done < <(find "$backups_dir" -maxdepth 1 -type d -name "pre-rollback-*" -mtime +7 -print0 2>/dev/null)
    fi
    
    if [ $deleted_count -gt 0 ]; then
        log_success "Cleaned up $deleted_count old backups"
    else
        log_info "No old backups to clean up"
    fi
}

# =============================================================================
# Main Backup Function
# =============================================================================

main() {
    print_banner
    
    # Create log directory
    mkdir -p "$PROJECT_ROOT/logs"
    
    local start_time=$(date +%s)
    
    # Execute backup steps
    create_backup_directory
    backup_database
    backup_redis
    backup_application_data
    backup_configuration
    backup_ssl_certificates
    backup_docker_volumes
    create_backup_manifest
    
    if verify_backup; then
        cleanup_old_backups
        
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        local total_size=$(get_file_size "$BACKUP_DIR")
        
        log_success "🎉 Backup completed successfully in ${duration}s"
        log_success "📦 Total backup size: $total_size"
        
        echo -e "${GREEN}"
        echo "================================================================="
        echo "  TidyFrame Backup Completed!"
        echo ""
        echo "  📁 Backup Location: $BACKUP_DIR"
        echo "  📊 Backup Size: $total_size"
        echo "  ⏱️  Duration: ${duration}s"
        echo ""
        echo "  📋 Manifest: $BACKUP_DIR/backup_manifest.txt"
        echo "  📝 Log File: $BACKUP_LOG"
        echo ""
        echo "  🔄 Restore Command:"
        echo "     ./scripts/rollback.sh $BACKUP_NAME"
        echo "================================================================="
        echo -e "${NC}"
        
        # Return backup directory for scripts
        echo "$BACKUP_DIR"
        
    else
        log_error "Backup completed but verification failed"
        exit 1
    fi
}

# =============================================================================
# Script Entry Point
# =============================================================================

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            BACKUP_NAME="$2"
            BACKUP_DIR="$PROJECT_ROOT/backups/$BACKUP_NAME"
            shift 2
            ;;
        --dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --no-compress)
            COMPRESS_BACKUP=false
            shift
            ;;
        --include-volumes)
            INCLUDE_DOCKER_VOLUMES=true
            shift
            ;;
        --no-verify)
            VERIFY_BACKUP=false
            shift
            ;;
        --retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        --help)
            echo "TidyFrame Backup Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --name NAME           Set backup name (default: backup-YYYYMMDD_HHMMSS)"
            echo "  --dir PATH            Set backup directory (default: PROJECT_ROOT/backups/NAME)"
            echo "  --no-compress         Disable backup compression"
            echo "  --include-volumes     Include Docker volumes in backup"
            echo "  --no-verify           Skip backup verification"
            echo "  --retention DAYS      Set backup retention period (default: 30)"
            echo "  --help                Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  BACKUP_NAME           Backup name"
            echo "  BACKUP_DIR            Backup directory"
            echo "  COMPRESS_BACKUP       Enable/disable compression (true/false)"
            echo "  INCLUDE_DOCKER_VOLUMES Include Docker volumes (true/false)"
            echo "  RETENTION_DAYS        Backup retention period"
            echo "  VERIFY_BACKUP         Enable/disable verification (true/false)"
            echo ""
            echo "Examples:"
            echo "  $0                                # Full backup with defaults"
            echo "  $0 --name manual-backup          # Custom backup name"
            echo "  $0 --include-volumes --no-compress # Include volumes without compression"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Run main function
main