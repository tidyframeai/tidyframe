# TidyFrame Gemini AI Processing Test Suite

This comprehensive test suite validates the Gemini AI processing functionality in the TidyFrame application, ensuring it's ready for production deployment.

## Overview

The test suite includes the following components:

### 1. Core AI Validation Test (`gemini_ai_validation_test.py`)
- **Purpose**: Validates end-to-end Gemini AI processing functionality
- **Features Tested**:
  - CSV file upload and validation
  - Gemini AI name parsing and entity classification
  - Results format validation and download
  - AI accuracy and confidence metrics
  - Error handling and edge cases

### 2. Subscription Bypass Test (`subscription_bypass_test.py`)
- **Purpose**: Helps bypass subscription requirements during testing
- **Use Cases**:
  - Development environment testing
  - CI/CD pipeline validation
  - Local testing without payment setup

### 3. Performance Benchmark Test (`performance_benchmark_test.py`)
- **Purpose**: Tests AI processing performance and scalability
- **Metrics Measured**:
  - Processing throughput (rows per second)
  - Concurrent processing efficiency
  - Resource usage (CPU, memory)
  - API cost optimization
  - Scalability analysis

### 4. Test Runner Script (`run_ai_tests.sh`)
- **Purpose**: Orchestrates all tests with comprehensive reporting
- **Features**:
  - Dependency checking
  - Service health validation
  - Comprehensive test execution
  - Detailed logging and reporting

## Quick Start

### Prerequisites

1. **Python 3.7+** with required packages:
```bash
pip install requests pandas aiohttp psutil
```

2. **TidyFrame Backend** running (typically on http://localhost:8000)

3. **Gemini API Key** configured in environment or backend

### Running Tests

#### Option 1: Run All Tests (Recommended)
```bash
# Run all tests with default settings
./run_ai_tests.sh

# Run tests against production API
TIDYFRAME_BASE_URL=https://api.tidyframe.com ./run_ai_tests.sh

# Run tests with API key
TIDYFRAME_API_KEY=your_api_key ./run_ai_tests.sh
```

#### Option 2: Run Individual Tests
```bash
# Test subscription bypass (for development)
python3 subscription_bypass_test.py --base-url http://localhost:8000

# Run comprehensive AI validation
python3 gemini_ai_validation_test.py --base-url http://localhost:8000 --api-key your_key

# Run performance benchmarks
python3 performance_benchmark_test.py --base-url http://localhost:8000
```

### Environment Variables

- `TIDYFRAME_BASE_URL`: Base URL for TidyFrame API (default: http://localhost:8000)
- `TIDYFRAME_API_KEY`: API key for authenticated requests (optional for development)

## Test Data

The test suite automatically generates realistic test data that exercises all AI features:

### Entity Types Tested
- **Person Names**: Simple names, complex international names, joint names
- **Company Entities**: LLCs, corporations, partnerships, agricultural businesses
- **Trust Entities**: Family trusts, living trusts, estates
- **Edge Cases**: Invalid inputs, single letters, unknown entities

### Name Patterns Tested
- **Simple Pattern**: "John Smith"
- **Last-First-Initial**: "Moore Norman H" (common in property records)
- **Joint Names**: "Jett David W. & Jennifer M."
- **Shared Last Names**: "Tom & Sarah Johnson"
- **Complex Names**: "O'Brien Michael Patrick", "Van Der Berg Christina"
- **Titles/Suffixes**: "Dr. Robert Smith Jr."

## Expected Test Results

### Success Criteria

1. **Entity Classification Accuracy**: ≥ 80%
2. **High Confidence Results**: ≥ 70%
3. **Average Confidence Score**: ≥ 0.8
4. **Processing Success Rate**: ≥ 90%
5. **Processing Speed**: ≥ 10 rows per second

### Performance Benchmarks

- **Small Files (50-100 rows)**: 15-25 rows/second
- **Medium Files (500 rows)**: 10-20 rows/second
- **Large Files (1000+ rows)**: 8-15 rows/second
- **Concurrent Processing**: 70%+ efficiency

## Output and Reporting

### Test Reports
All tests generate detailed JSON reports saved to `/tests/results/`:
- `ai_test_report_[timestamp].json`: AI validation results
- `performance_benchmark_[timestamp].json`: Performance metrics
- `test_run_[timestamp].log`: Complete test execution log

### Sample Output
```
TIDYFRAME GEMINI AI PROCESSING - COMPREHENSIVE TEST SUITE
============================================================

✓ Health endpoint test passed
✓ CSV upload test passed - Job ID: abc123
✓ Job processing completed in 12.34s
✓ AI results validation passed
✓ Results download test passed

Entity Classification Results:
  person_count: Expected 12, Got 11 (Accuracy: 91.7%)
  company_count: Expected 3, Got 3 (Accuracy: 100.0%)
  trust_count: Expected 2, Got 2 (Accuracy: 100.0%)

Overall Entity Classification Accuracy: 94.1%
High Confidence Results: 15/17 (88.2%)

🎉 ALL TESTS PASSED! TidyFrame AI processing is ready for production.
```

## Troubleshooting

### Common Issues

1. **"Health check failed"**
   - Ensure TidyFrame backend is running
   - Check the base URL configuration
   - Verify network connectivity

2. **"Subscription/billing middleware blocking requests"**
   - Use the subscription bypass test to identify issues
   - Check billing middleware configuration
   - Ensure test user has proper permissions

3. **"Gemini API errors"**
   - Verify GEMINI_API_KEY is set correctly
   - Check API quota and billing status
   - Ensure network can reach Google APIs

4. **"Low AI accuracy"**
   - Check Gemini prompt configuration
   - Verify entity classification logic
   - Review test data expectations

5. **"Poor performance"**
   - Check system resources (CPU, memory)
   - Verify database performance
   - Review concurrent processing limits

### Debug Mode
Run tests with verbose logging:
```bash
python3 gemini_ai_validation_test.py --verbose --base-url http://localhost:8000
```

### Manual Testing
For manual testing, use the provided test CSV data:
```csv
names,address,city,state
Moore Norman H,119 W 5th St,Hartford,IL
Jett David W. & Jennifer M.,971 Honeyridge Rd,Catawissa,MO
Johnson Family Trust,890 Trust Ave,Aurora,IL
ABC Properties LLC,987 Business Blvd,Schaumburg,IL
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: TidyFrame AI Tests
on: [push, pull_request]

jobs:
  ai-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: pip install requests pandas aiohttp psutil
      - name: Start TidyFrame services
        run: docker-compose up -d
      - name: Wait for services
        run: sleep 30
      - name: Run AI tests
        run: ./tests/run_ai_tests.sh
        env:
          TIDYFRAME_BASE_URL: http://localhost:8000
          TIDYFRAME_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

### Docker Integration
```bash
# Run tests in Docker environment
docker-compose exec backend python3 /app/tests/gemini_ai_validation_test.py
```

## Advanced Usage

### Custom Test Data
Create your own test CSV files and use them:
```python
from gemini_ai_validation_test import TidyFrameAITestSuite

test_suite = TidyFrameAITestSuite(base_url="http://localhost:8000")
job_id = test_suite.test_csv_upload("/path/to/your/test.csv")
```

### Performance Tuning
Adjust performance test parameters:
```python
from performance_benchmark_test import PerformanceBenchmarkTest

benchmark = PerformanceBenchmarkTest()
# Test with larger files
result = await benchmark.benchmark_single_file_processing(5000)
```

### Custom Validation Criteria
Modify validation thresholds in the test scripts:
```python
# In gemini_ai_validation_test.py
validation_passed = (
    overall_accuracy >= 85.0 and      # Increase accuracy requirement
    high_confidence_rate >= 75.0 and  # Increase confidence requirement
    avg_confidence >= 0.85 and        # Higher average confidence
    success_rate >= 95.0               # Higher success rate
)
```

## Support

For issues with the test suite:

1. Check the troubleshooting section above
2. Review test logs in `/tests/results/`
3. Verify Gemini AI service configuration
4. Check TidyFrame backend logs
5. Create an issue with detailed error information

## Contributing

To add new tests:

1. Follow the existing test structure
2. Include comprehensive error handling
3. Generate detailed reports
4. Update this documentation
5. Ensure tests can run in CI/CD environments