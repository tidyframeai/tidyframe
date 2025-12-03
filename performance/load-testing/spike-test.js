/**
 * Spike Load Testing - Sudden Traffic Increases
 * Tests system behavior under sudden load spikes
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
export const spikeResponseTime = new Trend('spike_response_time');
export const spikeErrorRate = new Rate('spike_error_rate');
export const recoveryTime = new Trend('recovery_time');

// Spike test configuration - simulates sudden traffic spikes
export const options = {
  stages: [
    // Normal baseline load
    { duration: '2m', target: 20 },
    // Sudden spike to 150 users
    { duration: '10s', target: 150 },
    // Hold spike for 1 minute
    { duration: '1m', target: 150 },
    // Another spike to 300 users
    { duration: '10s', target: 300 },
    // Hold peak spike
    { duration: '30s', target: 300 },
    // Gradual recovery
    { duration: '1m', target: 50 },
    // Back to baseline
    { duration: '2m', target: 20 },
    // Final spike test
    { duration: '5s', target: 200 },
    { duration: '30s', target: 200 },
    // Complete recovery
    { duration: '2m', target: 0 },
  ],
  
  thresholds: {
    'spike_response_time': ['p(95)<5000'], // Allow higher response time during spikes
    'spike_error_rate': ['rate<0.1'],      // Allow up to 10% error rate during spikes
    'http_req_duration': ['p(99)<10000'],  // 99th percentile under 10s
    'http_req_failed': ['rate<0.15'],      // Up to 15% failure rate acceptable during extreme spikes
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const testUsers = [
  { email: 'spiketest1@example.com', password: 'TestPassword123!' },
  { email: 'spiketest2@example.com', password: 'TestPassword123!' },
];

let authToken = '';

export default function() {
  // Determine current load phase
  const currentVUs = __ENV.K6_VUS || 1;
  const isSpike = currentVUs > 100;
  
  if (isSpike) {
    spikeTestScenario();
  } else {
    normalLoadScenario();
  }
  
  // Vary sleep time based on load
  const sleepTime = isSpike ? Math.random() * 0.5 + 0.1 : Math.random() * 1 + 0.5;
  sleep(sleepTime);
}

function normalLoadScenario() {
  group('Normal Load Operations', function() {
    if (authenticate()) {
      // Standard user operations
      checkDashboard();
      sleep(1);
      checkJobs();
    }
  });
}

function spikeTestScenario() {
  group('Spike Load Operations', function() {
    // Simpler operations during spike to focus on core functionality
    const startTime = Date.now();
    
    // Quick health check
    const healthResponse = http.get(`${BASE_URL}/health`, {
      tags: { name: 'spike_health' },
      timeout: '10s',
    });
    
    const success = check(healthResponse, {
      'health check during spike': (r) => r.status === 200,
      'response time reasonable': (r) => r.timings.duration < 5000,
    });
    
    spikeResponseTime.add(healthResponse.timings.duration);
    spikeErrorRate.add(!success);
    
    // If health check fails, skip other operations
    if (!success) {
      return;
    }
    
    // Try authentication during spike
    if (authenticate()) {
      // Minimal operations during spike
      quickDashboardCheck();
    }
    
    // Measure recovery time (how long it takes to get back to normal response times)
    if (healthResponse.timings.duration < 1000) {
      recoveryTime.add(Date.now() - startTime);
    }
  });
}

function authenticate() {
  const user = testUsers[Math.floor(Math.random() * testUsers.length)];
  
  const response = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    `username=${user.email}&password=${user.password}`,
    {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      tags: { name: 'spike_auth' },
      timeout: '15s',
    }
  );
  
  const success = check(response, {
    'spike auth successful': (r) => r.status === 200,
  });
  
  if (success) {
    authToken = response.json('access_token');
    return true;
  }
  
  return false;
}

function checkDashboard() {
  const response = http.get(`${BASE_URL}/api/v1/dashboard/stats`, {
    headers: { 'Authorization': `Bearer ${authToken}` },
    tags: { name: 'normal_dashboard' },
    timeout: '10s',
  });
  
  check(response, {
    'normal dashboard loaded': (r) => r.status === 200,
    'dashboard response time ok': (r) => r.timings.duration < 3000,
  });
}

function quickDashboardCheck() {
  const response = http.get(`${BASE_URL}/api/v1/dashboard/stats`, {
    headers: { 'Authorization': `Bearer ${authToken}` },
    tags: { name: 'spike_dashboard' },
    timeout: '20s', // Longer timeout during spikes
  });
  
  const success = check(response, {
    'spike dashboard accessible': (r) => r.status < 500, // Accept any non-server error
    'spike dashboard not timing out': (r) => r.timings.duration < 20000,
  });
  
  spikeResponseTime.add(response.timings.duration);
  spikeErrorRate.add(!success);
}

function checkJobs() {
  const response = http.get(`${BASE_URL}/api/v1/jobs?limit=10`, {
    headers: { 'Authorization': `Bearer ${authToken}` },
    tags: { name: 'normal_jobs' },
    timeout: '10s',
  });
  
  check(response, {
    'jobs retrieved normally': (r) => r.status === 200,
  });
}

export function handleSummary(data) {
  const spikeMetrics = {
    spike_response_time: data.metrics.spike_response_time,
    spike_error_rate: data.metrics.spike_error_rate,
    recovery_time: data.metrics.recovery_time,
    total_requests: data.metrics.http_reqs.count,
    failed_requests: data.metrics.http_req_failed.count,
    avg_response_time: data.metrics.http_req_duration.avg,
    p95_response_time: data.metrics.http_req_duration.p95,
    p99_response_time: data.metrics.http_req_duration.p99,
  };
  
  return {
    'spike-test-results.json': JSON.stringify(spikeMetrics, null, 2),
    'spike-test-summary.html': generateSpikeReport(data),
    stdout: `
Spike Test Summary
==================

🔥 Spike Performance Analysis:
   - Peak Response Time: ${data.metrics.http_req_duration.max?.toFixed(2)}ms
   - 95th Percentile: ${data.metrics.http_req_duration.p95?.toFixed(2)}ms
   - Error Rate During Spikes: ${(data.metrics.spike_error_rate?.rate * 100)?.toFixed(2)}%
   - Total Requests: ${data.metrics.http_reqs.count}
   - Failed Requests: ${data.metrics.http_req_failed.count}

⚡ System Resilience:
   - Recovery Time: ${data.metrics.recovery_time?.avg?.toFixed(2)}ms avg
   - System handled ${data.metrics.http_reqs.count} requests during spike test
   - Error rate: ${(data.metrics.http_req_failed.rate * 100).toFixed(2)}%

📈 Recommendations:
   ${getSpikeTestRecommendations(data)}
    `,
  };
}

function generateSpikeReport(data) {
  return `
<!DOCTYPE html>
<html>
<head>
    <title>Spike Test Results - TidyFrame</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .metric { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .error { background-color: #ffe6e6; border-left: 4px solid #dc3545; }
        .success { background-color: #e6ffe6; border-left: 4px solid #28a745; }
        .warning { background-color: #fff3cd; border-left: 4px solid #ffc107; }
        .chart { width: 100%; height: 200px; background: #f0f0f0; margin: 10px 0; }
        h1, h2 { color: #2c3e50; }
        .summary { background: #e8f4f8; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>🔥 Spike Load Test Results</h1>
    
    <div class="summary">
        <h2>Test Overview</h2>
        <p><strong>Test Type:</strong> Sudden Traffic Spike Simulation</p>
        <p><strong>Peak Concurrent Users:</strong> 300</p>
        <p><strong>Spike Duration:</strong> Multiple spikes with 30s-1m holds</p>
        <p><strong>Date:</strong> ${new Date().toISOString()}</p>
    </div>

    <h2>📊 Key Metrics</h2>
    
    <div class="metric ${data.metrics.http_req_failed.rate < 0.1 ? 'success' : data.metrics.http_req_failed.rate < 0.2 ? 'warning' : 'error'}">
        <strong>Overall Error Rate:</strong> ${(data.metrics.http_req_failed.rate * 100).toFixed(2)}%
        <br><small>Target: < 10% during spikes</small>
    </div>
    
    <div class="metric ${data.metrics.http_req_duration.p95 < 5000 ? 'success' : data.metrics.http_req_duration.p95 < 10000 ? 'warning' : 'error'}">
        <strong>95th Percentile Response Time:</strong> ${data.metrics.http_req_duration.p95.toFixed(2)}ms
        <br><small>Target: < 5000ms during spikes</small>
    </div>
    
    <div class="metric">
        <strong>Peak Response Time:</strong> ${data.metrics.http_req_duration.max.toFixed(2)}ms
    </div>
    
    <div class="metric">
        <strong>Total Requests Processed:</strong> ${data.metrics.http_reqs.count}
    </div>
    
    <div class="metric ${data.metrics.recovery_time?.avg < 2000 ? 'success' : 'warning'}">
        <strong>Average Recovery Time:</strong> ${data.metrics.recovery_time?.avg?.toFixed(2) || 'N/A'}ms
        <br><small>Time to return to normal response times</small>
    </div>

    <h2>🎯 System Resilience Analysis</h2>
    
    <div class="metric">
        <h3>Spike Handling Capability</h3>
        <ul>
            <li>System handled sudden 7.5x load increase (20 → 150 users)</li>
            <li>Maintained ${((1 - data.metrics.http_req_failed.rate) * 100).toFixed(1)}% availability during spikes</li>
            <li>Peak concurrent users: 300</li>
        </ul>
    </div>
    
    <div class="metric">
        <h3>Performance Degradation</h3>
        <ul>
            <li>Response time increased by ${((data.metrics.http_req_duration.p95 / data.metrics.http_req_duration.avg - 1) * 100).toFixed(1)}% at 95th percentile</li>
            <li>Error rate during spikes: ${(data.metrics.spike_error_rate?.rate * 100 || 0).toFixed(2)}%</li>
            <li>Recovery time: ${data.metrics.recovery_time?.avg?.toFixed(0) || 'N/A'}ms average</li>
        </ul>
    </div>

    <h2>🚀 Recommendations</h2>
    <div class="metric">
        ${getSpikeTestRecommendations(data)}
    </div>

    <h2>📈 Detailed Metrics</h2>
    <div class="metric">
        <table style="width: 100%; border-collapse: collapse;">
            <tr><th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Metric</th><th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Value</th></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;">Average Response Time</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${data.metrics.http_req_duration.avg.toFixed(2)}ms</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;">Median Response Time</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${data.metrics.http_req_duration.med.toFixed(2)}ms</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;">90th Percentile</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${data.metrics.http_req_duration.p90.toFixed(2)}ms</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;">99th Percentile</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${data.metrics.http_req_duration.p99.toFixed(2)}ms</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;">Request Rate</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${data.metrics.http_reqs.rate.toFixed(2)}/sec</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;">Data Received</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${(data.metrics.data_received.count / 1024 / 1024).toFixed(2)} MB</td></tr>
        </table>
    </div>

    <p><em>Generated on ${new Date().toLocaleString()}</em></p>
</body>
</html>
  `;
}

function getSpikeTestRecommendations(data) {
  let recommendations = [];
  
  if (data.metrics.http_req_failed.rate > 0.1) {
    recommendations.push('⚠️ High error rate during spikes - implement circuit breaker pattern and rate limiting');
  }
  
  if (data.metrics.http_req_duration.p95 > 5000) {
    recommendations.push('🐌 Slow response times during spikes - consider auto-scaling and load balancing improvements');
  }
  
  if (data.metrics.recovery_time?.avg > 3000) {
    recommendations.push('⏰ Slow recovery time - optimize cache warming and connection pooling');
  }
  
  if (data.metrics.http_reqs.rate < 50) {
    recommendations.push('📉 Low throughput during spikes - review database connection limits and async processing');
  }
  
  if (recommendations.length === 0) {
    recommendations.push('✅ Excellent spike handling! System shows good resilience to sudden load increases');
  }
  
  recommendations.push('🔧 Consider implementing: Auto-scaling policies, CDN for static assets, Database read replicas');
  
  return `<ul>${recommendations.map(r => `<li>${r}</li>`).join('')}</ul>`;
}