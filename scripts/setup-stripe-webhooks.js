#!/usr/bin/env node

/**
 * Automated Stripe Webhook Setup
 *
 * Creates webhook endpoints in Stripe (test + live modes) and pushes
 * the signing secrets to Cloudflare Workers.
 *
 * Usage:
 *   pnpm setup:webhooks --url https://your-worker.workers.dev
 *   pnpm setup:webhooks  (auto-detects from wrangler)
 *
 * Requirements:
 *   - STRIPE_SECRET_KEY_TEST in .env
 *   - STRIPE_SECRET_KEY_LIVE in .env (for production)
 *   - CLOUDFLARE_API_TOKEN in .env (for pushing secrets)
 *   - wrangler CLI installed
 */

import 'dotenv/config';
import { execSync } from 'child_process';
import { existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '..');
const serverDir = join(rootDir, 'packages', 'server');

// Parse command line arguments
const args = process.argv.slice(2);
const urlArg = args.find(arg => arg.startsWith('--url='));
const testOnly = args.includes('--test-only');

// Events to subscribe to
const WEBHOOK_EVENTS = [
  'customer.subscription.created',
  'customer.subscription.updated',
  'customer.subscription.deleted',
  'invoice.payment_succeeded',
  'invoice.payment_failed',
  'customer.created',
  'customer.updated',
];

console.log('🔗 Stripe Webhook Automation\n');

// Get Worker URL
let workerUrl;
if (urlArg) {
  workerUrl = urlArg.replace('--url=', '');
} else {
  console.log('📡 Detecting Worker URL from wrangler...');
  try {
    // Get worker subdomain from wrangler.toml
    const wranglerOutput = execSync('wrangler whoami', {
      cwd: serverDir,
      encoding: 'utf-8',
    });

    // Extract account subdomain (or use default pattern)
    // This is a simplified version - might need adjustment based on wrangler output
    const accountMatch = wranglerOutput.match(/Account ID: (\w+)/);
    if (accountMatch) {
      workerUrl = `https://xswarm-server.${accountMatch[1]}.workers.dev`;
      console.log(`  Detected: ${workerUrl}`);
    } else {
      console.error('❌ Could not detect Worker URL from wrangler');
      console.error('   Please provide URL manually: pnpm setup:webhooks --url https://your-worker.workers.dev');
      process.exit(1);
    }
  } catch (error) {
    console.error('❌ Failed to detect Worker URL:', error.message);
    console.error('   Please provide URL manually: pnpm setup:webhooks --url https://your-worker.workers.dev');
    process.exit(1);
  }
}

const webhookUrl = `${workerUrl}/stripe/webhook`;
console.log(`\n🎯 Webhook endpoint: ${webhookUrl}\n`);

/**
 * Create or update webhook endpoint in Stripe
 */
async function setupWebhook(mode, apiKey) {
  console.log(`\n📝 Setting up ${mode} mode webhook...`);

  try {
    // Check if webhook already exists
    const listResponse = await fetch('https://api.stripe.com/v1/webhook_endpoints', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
      },
    });

    if (!listResponse.ok) {
      throw new Error(`Failed to list webhooks: ${listResponse.statusText}`);
    }

    const { data: existingWebhooks } = await listResponse.json();
    const existingWebhook = existingWebhooks.find(wh => wh.url === webhookUrl);

    let webhookId;
    let secret;

    if (existingWebhook) {
      console.log('  ℹ️  Webhook already exists, updating...');
      webhookId = existingWebhook.id;

      // Update existing webhook
      const updateParams = new URLSearchParams();
      WEBHOOK_EVENTS.forEach(event => {
        updateParams.append('enabled_events[]', event);
      });

      const updateResponse = await fetch(`https://api.stripe.com/v1/webhook_endpoints/${webhookId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: updateParams.toString(),
      });

      if (!updateResponse.ok) {
        throw new Error(`Failed to update webhook: ${updateResponse.statusText}`);
      }

      const webhook = await updateResponse.json();
      secret = webhook.secret;
      console.log('  ✓ Webhook updated successfully');

    } else {
      console.log('  Creating new webhook...');

      // Create new webhook
      const createParams = new URLSearchParams();
      createParams.append('url', webhookUrl);
      WEBHOOK_EVENTS.forEach(event => {
        createParams.append('enabled_events[]', event);
      });

      const createResponse = await fetch('https://api.stripe.com/v1/webhook_endpoints', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: createParams.toString(),
      });

      if (!createResponse.ok) {
        const errorText = await createResponse.text();
        throw new Error(`Failed to create webhook: ${createResponse.statusText}\n${errorText}`);
      }

      const webhook = await createResponse.json();
      webhookId = webhook.id;
      secret = webhook.secret;
      console.log('  ✓ Webhook created successfully');
    }

    console.log(`  ID: ${webhookId}`);
    console.log(`  Secret: ${secret.substring(0, 20)}...`);

    return { id: webhookId, secret };

  } catch (error) {
    console.error(`  ✗ Failed to setup ${mode} webhook:`, error.message);
    throw error;
  }
}

/**
 * Push webhook secret to Cloudflare Workers
 */
function pushSecretToWorker(secretName, secretValue) {
  console.log(`\n📤 Pushing ${secretName} to Cloudflare Workers...`);

  try {
    execSync(
      `echo "${secretValue}" | wrangler secret put ${secretName}`,
      {
        cwd: serverDir,
        stdio: 'pipe',
      }
    );
    console.log(`  ✓ ${secretName} pushed successfully`);
    return true;
  } catch (error) {
    console.error(`  ✗ Failed to push ${secretName}:`, error.message);
    return false;
  }
}

// Main execution
async function main() {
  // Validate environment
  if (!existsSync(join(rootDir, '.env'))) {
    console.error('❌ .env file not found in project root');
    process.exit(1);
  }

  if (!existsSync(serverDir)) {
    console.error('❌ packages/server directory not found');
    process.exit(1);
  }

  const testKey = process.env.STRIPE_SECRET_KEY_TEST;
  const liveKey = process.env.STRIPE_SECRET_KEY_LIVE;

  if (!testKey) {
    console.error('❌ STRIPE_SECRET_KEY_TEST not found in .env');
    process.exit(1);
  }

  const results = {
    test: null,
    live: null,
  };

  // Setup test mode webhook
  try {
    results.test = await setupWebhook('test', testKey);
    pushSecretToWorker('STRIPE_WEBHOOK_SECRET_TEST', results.test.secret);
  } catch (error) {
    console.error('\n❌ Test webhook setup failed');
    process.exit(1);
  }

  // Setup live mode webhook (if not test-only and key exists)
  if (!testOnly && liveKey) {
    try {
      results.live = await setupWebhook('live', liveKey);
      pushSecretToWorker('STRIPE_WEBHOOK_SECRET_LIVE', results.live.secret);
    } catch (error) {
      console.error('\n⚠️  Live webhook setup failed (continuing anyway)');
    }
  } else if (!testOnly && !liveKey) {
    console.log('\n⚠️  STRIPE_SECRET_KEY_LIVE not found in .env, skipping live mode');
  }

  // Summary
  console.log('\n✅ Webhook setup complete!\n');
  console.log('📋 Summary:');
  console.log(`  Endpoint URL: ${webhookUrl}`);
  console.log(`  Test webhook: ${results.test?.id || 'N/A'}`);
  console.log(`  Live webhook: ${results.live?.id || 'N/A'}`);
  console.log('\n📝 Next steps:');
  console.log('  1. Test webhook delivery: curl -X POST ' + webhookUrl);
  console.log('  2. View webhook logs: wrangler tail');
  console.log('  3. Trigger test event: stripe trigger customer.subscription.created\n');
}

main().catch(error => {
  console.error('\n❌ Fatal error:', error);
  process.exit(1);
});
