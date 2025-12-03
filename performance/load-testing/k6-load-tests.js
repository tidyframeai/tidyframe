/**
 * Comprehensive Load Testing Suite with k6
 * Tests for 100+ concurrent users across critical user flows
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';
import { randomString, randomItem } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// Custom metrics
export const errorRate = new Rate('error_rate');
export const responseTime = new Trend('response_time');
export const requestsPerSecond = new Rate('requests_per_second');
export const activeUsers = new Gauge('active_users');
export const failedRequests = new Counter('failed_requests');

// Test configuration
export const options = {
  stages: [
    // Warm up
    { duration: '30s', target: 10 },
    // Ramp up to 50 users
    { duration: '1m', target: 50 },
    // Ramp up to 100 users
    { duration: '2m', target: 100 },
    // Hold at 100 users
    { duration: '5m', target: 100 },
    // Peak load test - 200 users
    { duration: '1m', target: 200 },
    // Hold peak
    { duration: '2m', target: 200 },
    // Ramp down
    { duration: '2m', target: 50 },
    { duration: '1m', target: 0 },
  ],
  
  thresholds: {
    // Response time thresholds
    'response_time': ['p(95)<2000', 'p(99)<5000'],
    'http_req_duration': ['p(95)<1500', 'p(99)<3000'],
    
    // Error rate thresholds
    'error_rate': ['rate<0.05'], // Less than 5% error rate
    'http_req_failed': ['rate<0.05'],
    
    // Request rate thresholds
    'http_reqs': ['rate>100'], // At least 100 requests per second
    
    // Specific endpoint thresholds
    'http_req_duration{name:auth}': ['p(95)<1000'],
    'http_req_duration{name:dashboard}': ['p(95)<2000'],
    'http_req_duration{name:upload}': ['p(95)<10000'],
  },
  
  // Cloud or on-premise execution
  ext: {
    loadimpact: {
      distribution: {
        'amazon:us:ashburn': { loadZone: 'amazon:us:ashburn', percent: 100 },
      },
    },
  },
};

// Test data
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const FRONTEND_URL = __ENV.FRONTEND_URL || 'http://localhost:3000';

// Test users - would normally be loaded from a file
const testUsers = [
  { email: 'loadtest1@example.com', password: 'TestPassword123!' },
  { email: 'loadtest2@example.com', password: 'TestPassword123!' },
  { email: 'loadtest3@example.com', password: 'TestPassword123!' },
  // Add more test users as needed
];

// Sample CSV data for file uploads
const csvData = `Name,Email,Phone
John Smith,john.smith@example.com,555-1234
Jane Doe,jane.doe@example.com,555-5678
Bob Johnson,bob.johnson@example.com,555-9012`;

let authToken = '';
let userId = '';

export function setup() {
  console.log('Setting up load test environment...');
  
  // Create test users if needed
  // This would typically be done outside of k6
  return { baseUrl: BASE_URL };
}

export default function(data) {
  // Update active users metric
  activeUsers.add(1);
  
  // Simulate different user behaviors
  const userBehavior = randomItem(['heavy_user', 'light_user', 'api_user', 'dashboard_user']);
  
  switch(userBehavior) {
    case 'heavy_user':
      heavyUserScenario();
      break;
    case 'light_user':
      lightUserScenario();
      break;
    case 'api_user':
      apiUserScenario();
      break;
    case 'dashboard_user':
      dashboardUserScenario();
      break;
  }
  
  // Random sleep between 1-3 seconds
  sleep(Math.random() * 2 + 1);
}

function heavyUserScenario() {
  group('Heavy User Flow', function() {
    // Login
    if (loginUser()) {
      // Upload multiple files
      uploadFile();
      sleep(2);
      
      // Check job status multiple times
      for(let i = 0; i < 5; i++) {
        checkJobStatus();
        sleep(1);
      }
      
      // Access dashboard
      accessDashboard();
      sleep(1);
      
      // Download results
      downloadResults();
    }
  });
}

function lightUserScenario() {
  group('Light User Flow', function() {
    // Simple dashboard access
    if (loginUser()) {
      accessDashboard();
      sleep(2);
      
      // Check recent jobs
      getUserJobs();
      sleep(1);
    }
  });
}

function apiUserScenario() {
  group('API User Flow', function() {
    // API key authentication
    if (authenticateWithApiKey()) {
      // Multiple API calls
      for(let i = 0; i < 10; i++) {
        apiParseRequest();
        sleep(0.1);
      }
    }
  });
}

function dashboardUserScenario() {
  group('Dashboard User Flow', function() {
    if (loginUser()) {
      accessDashboard();
      sleep(1);
      getUserJobs();
      sleep(1);
      getUserStats();
      sleep(1);
      checkNotifications();
    }
  });
}

function loginUser() {
  group('Authentication', function() {
    const user = randomItem(testUsers);
    
    const loginPayload = {
      username: user.email,
      password: user.password,
    };
    
    const params = {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      tags: { name: 'auth' },
    };
    
    const response = http.post(
      `${BASE_URL}/api/v1/auth/login`,
      Object.keys(loginPayload).map(key => 
        encodeURIComponent(key) + '=' + encodeURIComponent(loginPayload[key])
      ).join('&'),
      params
    );
    
    const success = check(response, {
      'login successful': (r) => r.status === 200,
      'token received': (r) => r.json('access_token') !== undefined,
      'response time < 1000ms': (r) => r.timings.duration < 1000,
    });
    
    responseTime.add(response.timings.duration);
    errorRate.add(!success);
    
    if (success) {
      authToken = response.json('access_token');
      return true;
    } else {
      failedRequests.add(1);
      return false;
    }
  });
}

function authenticateWithApiKey() {
  // Simulate API key authentication
  const apiKey = __ENV.TEST_API_KEY || 'test-api-key-123';
  
  const response = http.get(`${BASE_URL}/api/v1/users/me`, {
    headers: {
      'X-API-Key': apiKey,
    },
    tags: { name: 'api_auth' },
  });
  
  const success = check(response, {
    'API key auth successful': (r) => r.status === 200,
  });
  
  responseTime.add(response.timings.duration);
  errorRate.add(!success);
  
  return success;
}

function uploadFile() {
  group('File Upload', function() {
    const boundary = '----formdata-k6-' + Math.random().toString(16);
    const formData = `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="test.csv"\r\nContent-Type: text/csv\r\n\r\n${csvData}\r\n--${boundary}--`;
    
    const response = http.post(`${BASE_URL}/api/v1/jobs/upload`, formData, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
      },
      tags: { name: 'upload' },
    });
    
    const success = check(response, {
      'upload successful': (r) => r.status === 201,
      'job ID received': (r) => r.json('job_id') !== undefined,
      'response time < 10s': (r) => r.timings.duration < 10000,
    });
    
    responseTime.add(response.timings.duration);
    errorRate.add(!success);
    
    if (success) {
      const jobId = response.json('job_id');
      return jobId;
    } else {
      failedRequests.add(1);
      return null;
    }
  });
}

function checkJobStatus() {
  group('Job Status Check', function() {
    const response = http.get(`${BASE_URL}/api/v1/jobs`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
      },
      tags: { name: 'job_status' },
    });
    
    const success = check(response, {
      'job status retrieved': (r) => r.status === 200,
      'jobs array exists': (r) => Array.isArray(r.json('jobs')),
      'response time < 2s': (r) => r.timings.duration < 2000,
    });
    
    responseTime.add(response.timings.duration);
    errorRate.add(!success);
    
    if (!success) {
      failedRequests.add(1);
    }
  });
}

function accessDashboard() {
  group('Dashboard Access', function() {
    const response = http.get(`${BASE_URL}/api/v1/dashboard/stats`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
      },
      tags: { name: 'dashboard' },
    });
    
    const success = check(response, {
      'dashboard loaded': (r) => r.status === 200,
      'stats object exists': (r) => typeof r.json() === 'object',
      'response time < 2s': (r) => r.timings.duration < 2000,
    });
    
    responseTime.add(response.timings.duration);
    errorRate.add(!success);
    
    if (!success) {
      failedRequests.add(1);
    }
  });
}

function getUserJobs() {
  group('User Jobs', function() {
    const response = http.get(`${BASE_URL}/api/v1/jobs?limit=20&offset=0`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
      },
      tags: { name: 'user_jobs' },
    });
    
    const success = check(response, {
      'jobs retrieved': (r) => r.status === 200,
      'response time < 1.5s': (r) => r.timings.duration < 1500,
    });
    
    responseTime.add(response.timings.duration);
    errorRate.add(!success);
  });
}

function getUserStats() {
  group('User Statistics', function() {
    const response = http.get(`${BASE_URL}/api/v1/users/me/stats`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
      },
      tags: { name: 'user_stats' },
    });
    
    check(response, {
      'stats retrieved': (r) => r.status === 200,
      'response time < 1s': (r) => r.timings.duration < 1000,
    });
    
    responseTime.add(response.timings.duration);
  });
}

function checkNotifications() {
  group('Notifications', function() {
    const response = http.get(`${BASE_URL}/api/v1/notifications`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
      },
      tags: { name: 'notifications' },
    });
    
    check(response, {
      'notifications retrieved': (r) => r.status === 200,
    });
    
    responseTime.add(response.timings.duration);
  });
}

function downloadResults() {
  group('Download Results', function() {
    // This would download actual result files
    // Simulated here with a simple GET request
    const response = http.get(`${BASE_URL}/api/v1/jobs/latest/download`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
      },
      tags: { name: 'download' },
    });
    
    check(response, {
      'download initiated': (r) => r.status === 200 || r.status === 302,
    });
    
    responseTime.add(response.timings.duration);
  });
}

function apiParseRequest() {
  group('API Parse Request', function() {
    const testName = randomString(10);
    
    const response = http.post(`${BASE_URL}/api/v1/parse`, 
      JSON.stringify({ name: testName }), 
      {
        headers: {
          'X-API-Key': __ENV.TEST_API_KEY || 'test-api-key-123',
          'Content-Type': 'application/json',
        },
        tags: { name: 'api_parse' },
      }
    );
    
    check(response, {
      'parse successful': (r) => r.status === 200,
      'result returned': (r) => r.json('result') !== undefined,
      'response time < 5s': (r) => r.timings.duration < 5000,
    });
    
    responseTime.add(response.timings.duration);
  });
}

export function teardown(data) {
  console.log('Load test completed. Cleaning up...');
  
  // Output final metrics
  console.log(`Average response time: ${responseTime.avg}ms`);
  console.log(`95th percentile response time: ${responseTime.p95}ms`);
  console.log(`Error rate: ${(errorRate.rate * 100).toFixed(2)}%`);
  console.log(`Total failed requests: ${failedRequests.count}`);
}

// Helper function for data-driven testing
export function handleSummary(data) {
  return {
    'performance-summary.json': JSON.stringify(data, null, 2),
    'performance-summary.html': htmlReport(data),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function htmlReport(data) {
  return `
<!DOCTYPE html>
<html>
<head>
    <title>Load Test Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .metric { background: #f5f5f5; padding: 10px; margin: 5px 0; }
        .error { color: red; }
        .success { color: green; }
        .warning { color: orange; }
    </style>
</head>
<body>
    <h1>Load Test Results - TidyFrame</h1>
    
    <h2>Summary</h2>
    <div class="metric">
        <strong>Total Requests:</strong> ${data.metrics.http_reqs.count}
    </div>
    <div class="metric">
        <strong>Failed Requests:</strong> ${data.metrics.http_req_failed.count} 
        (${(data.metrics.http_req_failed.rate * 100).toFixed(2)}%)
    </div>
    <div class="metric">
        <strong>Average Response Time:</strong> ${data.metrics.http_req_duration.avg.toFixed(2)}ms
    </div>
    <div class="metric">
        <strong>95th Percentile:</strong> ${data.metrics.http_req_duration.p95.toFixed(2)}ms
    </div>
    <div class="metric">
        <strong>99th Percentile:</strong> ${data.metrics.http_req_duration.p99.toFixed(2)}ms
    </div>
    
    <h2>Thresholds</h2>
    ${Object.entries(data.thresholds || {}).map(([name, threshold]) => `
        <div class="metric ${threshold.ok ? 'success' : 'error'}">
            <strong>${name}:</strong> ${threshold.ok ? 'PASSED' : 'FAILED'}
        </div>
    `).join('')}
    
    <h2>Test Configuration</h2>
    <div class="metric">
        <strong>Max Virtual Users:</strong> 200
    </div>
    <div class="metric">
        <strong>Test Duration:</strong> ~15 minutes
    </div>
    <div class="metric">
        <strong>Base URL:</strong> ${BASE_URL}
    </div>
    
    <p><em>Generated on ${new Date().toISOString()}</em></p>
</body>
</html>
  `;
}

function textSummary(data, options) {
  // k6 built-in text summary
  return `
Load Test Summary
=================

Total Requests: ${data.metrics.http_reqs.count}
Failed Requests: ${data.metrics.http_req_failed.count} (${(data.metrics.http_req_failed.rate * 100).toFixed(2)}%)
Request Rate: ${data.metrics.http_reqs.rate.toFixed(2)}/s

Response Times:
- Average: ${data.metrics.http_req_duration.avg.toFixed(2)}ms
- Min: ${data.metrics.http_req_duration.min.toFixed(2)}ms
- Max: ${data.metrics.http_req_duration.max.toFixed(2)}ms
- 95th Percentile: ${data.metrics.http_req_duration.p95.toFixed(2)}ms
- 99th Percentile: ${data.metrics.http_req_duration.p99.toFixed(2)}ms

Data Transfer:
- Sent: ${(data.metrics.data_sent.count / 1024 / 1024).toFixed(2)}MB
- Received: ${(data.metrics.data_received.count / 1024 / 1024).toFixed(2)}MB
  `;
}