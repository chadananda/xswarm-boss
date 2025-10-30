#!/usr/bin/env node
/**
 * xSwarm Boss - Pre-Deployment Verification Script
 *
 * Comprehensive checks before deploying to production:
 * - Environment variables validation
 * - Database connectivity and schema
 * - API credentials verification
 * - Cloudflare Workers configuration
 * - R2 bucket accessibility
 * - Webhook endpoints
 * - DNS and SSL configuration
 *
 * Usage: node deployment/scripts/pre-deploy-check.js [--env=production|staging]
 */

import { config } from 'dotenv';
import { createClient } from '@libsql/client';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import Stripe from 'stripe';

// Load environment variables
config();

// Parse command line arguments
const args = process.argv.slice(2);
const envArg = args.find(arg => arg.startsWith('--env='));
const targetEnv = envArg ? envArg.split('=')[1] : 'production';

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

function logCheck(name, status, details = '') {
  const symbol = status === 'pass' ? '✅' : status === 'fail' ? '❌' : '⚠️';
  const color = status === 'pass' ? 'green' : status === 'fail' ? 'red' : 'yellow';
  log(`${symbol} ${name}`, color);
  if (details) {
    log(`   ${details}`, 'reset');
  }
}

// Track overall results
const results = {
  passed: 0,
  failed: 0,
  warnings: 0,
  checks: [],
};

function recordCheck(name, status, details = '', critical = true) {
  results.checks.push({ name, status, details, critical });
  if (status === 'pass') results.passed++;
  else if (status === 'fail') results.failed++;
  else results.warnings++;

  logCheck(name, status, details);
}

// Required environment variables by category
const requiredEnvVars = {
  ai: {
    ANTHROPIC_API_KEY: 'Claude AI API key',
    OPENAI_API_KEY: 'OpenAI API key for embeddings',
  },
  database: {
    TURSO_DATABASE_URL: 'Turso database URL',
    TURSO_AUTH_TOKEN: 'Turso authentication token',
  },
  twilio: {
    TWILIO_AUTH_TOKEN_LIVE: 'Twilio authentication token (live)',
  },
  sendgrid: {
    SENDGRID_API_KEY_LIVE: 'SendGrid API key (live)',
  },
  stripe: {
    STRIPE_SECRET_KEY_LIVE: 'Stripe secret key (live)',
    STRIPE_WEBHOOK_SECRET_LIVE: 'Stripe webhook secret (live)',
  },
  cloudflare: {
    CLOUDFLARE_API_TOKEN: 'Cloudflare API token',
    S3_ACCESS_KEY_ID: 'R2 access key ID',
    S3_SECRET_ACCESS_KEY: 'R2 secret access key',
  },
  auth: {
    JWT_SECRET: 'JWT signing secret',
  },
};

// Check environment variables
async function checkEnvironmentVariables() {
  logSection('Environment Variables Check');

  for (const [category, vars] of Object.entries(requiredEnvVars)) {
    log(`\n${category.toUpperCase()}:`, 'blue');

    for (const [key, description] of Object.entries(vars)) {
      const value = process.env[key];

      if (!value) {
        recordCheck(
          `${key}`,
          'fail',
          `Missing: ${description}`,
          true
        );
      } else if (value.includes('xxxxx') || value.includes('your_')) {
        recordCheck(
          `${key}`,
          'fail',
          'Contains placeholder value - not configured',
          true
        );
      } else {
        // Validate format based on key type
        let valid = true;
        let reason = '';

        if (key.includes('ANTHROPIC')) {
          valid = value.startsWith('sk-ant-');
          reason = valid ? '' : 'Should start with sk-ant-';
        } else if (key.includes('OPENAI')) {
          valid = value.startsWith('sk-');
          reason = valid ? '' : 'Should start with sk-';
        } else if (key.includes('STRIPE_SECRET')) {
          valid = value.startsWith('sk_live_') || value.startsWith('sk_test_');
          reason = valid ? '' : 'Should start with sk_live_ or sk_test_';
        } else if (key.includes('TURSO_DATABASE_URL')) {
          valid = value.startsWith('libsql://');
          reason = valid ? '' : 'Should start with libsql://';
        } else if (key.includes('JWT_SECRET')) {
          valid = value.length >= 32;
          reason = valid ? '' : 'Should be at least 32 characters';
        }

        recordCheck(
          `${key}`,
          valid ? 'pass' : 'fail',
          reason || `Length: ${value.length} chars`,
          true
        );
      }
    }
  }
}

// Check database connectivity and schema
async function checkDatabase() {
  logSection('Database Connectivity & Schema Check');

  const dbUrl = process.env.TURSO_DATABASE_URL;
  const authToken = process.env.TURSO_AUTH_TOKEN;

  if (!dbUrl || !authToken) {
    recordCheck('Database Connection', 'fail', 'Missing credentials', true);
    return;
  }

  try {
    const db = createClient({ url: dbUrl, authToken });

    // Test connection
    await db.execute('SELECT 1');
    recordCheck('Database Connection', 'pass', `Connected to ${dbUrl.split('@')[1]}`);

    // Check for required tables
    const tables = await db.execute(`
      SELECT name FROM sqlite_master
      WHERE type='table' AND name NOT LIKE 'sqlite_%'
      ORDER BY name
    `);

    const tableNames = tables.rows.map(r => r.name);
    const requiredTables = [
      'users',
      'teams',
      'team_members',
      'projects',
      'tasks',
      'messages',
      'buzz_listings',
      'suggestions',
      'email_campaigns',
      'scheduled_tasks',
    ];

    const missingTables = requiredTables.filter(t => !tableNames.includes(t));

    if (missingTables.length === 0) {
      recordCheck('Database Schema', 'pass', `All ${requiredTables.length} required tables exist`);
    } else {
      recordCheck(
        'Database Schema',
        'fail',
        `Missing tables: ${missingTables.join(', ')}`,
        true
      );
    }

    // Check migrations table
    try {
      const migrations = await db.execute('SELECT COUNT(*) as count FROM _migrations');
      recordCheck(
        'Migration Tracking',
        'pass',
        `${migrations.rows[0].count} migrations applied`
      );
    } catch (error) {
      recordCheck(
        'Migration Tracking',
        'warn',
        'Migrations table not found - run migrate-all.js',
        false
      );
    }

  } catch (error) {
    recordCheck('Database Connection', 'fail', error.message, true);
  }
}

// Check API credentials by making test calls
async function checkAPICredentials() {
  logSection('API Credentials Verification');

  // Check Anthropic API
  if (process.env.ANTHROPIC_API_KEY) {
    try {
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'x-api-key': process.env.ANTHROPIC_API_KEY,
          'anthropic-version': '2023-06-01',
          'content-type': 'application/json',
        },
        body: JSON.stringify({
          model: 'claude-3-5-sonnet-20241022',
          max_tokens: 10,
          messages: [{ role: 'user', content: 'test' }],
        }),
      });

      if (response.ok || response.status === 400) {
        recordCheck('Anthropic API', 'pass', 'API key is valid');
      } else {
        const error = await response.text();
        recordCheck('Anthropic API', 'fail', `Invalid API key: ${response.status}`, true);
      }
    } catch (error) {
      recordCheck('Anthropic API', 'fail', error.message, true);
    }
  }

  // Check OpenAI API
  if (process.env.OPENAI_API_KEY) {
    try {
      const response = await fetch('https://api.openai.com/v1/models', {
        headers: {
          'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
        },
      });

      if (response.ok) {
        recordCheck('OpenAI API', 'pass', 'API key is valid');
      } else {
        recordCheck('OpenAI API', 'fail', `Invalid API key: ${response.status}`, true);
      }
    } catch (error) {
      recordCheck('OpenAI API', 'fail', error.message, true);
    }
  }

  // Check Stripe API
  if (process.env.STRIPE_SECRET_KEY_LIVE) {
    try {
      const stripe = new Stripe(process.env.STRIPE_SECRET_KEY_LIVE);
      const account = await stripe.balance.retrieve();
      recordCheck('Stripe API', 'pass', 'API key is valid');
    } catch (error) {
      recordCheck('Stripe API', 'fail', error.message, true);
    }
  }

  // Check SendGrid API
  if (process.env.SENDGRID_API_KEY_LIVE) {
    try {
      const response = await fetch('https://api.sendgrid.com/v3/user/profile', {
        headers: {
          'Authorization': `Bearer ${process.env.SENDGRID_API_KEY_LIVE}`,
        },
      });

      if (response.ok) {
        recordCheck('SendGrid API', 'pass', 'API key is valid');
      } else {
        recordCheck('SendGrid API', 'fail', `Invalid API key: ${response.status}`, true);
      }
    } catch (error) {
      recordCheck('SendGrid API', 'fail', error.message, true);
    }
  }

  // Check Twilio API
  if (process.env.TWILIO_AUTH_TOKEN_LIVE) {
    const accountSid = process.env.TWILIO_ACCOUNT_SID || '***REMOVED***';
    const authToken = process.env.TWILIO_AUTH_TOKEN_LIVE;
    const auth = Buffer.from(`${accountSid}:${authToken}`).toString('base64');

    try {
      const response = await fetch(`https://api.twilio.com/2010-04-01/Accounts/${accountSid}.json`, {
        headers: {
          'Authorization': `Basic ${auth}`,
        },
      });

      if (response.ok) {
        recordCheck('Twilio API', 'pass', 'Auth token is valid');
      } else {
        recordCheck('Twilio API', 'fail', `Invalid auth token: ${response.status}`, true);
      }
    } catch (error) {
      recordCheck('Twilio API', 'fail', error.message, true);
    }
  }
}

// Check Cloudflare Workers configuration
async function checkCloudflareConfig() {
  logSection('Cloudflare Workers Configuration');

  // Check wrangler.toml exists
  const wranglerPath = resolve(process.cwd(), 'wrangler.toml');
  try {
    const wranglerContent = readFileSync(wranglerPath, 'utf-8');
    recordCheck('wrangler.toml', 'pass', 'Configuration file exists');

    // Check account_id is set
    if (wranglerContent.includes('account_id')) {
      const match = wranglerContent.match(/account_id\s*=\s*"([^"]+)"/);
      if (match && match[1] && !match[1].includes('YOUR')) {
        recordCheck('Cloudflare Account ID', 'pass', `ID: ${match[1].substring(0, 8)}...`);
      } else {
        recordCheck('Cloudflare Account ID', 'fail', 'Not configured in wrangler.toml', true);
      }
    } else {
      recordCheck('Cloudflare Account ID', 'fail', 'Missing in wrangler.toml', true);
    }

    // Check R2 bucket configuration
    if (wranglerContent.includes('r2_buckets')) {
      recordCheck('R2 Bucket Config', 'pass', 'R2 buckets configured');
    } else {
      recordCheck('R2 Bucket Config', 'fail', 'R2 buckets not configured', true);
    }

  } catch (error) {
    recordCheck('wrangler.toml', 'fail', 'File not found or not readable', true);
  }

  // Check Cloudflare API token
  if (process.env.CLOUDFLARE_API_TOKEN) {
    try {
      const response = await fetch('https://api.cloudflare.com/client/v4/user/tokens/verify', {
        headers: {
          'Authorization': `Bearer ${process.env.CLOUDFLARE_API_TOKEN}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        recordCheck('Cloudflare API Token', 'pass', 'Token is valid');
      } else {
        recordCheck('Cloudflare API Token', 'fail', 'Invalid token', true);
      }
    } catch (error) {
      recordCheck('Cloudflare API Token', 'fail', error.message, true);
    }
  }
}

// Check webhook configurations
async function checkWebhooks() {
  logSection('Webhook Configuration');

  // Check if webhook secrets are set
  const webhooks = {
    'Stripe Webhook Secret': process.env.STRIPE_WEBHOOK_SECRET_LIVE,
    'Twilio Phone Number': process.env.TWILIO_PHONE_NUMBER,
    'SendGrid From Email': process.env.SENDGRID_FROM_EMAIL || process.env.FROM_EMAIL,
  };

  for (const [name, value] of Object.entries(webhooks)) {
    if (!value) {
      recordCheck(name, 'fail', 'Not configured', true);
    } else if (value.includes('your_') || value.includes('xxxxx')) {
      recordCheck(name, 'fail', 'Placeholder value - not configured', true);
    } else {
      recordCheck(name, 'pass', `Configured: ${value.substring(0, 20)}...`);
    }
  }
}

// Check DNS and domain configuration
async function checkDNSConfig() {
  logSection('DNS & Domain Configuration');

  const domains = [
    'xswarm.ai',
    'boss.xswarm.ai',
  ];

  for (const domain of domains) {
    try {
      const response = await fetch(`https://${domain}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      });

      if (response.ok) {
        recordCheck(`${domain}`, 'pass', 'Domain is accessible');
      } else {
        recordCheck(`${domain}`, 'warn', `Returns ${response.status}`, false);
      }
    } catch (error) {
      recordCheck(`${domain}`, 'warn', 'Not accessible or no health endpoint', false);
    }
  }
}

// Generate final report
function generateReport() {
  logSection('Pre-Deployment Check Summary');

  log(`\nTotal Checks: ${results.checks.length}`, 'cyan');
  log(`✅ Passed: ${results.passed}`, 'green');
  log(`❌ Failed: ${results.failed}`, 'red');
  log(`⚠️  Warnings: ${results.warnings}`, 'yellow');

  const criticalFailures = results.checks.filter(c => c.status === 'fail' && c.critical);

  if (criticalFailures.length > 0) {
    log(`\n🚨 CRITICAL FAILURES (${criticalFailures.length}):`, 'red');
    criticalFailures.forEach(check => {
      log(`   • ${check.name}: ${check.details}`, 'red');
    });
    log('\n❌ DEPLOYMENT BLOCKED', 'red');
    log('Fix critical failures before deploying to production.', 'yellow');
    return false;
  } else if (results.failed > 0) {
    log('\n⚠️  Some non-critical checks failed', 'yellow');
    log('Review failures before deploying to production.', 'yellow');
    return false;
  } else if (results.warnings > 0) {
    log('\n✅ All critical checks passed!', 'green');
    log('⚠️  Some warnings present - review before deployment', 'yellow');
    return true;
  } else {
    log('\n✅ ALL CHECKS PASSED!', 'green');
    log('🚀 Ready for production deployment!', 'green');
    return true;
  }
}

// Main execution
async function main() {
  log('\n🔍 xSwarm Boss - Pre-Deployment Verification', 'cyan');
  log(`Target Environment: ${targetEnv.toUpperCase()}`, 'cyan');
  log(`Timestamp: ${new Date().toISOString()}`, 'cyan');

  try {
    await checkEnvironmentVariables();
    await checkDatabase();
    await checkAPICredentials();
    await checkCloudflareConfig();
    await checkWebhooks();
    await checkDNSConfig();

    const passed = generateReport();

    log(''); // Empty line

    if (!passed) {
      process.exit(1);
    }

  } catch (error) {
    log(`\n❌ Unexpected error: ${error.message}`, 'red');
    console.error(error);
    process.exit(1);
  }
}

main();
