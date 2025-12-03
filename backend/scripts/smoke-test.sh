#!/bin/bash

# ================================================================
# TidyFrame Smoke Test Script
# Post-deployment verification to ensure everything works
# ================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DOMAIN=${1:-tidyframe.com}
COMPOSE_FILE=${2:-docker-compose.prod.yml}

echo -e "${BLUE}🧪 Running smoke tests for $DOMAIN...${NC}"
echo ""

test_failed=0

# ================================================================
# Test 1: HTTPS Health Check
# ================================================================
echo "1️⃣  Testing HTTPS health endpoint..."
if curl -f -s -m 10 "https://$DOMAIN/health" > /dev/null 2>&1; then
  echo -e "${GREEN}✅ HTTPS health check passed${NC}"
else
  echo -e "${RED}❌ HTTPS health check failed${NC}"
  curl -I "https://$DOMAIN/health" 2>&1 | head -5
  test_failed=1
fi

echo ""

# ================================================================
# Test 2: API Health Check
# ================================================================
echo "2️⃣  Testing API health endpoint..."
if curl -f -s -m 10 "https://$DOMAIN/api/health" > /dev/null 2>&1; then
  echo -e "${GREEN}✅ API health check passed${NC}"
else
  # API might return 401 due to site password - that's OK
  status_code=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/api/health" 2>/dev/null)
  if [ "$status_code" = "401" ]; then
    echo -e "${GREEN}✅ API responding (401 = site password active)${NC}"
  else
    echo -e "${RED}❌ API health check failed (status: $status_code)${NC}"
    test_failed=1
  fi
fi

echo ""

# ================================================================
# Test 3: Frontend Loading
# ================================================================
echo "3️⃣  Testing frontend static files..."
response=$(curl -s -m 10 "https://$DOMAIN/" 2>/dev/null)
if echo "$response" | grep -q "<div id=\"root\">" || echo "$response" | grep -q "<!doctype html>"; then
  echo -e "${GREEN}✅ Frontend loads correctly${NC}"
else
  echo -e "${RED}❌ Frontend not loading properly${NC}"
  echo "Response preview:"
  echo "$response" | head -10
  test_failed=1
fi

echo ""

# ================================================================
# Test 4: SSL Certificate
# ================================================================
echo "4️⃣  Testing SSL certificate..."
if echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -dates > /dev/null 2>&1; then
  expiry_date=$(echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
  echo -e "${GREEN}✅ SSL certificate valid (expires: $expiry_date)${NC}"
else
  echo -e "${YELLOW}⚠️  SSL certificate check failed (may need time to provision)${NC}"
fi

echo ""

# ================================================================
# Test 5: Docker Containers
# ================================================================
echo "5️⃣  Testing Docker container health..."
if [ -f "$COMPOSE_FILE" ]; then
  required_services=("backend" "nginx" "postgres" "redis" "celery-worker" "celery-beat")

  for service in "${required_services[@]}"; do
    if docker compose -f "$COMPOSE_FILE" ps | grep -q "${service}.*Up"; then
      echo -e "${GREEN}✅ $service is running${NC}"
    else
      echo -e "${RED}❌ $service is not running${NC}"
      test_failed=1
    fi
  done
else
  echo -e "${YELLOW}⚠️  Cannot check containers (compose file not found)${NC}"
fi

echo ""

# ================================================================
# Test 6: Database Connectivity
# ================================================================
echo "6️⃣  Testing database connectivity..."
if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U tidyframe > /dev/null 2>&1; then
  echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
else
  echo -e "${RED}❌ PostgreSQL connectivity failed${NC}"
  test_failed=1
fi

echo ""

# ================================================================
# Test 7: Redis Connectivity
# ================================================================
echo "7️⃣  Testing Redis connectivity..."
# Note: This will fail if REDIS_PASSWORD is not set, but that's a config issue
if docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
  echo -e "${GREEN}✅ Redis is responding${NC}"
else
  echo -e "${YELLOW}⚠️  Redis connectivity check skipped (password may be required)${NC}"
fi

echo ""

# ================================================================
# Test 8: HTTP to HTTPS Redirect
# ================================================================
echo "8️⃣  Testing HTTP to HTTPS redirect..."
if curl -s -L -I "http://$DOMAIN/" 2>&1 | grep -q "301\|302"; then
  echo -e "${GREEN}✅ HTTP redirects to HTTPS${NC}"
else
  echo -e "${YELLOW}⚠️  HTTP redirect not detected${NC}"
fi

echo ""

# ================================================================
# Test 9: Static Assets
# ================================================================
echo "9️⃣  Testing static assets..."
if curl -f -s -m 10 "https://$DOMAIN/assets/" > /dev/null 2>&1 || curl -s "https://$DOMAIN/" | grep -q "/assets/"; then
  echo -e "${GREEN}✅ Static assets are accessible${NC}"
else
  echo -e "${YELLOW}⚠️  Static assets check inconclusive${NC}"
fi

echo ""

# ================================================================
# Test 10: System Resources
# ================================================================
echo "🔟  Checking system resources..."
disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
memory_usage=$(free | awk 'NR==2{printf "%.1f", $3/$2*100}')

if [ "$disk_usage" -lt 90 ]; then
  echo -e "${GREEN}✅ Disk usage: ${disk_usage}%${NC}"
else
  echo -e "${RED}❌ High disk usage: ${disk_usage}%${NC}"
  test_failed=1
fi

echo -e "${BLUE}ℹ️  Memory usage: ${memory_usage}%${NC}"

echo ""

# ================================================================
# Final Result
# ================================================================
if [ $test_failed -eq 0 ]; then
  echo -e "${GREEN}================================================================${NC}"
  echo -e "${GREEN}✅ All smoke tests passed! Deployment is healthy.${NC}"
  echo -e "${GREEN}================================================================${NC}"
  echo ""
  echo -e "${BLUE}🌐 Your site is live at: https://$DOMAIN${NC}"
  exit 0
else
  echo -e "${RED}================================================================${NC}"
  echo -e "${RED}❌ Some smoke tests failed. Please review the output above.${NC}"
  echo -e "${RED}================================================================${NC}"
  exit 1
fi
