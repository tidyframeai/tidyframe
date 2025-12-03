#!/bin/bash

# ================================================================
# TidyFrame Deployment Validation Script
# Pre-deployment checks to prevent configuration errors
# ================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔍 Running pre-deployment validation..."
echo ""

validation_failed=0

# ================================================================
# Check 1: Nginx Configuration Validation
# ================================================================
echo "📋 Checking nginx configurations..."

# Check for directories in nginx/conf.d
if [ -d "nginx/conf.d" ]; then
  for item in nginx/conf.d/*; do
    if [ -d "$item" ] && [[ ! "$item" =~ \.disabled$ ]]; then
      echo -e "${RED}❌ ERROR: Directory found in nginx/conf.d: $(basename $item)${NC}"
      echo "   Nginx will fail to load this as a config file"
      validation_failed=1
    fi
  done

  # Check for duplicate upstream definitions
  if grep -r "^upstream" nginx/conf.d/*.conf 2>/dev/null | grep -v ".disabled" | sort | uniq -d | grep -q .; then
    echo -e "${RED}❌ ERROR: Duplicate upstream definitions found in nginx configs${NC}"
    grep -r "^upstream" nginx/conf.d/*.conf 2>/dev/null | grep -v ".disabled"
    validation_failed=1
  fi

  # Check for temp or disabled configs that aren't disabled
  temp_configs=$(ls nginx/conf.d/ | grep -E "(temp-.*\.conf$|.*\.disabled[^/]*\.conf$)" | grep -v "\.disabled$" | wc -l)
  if [ $temp_configs -gt 0 ]; then
    echo -e "${YELLOW}⚠️  WARNING: Found $temp_configs temporary configs that should be disabled${NC}"
    ls nginx/conf.d/ | grep -E "(temp-.*\.conf$)" | grep -v "\.disabled$"
  fi
fi

# Validate nginx syntax using Docker (optional - may fail in dev environment)
if command -v docker &> /dev/null; then
  echo "   Validating nginx configuration structure..."
  # Check that tidyframe-production.conf exists
  if [ -f "nginx/conf.d/tidyframe-production.conf" ]; then
    echo -e "${GREEN}✅ Production nginx config found${NC}"
  else
    echo -e "${RED}❌ nginx/conf.d/tidyframe-production.conf is missing${NC}"
    validation_failed=1
  fi
else
  echo -e "${YELLOW}⚠️  Docker not available, skipping nginx validation${NC}"
fi

echo ""

# ================================================================
# Check 2: Test Files in Wrong Locations
# ================================================================
echo "📋 Checking for misplaced test files..."

test_files_in_app=$(find backend/app -maxdepth 1 -name "test_*.py" -o -name "*_test.py" -o -name "final_*.py" 2>/dev/null | wc -l)
if [ $test_files_in_app -gt 0 ]; then
  echo -e "${YELLOW}⚠️  WARNING: Found $test_files_in_app test files in backend/app/${NC}"
  find backend/app -maxdepth 1 -name "test_*.py" -o -name "*_test.py" -o -name "final_*.py"
  echo "   These should be in backend/tests/"
else
  echo -e "${GREEN}✅ No test files in backend/app/${NC}"
fi

echo ""

# ================================================================
# Check 3: Frontend Static Files
# ================================================================
echo "📋 Checking frontend static files..."

if [ ! -f "backend/app/static/index.html" ]; then
  echo -e "${RED}❌ ERROR: Frontend static files not built${NC}"
  echo "   Run: cd frontend && npm run build && cp -r dist/* ../backend/app/static/"
  validation_failed=1
else
  static_size=$(du -sh backend/app/static | cut -f1)
  echo -e "${GREEN}✅ Static files exist (${static_size})${NC}"
fi

echo ""

# ================================================================
# Check 4: Hardcoded localhost References
# ================================================================
echo "📋 Checking for hardcoded localhost in production configs..."

if grep -r "localhost" nginx/conf.d/tidyframe-production.conf docker-compose.prod.yml 2>/dev/null | grep -v "#" | grep -v "healthcheck" | grep -v "127.0.0.1"; then
  echo -e "${YELLOW}⚠️  WARNING: Found localhost references in production configs${NC}"
  echo "   (Note: localhost in healthchecks is OK)"
else
  echo -e "${GREEN}✅ No problematic localhost references${NC}"
fi

echo ""

# ================================================================
# Check 5: Environment Files
# ================================================================
echo "📋 Checking environment configuration..."

if [ ! -f ".env.production" ] && [ ! -f ".env" ]; then
  echo -e "${RED}❌ ERROR: No .env.production or .env file found${NC}"
  validation_failed=1
else
  echo -e "${GREEN}✅ Environment file exists${NC}"
fi

echo ""

# ================================================================
# Check 6: Python Cache Files
# ================================================================
echo "📋 Checking for Python cache files..."

pycache_count=$(find backend -type d -name "__pycache__" 2>/dev/null | wc -l)
if [ $pycache_count -gt 0 ]; then
  echo -e "${YELLOW}⚠️  WARNING: Found $pycache_count __pycache__ directories${NC}"
  echo "   Run: find backend -type d -name '__pycache__' -exec rm -rf {} +"
else
  echo -e "${GREEN}✅ No Python cache files${NC}"
fi

echo ""

# ================================================================
# Check 7: Docker Compose Configuration
# ================================================================
echo "📋 Checking Docker Compose configuration..."

if [ -f "docker-compose.prod.yml" ]; then
  # Check if orphan services are defined
  if grep -q "frontend:" docker-compose.prod.yml || grep -q "flower:" docker-compose.prod.yml; then
    echo -e "${YELLOW}⚠️  WARNING: Orphan services (frontend/flower) defined in prod compose${NC}"
  else
    echo -e "${GREEN}✅ No orphan services in prod compose${NC}"
  fi
else
  echo -e "${RED}❌ ERROR: docker-compose.prod.yml not found${NC}"
  validation_failed=1
fi

echo ""

# ================================================================
# Final Result
# ================================================================
if [ $validation_failed -eq 0 ]; then
  echo -e "${GREEN}================================================================${NC}"
  echo -e "${GREEN}✅ All validation checks passed!${NC}"
  echo -e "${GREEN}================================================================${NC}"
  exit 0
else
  echo -e "${RED}================================================================${NC}"
  echo -e "${RED}❌ Validation failed! Please fix errors above before deploying.${NC}"
  echo -e "${RED}================================================================${NC}"
  exit 1
fi
