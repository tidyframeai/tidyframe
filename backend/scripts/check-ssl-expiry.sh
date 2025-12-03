#!/bin/bash

# =============================================================================
# SSL Certificate Expiry Monitor
# =============================================================================
# Checks SSL certificate expiration and alerts if renewal is needed
# Intended to run daily via cron
# =============================================================================

set -euo pipefail

# Configuration
DOMAIN="${DOMAIN:-tidyframe.com}"
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
WARNING_DAYS=30  # Alert if cert expires within this many days
ALERT_EMAIL="${ADMIN_EMAIL:-tidyframeai@gmail.com}"
LOG_FILE="/var/log/ssl-expiry-check.log"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

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

    # Check certbot auto-renewal status
    log "Checking certbot auto-renewal status..."
    if systemctl is-active --quiet certbot.timer; then
        log "${GREEN}OK: Certbot auto-renewal timer is active${NC}"
    else
        log "${RED}ERROR: Certbot auto-renewal timer is NOT active!${NC}"
        logger -t ssl-expiry -p user.err "Certbot auto-renewal timer is not active"
    fi

    exit 1

else
    log "${GREEN}OK: SSL certificate is valid for $DAYS_UNTIL_EXPIRY days${NC}"

    # Verify certbot timer is still active
    if ! systemctl is-active --quiet certbot.timer; then
        log "${YELLOW}WARNING: Certbot auto-renewal timer is not active${NC}"
        logger -t ssl-expiry -p user.warning "Certbot auto-renewal timer is not active"
    fi

    exit 0
fi
