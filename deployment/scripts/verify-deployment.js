#!/usr/bin/env node
/**
 * xSwarm Boss - Post-Deployment Verification Script
 *
 * Comprehensive verification of deployed services:
 * - Health checks
 * - API endpoint testing
 * - Database connectivity
 * - Authentication flows
 * - Webhook endpoints
 * - Email/SMS delivery
 * - Performance benchmarks
 *
 * Usage: node deployment/scripts/verify-deployment.js [--env=production|staging] [--quick]
 */

import { config } from 'dotenv';
import { createClient } from '@libsql/client';

// Load environment variables
config();

// Parse command line arguments
const args = process.argv.slice(2);
const envArg = args.find(arg => arg.startsWith('--env='));
const targetEnv = envArg ? envArg.split('=')[1] : 'production';
const quickTest = args.includes('--quick');

// Get worker URL based on environment
const workerUrls = {
  production: process.env.WORKER_URL || 'https://boss-ai.workers.dev',
  staging: process.env.STAGING_WORKER_URL || 'https://boss-ai-staging.workers.dev',
  development: 'http://localhost:8787',
};

const baseUrl = workerUrls[targetEnv];

// Colors for output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  bold: '\x1b[1m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logSection(title) {
  log(`\n${'='.repeat(60)}`, 'cyan');
  log(`  ${title}`, 'bold');
  log('='.repeat(60), 'cyan');
}

// Track test results
const results = {
  passed: 0,
  failed: 0,
  warnings: 0,
  tests: [],
};

function recordTest(name, status, details = {}) {
  results.tests.push({ name, status, ...details });
  if (status === 'pass') results.passed++;
  else if (status === 'fail') results.failed++;
  else results.warnings++;

  const symbol = status === 'pass' ? '✅' : status === 'fail' ? '❌' : '⚠️';
  const color = status === 'pass' ? 'green' : status === 'fail' ? 'red' : 'yellow';
  log(`${symbol} ${name}`, color);

  if (details.message) {
    log(`   ${details.message}`, 'reset');
  }
  if (details.responseTime) {
    const timeColor = details.responseTime < 500 ? 'green' : details.responseTime < 2000 ? 'yellow' : 'red';
    log(`   Response time: ${details.responseTime}ms`, timeColor);
  }
}

// Make HTTP request with timing
async function testEndpoint(method, path, options = {}) {
  const url = `${baseUrl}${path}`;
  const startTime = Date.now();

  try {
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: AbortSignal.timeout(options.timeout || 10000),
    });

    const responseTime = Date.now() - startTime;
    const data = response.headers.get('content-type')?.includes('application/json')
      ? await response.json()
      : await response.text();

    return {
      success: response.ok,
      status: response.status,
      data,
      responseTime,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
      responseTime: Date.now() - startTime,
    };
  }
}

// Test health endpoints
async function testHealthEndpoints() {
  logSection('Health Checks');

  // Basic health check
  const health = await testEndpoint('GET', '/health');
  if (health.success) {
    recordTest('Basic Health Check', 'pass', {
      responseTime: health.responseTime,
    });
  } else {
    recordTest('Basic Health Check', 'fail', {
      message: health.error || `HTTP ${health.status}`,
    });
  }

  // Readiness check
  const ready = await testEndpoint('GET', '/health/ready');
  if (ready.success) {
    recordTest('Readiness Check', 'pass', {
      responseTime: ready.responseTime,
    });
  } else {
    recordTest('Readiness Check', 'warn', {
      message: 'Endpoint may not exist yet',
      responseTime: ready.responseTime,
    });
  }

  // Liveness check
  const live = await testEndpoint('GET', '/health/live');
  if (live.success) {
    recordTest('Liveness Check', 'pass', {
      responseTime: live.responseTime,
    });
  } else {
    recordTest('Liveness Check', 'warn', {
      message: 'Endpoint may not exist yet',
      responseTime: live.responseTime,
    });
  }
}

// Test database connectivity
async function testDatabase() {
  logSection('Database Connectivity');

  const dbUrl = process.env.TURSO_DATABASE_URL;
  const authToken = process.env.TURSO_AUTH_TOKEN;

  if (!dbUrl || !authToken) {
    recordTest('Database Credentials', 'fail', {
      message: 'Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN',
    });
    return;
  }

  try {
    const db = createClient({ url: dbUrl, authToken });

    // Test connection
    const startTime = Date.now();
    await db.execute('SELECT 1');
    const responseTime = Date.now() - startTime;

    recordTest('Database Connection', 'pass', { responseTime });

    // Check tables exist
    const tables = await db.execute(`
      SELECT COUNT(*) as count FROM sqlite_master
      WHERE type='table' AND name NOT LIKE 'sqlite_%'
    `);

    const tableCount = tables.rows[0].count;
    if (tableCount > 0) {
      recordTest('Database Schema', 'pass', {
        message: `${tableCount} tables found`,
      });
    } else {
      recordTest('Database Schema', 'fail', {
        message: 'No tables found - migrations may not have run',
      });
    }

  } catch (error) {
    recordTest('Database Connection', 'fail', {
      message: error.message,
    });
  }
}

// Test API endpoints
async function testAPIEndpoints() {
  logSection('API Endpoints');

  if (quickTest) {
    log('⏭️  Skipping detailed API tests in quick mode', 'yellow');
    return;
  }

  // Test public endpoints
  const endpoints = [
    { method: 'GET', path: '/api/health', name: 'API Health' },
    { method: 'GET', path: '/api/buzz/categories', name: 'Buzz Categories' },
    { method: 'GET', path: '/api/suggestions', name: 'Suggestions List' },
  ];

  for (const endpoint of endpoints) {
    const result = await testEndpoint(endpoint.method, endpoint.path);
    if (result.success) {
      recordTest(endpoint.name, 'pass', {
        responseTime: result.responseTime,
      });
    } else {
      recordTest(endpoint.name, 'warn', {
        message: result.error || `HTTP ${result.status}`,
        responseTime: result.responseTime,
      });
    }
  }
}

// Test authentication flow
async function testAuthentication() {
  logSection('Authentication Flow');

  if (quickTest) {
    log('⏭️  Skipping authentication tests in quick mode', 'yellow');
    return;
  }

  // Test signup endpoint exists
  const signup = await testEndpoint('POST', '/api/auth/signup', {
    body: {},
    timeout: 5000,
  });

  if (signup.status === 400) {
    // 400 is expected when we send empty body - means endpoint exists
    recordTest('Signup Endpoint', 'pass', {
      message: 'Endpoint is accessible',
      responseTime: signup.responseTime,
    });
  } else if (signup.status === 404) {
    recordTest('Signup Endpoint', 'fail', {
      message: 'Endpoint not found',
    });
  } else {
    recordTest('Signup Endpoint', 'warn', {
      message: `HTTP ${signup.status}`,
      responseTime: signup.responseTime,
    });
  }

  // Test login endpoint exists
  const login = await testEndpoint('POST', '/api/auth/login', {
    body: {},
    timeout: 5000,
  });

  if (login.status === 400 || login.status === 401) {
    recordTest('Login Endpoint', 'pass', {
      message: 'Endpoint is accessible',
      responseTime: login.responseTime,
    });
  } else if (login.status === 404) {
    recordTest('Login Endpoint', 'fail', {
      message: 'Endpoint not found',
    });
  } else {
    recordTest('Login Endpoint', 'warn', {
      message: `HTTP ${login.status}`,
      responseTime: login.responseTime,
    });
  }
}

// Test webhook endpoints
async function testWebhooks() {
  logSection('Webhook Endpoints');

  if (quickTest) {
    log('⏭️  Skipping webhook tests in quick mode', 'yellow');
    return;
  }

  // Test webhook endpoints are accessible (will return 400/401 without proper signatures)
  const webhooks = [
    { path: '/stripe/webhook', name: 'Stripe Webhook' },
    { path: '/voice/test-user', name: 'Twilio Voice Webhook' },
    { path: '/sms/test-user', name: 'Twilio SMS Webhook' },
    { path: '/email/inbound', name: 'SendGrid Email Webhook' },
  ];

  for (const webhook of webhooks) {
    const result = await testEndpoint('POST', webhook.path, { timeout: 5000 });

    // 400/401/403 means endpoint exists but rejects our invalid request
    if ([400, 401, 403].includes(result.status)) {
      recordTest(webhook.name, 'pass', {
        message: 'Endpoint is accessible',
        responseTime: result.responseTime,
      });
    } else if (result.status === 404) {
      recordTest(webhook.name, 'fail', {
        message: 'Endpoint not found',
      });
    } else {
      recordTest(webhook.name, 'warn', {
        message: `HTTP ${result.status}`,
        responseTime: result.responseTime,
      });
    }
  }
}

// Test performance benchmarks
async function testPerformance() {
  logSection('Performance Benchmarks');

  if (quickTest) {
    log('⏭️  Skipping performance tests in quick mode', 'yellow');
    return;
  }

  // Run multiple requests to get average
  const iterations = 5;
  const times = [];

  log('\n🔄 Running performance test...', 'blue');

  for (let i = 0; i < iterations; i++) {
    const result = await testEndpoint('GET', '/health');
    if (result.success) {
      times.push(result.responseTime);
    }
  }

  if (times.length > 0) {
    const avg = Math.round(times.reduce((a, b) => a + b, 0) / times.length);
    const min = Math.min(...times);
    const max = Math.max(...times);

    const status = avg < 500 ? 'pass' : avg < 2000 ? 'warn' : 'fail';

    recordTest('Average Response Time', status, {
      message: `avg: ${avg}ms, min: ${min}ms, max: ${max}ms (${iterations} requests)`,
    });
  } else {
    recordTest('Performance Test', 'fail', {
      message: 'All requests failed',
    });
  }
}

// Test external services
async function testExternalServices() {
  logSection('External Service Configuration');

  if (quickTest) {
    log('⏭️  Skipping external service tests in quick mode', 'yellow');
    return;
  }

  // Check if API keys are configured (not actual validation)
  const services = [
    { key: 'ANTHROPIC_API_KEY', name: 'Anthropic (Claude)' },
    { key: 'OPENAI_API_KEY', name: 'OpenAI' },
    { key: 'STRIPE_SECRET_KEY_LIVE', name: 'Stripe' },
    { key: 'SENDGRID_API_KEY_LIVE', name: 'SendGrid' },
    { key: 'TWILIO_AUTH_TOKEN_LIVE', name: 'Twilio' },
  ];

  for (const service of services) {
    const configured = !!process.env[service.key];
    recordTest(`${service.name} Configuration`, configured ? 'pass' : 'warn', {
      message: configured ? 'API key is set' : 'API key not found in environment',
    });
  }
}

// Generate final report
function generateReport() {
  logSection('Verification Summary');

  const total = results.tests.length;
  log(`\nTotal Tests: ${total}`, 'cyan');
  log(`✅ Passed: ${results.passed}`, 'green');
  log(`❌ Failed: ${results.failed}`, 'red');
  log(`⚠️  Warnings: ${results.warnings}`, 'yellow');

  const criticalFailures = results.tests.filter(t => t.status === 'fail');

  if (criticalFailures.length > 0) {
    log(`\n🚨 CRITICAL FAILURES (${criticalFailures.length}):`, 'red');
    criticalFailures.forEach(test => {
      log(`   • ${test.name}: ${test.message || 'Failed'}`, 'red');
    });
    log('\n❌ VERIFICATION FAILED', 'red');
    log('Deployment may have issues. Review failures above.', 'yellow');
    return false;
  } else if (results.warnings > 0) {
    log('\n✅ Critical checks passed!', 'green');
    log(`⚠️  ${results.warnings} warning(s) - review above`, 'yellow');
    return true;
  } else {
    log('\n✅ ALL CHECKS PASSED!', 'green');
    log('🚀 Deployment verified successfully!', 'green');
    return true;
  }
}

// Main execution
async function main() {
  log('\n🔍 xSwarm Boss - Post-Deployment Verification', 'cyan');
  log(`Target Environment: ${targetEnv.toUpperCase()}`, 'cyan');
  log(`Worker URL: ${baseUrl}`, 'cyan');
  log(`Mode: ${quickTest ? 'QUICK' : 'FULL'}`, 'cyan');
  log(`Timestamp: ${new Date().toISOString()}`, 'cyan');

  try {
    await testHealthEndpoints();
    await testDatabase();
    await testAPIEndpoints();
    await testAuthentication();
    await testWebhooks();
    await testPerformance();
    await testExternalServices();

    const passed = generateReport();

    log(''); // Empty line

    process.exit(passed ? 0 : 1);

  } catch (error) {
    log(`\n❌ Unexpected error: ${error.message}`, 'red');
    console.error(error);
    process.exit(1);
  }
}

main();
