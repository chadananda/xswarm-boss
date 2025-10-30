/**
 * Test Configuration
 * Environment and configuration for test suite
 */

import { config } from 'dotenv';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables
config({ path: join(__dirname, '../.env') });

/**
 * Test configuration object
 */
export const testConfig = {
  // API Configuration
  api: {
    baseUrl: process.env.TEST_API_URL || process.env.API_URL || 'http://localhost:8787',
    timeout: parseInt(process.env.TEST_API_TIMEOUT || '30000', 10),
  },

  // Database Configuration
  database: {
    url: process.env.TEST_DATABASE_URL || process.env.TURSO_DATABASE_URL,
    authToken: process.env.TEST_AUTH_TOKEN || process.env.TURSO_AUTH_TOKEN,
  },

  // Email Configuration (for testing email delivery)
  email: {
    sendgridApiKey: process.env.SENDGRID_API_KEY,
    testRecipient: process.env.TEST_EMAIL_RECIPIENT || 'test@example.com',
  },

  // Stripe Configuration (for testing payments)
  stripe: {
    secretKey: process.env.STRIPE_SECRET_KEY,
    webhookSecret: process.env.STRIPE_WEBHOOK_SECRET,
    testMode: process.env.STRIPE_TEST_MODE !== 'false',
  },

  // Test Data Configuration
  testData: {
    defaultPassword: 'TestPassword123!',
    testEmailDomain: '@test.xswarm.local',
  },

  // Performance Thresholds
  performance: {
    maxApiResponseTime: 1000, // ms
    maxDatabaseQueryTime: 100, // ms
    maxE2ETestTime: 5000, // ms
  },

  // Feature Flags
  features: {
    runIntegrationTests: process.env.RUN_INTEGRATION_TESTS !== 'false',
    runE2ETests: process.env.RUN_E2E_TESTS !== 'false',
    runPerformanceTests: process.env.RUN_PERFORMANCE_TESTS !== 'false',
    runSecurityTests: process.env.RUN_SECURITY_TESTS !== 'false',
  },
};

/**
 * Validate test configuration
 */
export function validateConfig() {
  const errors = [];

  if (!testConfig.database.url) {
    errors.push('Database URL not configured (TEST_DATABASE_URL or TURSO_DATABASE_URL)');
  }

  if (!testConfig.api.baseUrl) {
    errors.push('API base URL not configured (TEST_API_URL or API_URL)');
  }

  if (errors.length > 0) {
    throw new Error(`Test configuration errors:\n${errors.join('\n')}`);
  }
}

/**
 * Get test user credentials for different tiers
 */
export function getTestCredentials(tier = 'free') {
  const timestamp = Date.now();
  const random = Math.random().toString(36).slice(2, 8);

  return {
    email: `test-${tier}-${timestamp}-${random}${testConfig.testData.testEmailDomain}`,
    name: `Test ${tier} User`,
    password: testConfig.testData.defaultPassword,
    subscription_tier: tier,
  };
}

export default testConfig;
