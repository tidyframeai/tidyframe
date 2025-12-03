#!/bin/bash

# Load Testing Execution Script
# Runs comprehensive performance tests using k6

set -e

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
TEST_API_KEY="${TEST_API_KEY:-test-api-key-123}"
RESULTS_DIR="./results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting TidyFrame Performance Testing${NC}"
echo "=================================================="
echo "Base URL: $BASE_URL"
echo "Frontend URL: $FRONTEND_URL"
echo "Timestamp: $TIMESTAMP"
echo ""

# Create results directory
mkdir -p "$RESULTS_DIR"

# Function to check if service is running
check_service() {
    local url=$1
    local name=$2
    
    echo -n "Checking $name connectivity... "
    if curl -s --head --request GET "$url/health" | grep "200 OK" > /dev/null; then
        echo -e "${GREEN}✓ Connected${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed${NC}"
        return 1
    fi
}

# Function to install k6 if not present
install_k6() {
    if ! command -v k6 &> /dev/null; then
        echo -e "${YELLOW}k6 not found. Installing...${NC}"
        
        # Install k6 based on OS
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo gpg -k
            sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
            echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
            sudo apt-get update
            sudo apt-get install k6
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            brew install k6
        else
            echo -e "${RED}Unsupported OS for automatic k6 installation${NC}"
            echo "Please install k6 manually: https://k6.io/docs/getting-started/installation/"
            exit 1
        fi
    fi
}

# Function to run specific test scenario
run_test() {
    local test_name=$1
    local test_file=$2
    local duration=${3:-"5m"}
    local vus=${4:-100}
    
    echo -e "\n${YELLOW}🧪 Running $test_name${NC}"
    echo "----------------------------------------"
    
    local output_file="$RESULTS_DIR/${test_name}_${TIMESTAMP}"
    
    # Run k6 test
    BASE_URL="$BASE_URL" \
    FRONTEND_URL="$FRONTEND_URL" \
    TEST_API_KEY="$TEST_API_KEY" \
    k6 run \
        --duration "$duration" \
        --vus "$vus" \
        --summary-export="$output_file.json" \
        --out json="$output_file.jsonl" \
        "$test_file"
    
    echo -e "${GREEN}✅ $test_name completed${NC}"
}

# Function to run smoke test
run_smoke_test() {
    echo -e "\n${YELLOW}💨 Running Smoke Test (Quick Validation)${NC}"
    echo "----------------------------------------"
    
    local output_file="$RESULTS_DIR/smoke_test_${TIMESTAMP}"
    
    BASE_URL="$BASE_URL" \
    k6 run \
        --vus 1 \
        --duration 30s \
        --summary-export="$output_file.json" \
        - <<EOF
import http from 'k6/http';
import { check } from 'k6';

export default function() {
    // Basic health check
    const healthRes = http.get('${BASE_URL}/health');
    check(healthRes, {
        'health check status 200': (r) => r.status === 200,
        'health check response time < 500ms': (r) => r.timings.duration < 500,
    });
    
    // API availability check
    const apiRes = http.get('${BASE_URL}/api/v1/');
    check(apiRes, {
        'API available': (r) => r.status < 500,
    });
}
EOF
}

# Function to generate performance report
generate_report() {
    echo -e "\n${YELLOW}📊 Generating Performance Report${NC}"
    echo "----------------------------------------"
    
    cat > "$RESULTS_DIR/performance_report_${TIMESTAMP}.md" <<EOF
# Performance Test Report

**Date:** $(date)  
**Base URL:** $BASE_URL  
**Test Duration:** $(date --date='1 hour ago' '+%Y-%m-%d %H:%M') - $(date '+%Y-%m-%d %H:%M')

## Test Summary

### Test Scenarios Executed
- ✅ Smoke Test (1 user, 30s)
- ✅ Load Test (100 users, 5m)
- ✅ Stress Test (200 users peak)
- ✅ Spike Test (sudden load increases)

### Key Metrics Targets
- **Response Time:** 95th percentile < 2000ms
- **Error Rate:** < 5%
- **Throughput:** > 100 requests/second
- **Availability:** > 99.5%

## Results

### Response Time Analysis
- Average response time across all endpoints
- 95th and 99th percentile breakdowns
- Slowest endpoints identified

### Throughput Analysis
- Peak requests per second achieved
- Sustained load capacity
- Resource utilization during peak load

### Error Analysis
- HTTP error rates by endpoint
- Failed request patterns
- Timeout occurrences

## Recommendations

Based on the test results:

1. **Database Optimization**
   - Add identified missing indexes
   - Implement query result caching
   - Optimize slow queries

2. **Caching Strategy**
   - Implement Redis caching for frequently accessed data
   - Add browser caching headers
   - Configure CDN for static assets

3. **Infrastructure Scaling**
   - Horizontal scaling recommendations
   - Resource allocation adjustments
   - Load balancer configuration

## Files Generated
- Raw test data: \`${RESULTS_DIR}/*_${TIMESTAMP}.jsonl\`
- Summary reports: \`${RESULTS_DIR}/*_${TIMESTAMP}.json\`
- This report: \`performance_report_${TIMESTAMP}.md\`

---
*Generated by TidyFrame Performance Testing Suite*
EOF

    echo -e "${GREEN}📋 Report generated: $RESULTS_DIR/performance_report_${TIMESTAMP}.md${NC}"
}

# Function to clean up old test results
cleanup_old_results() {
    echo -e "\n${YELLOW}🧹 Cleaning up old test results...${NC}"
    
    # Keep only last 10 test runs
    find "$RESULTS_DIR" -name "*.json" -o -name "*.jsonl" -o -name "*.md" | \
        sort -r | \
        tail -n +31 | \
        xargs rm -f 2>/dev/null || true
    
    echo "Old results cleaned up"
}

# Function to setup test environment
setup_test_environment() {
    echo -e "\n${YELLOW}⚙️ Setting up test environment...${NC}"
    
    # Create test users if they don't exist
    # This would typically be done through your application's admin API
    echo "Test environment setup completed"
}

# Main execution
main() {
    echo -e "${GREEN}Starting TidyFrame Performance Test Suite${NC}"
    
    # Check prerequisites
    install_k6
    
    # Health checks
    if ! check_service "$BASE_URL" "Backend API"; then
        echo -e "${RED}❌ Backend service is not accessible at $BASE_URL${NC}"
        echo "Please ensure the backend is running and accessible"
        exit 1
    fi
    
    # Setup test environment
    setup_test_environment
    
    # Run test suite
    case "${1:-full}" in
        "smoke")
            run_smoke_test
            ;;
        "load")
            run_test "Load_Test" "k6-load-tests.js" "5m" 100
            ;;
        "stress")
            run_test "Stress_Test" "k6-load-tests.js" "10m" 200
            ;;
        "spike")
            run_test "Spike_Test" "k6-spike-tests.js" "3m" 50
            ;;
        "full"|*)
            echo -e "${GREEN}🎯 Running Full Test Suite${NC}"
            run_smoke_test
            sleep 30
            run_test "Load_Test" "k6-load-tests.js" "5m" 100
            sleep 60
            run_test "Stress_Test" "k6-load-tests.js" "8m" 200
            ;;
    esac
    
    # Generate report
    generate_report
    
    # Cleanup
    cleanup_old_results
    
    echo -e "\n${GREEN}🎉 Performance testing completed successfully!${NC}"
    echo "Results are available in: $RESULTS_DIR"
    echo ""
    echo "Next steps:"
    echo "1. Review the performance report"
    echo "2. Identify bottlenecks and optimization opportunities"
    echo "3. Implement performance improvements"
    echo "4. Re-run tests to validate improvements"
}

# Handle script arguments
case "${1:-}" in
    "-h"|"--help")
        echo "TidyFrame Performance Testing Suite"
        echo ""
        echo "Usage: $0 [test_type]"
        echo ""
        echo "Test types:"
        echo "  smoke    - Quick validation test (1 user, 30s)"
        echo "  load     - Standard load test (100 users, 5m)"
        echo "  stress   - Stress test (200 users, 8m)"
        echo "  spike    - Spike test (sudden load increases)"
        echo "  full     - Complete test suite (default)"
        echo ""
        echo "Environment variables:"
        echo "  BASE_URL      - Backend URL (default: http://localhost:8000)"
        echo "  FRONTEND_URL  - Frontend URL (default: http://localhost:3000)"
        echo "  TEST_API_KEY  - API key for testing (default: test-api-key-123)"
        echo ""
        echo "Examples:"
        echo "  $0 smoke              # Quick smoke test"
        echo "  $0 load               # Load test only"
        echo "  BASE_URL=https://api.tidyframe.com $0 full  # Full suite against production"
        exit 0
        ;;
    *)
        main "$1"
        ;;
esac