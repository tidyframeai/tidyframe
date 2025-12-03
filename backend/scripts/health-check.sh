#!/bin/bash

# =============================================================================
# TidyFrame Health Check and Monitoring Script
# =============================================================================
# This script provides comprehensive health monitoring for TidyFrame:
# - Service availability checks
# - Database connectivity and performance
# - API endpoint testing
# - Resource utilization monitoring
# - SSL certificate validation
# - Automated alerts and reporting
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration & Constants
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
HEALTH_LOG="$PROJECT_ROOT/logs/health-check-$(date +%Y%m%d_%H%M%S).log"
ALERT_LOG="$PROJECT_ROOT/logs/alerts.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default configuration - can be overridden via environment variables
DOMAIN=${DOMAIN:-"tidyframe.com"}
CHECK_INTERVAL=${CHECK_INTERVAL:-300}  # 5 minutes
ALERT_EMAIL=${ALERT_EMAIL:-""}
SLACK_WEBHOOK=${SLACK_WEBHOOK:-""}
MAX_RESPONSE_TIME=${MAX_RESPONSE_TIME:-5000}  # 5 seconds
MIN_DISK_SPACE_GB=${MIN_DISK_SPACE_GB:-5}
MIN_MEMORY_MB=${MIN_MEMORY_MB:-512}
MAX_CPU_PERCENT=${MAX_CPU_PERCENT:-90}

# Health check results
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
HEALTH_SCORE=0

# =============================================================================
# Utility Functions
# =============================================================================

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] [$level] $message" | tee -a "$HEALTH_LOG"
}

log_info() {
    log "INFO" "${BLUE}$*${NC}"
}

log_success() {
    log "SUCCESS" "${GREEN}$*${NC}"
    ((PASSED_CHECKS++))
}

log_warning() {
    log "WARNING" "${YELLOW}$*${NC}"
}

log_error() {
    log "ERROR" "${RED}$*${NC}"
    ((FAILED_CHECKS++))
}

log_alert() {
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] ALERT: $message" | tee -a "$ALERT_LOG"
    send_alert "$message"
}

increment_check() {
    ((TOTAL_CHECKS++))
}

print_banner() {
    echo -e "${GREEN}"
    echo "================================================================="
    echo "  TidyFrame Health Check & Monitoring"
    echo "  Domain: $DOMAIN"
    echo "  Timestamp: $(date)"
    echo "================================================================="
    echo -e "${NC}"
}

# =============================================================================
# Alert Functions
# =============================================================================

send_alert() {
    local message="$1"
    local severity="${2:-WARNING}"
    
    # Email alert
    if [ -n "$ALERT_EMAIL" ] && command -v mail &> /dev/null; then
        echo "TidyFrame Health Alert - $severity: $message" | mail -s "TidyFrame Alert" "$ALERT_EMAIL" || true
    fi
    
    # Slack webhook alert
    if [ -n "$SLACK_WEBHOOK" ] && command -v curl &> /dev/null; then
        local payload=$(cat << EOF
{
    "text": "🚨 TidyFrame Health Alert",
    "attachments": [
        {
            "color": "$([ "$severity" = "CRITICAL" ] && echo "danger" || echo "warning")",
            "fields": [
                {
                    "title": "Severity",
                    "value": "$severity",
                    "short": true
                },
                {
                    "title": "Message",
                    "value": "$message",
                    "short": false
                },
                {
                    "title": "Timestamp",
                    "value": "$(date)",
                    "short": true
                },
                {
                    "title": "Server",
                    "value": "$(hostname)",
                    "short": true
                }
            ]
        }
    ]
}
EOF
)
        curl -X POST -H 'Content-type: application/json' \
            --data "$payload" \
            "$SLACK_WEBHOOK" &>/dev/null || true
    fi
}

# =============================================================================
# Docker Service Health Checks
# =============================================================================

check_docker_services() {
    log_info "Checking Docker services status..."
    increment_check
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        return 1
    fi
    
    if ! docker info &>/dev/null; then
        log_error "Docker daemon is not running"
        return 1
    fi
    
    # Check if docker compose file exists
    if [ ! -f "$PROJECT_ROOT/docker-compose.prod.yml" ]; then
        log_error "Docker Compose production file not found"
        return 1
    fi
    
    # Get service status
    local services=("postgres" "redis" "backend" "frontend" "nginx")
    local failed_services=()
    
    for service in "${services[@]}"; do
        increment_check
        if docker compose -f "$PROJECT_ROOT/docker-compose.prod.yml" ps "$service" | grep -q "Up"; then
            log_success "Service $service is running"
        else
            log_error "Service $service is not running"
            failed_services+=("$service")
        fi
    done
    
    if [ ${#failed_services[@]} -gt 0 ]; then
        log_alert "Failed services: ${failed_services[*]}" "CRITICAL"
        return 1
    fi
    
    log_success "All Docker services are running"
}

# =============================================================================
# Database Health Checks
# =============================================================================

check_database_health() {
    log_info "Checking database health..."
    
    # PostgreSQL check
    increment_check
    if docker exec tidyframe-postgres-prod pg_isready -U tidyframe -d tidyframe &>/dev/null; then
        log_success "PostgreSQL is responding"
        
        # Check database connections
        increment_check
        local connections=$(docker exec tidyframe-postgres-prod psql -U tidyframe -d tidyframe -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs)
        if [ -n "$connections" ] && [ "$connections" -lt 180 ]; then  # Max 180 out of 200 connections
            log_success "PostgreSQL connections: $connections/200"
        else
            log_warning "PostgreSQL connection count high: $connections/200"
        fi
        
        # Check database size
        increment_check
        local db_size=$(docker exec tidyframe-postgres-prod psql -U tidyframe -d tidyframe -t -c "SELECT pg_size_pretty(pg_database_size('tidyframe'));" 2>/dev/null | xargs)
        if [ -n "$db_size" ]; then
            log_success "Database size: $db_size"
        fi
        
    else
        log_error "PostgreSQL is not responding"
        log_alert "PostgreSQL database is down" "CRITICAL"
    fi
    
    # Redis check
    increment_check
    if [ -n "${REDIS_PASSWORD:-}" ]; then
        if docker exec tidyframe-redis-prod redis-cli -a "$REDIS_PASSWORD" ping &>/dev/null; then
            log_success "Redis is responding"
            
            # Check Redis memory usage
            increment_check
            local redis_memory=$(docker exec tidyframe-redis-prod redis-cli -a "$REDIS_PASSWORD" INFO memory | grep "used_memory_human" | cut -d: -f2 | tr -d '\r')
            if [ -n "$redis_memory" ]; then
                log_success "Redis memory usage: $redis_memory"
            fi
            
        else
            log_error "Redis is not responding"
            log_alert "Redis cache is down" "CRITICAL"
        fi
    else
        log_warning "Redis password not set, skipping Redis checks"
    fi
}

# =============================================================================
# API Health Checks
# =============================================================================

check_api_endpoints() {
    log_info "Checking API endpoints..."
    
    # Internal health check
    increment_check
    local start_time=$(date +%s%3N)
    if curl -f -s -m 10 "http://localhost:8000/health" > /dev/null; then
        local end_time=$(date +%s%3N)
        local response_time=$((end_time - start_time))
        
        if [ "$response_time" -lt "$MAX_RESPONSE_TIME" ]; then
            log_success "API health endpoint responding (${response_time}ms)"
        else
            log_warning "API health endpoint slow response (${response_time}ms)"
        fi
    else
        log_error "API health endpoint not responding"
        log_alert "API health endpoint is down" "CRITICAL"
    fi
    
    # Test database connectivity through API
    increment_check
    if curl -f -s -m 15 "http://localhost:8000/health/db" > /dev/null 2>&1; then
        log_success "API database connectivity check passed"
    else
        log_warning "API database connectivity check failed or endpoint not available"
    fi
    
    # External health check (if domain is configured)
    if [ "$DOMAIN" != "tidyframe.com" ] || dig +short "$DOMAIN" > /dev/null 2>&1; then
        increment_check
        local start_time=$(date +%s%3N)
        if curl -f -s -m 15 "https://$DOMAIN/health" > /dev/null; then
            local end_time=$(date +%s%3N)
            local response_time=$((end_time - start_time))
            log_success "External API health check passed (${response_time}ms)"
        else
            log_error "External API health check failed"
            log_alert "External API endpoint is not accessible" "CRITICAL"
        fi
    fi
}

# =============================================================================
# Frontend Health Checks
# =============================================================================

check_frontend_health() {
    log_info "Checking frontend application..."
    
    # Internal frontend check
    increment_check
    if curl -f -s -m 10 "http://localhost:3000" > /dev/null; then
        log_success "Frontend is responding internally"
    else
        log_error "Frontend is not responding internally"
    fi
    
    # External frontend check
    if [ "$DOMAIN" != "tidyframe.com" ] || dig +short "$DOMAIN" > /dev/null 2>&1; then
        increment_check
        if curl -f -s -m 15 "https://$DOMAIN" > /dev/null; then
            log_success "Frontend is accessible externally"
        else
            log_error "Frontend is not accessible externally"
            log_alert "Frontend website is not accessible" "CRITICAL"
        fi
    fi
}

# =============================================================================
# SSL Certificate Checks
# =============================================================================

check_ssl_certificates() {
    log_info "Checking SSL certificates..."
    
    local ssl_cert_path="$PROJECT_ROOT/data/ssl/fullchain.pem"
    
    increment_check
    if [ -f "$ssl_cert_path" ]; then
        # Check certificate expiration
        local expiry_date=$(openssl x509 -enddate -noout -in "$ssl_cert_path" | cut -d= -f2)
        local expiry_timestamp=$(date -d "$expiry_date" +%s)
        local current_timestamp=$(date +%s)
        local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
        
        if [ "$days_until_expiry" -gt 30 ]; then
            log_success "SSL certificate valid for $days_until_expiry days"
        elif [ "$days_until_expiry" -gt 7 ]; then
            log_warning "SSL certificate expires in $days_until_expiry days"
        elif [ "$days_until_expiry" -gt 0 ]; then
            log_error "SSL certificate expires in $days_until_expiry days"
            log_alert "SSL certificate expires soon: $days_until_expiry days" "WARNING"
        else
            log_error "SSL certificate has expired"
            log_alert "SSL certificate has expired" "CRITICAL"
        fi
        
        # Check certificate chain
        increment_check
        if openssl verify -CAfile "$ssl_cert_path" "$ssl_cert_path" &>/dev/null; then
            log_success "SSL certificate chain is valid"
        else
            log_warning "SSL certificate chain validation failed"
        fi
        
    else
        log_warning "SSL certificate file not found at $ssl_cert_path"
    fi
    
    # Test SSL connection if domain is accessible
    if [ "$DOMAIN" != "tidyframe.com" ] || dig +short "$DOMAIN" > /dev/null 2>&1; then
        increment_check
        if echo | openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" 2>/dev/null | grep -q "Verification: OK"; then
            log_success "SSL connection verification passed"
        else
            log_warning "SSL connection verification failed"
        fi
    fi
}

# =============================================================================
# System Resource Checks
# =============================================================================

check_system_resources() {
    log_info "Checking system resources..."
    
    # Disk space check
    increment_check
    local available_space_gb=$(df "$PROJECT_ROOT" | awk 'NR==2 {printf "%.1f", $4/1024/1024}')
    if (( $(echo "$available_space_gb >= $MIN_DISK_SPACE_GB" | bc -l) )); then
        log_success "Disk space available: ${available_space_gb}GB"
    else
        log_error "Low disk space: ${available_space_gb}GB available (minimum: ${MIN_DISK_SPACE_GB}GB)"
        log_alert "Low disk space: ${available_space_gb}GB available" "WARNING"
    fi
    
    # Memory check
    increment_check
    local available_memory_mb=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    if [ "$available_memory_mb" -gt "$MIN_MEMORY_MB" ]; then
        log_success "Available memory: ${available_memory_mb}MB"
    else
        log_warning "Low memory: ${available_memory_mb}MB available (minimum: ${MIN_MEMORY_MB}MB)"
    fi
    
    # CPU usage check
    increment_check
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    if (( $(echo "$cpu_usage < $MAX_CPU_PERCENT" | bc -l) )); then
        log_success "CPU usage: ${cpu_usage}%"
    else
        log_warning "High CPU usage: ${cpu_usage}%"
    fi
    
    # Load average check
    increment_check
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local cpu_cores=$(nproc)
    if (( $(echo "$load_avg < $cpu_cores" | bc -l) )); then
        log_success "Load average: $load_avg (${cpu_cores} cores)"
    else
        log_warning "High load average: $load_avg (${cpu_cores} cores)"
    fi
}

# =============================================================================
# Application-Specific Checks
# =============================================================================

check_application_health() {
    log_info "Checking application-specific health..."
    
    # Check file upload directory
    increment_check
    local upload_dir="$PROJECT_ROOT/data/uploads"
    if [ -d "$upload_dir" ] && [ -w "$upload_dir" ]; then
        local upload_count=$(find "$upload_dir" -type f | wc -l)
        log_success "Upload directory accessible with $upload_count files"
    else
        log_error "Upload directory not accessible: $upload_dir"
    fi
    
    # Check results directory
    increment_check
    local results_dir="$PROJECT_ROOT/data/results"
    if [ -d "$results_dir" ] && [ -w "$results_dir" ]; then
        local results_count=$(find "$results_dir" -type f | wc -l)
        log_success "Results directory accessible with $results_count files"
    else
        log_error "Results directory not accessible: $results_dir"
    fi
    
    # Check log directory
    increment_check
    local logs_dir="$PROJECT_ROOT/logs"
    if [ -d "$logs_dir" ] && [ -w "$logs_dir" ]; then
        local log_size=$(du -sh "$logs_dir" | cut -f1)
        log_success "Logs directory accessible (size: $log_size)"
    else
        log_warning "Logs directory not accessible: $logs_dir"
    fi
    
    # Check Celery worker health (if running)
    increment_check
    if docker ps | grep -q "tidyframe-celery-worker"; then
        if docker exec tidyframe-celery-worker-prod celery -A app.core.celery_app inspect ping &>/dev/null; then
            log_success "Celery workers are responding"
        else
            log_warning "Celery workers are not responding"
        fi
    else
        log_warning "Celery worker container not running"
    fi
}

# =============================================================================
# Performance Metrics Collection
# =============================================================================

collect_performance_metrics() {
    log_info "Collecting performance metrics..."
    
    local metrics_file="$PROJECT_ROOT/logs/metrics-$(date +%Y%m%d_%H%M%S).json"
    
    cat > "$metrics_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "hostname": "$(hostname)",
    "uptime": "$(uptime -p)",
    "load_average": "$(uptime | awk -F'load average:' '{print $2}')",
    "memory": {
        "total_mb": $(free -m | awk 'NR==2{print $2}'),
        "used_mb": $(free -m | awk 'NR==2{print $3}'),
        "available_mb": $(free -m | awk 'NR==2{print $7}')
    },
    "disk": {
        "total_gb": $(df "$PROJECT_ROOT" | awk 'NR==2 {printf "%.1f", $2/1024/1024}'),
        "used_gb": $(df "$PROJECT_ROOT" | awk 'NR==2 {printf "%.1f", $3/1024/1024}'),
        "available_gb": $(df "$PROJECT_ROOT" | awk 'NR==2 {printf "%.1f", $4/1024/1024}')
    },
    "docker": {
        "running_containers": $(docker ps -q | wc -l),
        "total_containers": $(docker ps -a -q | wc -l)
    },
    "health_score": $HEALTH_SCORE
}
EOF

    log_info "Performance metrics saved to: $metrics_file"
}

# =============================================================================
# Generate Health Report
# =============================================================================

generate_health_report() {
    local report_file="$PROJECT_ROOT/logs/health-report-$(date +%Y%m%d_%H%M%S).md"
    
    # Calculate health score
    if [ "$TOTAL_CHECKS" -gt 0 ]; then
        HEALTH_SCORE=$(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))
    fi
    
    local health_status=""
    if [ "$HEALTH_SCORE" -ge 95 ]; then
        health_status="🟢 EXCELLENT"
    elif [ "$HEALTH_SCORE" -ge 80 ]; then
        health_status="🟡 GOOD"
    elif [ "$HEALTH_SCORE" -ge 60 ]; then
        health_status="🟠 FAIR"
    else
        health_status="🔴 POOR"
    fi
    
    cat > "$report_file" << EOF
# TidyFrame Health Check Report

**Generated:** $(date)  
**Server:** $(hostname)  
**Domain:** $DOMAIN  

## Overall Health Score: $HEALTH_SCORE% $health_status

- **Total Checks:** $TOTAL_CHECKS
- **Passed:** $PASSED_CHECKS ✅
- **Failed:** $FAILED_CHECKS ❌

## System Information

**Uptime:** $(uptime -p)  
**Load Average:** $(uptime | awk -F'load average:' '{print $2}')  
**Memory:** $(free -h | awk 'NR==2{printf "%s/%s (%.1f%%)", $3,$2,$3*100/$2}')  
**Disk:** $(df -h "$PROJECT_ROOT" | awk 'NR==2{printf "%s/%s (%s used)", $3,$2,$5}')  

## Service Status

\`\`\`
$(docker compose -f "$PROJECT_ROOT/docker-compose.prod.yml" ps 2>/dev/null || echo "Docker Compose not available")
\`\`\`

## Recent Alerts

\`\`\`
$(tail -n 10 "$ALERT_LOG" 2>/dev/null || echo "No recent alerts")
\`\`\`

## Recommendations

EOF

    # Add recommendations based on health score
    if [ "$HEALTH_SCORE" -lt 80 ]; then
        cat >> "$report_file" << EOF
- ⚠️ **Action Required:** System health below 80%
- Check failed services and resolve issues
- Monitor resource usage and optimize if necessary
- Review logs for error patterns
EOF
    elif [ "$HEALTH_SCORE" -lt 95 ]; then
        cat >> "$report_file" << EOF
- ✅ **Good Status:** Minor issues detected
- Review warnings in health check log
- Consider preventive maintenance
EOF
    else
        cat >> "$report_file" << EOF
- 🎉 **Excellent Status:** All systems operating normally
- Continue regular monitoring
- Schedule routine maintenance during low-traffic periods
EOF
    fi
    
    cat >> "$report_file" << EOF

## Log Files

- **Health Check:** $HEALTH_LOG
- **Alerts:** $ALERT_LOG
- **Application Logs:** \`docker compose -f docker-compose.prod.yml logs\`

---
*Generated by TidyFrame Health Check System*
EOF

    log_info "Health report generated: $report_file"
}

# =============================================================================
# Main Health Check Function
# =============================================================================

main() {
    print_banner
    
    local start_time=$(date +%s)
    
    # Create necessary directories
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Load environment if available
    if [ -f "$PROJECT_ROOT/.env" ]; then
        set -a
        source "$PROJECT_ROOT/.env" 2>/dev/null || true
        set +a
    fi
    
    log_info "Starting comprehensive health check..."
    
    # Run all health checks
    check_docker_services
    check_database_health
    check_api_endpoints
    check_frontend_health
    check_ssl_certificates
    check_system_resources
    check_application_health
    
    # Collect performance metrics
    collect_performance_metrics
    
    # Generate comprehensive report
    generate_health_report
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Calculate final health score
    if [ "$TOTAL_CHECKS" -gt 0 ]; then
        HEALTH_SCORE=$(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))
    fi
    
    echo -e "${GREEN}"
    echo "================================================================="
    echo "  Health Check Complete!"
    echo ""
    echo "  📊 Overall Health Score: $HEALTH_SCORE%"
    echo "  ✅ Passed Checks: $PASSED_CHECKS/$TOTAL_CHECKS"
    echo "  ⏱️  Duration: ${duration}s"
    echo ""
    
    if [ "$HEALTH_SCORE" -ge 95 ]; then
        echo "  🎉 System Status: EXCELLENT - All systems operating normally"
    elif [ "$HEALTH_SCORE" -ge 80 ]; then
        echo "  👍 System Status: GOOD - Minor issues detected"
    elif [ "$HEALTH_SCORE" -ge 60 ]; then
        echo "  ⚠️  System Status: FAIR - Several issues need attention"
    else
        echo "  🚨 System Status: POOR - Critical issues require immediate action"
    fi
    
    echo ""
    echo "  📝 Health Log: $HEALTH_LOG"
    echo "  📋 Health Report: Available in logs/"
    echo "================================================================="
    echo -e "${NC}"
    
    # Exit with appropriate code based on health score
    if [ "$HEALTH_SCORE" -ge 80 ]; then
        exit 0
    elif [ "$HEALTH_SCORE" -ge 60 ]; then
        exit 1
    else
        exit 2
    fi
}

# =============================================================================
# Monitoring Mode
# =============================================================================

monitor_mode() {
    log_info "Starting continuous monitoring mode (interval: ${CHECK_INTERVAL}s)"
    
    while true; do
        main
        sleep "$CHECK_INTERVAL"
    done
}

# =============================================================================
# Script Entry Point
# =============================================================================

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --monitor)
            monitor_mode
            exit 0
            ;;
        --interval)
            CHECK_INTERVAL="$2"
            shift 2
            ;;
        --alert-email)
            ALERT_EMAIL="$2"
            shift 2
            ;;
        --slack-webhook)
            SLACK_WEBHOOK="$2"
            shift 2
            ;;
        --help)
            echo "TidyFrame Health Check and Monitoring Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --domain DOMAIN          Domain to check (default: tidyframe.com)"
            echo "  --monitor               Run in continuous monitoring mode"
            echo "  --interval SECONDS      Check interval for monitoring mode (default: 300)"
            echo "  --alert-email EMAIL     Email address for alerts"
            echo "  --slack-webhook URL     Slack webhook URL for alerts"
            echo "  --help                  Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  DOMAIN                  Domain name"
            echo "  CHECK_INTERVAL          Monitoring interval in seconds"
            echo "  ALERT_EMAIL             Email for alerts"
            echo "  SLACK_WEBHOOK           Slack webhook for alerts"
            echo "  MAX_RESPONSE_TIME       Max API response time in ms"
            echo "  MIN_DISK_SPACE_GB       Minimum disk space in GB"
            echo "  MIN_MEMORY_MB           Minimum available memory in MB"
            echo "  MAX_CPU_PERCENT         Maximum CPU usage percentage"
            echo ""
            echo "Examples:"
            echo "  $0                      # Single health check"
            echo "  $0 --monitor            # Continuous monitoring"
            echo "  $0 --domain example.com # Check specific domain"
            echo "  $0 --alert-email admin@example.com --monitor"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main