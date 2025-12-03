#!/bin/bash

# Comprehensive validation script for recent changes
# Run this before deploying to production

echo "🔍 Running Comprehensive Validation Tests..."
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Test 1: TypeScript Compilation
echo "📝 Test 1: TypeScript Compilation"
if npm run typecheck > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PASSED${NC} - No TypeScript errors"
else
    echo -e "${RED}❌ FAILED${NC} - TypeScript compilation errors found"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Test 2: Production Build
echo "🏗️  Test 2: Production Build"
if npm run build > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PASSED${NC} - Build completed successfully"
else
    echo -e "${RED}❌ FAILED${NC} - Build failed"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Test 3: ESLint Check
echo "🔎 Test 3: ESLint Validation"
LINT_ERRORS=$(npm run lint 2>&1 | grep -c "error")
LINT_WARNINGS=$(npm run lint 2>&1 | grep -c "warning")

if [ "$LINT_ERRORS" -eq 0 ]; then
    echo -e "${GREEN}✅ PASSED${NC} - No ESLint errors found"
    if [ "$LINT_WARNINGS" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  ${LINT_WARNINGS} warning(s) found (acceptable)${NC}"
        WARNINGS=$((WARNINGS + LINT_WARNINGS))
    fi
else
    echo -e "${RED}❌ FAILED${NC} - ${LINT_ERRORS} ESLint error(s) found"
    ERRORS=$((ERRORS + LINT_ERRORS))
fi
echo ""

# Test 4: Required Files Exist
echo "📁 Test 4: File Structure Validation"
MISSING=0

if [ -f "src/components/docs/ApiDocsContent.tsx" ]; then
    echo -e "${GREEN}✅${NC} ApiDocsContent.tsx exists"
else
    echo -e "${RED}❌${NC} ApiDocsContent.tsx missing"
    MISSING=$((MISSING + 1))
fi

if [ -f "src/pages/ApiDocsPage.tsx" ]; then
    echo -e "${GREEN}✅${NC} ApiDocsPage.tsx exists"
else
    echo -e "${RED}❌${NC} ApiDocsPage.tsx missing"
    MISSING=$((MISSING + 1))
fi

if [ -f "src/pages/dashboard/DashboardHome.tsx" ]; then
    echo -e "${GREEN}✅${NC} DashboardHome.tsx exists"
else
    echo -e "${RED}❌${NC} DashboardHome.tsx missing"
    MISSING=$((MISSING + 1))
fi

if [ "$MISSING" -eq 0 ]; then
    echo -e "${GREEN}✅ PASSED${NC} - All required files exist"
else
    echo -e "${RED}❌ FAILED${NC} - ${MISSING} file(s) missing"
    ERRORS=$((ERRORS + MISSING))
fi
echo ""

# Test 5: No Hardcoded Values
echo "💰 Test 5: Hardcoding Check"
HARDCODED_COUNT=0

# Check for hardcoded overage rates (excluding comments and test files)
if grep -r "0\.002\|overage.*0\.01" src/pages src/components --include="*.tsx" --include="*.ts" | grep -v "billingConfig\|// " | grep -q .; then
    echo -e "${YELLOW}⚠️  WARNING${NC} - Potential hardcoded pricing found"
    HARDCODED_COUNT=$((HARDCODED_COUNT + 1))
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "${GREEN}✅${NC} No hardcoded pricing in calculations"
fi

# Check for <a href> internal links (should use <Link>)
ANCHOR_COUNT=$(grep -r '<a href="/' src/pages src/components --include="*.tsx" | grep -v "http\|mailto\|external" | wc -l)
if [ "$ANCHOR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅${NC} No internal <a href> tags (using React Router)"
else
    echo -e "${YELLOW}⚠️  WARNING${NC} - ${ANCHOR_COUNT} internal anchor tag(s) found"
    WARNINGS=$((WARNINGS + 1))
fi

if [ "$HARDCODED_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ PASSED${NC} - No hardcoding issues"
fi
echo ""

# Test 6: Import Validation
echo "📦 Test 6: Import Check"
IMPORT_ERRORS=0

# Check if ApiDocsContent is imported in ApiKeys
if grep -q "import.*ApiDocsContent" src/pages/dashboard/ApiKeys.tsx; then
    echo -e "${GREEN}✅${NC} ApiDocsContent imported in ApiKeys.tsx"
else
    echo -e "${RED}❌${NC} ApiDocsContent NOT imported in ApiKeys.tsx"
    IMPORT_ERRORS=$((IMPORT_ERRORS + 1))
fi

# Check if Link is imported in Billing
if grep -q "import.*Link" src/pages/dashboard/Billing.tsx; then
    echo -e "${GREEN}✅${NC} Link imported in Billing.tsx"
else
    echo -e "${RED}❌${NC} Link NOT imported in Billing.tsx"
    IMPORT_ERRORS=$((IMPORT_ERRORS + 1))
fi

# Check if hasActiveSubscription is used in DashboardHome
if grep -q "hasActiveSubscription" src/pages/dashboard/DashboardHome.tsx; then
    echo -e "${GREEN}✅${NC} hasActiveSubscription used in DashboardHome.tsx"
else
    echo -e "${RED}❌${NC} hasActiveSubscription NOT used in DashboardHome.tsx"
    IMPORT_ERRORS=$((IMPORT_ERRORS + 1))
fi

if [ "$IMPORT_ERRORS" -eq 0 ]; then
    echo -e "${GREEN}✅ PASSED${NC} - All imports correct"
else
    echo -e "${RED}❌ FAILED${NC} - ${IMPORT_ERRORS} import error(s)"
    ERRORS=$((ERRORS + IMPORT_ERRORS))
fi
echo ""

# Test 7: Routing Consistency
echo "🔀 Test 7: Routing Consistency"
ROUTING_ISSUES=0

# Check PaymentSuccessPage redirects
DASHBOARD_UPLOAD_COUNT=$(grep -c "navigate('/dashboard/upload" src/pages/payment/PaymentSuccessPage.tsx)
if [ "$DASHBOARD_UPLOAD_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅${NC} PaymentSuccessPage redirects standardized"
else
    echo -e "${RED}❌${NC} PaymentSuccessPage still has inconsistent redirects"
    ROUTING_ISSUES=$((ROUTING_ISSUES + 1))
fi

# Check Navbar conditional routing
if grep -q 'to={user.*"/dashboard/api-keys".*"/docs"}' src/components/layout/Navbar.tsx; then
    echo -e "${GREEN}✅${NC} Navbar has intelligent API docs routing"
else
    echo -e "${RED}❌${NC} Navbar routing not conditional"
    ROUTING_ISSUES=$((ROUTING_ISSUES + 1))
fi

if [ "$ROUTING_ISSUES" -eq 0 ]; then
    echo -e "${GREEN}✅ PASSED${NC} - Routing is consistent"
else
    echo -e "${RED}❌ FAILED${NC} - ${ROUTING_ISSUES} routing issue(s)"
    ERRORS=$((ERRORS + ROUTING_ISSUES))
fi
echo ""

# Test 8: Grace Period Extension
echo "⏱️  Test 8: Grace Period Validation"
if grep -q "60000" src/components/auth/ProtectedRoute.tsx; then
    echo -e "${GREEN}✅ PASSED${NC} - Grace period extended to 60 seconds"
else
    echo -e "${RED}❌ FAILED${NC} - Grace period not extended"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 VALIDATION SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$ERRORS" -eq 0 ] && [ "$WARNINGS" -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo "   0 errors, 0 warnings"
    echo ""
    echo "🚀 Ready for deployment!"
    exit 0
elif [ "$ERRORS" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  PASSED WITH WARNINGS${NC}"
    echo "   0 errors, ${WARNINGS} warning(s)"
    echo ""
    echo "✅ Safe to deploy (warnings are acceptable)"
    exit 0
else
    echo -e "${RED}❌ VALIDATION FAILED${NC}"
    echo "   ${ERRORS} error(s), ${WARNINGS} warning(s)"
    echo ""
    echo "🛑 DO NOT DEPLOY - Fix errors first"
    exit 1
fi
