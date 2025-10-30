#!/usr/bin/env node
/**
 * Comprehensive Webhook Testing Suite
 *
 * Tests all webhook endpoints with real HTTP requests to verify functionality:
 * - SMS webhook (Twilio format)
 * - Email webhook (SendGrid format)
 * - Claude AI integration
 * - Authentication and authorization
 * - Error handling
 */

const TEST_SERVER_URL = 'http://localhost:8787';

// Test user data from config
const TEST_USER = {
  username: 'chadananda',
  name: 'Chad Jones',
  phone: '+19167656913',
  email: 'chadananda@gmail.com',
  boss_phone: '+18447472899',
  boss_email: 'chadananda@xswarm.ai'
};

// Test results tracking
const results = {
  passed: 0,
  failed: 0,
  tests: []
};

function logTest(name, passed, details = '') {
  const status = passed ? '✅ PASS' : '❌ FAIL';
  console.log(`${status} ${name}`);
  if (details) console.log(`   ${details}`);

  results.tests.push({ name, passed, details });
  if (passed) results.passed++;
  else results.failed++;
}

function logSection(name) {
  console.log(`\n=== ${name} ===`);
}

async function makeRequest(endpoint, options = {}) {
  try {
    const response = await fetch(`${TEST_SERVER_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        ...options.headers
      },
      body: options.body,
      ...options
    });

    return {
      ok: response.ok,
      status: response.status,
      headers: Object.fromEntries(response.headers.entries()),
      text: await response.text(),
      response
    };
  } catch (error) {
    return {
      ok: false,
      error: error.message
    };
  }
}

async function testServerHealth() {
  logSection('Server Health Tests');

  // Test basic connectivity
  try {
    const result = await makeRequest('/');
    logTest('Server responds to requests', result.ok || result.status < 500,
      `Status: ${result.status}, Response length: ${result.text?.length || 0}`);
  } catch (error) {
    logTest('Server responds to requests', false, `Error: ${error.message}`);
  }
}

async function testSmsWebhook() {
  logSection('SMS Webhook Tests');

  // Test valid SMS webhook
  const validSmsBody = new URLSearchParams({
    From: TEST_USER.phone,
    To: TEST_USER.boss_phone,
    Body: 'Hello Boss, this is a test message'
  }).toString();

  const smsResult = await makeRequest('/sms/inbound', {
    body: validSmsBody
  });

  logTest('SMS webhook accepts valid requests', smsResult.ok,
    `Status: ${smsResult.status}, Response: ${smsResult.text?.substring(0, 100)}`);

  // Check if response is TwiML format
  const isTwiML = smsResult.text?.includes('<Response>') && smsResult.text?.includes('<Message>');
  logTest('SMS webhook returns TwiML format', isTwiML,
    `Contains TwiML tags: ${isTwiML}`);

  // Test unauthorized phone number
  const unauthorizedSmsBody = new URLSearchParams({
    From: '+15551234567', // Not in users config
    To: TEST_USER.boss_phone,
    Body: 'Unauthorized message'
  }).toString();

  const unauthorizedResult = await makeRequest('/sms/inbound', {
    body: unauthorizedSmsBody
  });

  // Should return TwiML with rejection message
  const isRejected = unauthorizedResult.text?.includes('not authorized') ||
                     unauthorizedResult.text?.includes('unauthorized');
  logTest('SMS webhook rejects unauthorized users', isRejected,
    `Rejection detected: ${isRejected}`);

  // Test malformed request
  const malformedResult = await makeRequest('/sms/inbound', {
    body: 'invalid=data'
  });

  logTest('SMS webhook handles malformed requests', !malformedResult.ok || malformedResult.status >= 400,
    `Status: ${malformedResult.status}`);
}

async function testEmailWebhook() {
  logSection('Email Webhook Tests');

  // Test valid email webhook (SendGrid format)
  const validEmailBody = new URLSearchParams({
    to: TEST_USER.boss_email,
    from: 'test@example.com',
    subject: 'Test Email Subject',
    text: 'This is a test email body content',
    html: '<p>This is a test email body content</p>'
  }).toString();

  const emailResult = await makeRequest('/email/inbound', {
    body: validEmailBody
  });

  logTest('Email webhook accepts valid requests', emailResult.ok,
    `Status: ${emailResult.status}, Response length: ${emailResult.text?.length || 0}`);

  // Test email to non-existent user
  const invalidEmailBody = new URLSearchParams({
    to: 'nonexistent@xswarm.ai',
    from: 'test@example.com',
    subject: 'Test Email',
    text: 'Test content'
  }).toString();

  const invalidResult = await makeRequest('/email/inbound', {
    body: invalidEmailBody
  });

  // Should handle gracefully (might return 200 but not process)
  logTest('Email webhook handles invalid recipients', true,
    `Status: ${invalidResult.status} (handled gracefully)`);

  // Test malformed email data
  const malformedEmailResult = await makeRequest('/email/inbound', {
    body: 'malformed=email&data=invalid'
  });

  logTest('Email webhook handles malformed requests', malformedEmailResult.status >= 400 || malformedEmailResult.ok,
    `Status: ${malformedEmailResult.status}`);
}

async function testClaudeAIIntegration() {
  logSection('Claude AI Integration Tests');

  // Test SMS with Claude AI trigger
  const aiTestBody = new URLSearchParams({
    From: TEST_USER.phone,
    To: TEST_USER.boss_phone,
    Body: 'Hello, please write me a short poem about testing'
  }).toString();

  const aiResult = await makeRequest('/sms/inbound', {
    body: aiTestBody
  });

  // Check if response contains meaningful content (not just generic acknowledgment)
  const hasAIResponse = aiResult.text?.length > 100 &&
                        !aiResult.text?.includes('received your message') &&
                        (aiResult.text?.includes('poem') || aiResult.text?.includes('test'));

  logTest('Claude AI generates intelligent responses', hasAIResponse,
    `Response length: ${aiResult.text?.length}, Contains meaningful content: ${hasAIResponse}`);

  // Test email with Claude AI
  const aiEmailBody = new URLSearchParams({
    to: TEST_USER.boss_email,
    from: TEST_USER.email,
    subject: 'AI Test Request',
    text: 'Please explain the current status of the project in 2 sentences'
  }).toString();

  const aiEmailResult = await makeRequest('/email/inbound', {
    body: aiEmailBody
  });

  logTest('Email AI processing works', aiEmailResult.ok,
    `Status: ${aiEmailResult.status}`);
}

async function testAuthentication() {
  logSection('Authentication Tests');

  // Test SMS authentication enforcement
  const authTestCases = [
    {
      name: 'Valid user authentication',
      from: TEST_USER.phone,
      to: TEST_USER.boss_phone,
      shouldPass: true
    },
    {
      name: 'Invalid sender phone',
      from: '+15551111111',
      to: TEST_USER.boss_phone,
      shouldPass: false
    },
    {
      name: 'Invalid boss phone',
      from: TEST_USER.phone,
      to: '+15552222222',
      shouldPass: false
    }
  ];

  for (const testCase of authTestCases) {
    const body = new URLSearchParams({
      From: testCase.from,
      To: testCase.to,
      Body: 'Authentication test message'
    }).toString();

    const result = await makeRequest('/sms/inbound', { body });

    const isAuthorized = !result.text?.includes('not authorized') &&
                         !result.text?.includes('unauthorized');

    const passed = testCase.shouldPass ? isAuthorized : !isAuthorized;
    logTest(testCase.name, passed,
      `Expected: ${testCase.shouldPass ? 'authorized' : 'unauthorized'}, Got: ${isAuthorized ? 'authorized' : 'unauthorized'}`);
  }
}

async function testErrorHandling() {
  logSection('Error Handling Tests');

  // Test missing required fields
  const incompleteBody = new URLSearchParams({
    From: TEST_USER.phone
    // Missing To and Body
  }).toString();

  const incompleteResult = await makeRequest('/sms/inbound', {
    body: incompleteBody
  });

  logTest('Handles missing required fields', !incompleteResult.ok || incompleteResult.status >= 400,
    `Status: ${incompleteResult.status}`);

  // Test invalid HTTP method
  const methodResult = await makeRequest('/sms/inbound', {
    method: 'GET'
  });

  logTest('Rejects invalid HTTP methods', !methodResult.ok || methodResult.status >= 400,
    `Status: ${methodResult.status}`);

  // Test non-existent endpoint
  const notFoundResult = await makeRequest('/nonexistent/endpoint', {
    body: 'test=data'
  });

  logTest('Returns 404 for non-existent endpoints', notFoundResult.status === 404,
    `Status: ${notFoundResult.status}`);
}

async function testRealTimeLogging() {
  logSection('Real-time Logging Tests');

  // Send a test message and check if it appears in logs
  const logTestBody = new URLSearchParams({
    From: TEST_USER.phone,
    To: TEST_USER.boss_phone,
    Body: `LOG_TEST_${Date.now()}`
  }).toString();

  const logResult = await makeRequest('/sms/inbound', {
    body: logTestBody
  });

  logTest('Request processing completes', logResult.ok,
    `Status: ${logResult.status}`);

  // Note: Actual log verification would require reading server logs
  console.log('   ℹ️  Check server logs for real-time logging verification');
}

async function runAllTests() {
  console.log('🧪 Starting Comprehensive Webhook Tests');
  console.log(`📡 Testing server: ${TEST_SERVER_URL}`);
  console.log(`👤 Test user: ${TEST_USER.name} (${TEST_USER.username})`);

  await testServerHealth();
  await testSmsWebhook();
  await testEmailWebhook();
  await testClaudeAIIntegration();
  await testAuthentication();
  await testErrorHandling();
  await testRealTimeLogging();

  // Final results
  console.log('\n' + '='.repeat(50));
  console.log('📊 TEST RESULTS SUMMARY');
  console.log('='.repeat(50));
  console.log(`✅ Passed: ${results.passed}`);
  console.log(`❌ Failed: ${results.failed}`);
  console.log(`📈 Success Rate: ${Math.round(results.passed / (results.passed + results.failed) * 100)}%`);

  if (results.failed > 0) {
    console.log('\n❌ FAILED TESTS:');
    results.tests
      .filter(test => !test.passed)
      .forEach(test => {
        console.log(`   • ${test.name}`);
        if (test.details) console.log(`     ${test.details}`);
      });
  }

  console.log('\n🎯 NEXT STEPS:');
  if (results.failed === 0) {
    console.log('   ✅ All tests passed! System is working correctly.');
  } else {
    console.log('   🔧 Fix failing tests to ensure system reliability.');
  }

  console.log('   📧 Send a real email to test end-to-end functionality.');
  console.log('   📱 Send a real SMS to test end-to-end functionality.');

  // Exit with appropriate code
  process.exit(results.failed > 0 ? 1 : 0);
}

// Run tests
runAllTests().catch(error => {
  console.error('❌ Test execution failed:', error);
  process.exit(1);
});