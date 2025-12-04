#!/bin/bash
# =============================================================================
# TidyFrame Nginx Configuration Test Script
# =============================================================================
# Tests nginx configuration, SSL certificates, and certbot status
# Usage: ./test-nginx-config.sh
# =============================================================================

set -euo pipefail

# Configuration
PROJECT_ROOT="/opt/tidyframe"
DOMAIN="tidyframe.com"

# Load shared logging library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/logging.sh"

# Alias for consistency with old function name
log_warn() {
    log_warning "$*"
}

ERRORS=0

# Change to project root
cd "$PROJECT_ROOT"

echo "================================================================="
echo -e "${BLUE}TidyFrame Nginx Health Check${NC}"
echo "================================================================="
echo "  Date: $(date)"
echo "================================================================="
echo ""

# Test 1: Check if nginx container is running
log_info "Test 1: Checking nginx container status..."
if docker ps --format '{{.Names}}' | grep -q 'tidyframe_nginx'; then
    NGINX_STATUS=$(docker inspect --format='{{.State.Health.Status}}' tidyframe_nginx_1 2>/dev/null || echo "unknown")
    if [ "$NGINX_STATUS" = "healthy" ]; then
        log_success "Nginx container is running and healthy"
    else
        log_warn "Nginx container is running but health status: $NGINX_STATUS"
    fi
else
    log_error "Nginx container is NOT running!"
    ((ERRORS++))
fi

echo ""

# Test 2: Test nginx configuration syntax
log_info "Test 2: Testing nginx configuration syntax..."
if docker exec tidyframe_nginx_1 nginx -t 2>&1 | grep -q "test is successful"; then
    log_success "Nginx configuration syntax is valid"
else
    log_error "Nginx configuration has syntax errors!"
    docker exec tidyframe_nginx_1 nginx -t 2>&1
    ((ERRORS++))
fi

echo ""

# Test 3: Check SSL certificate validity
log_info "Test 3: Checking SSL certificate validity..."
if [ -f "certbot/conf/live/$DOMAIN/fullchain.pem" ]; then
    EXPIRY_DATE=$(openssl x509 -enddate -noout -in "certbot/conf/live/$DOMAIN/fullchain.pem" | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
    CURRENT_EPOCH=$(date +%s)
    DAYS_UNTIL_EXPIRY=$(( (EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))

    if [ $DAYS_UNTIL_EXPIRY -lt 0 ]; then
        log_error "SSL certificate has EXPIRED on $EXPIRY_DATE!"
        ((ERRORS++))
    elif [ $DAYS_UNTIL_EXPIRY -lt 30 ]; then
        log_warn "SSL certificate expires in $DAYS_UNTIL_EXPIRY days ($EXPIRY_DATE)"
        log_info "Run ./regenerate-ssl-cert.sh to renew"
    else
        log_success "SSL certificate is valid for $DAYS_UNTIL_EXPIRY days (expires: $EXPIRY_DATE)"
    fi

    # Check certificate subject
    CERT_SUBJECT=$(openssl x509 -subject -noout -in "certbot/conf/live/$DOMAIN/fullchain.pem" | cut -d= -f2-)
    log_info "Certificate subject: $CERT_SUBJECT"
else
    log_error "SSL certificate not found at certbot/conf/live/$DOMAIN/fullchain.pem"
    ((ERRORS++))
fi

echo ""

# Test 4: Check certbot container status
log_info "Test 4: Checking certbot container status..."
if docker ps --format '{{.Names}}' | grep -q 'tidyframe_certbot'; then
    log_success "Certbot container is running for auto-renewal"
else
    log_warn "Certbot container is NOT running - auto-renewal may not work"
    log_info "Run: docker-compose -f docker-compose.prod.yml up -d certbot"
fi

echo ""

# Test 5: Test HTTP to HTTPS redirect
log_info "Test 5: Testing HTTP to HTTPS redirect..."
HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN/ 2>/dev/null || echo "000")
if [ "$HTTP_RESPONSE" = "301" ]; then
    log_success "HTTP correctly redirects to HTTPS (301)"
else
    log_error "HTTP redirect failed (got $HTTP_RESPONSE, expected 301)"
    ((ERRORS++))
fi

echo ""

# Test 6: Test HTTPS connectivity
log_info "Test 6: Testing HTTPS connectivity..."
HTTPS_RESPONSE=$(curl -f -s -o /dev/null -w "%{http_code}" https://$DOMAIN/health 2>/dev/null || echo "000")
if [ "$HTTPS_RESPONSE" = "200" ]; then
    log_success "HTTPS is accessible (200 OK)"

    # Check HTTP/2 support
    HTTP_VERSION=$(curl -s -I https://$DOMAIN/health 2>&1 | head -1 | cut -d' ' -f1)
    if [[ "$HTTP_VERSION" == "HTTP/2" ]]; then
        log_success "HTTP/2 is enabled"
    else
        log_warn "HTTP/2 not detected (got: $HTTP_VERSION)"
    fi
else
    log_error "HTTPS connection failed (got $HTTPS_RESPONSE)"
    ((ERRORS++))
fi

echo ""

# Test 7: Check security headers
log_info "Test 7: Checking security headers..."
HEADERS=$(curl -s -I https://$DOMAIN/ 2>/dev/null)

check_header() {
    local header_name=$1
    if echo "$HEADERS" | grep -qi "^$header_name:"; then
        log_success "$header_name header is present"
    else
        log_warn "$header_name header is missing"
    fi
}

check_header "Strict-Transport-Security"
check_header "X-Frame-Options"
check_header "X-Content-Type-Options"
check_header "Content-Security-Policy"

echo ""

# Test 8: Check nginx configuration files
log_info "Test 8: Checking nginx configuration files..."
ACTIVE_CONFIGS=$(find nginx/conf.d -name "*.conf" -not -name "*.disabled" 2>/dev/null | wc -l)

if [ "$ACTIVE_CONFIGS" -eq 1 ]; then
    CONFIG_FILE=$(find nginx/conf.d -name "*.conf" -not -name "*.disabled" 2>/dev/null)
    log_success "Single active nginx config: $(basename "$CONFIG_FILE")"
elif [ "$ACTIVE_CONFIGS" -gt 1 ]; then
    log_error "Multiple active nginx configs found (should be only 1):"
    find nginx/conf.d -name "*.conf" -not -name "*.disabled" 2>/dev/null | while read -r config; do
        echo "    - $(basename "$config")"
    done
    ((ERRORS++))
else
    log_error "No active nginx config found!"
    ((ERRORS++))
fi

echo ""

# Test 9: Check .well-known/acme-challenge accessibility
log_info "Test 9: Testing Let's Encrypt challenge endpoint..."
ACME_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN/.well-known/acme-challenge/test 2>/dev/null || echo "000")
if [ "$ACME_RESPONSE" = "404" ] || [ "$ACME_RESPONSE" = "403" ] || [ "$ACME_RESPONSE" = "200" ]; then
    log_success "ACME challenge endpoint is accessible (got $ACME_RESPONSE)"
else
    log_warn "ACME challenge endpoint may not be accessible (got $ACME_RESPONSE)"
fi

echo ""

# Test 10: Check backend connectivity through nginx
log_info "Test 10: Testing backend API through nginx..."
API_RESPONSE=$(curl -f -s -o /dev/null -w "%{http_code}" https://$DOMAIN/api/health 2>/dev/null || echo "000")
if [ "$API_RESPONSE" = "200" ]; then
    log_success "Backend API is accessible through nginx"
else
    log_warn "Backend API test returned $API_RESPONSE (may require authentication)"
fi

echo ""

# Summary
echo "================================================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All critical tests passed!${NC}"
    echo "================================================================="
    exit 0
else
    echo -e "${RED}❌ $ERRORS critical test(s) failed!${NC}"
    echo "================================================================="
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check nginx logs: docker logs tidyframe_nginx_1"
    echo "2. Check nginx config: docker exec tidyframe_nginx_1 nginx -t"
    echo "3. Restart nginx: docker-compose -f docker-compose.prod.yml restart nginx"
    echo "4. Check SSL certificate: openssl x509 -in certbot/conf/live/$DOMAIN/fullchain.pem -text"
    echo ""
    exit 1
fi
