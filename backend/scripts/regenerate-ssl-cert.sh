#!/bin/bash
# =============================================================================
# TidyFrame SSL Certificate Regeneration Script
# =============================================================================
# Force renewal of Let's Encrypt SSL certificates
# Usage: ./regenerate-ssl-cert.sh [domain] [email]
# =============================================================================

set -euo pipefail

# Configuration
DOMAIN="${1:-tidyframe.com}"
EMAIL="${2:-tidyframeai@gmail.com}"
PROJECT_ROOT="/opt/tidyframe"

# Load shared logging library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/logging.sh"

# Alias for consistency with old function name
log_warn() {
    log_warning "$*"
}

# Change to project root
cd "$PROJECT_ROOT"

echo "================================================================="
echo -e "${BLUE}TidyFrame SSL Certificate Regeneration${NC}"
echo "================================================================="
echo "  Domain: $DOMAIN"
echo "  Email: $EMAIL"
echo "  Date: $(date)"
echo "================================================================="
echo ""

# Step 1: Check current certificate status
log_info "Checking current certificate status..."
if [ -f "certbot/conf/live/$DOMAIN/fullchain.pem" ]; then
    EXPIRY_DATE=$(openssl x509 -enddate -noout -in "certbot/conf/live/$DOMAIN/fullchain.pem" | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
    CURRENT_EPOCH=$(date +%s)
    DAYS_UNTIL_EXPIRY=$(( (EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))

    log_info "Current certificate expires: $EXPIRY_DATE ($DAYS_UNTIL_EXPIRY days remaining)"

    if [ $DAYS_UNTIL_EXPIRY -lt 0 ]; then
        log_error "Certificate has EXPIRED!"
    elif [ $DAYS_UNTIL_EXPIRY -lt 30 ]; then
        log_warn "Certificate expires in $DAYS_UNTIL_EXPIRY days - renewal recommended"
    else
        log_success "Certificate is valid for $DAYS_UNTIL_EXPIRY days"
    fi
else
    log_warn "No existing certificate found for $DOMAIN"
fi

echo ""

# Step 2: Ensure nginx is running for HTTP-01 challenge
log_info "Ensuring nginx is running for ACME challenge..."
docker-compose -f docker-compose.prod.yml up -d nginx
sleep 5

# Step 3: Test if domain is reachable
log_info "Testing domain reachability..."
if curl -f -s -m 10 "http://$DOMAIN/.well-known/acme-challenge/test" > /dev/null 2>&1 || \
   curl -f -s -m 10 "http://$DOMAIN/health" > /dev/null 2>&1; then
    log_success "Domain $DOMAIN is reachable"
else
    log_warn "Domain $DOMAIN may not be fully reachable - continuing anyway..."
fi

echo ""

# Step 4: Stop certbot container if running
log_info "Stopping certbot container..."
docker-compose -f docker-compose.prod.yml stop certbot 2>/dev/null || true

# Step 5: Force certificate renewal
log_info "Forcing certificate renewal with Let's Encrypt..."
echo ""

docker-compose -f docker-compose.prod.yml run --rm --entrypoint 'certbot' certbot renew \
  --force-renewal \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email

RENEWAL_STATUS=$?

echo ""

# Step 6: Check if renewal was successful
if [ $RENEWAL_STATUS -eq 0 ]; then
    log_success "Certificate renewal completed successfully!"

    # Verify new certificate
    if [ -f "certbot/conf/live/$DOMAIN/fullchain.pem" ]; then
        NEW_EXPIRY_DATE=$(openssl x509 -enddate -noout -in "certbot/conf/live/$DOMAIN/fullchain.pem" | cut -d= -f2)
        log_success "New certificate expires: $NEW_EXPIRY_DATE"
    fi

    echo ""
    log_info "Restarting nginx to apply new certificate..."
    docker-compose -f docker-compose.prod.yml restart nginx

    # Wait for nginx to restart
    sleep 10

    # Test HTTPS
    log_info "Testing HTTPS connection..."
    if curl -f -s -m 10 "https://$DOMAIN/health" > /dev/null 2>&1; then
        log_success "HTTPS is working with new certificate!"

        echo ""
        echo "================================================================="
        echo -e "${GREEN}✅ SSL Certificate Renewal Complete!${NC}"
        echo ""
        echo "  Domain: https://$DOMAIN"
        echo "  Certificate: Let's Encrypt"
        echo "  Expires: $NEW_EXPIRY_DATE"
        echo ""
        echo "================================================================="

        exit 0
    else
        log_error "HTTPS test failed after renewal"
        log_info "Please check nginx logs: docker logs tidyframe_nginx_1"
        exit 1
    fi

else
    log_error "Certificate renewal failed!"
    log_error "Please check:"
    log_error "1. DNS is properly configured (A records for $DOMAIN and www.$DOMAIN)"
    log_error "2. Port 80 is accessible from the internet"
    log_error "3. The domain is not rate-limited by Let's Encrypt"
    log_error "4. Nginx is properly configured with .well-known/acme-challenge location"

    echo ""
    log_info "Restarting certbot container..."
    docker-compose -f docker-compose.prod.yml up -d certbot

    exit 1
fi
