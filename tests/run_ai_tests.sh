#!/bin/bash
"""
TidyFrame AI Test Suite Runner
Comprehensive testing script for Gemini AI processing validation
"""

set -e  # Exit on any error

# Configuration
BASE_URL="${TIDYFRAME_BASE_URL:-http://localhost:8000}"
API_KEY="${TIDYFRAME_API_KEY:-}"
TEST_DIR="$(dirname "$0")"
RESULTS_DIR="$TEST_DIR/results"
LOG_FILE="$RESULTS_DIR/test_run_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create results directory
mkdir -p "$RESULTS_DIR"

# Logging function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Header
log "${BLUE}================================================================================================${NC}"
log "${BLUE}TIDYFRAME GEMINI AI PROCESSING - COMPREHENSIVE TEST SUITE${NC}"
log "${BLUE}================================================================================================${NC}"
log ""
log "Test Configuration:"
log "  Base URL: $BASE_URL"
log "  API Key: $(if [ -n "$API_KEY" ]; then echo "Provided"; else echo "Not provided"; fi)"
log "  Test Directory: $TEST_DIR"
log "  Results Directory: $RESULTS_DIR"
log "  Log File: $LOG_FILE"
log ""

# Check dependencies
log "${YELLOW}Checking dependencies...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    log "${RED}ERROR: Python3 is required but not installed${NC}"
    exit 1
fi

# Check required Python packages
REQUIRED_PACKAGES="requests pandas aiohttp psutil"
for package in $REQUIRED_PACKAGES; do
    if ! python3 -c "import $package" &> /dev/null; then
        log "${RED}ERROR: Required Python package '$package' is not installed${NC}"
        log "Please install with: pip install $package"
        exit 1
    fi
done

log "${GREEN}✓ All dependencies are available${NC}"
log ""

# Function to run a test and capture results
run_test() {
    local test_name="$1"
    local test_script="$2"
    local test_args="$3"
    
    log "${BLUE}Running $test_name...${NC}"
    log "Command: python3 $test_script $test_args"
    log ""
    
    if python3 "$test_script" $test_args >> "$LOG_FILE" 2>&1; then
        log "${GREEN}✓ $test_name PASSED${NC}"
        return 0
    else
        log "${RED}✗ $test_name FAILED${NC}"
        return 1
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local max_attempts=30
    local attempt=1
    
    log "${YELLOW}Waiting for TidyFrame service to be ready...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
            log "${GREEN}✓ Service is ready${NC}"
            return 0
        fi
        
        log "Attempt $attempt/$max_attempts - Service not ready, waiting..."
        sleep 2
        ((attempt++))
    done
    
    log "${RED}✗ Service is not responding after $max_attempts attempts${NC}"
    return 1
}

# Main test execution
main() {
    local tests_run=0
    local tests_passed=0
    local start_time=$(date +%s)
    
    # Wait for service
    if ! wait_for_service; then
        log "${RED}Cannot proceed with tests - service is not available${NC}"
        exit 1
    fi
    
    log ""
    log "${BLUE}Starting test execution...${NC}"
    log ""
    
    # Test 1: Subscription Bypass Test (for development)
    if [ -f "$TEST_DIR/subscription_bypass_test.py" ]; then
        ((tests_run++))
        if run_test "Subscription Bypass Test" "$TEST_DIR/subscription_bypass_test.py" "--base-url $BASE_URL"; then
            ((tests_passed++))
        fi
        log ""
    fi
    
    # Test 2: Comprehensive AI Validation Test
    if [ -f "$TEST_DIR/gemini_ai_validation_test.py" ]; then
        ((tests_run++))
        local ai_test_args="--base-url $BASE_URL"
        if [ -n "$API_KEY" ]; then
            ai_test_args="$ai_test_args --api-key $API_KEY"
        fi
        
        if run_test "Gemini AI Validation Test" "$TEST_DIR/gemini_ai_validation_test.py" "$ai_test_args"; then
            ((tests_passed++))
        fi
        log ""
    fi
    
    # Test 3: Performance Benchmark Test
    if [ -f "$TEST_DIR/performance_benchmark_test.py" ]; then
        ((tests_run++))
        local perf_test_args="--base-url $BASE_URL"
        if [ -n "$API_KEY" ]; then
            perf_test_args="$perf_test_args --api-key $API_KEY"
        fi
        
        if run_test "Performance Benchmark Test" "$TEST_DIR/performance_benchmark_test.py" "$perf_test_args"; then
            ((tests_passed++))
        fi
        log ""
    fi
    
    # Generate final report
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local success_rate=0
    
    if [ $tests_run -gt 0 ]; then
        success_rate=$((tests_passed * 100 / tests_run))
    fi
    
    log "${BLUE}================================================================================================${NC}"
    log "${BLUE}TEST SUITE COMPLETED${NC}"
    log "${BLUE}================================================================================================${NC}"
    log ""
    log "Test Summary:"
    log "  Tests Run: $tests_run"
    log "  Tests Passed: ${GREEN}$tests_passed${NC}"
    log "  Tests Failed: ${RED}$((tests_run - tests_passed))${NC}"
    log "  Success Rate: $success_rate%"
    log "  Duration: ${duration}s"
    log ""
    
    if [ $tests_passed -eq $tests_run ] && [ $tests_run -gt 0 ]; then
        log "${GREEN}🎉 ALL TESTS PASSED! TidyFrame AI processing is ready for production.${NC}"
        log ""
        log "Key validations completed:"
        log "  ✓ API endpoints are responding correctly"
        log "  ✓ Gemini AI processing is working"
        log "  ✓ Entity classification is accurate"
        log "  ✓ Name parsing handles complex patterns"
        log "  ✓ Performance meets expected thresholds"
        log "  ✓ Error handling is robust"
        log ""
        exit 0
    else
        log "${RED}❌ SOME TESTS FAILED! Review the issues before production deployment.${NC}"
        log ""
        log "Common issues to check:"
        log "  - Gemini API key configuration"
        log "  - Database connectivity"
        log "  - Subscription/billing middleware configuration"
        log "  - Network connectivity to Gemini APIs"
        log "  - Service resource limits"
        log ""
        log "Check the detailed log file for more information: $LOG_FILE"
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "TidyFrame AI Test Suite Runner"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Environment Variables:"
        echo "  TIDYFRAME_BASE_URL    Base URL for TidyFrame API (default: http://localhost:8000)"
        echo "  TIDYFRAME_API_KEY     API key for authenticated requests (optional)"
        echo ""
        echo "Options:"
        echo "  --help, -h            Show this help message"
        echo "  --check-deps          Check dependencies only"
        echo "  --logs               Show recent test logs"
        echo ""
        echo "Examples:"
        echo "  $0                                    # Run all tests with defaults"
        echo "  TIDYFRAME_BASE_URL=https://api.tidyframe.com $0  # Test production API"
        echo "  $0 --check-deps                      # Check dependencies only"
        echo ""
        exit 0
        ;;
    --check-deps)
        log "${YELLOW}Checking dependencies only...${NC}"
        # Dependency check is already done above
        log "${GREEN}✓ All dependencies are available - you can run the full test suite${NC}"
        exit 0
        ;;
    --logs)
        echo "Recent test logs:"
        if [ -f "$LOG_FILE" ]; then
            tail -50 "$LOG_FILE"
        else
            echo "No recent log file found"
        fi
        exit 0
        ;;
    *)
        # Run main tests
        main
        ;;
esac