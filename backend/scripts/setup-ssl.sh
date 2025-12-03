#!/bin/bash
set -e

# =============================================================================
# TidyFrame SSL Setup Script - Let's Encrypt Integration
# =============================================================================

DOMAIN=$1
EMAIL=$2
ENV=${3:-production}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    log_error "Usage: $0 <domain> <email> [environment]"
    exit 1
fi

log_info "Setting up Let's Encrypt SSL for $DOMAIN"

# Ensure we're in the right directory
cd /opt/tidyframe

# Ensure certbot directories exist
log_info "Creating certbot directories..."
mkdir -p certbot/conf
mkdir -p certbot/www

# First, ensure nginx is running with HTTP for the challenge
log_info "Starting nginx with HTTP configuration..."
docker compose -f docker-compose.prod.yml up -d nginx

# Wait for nginx to be ready
log_info "Waiting for nginx to be ready..."
sleep 10

# Test if domain is reachable
log_info "Testing domain reachability..."
if curl -f -s -m 10 "http://$DOMAIN/.well-known/acme-challenge/test" > /dev/null 2>&1 || curl -f -s -m 10 "http://$DOMAIN/health" > /dev/null 2>&1; then
    log_success "Domain $DOMAIN is reachable"
else
    log_error "Warning: Domain $DOMAIN may not be reachable. Continuing anyway..."
fi

# Generate certificates using certbot
log_info "Generating SSL certificates with Let's Encrypt..."
docker compose -f docker-compose.prod.yml run --rm --entrypoint 'certbot' certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email $EMAIL \
  --agree-tos \
  --no-eff-email \
  --force-renewal \
  -d $DOMAIN \
  -d www.$DOMAIN

# Check if certificates were generated
if [ -d "certbot/conf/live/$DOMAIN" ]; then
    log_success "SSL certificates generated successfully"

    # Create SSL-enabled nginx configuration
    log_info "Creating SSL-enabled nginx configuration..."

    # Create a new SSL configuration that includes both HTTP and HTTPS
    cat > nginx/conf.d/tidyframe-ssl.conf << EOF
upstream backend_servers {
    server backend:8000;
}

# HTTP server - redirect to HTTPS except for Let's Encrypt challenges
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;

    # Allow Let's Encrypt challenges
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 256;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml application/atom+xml image/svg+xml application/vnd.ms-fontobject application/x-font-ttf font/opentype;

    # Rate limiting
    limit_req zone=api burst=20 nodelay;

    # API Proxy
    location /api/ {
        proxy_pass http://backend_servers/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Authorization \$http_authorization;
        proxy_pass_header Authorization;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # CORS headers for production
        add_header 'Access-Control-Allow-Origin' 'https://$DOMAIN' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
    }

    # Docs endpoint
    location /docs {
        proxy_pass http://backend_servers/docs;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Health check
    location /health {
        access_log off;
        proxy_pass http://backend_servers/health;
    }

    # Frontend and all other routes
    location / {
        proxy_pass http://backend_servers/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Authorization \$http_authorization;
        proxy_pass_header Authorization;
    }
}
EOF

    # Disable the non-SSL production config and enable SSL config
    log_info "Enabling SSL configuration..."
    mv nginx/conf.d/tidyframe-production.conf nginx/conf.d/tidyframe-production.conf.disabled 2>/dev/null || true

    # Restart nginx with SSL configuration
    log_info "Restarting nginx with SSL enabled..."
    docker compose -f docker-compose.prod.yml restart nginx

    # Wait for nginx to restart
    sleep 5

    # Test HTTPS
    log_info "Testing HTTPS connection..."
    if curl -f -s -m 10 "https://$DOMAIN/health" > /dev/null 2>&1; then
        log_success "HTTPS is working!"
        echo ""
        echo "================================================================="
        echo -e "${GREEN}✅ SSL Setup Complete!${NC}"
        echo ""
        echo "  Domain: https://$DOMAIN"
        echo "  Certificate: Let's Encrypt"
        echo "  Auto-renewal: Enabled via certbot container"
        echo ""
        echo "================================================================="
    else
        log_error "HTTPS test failed, but certificates are installed"
        log_info "You may need to wait a few minutes for DNS propagation"
    fi

else
    log_error "Failed to generate SSL certificates"
    log_error "Please check:"
    log_error "1. DNS is properly configured (A records for $DOMAIN and www.$DOMAIN)"
    log_error "2. Port 80 is accessible from the internet"
    log_error "3. The domain is not rate-limited by Let's Encrypt"
    exit 1
fi

log_success "SSL setup script completed!"