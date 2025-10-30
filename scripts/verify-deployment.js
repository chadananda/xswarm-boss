#!/usr/bin/env node
/**
 * Boss AI - Deployment Verification
 *
 * Tests the deployed Worker to ensure everything is working correctly.
 */

import { readFileSync } from 'fs';

// Colors
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logSection(title) {
  console.log('');
  log('='.repeat(80), 'cyan');
  log(title, 'cyan');
  log('='.repeat(80), 'cyan');
  console.log('');
}

async function testEndpoint(url, description) {
  try {
    const response = await fetch(url);
    const data = await response.json();

    if (response.ok) {
      log(`  ✅ ${description}`, 'green');
      return { success: true, data };
    } else {
      log(`  ❌ ${description} - HTTP ${response.status}`, 'red');
      return { success: false, status: response.status };
    }
  } catch (error) {
    log(`  ❌ ${description} - ${error.message}`, 'red');
    return { success: false, error: error.message };
  }
}

async function main() {
  log('\n🔍 Boss AI - Deployment Verification', 'cyan');
  log('Testing deployed Worker endpoints...\n', 'cyan');

  // Get Worker URL from command line or use default
  const workerUrl = process.argv[2] || process.env.WORKER_URL;

  if (!workerUrl) {
    log('❌ Error: No Worker URL provided', 'red');
    log('Usage: node scripts/verify-deployment.js <worker-url>', 'yellow');
    log('Example: node scripts/verify-deployment.js https://boss-ai.your-subdomain.workers.dev', 'yellow');
    process.exit(1);
  }

  log(`🌐 Testing: ${workerUrl}`, 'blue');

  const tests = [
    {
      url: `${workerUrl}/health`,
      description: 'Health check endpoint',
    },
    {
      url: `${workerUrl}/`,
      description: 'Root endpoint',
    },
  ];

  let passed = 0;
  let failed = 0;

  logSection('Running Tests');

  for (const test of tests) {
    const result = await testEndpoint(test.url, test.description);
    if (result.success) {
      passed++;
      if (result.data) {
        log(`    Response: ${JSON.stringify(result.data).slice(0, 100)}...`, 'cyan');
      }
    } else {
      failed++;
    }
    console.log('');
  }

  logSection('Test Results');

  log(`✅ Passed: ${passed}`, 'green');
  log(`❌ Failed: ${failed}`, failed > 0 ? 'red' : 'green');
  console.log('');

  if (failed === 0) {
    log('🎉 All tests passed! Your deployment is working correctly.', 'green');
    log('', 'reset');
    log('Next steps:', 'yellow');
    log('  1. Send a test SMS to your Twilio number', 'cyan');
    log('  2. Send a test email to your inbound address', 'cyan');
    log('  3. Run the Rust CLI: cargo run -- "Hello Boss"', 'cyan');
    log('  4. Check logs: wrangler tail', 'cyan');
    log('', 'reset');
  } else {
    log('⚠️  Some tests failed. Please check the errors above.', 'yellow');
    log('', 'reset');
    log('Troubleshooting:', 'yellow');
    log('  1. Check if the Worker is deployed: wrangler deployments list', 'cyan');
    log('  2. Check Worker logs: wrangler tail', 'cyan');
    log('  3. Verify secrets are set: wrangler secret list', 'cyan');
    log('  4. Re-run deployment: pnpm run deploy', 'cyan');
    log('', 'reset');
    process.exit(1);
  }
}

main().catch((error) => {
  log(`\n❌ Unexpected error: ${error.message}`, 'red');
  process.exit(1);
});
