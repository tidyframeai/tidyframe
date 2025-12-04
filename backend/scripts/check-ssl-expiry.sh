#!/bin/bash

# =============================================================================
# SSL Certificate Expiry Monitor (Docker-Compatible)
# =============================================================================
# Checks SSL certificate expiration and alerts if renewal is needed
# Intended to run daily via cron on Docker Compose production environment
# =============================================================================

set -euo pipefail

# Load shared logging library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/logging.sh"

# Configuration
PROJECT_ROOT="${PROJECT_ROOT:-/opt/tidyframe}"
DOMAIN="${DOMAIN:-tidyframe.com}"
CERT_PATH="$PROJECT_ROOT/certbot/conf/live/$DOMAIN/fullchain.pem"
WARNING_DAYS=30  # Alert if cert expires within this many days
ALERT_EMAIL="${ADMIN_EMAIL:-tidyframeai@gmail.com}"
LOG_FILE="$PROJECT_ROOT/logs/ssl-expiry-check.log"

# Create logs directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

# Override log function to add file output
log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] $*" | tee -a "$LOG_FILE"
}

# Check if running with appropriate permissions
if [ ! -r "$CERT_PATH" ]; then
    log "${RED}ERROR: Cannot read certificate at $CERT_PATH${NC}"
    log "This script requires read access to Let's Encrypt certificates"
    exit 1
fi

# Get certificate expiry date
EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_PATH" | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
CURRENT_EPOCH=$(date +%s)

# Calculate days until expiry
DAYS_UNTIL_EXPIRY=$(( (EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))

log "SSL Certificate Status:"
log "  Domain: $DOMAIN"
log "  Expires: $EXPIRY_DATE"
log "  Days remaining: $DAYS_UNTIL_EXPIRY"

# Check expiry status
if [ $DAYS_UNTIL_EXPIRY -lt 0 ]; then
    log "${RED}CRITICAL: SSL certificate has EXPIRED!${NC}"

    # Send critical alert
    if command -v mail &> /dev/null; then
        echo "SSL certificate for $DOMAIN has EXPIRED on $EXPIRY_DATE!" | \
            mail -s "CRITICAL: SSL Certificate EXPIRED - $DOMAIN" "$ALERT_EMAIL"
    fi

    # Log to system log
    logger -t ssl-expiry -p user.crit "SSL certificate for $DOMAIN has expired"

    exit 2

elif [ $DAYS_UNTIL_EXPIRY -lt $WARNING_DAYS ]; then
    log "${YELLOW}WARNING: SSL certificate expires in $DAYS_UNTIL_EXPIRY days${NC}"

    # Send warning alert
    if command -v mail &> /dev/null; then
        echo "SSL certificate for $DOMAIN will expire in $DAYS_UNTIL_EXPIRY days on $EXPIRY_DATE. Please ensure auto-renewal is working." | \
            mail -s "WARNING: SSL Certificate Expiring Soon - $DOMAIN" "$ALERT_EMAIL"
    fi

    # Log to system log
    logger -t ssl-expiry -p user.warning "SSL certificate for $DOMAIN expires in $DAYS_UNTIL_EXPIRY days"

    # Check certbot auto-renewal status (Docker container)
    log "Checking certbot container status..."
    if docker ps --format '{{.Names}}' | grep -q 'tidyframe.*certbot'; then
        CERTBOT_STATUS=$(docker inspect --format='{{.State.Status}}' $(docker ps --format '{{.Names}}' | grep 'tidyframe.*certbot') 2>/dev/null || echo "unknown")
        if [ "$CERTBOT_STATUS" = "running" ]; then
            log "${GREEN}OK: Certbot container is running for auto-renewal${NC}"
        else
            log "${YELLOW}WARNING: Certbot container exists but status: $CERTBOT_STATUS${NC}"
        fi
    else
        log "${RED}ERROR: Certbot container is NOT running!${NC}"
        logger -t ssl-expiry -p user.err "Certbot container is not running"
    fi

    exit 1

else
    log "${GREEN}OK: SSL certificate is valid for $DAYS_UNTIL_EXPIRY days${NC}"

    # Verify certbot container is still running
    if ! docker ps --format '{{.Names}}' | grep -q 'tidyframe.*certbot'; then
        log "${YELLOW}WARNING: Certbot container is not running${NC}"
        logger -t ssl-expiry -p user.warning "Certbot container is not running"
    else
        log "${GREEN}OK: Certbot container is running${NC}"
    fi

    exit 0
fi
