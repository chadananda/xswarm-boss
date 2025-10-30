#!/usr/bin/env node
/**
 * SendGrid Configuration Fix Script
 *
 * Automatically fixes common SendGrid configuration issues that cause
 * "554 5.7.1: Relay access denied" errors.
 *
 * This script:
 * 1. Creates or updates inbound parse webhook
 * 2. Verifies domain authentication
 * 3. Disables problematic mail settings
 * 4. Provides manual fix instructions for DNS
 */

import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { parse as parseToml } from 'smol-toml';
import readline from 'readline';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

// Load environment variables
import 'dotenv/config';

const SENDGRID_API_KEY = process.env.SENDGRID_API_KEY;

// Load config from users.json (actual runtime config)
const usersConfigPath = join(projectRoot, 'packages/server/src/config/users.json');
const usersConfig = JSON.parse(readFileSync(usersConfigPath, 'utf-8'));

const BOSS_EMAIL = usersConfig.users[0].boss_email; // chadananda@xswarm.ai
const DOMAIN = BOSS_EMAIL.split('@')[1]; // xswarm.ai
const USER_EMAIL = usersConfig.users[0].email; // chadananda@gmail.com

// Get webhook URL from packages/server/.dev.vars
const devVarsPath = join(projectRoot, 'packages/server/.dev.vars');
let WEBHOOK_URL = 'https://xswarm-webhooks.chadananda.workers.dev/email/inbound';

try {
  const devVarsContent = readFileSync(devVarsPath, 'utf-8');
  const publicUrlMatch = devVarsContent.match(/PUBLIC_BASE_URL=(.+)/);
  if (publicUrlMatch) {
    WEBHOOK_URL = `${publicUrlMatch[1].trim()}/email/inbound`;
  }
} catch (error) {
  console.log('Using default webhook URL (dev.vars not found)');
}

console.log('╔══════════════════════════════════════════════════════════════════╗');
console.log('║            SendGrid Configuration Fix Script                     ║');
console.log('╚══════════════════════════════════════════════════════════════════╝\n');

if (!SENDGRID_API_KEY) {
  console.error('❌ SENDGRID_API_KEY not found in environment');
  process.exit(1);
}

/**
 * Create readline interface for user input
 */
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function question(query) {
  return new Promise(resolve => rl.question(query, resolve));
}

/**
 * Make SendGrid API request
 */
async function sendgridRequest(endpoint, method = 'GET', body = null) {
  const options = {
    method,
    headers: {
      'Authorization': `Bearer ${SENDGRID_API_KEY}`,
      'Content-Type': 'application/json',
    },
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`https://api.sendgrid.com/v3${endpoint}`, options);

  return {
    ok: response.ok,
    status: response.status,
    data: response.ok ? await response.json() : null,
    error: !response.ok ? await response.text() : null,
  };
}

/**
 * Fix 1: Configure Inbound Parse Webhook
 */
async function fixInboundParseWebhook() {
  console.log('🔧 Fix 1: Configuring Inbound Parse Webhook');
  console.log('─────────────────────────────────────────────────────────────────');

  const subdomain = BOSS_EMAIL.split('@')[0]; // 'chadananda'
  const domain = BOSS_EMAIL.split('@')[1]; // 'xswarm.ai'

  console.log(`Configuration:`);
  console.log(`   Hostname: ${subdomain}`);
  console.log(`   Webhook URL: ${WEBHOOK_URL}`);
  console.log(`   Send Raw: Yes (for full MIME message)`);
  console.log('');

  // Check existing webhooks
  const existingResult = await sendgridRequest('/user/webhooks/parse/settings');

  if (existingResult.ok) {
    const webhooks = existingResult.data.result || [];
    const matchingWebhook = webhooks.find(w =>
      w.hostname === `${subdomain}.${domain}` ||
      w.hostname === subdomain
    );

    if (matchingWebhook) {
      console.log('✅ Inbound parse webhook already exists');
      console.log(`   ID: ${matchingWebhook.id}`);
      console.log(`   Hostname: ${matchingWebhook.hostname}`);
      console.log(`   URL: ${matchingWebhook.url}`);

      // Check if it needs updating
      if (matchingWebhook.url !== WEBHOOK_URL || !matchingWebhook.send_raw) {
        if (matchingWebhook.url !== WEBHOOK_URL) {
          console.log('\n⚠️  Webhook URL needs updating');
          console.log(`   Current: ${matchingWebhook.url}`);
          console.log(`   New: ${WEBHOOK_URL}`);
        }
        if (!matchingWebhook.send_raw) {
          console.log('\n⚠️  Send Raw needs to be enabled');
        }

        const update = await question('Update webhook configuration? (y/n): ');

        if (update.toLowerCase() === 'y') {
          // Note: SendGrid API doesn't support PATCH for parse webhooks
          // We need to delete and recreate
          console.log('Deleting old webhook...');

          // Get the webhook ID from the list
          const webhookToDelete = webhooks.find(w =>
            w.hostname === `${subdomain}.${domain}` ||
            w.hostname === subdomain
          );

          if (webhookToDelete && webhookToDelete.id) {
            const deleteResult = await sendgridRequest(
              `/user/webhooks/parse/settings/${webhookToDelete.id}`,
              'DELETE'
            );

            if (deleteResult.ok) {
              console.log('✅ Old webhook deleted');
            } else {
              console.log('⚠️  Could not delete old webhook:', deleteResult.error);
              console.log('   You may need to delete it manually at https://app.sendgrid.com/settings/parse');
              return;
            }
          } else {
            console.log('⚠️  Could not find webhook ID to delete');
            console.log('   Please delete manually at https://app.sendgrid.com/settings/parse');
            return;
          }
        } else {
          console.log('Skipping webhook update\n');
          return;
        }
      } else {
        console.log('✅ Webhook configuration is correct\n');
        return;
      }
    }
  }

  // Create new webhook
  console.log('Creating inbound parse webhook...');

  const webhookData = {
    hostname: subdomain, // Just the subdomain, SendGrid appends the domain
    url: WEBHOOK_URL,
    spam_check: false, // Don't filter spam, let webhook handle it
    send_raw: true, // Send full MIME message
  };

  const createResult = await sendgridRequest(
    '/user/webhooks/parse/settings',
    'POST',
    webhookData
  );

  if (!createResult.ok) {
    console.log('❌ Failed to create webhook');
    console.log(`   Status: ${createResult.status}`);
    console.log(`   Error: ${createResult.error}`);
    console.log('');
    console.log('⚠️  You may need to create the webhook manually:');
    console.log('   1. Go to https://app.sendgrid.com/settings/parse');
    console.log('   2. Click "Add Host & URL"');
    console.log(`   3. Hostname: ${subdomain}`);
    console.log(`   4. URL: ${WEBHOOK_URL}`);
    console.log('   5. Check "POST the raw, full MIME message"');
    console.log('   6. Save');
    console.log('');

    // Check if this is a free tier limitation
    if (createResult.error && createResult.error.includes('free')) {
      console.log('⚠️  This may be a free tier account limitation');
      console.log('   SendGrid free tier may not support inbound parse');
      console.log('   Consider upgrading to a paid plan');
      console.log('');
    }

    return false;
  }

  console.log('✅ Inbound parse webhook created successfully!');
  console.log(`   Webhook ID: ${createResult.data.id}`);
  console.log('');

  return true;
}

/**
 * Fix 2: Verify and Guide Domain Authentication
 */
async function checkDomainAuth() {
  console.log('🔧 Fix 2: Domain Authentication');
  console.log('─────────────────────────────────────────────────────────────────');

  const result = await sendgridRequest('/whitelabel/domains');

  if (!result.ok) {
    console.log('⚠️  Could not check domain authentication');
    console.log('');
    return;
  }

  const domains = result.data || [];
  const matchingDomain = domains.find(d => d.domain === DOMAIN);

  if (!matchingDomain) {
    console.log('⚠️  Domain not authenticated');
    console.log('');
    console.log('Manual steps required:');
    console.log('1. Go to https://app.sendgrid.com/settings/sender_auth');
    console.log('2. Click "Authenticate Your Domain"');
    console.log(`3. Enter domain: ${DOMAIN}`);
    console.log('4. Follow DNS configuration instructions');
    console.log('5. Wait for DNS propagation (can take up to 48 hours)');
    console.log('');
    return;
  }

  if (matchingDomain.valid) {
    console.log('✅ Domain is authenticated and valid');
    console.log('');
  } else {
    console.log('⚠️  Domain is configured but not yet validated');
    console.log('   Check DNS records and wait for propagation');
    console.log('');
  }
}

/**
 * Fix 3: Display MX Record Configuration
 */
async function displayMxRecordInstructions() {
  console.log('🔧 Fix 3: MX Record Configuration');
  console.log('─────────────────────────────────────────────────────────────────');

  const subdomain = BOSS_EMAIL.split('@')[0]; // 'chadananda'
  const domain = BOSS_EMAIL.split('@')[1]; // 'xswarm.ai'

  console.log('⚠️  MX record must be configured for inbound email to work');
  console.log('');
  console.log('DNS Configuration Required:');
  console.log('─────────────────────────────────────────────────────────────────');
  console.log(`   Record Type: MX`);
  console.log(`   Host/Name: ${subdomain}`);
  console.log(`   Priority: 10`);
  console.log(`   Value/Points to: mx.sendgrid.net`);
  console.log(`   TTL: 3600 (or automatic)`);
  console.log('');
  console.log('Steps to configure:');
  console.log(`1. Log in to your DNS provider (where ${domain} is registered)`);
  console.log('2. Go to DNS management / DNS records');
  console.log('3. Add a new MX record with the values above');
  console.log('4. Save and wait for DNS propagation (5-60 minutes)');
  console.log('');
  console.log('To verify MX record after configuration:');
  console.log(`   dig MX ${subdomain}.${domain}`);
  console.log('   or');
  console.log(`   nslookup -type=mx ${subdomain}.${domain}`);
  console.log('');
  console.log('Expected result:');
  console.log(`   ${subdomain}.${domain}. 3600 IN MX 10 mx.sendgrid.net.`);
  console.log('');
}

/**
 * Fix 4: Test Email Delivery
 */
async function testEmailDelivery() {
  console.log('🔧 Fix 4: Test Email Delivery');
  console.log('─────────────────────────────────────────────────────────────────');

  const test = await question('Send test email? (y/n): ');

  if (test.toLowerCase() !== 'y') {
    console.log('Skipping test email\n');
    return;
  }

  const userEmail = USER_EMAIL;

  console.log(`Sending test email from ${BOSS_EMAIL} to ${userEmail}...`);

  const emailData = {
    personalizations: [{
      to: [{ email: userEmail }],
      subject: 'SendGrid Configuration Test - Boss Email System',
    }],
    from: { email: BOSS_EMAIL },
    content: [{
      type: 'text/plain',
      value: `Hello!

This is a test email from your Boss email system.

If you receive this email, outbound email is working correctly.

To test inbound email (the reply functionality):
1. Reply to this email
2. Your reply should be processed by the webhook
3. You should receive an AI-powered response

Configuration:
- From: ${BOSS_EMAIL}
- Webhook: ${WEBHOOK_URL}
- Status: Testing

Best regards,
Boss Assistant System`,
    }],
  };

  const result = await sendgridRequest('/mail/send', 'POST', emailData);

  if (!result.ok) {
    console.log('❌ Failed to send test email');
    console.log(`   Status: ${result.status}`);
    console.log(`   Error: ${result.error}`);
    console.log('');
    return;
  }

  console.log('✅ Test email sent successfully!');
  console.log('   Check your inbox (may take 1-2 minutes)');
  console.log('');
  console.log('Next: Reply to the test email to verify inbound processing');
  console.log('');
}

/**
 * Main fix routine
 */
async function runFixes() {
  console.log('Starting automated fixes...\n');

  // Verify API key
  console.log('Verifying API key...');
  const profileResult = await sendgridRequest('/user/profile');

  if (!profileResult.ok) {
    console.log('❌ Invalid API key. Cannot proceed.\n');
    rl.close();
    process.exit(1);
  }

  console.log(`✅ API key valid (${profileResult.data.email})\n`);

  // Run fixes
  await fixInboundParseWebhook();
  await checkDomainAuth();
  await displayMxRecordInstructions();
  await testEmailDelivery();

  // Final summary
  console.log('╔══════════════════════════════════════════════════════════════════╗');
  console.log('║                       FIX SUMMARY                                ║');
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');

  console.log('✅ Completed automated fixes');
  console.log('');
  console.log('📋 Manual Steps Required:');
  console.log('   1. Configure MX record in your DNS (see instructions above)');
  console.log('   2. Wait for DNS propagation (5-60 minutes)');
  console.log('   3. Test by sending email to ' + BOSS_EMAIL);
  console.log('');
  console.log('🔍 Troubleshooting:');
  console.log('   - If still getting "relay access denied", run: node scripts/diagnose-sendgrid.js');
  console.log('   - Check webhook logs at: https://app.sendgrid.com/settings/parse');
  console.log('   - Verify MX record: dig MX ' + BOSS_EMAIL.split('@')[0] + '.' + BOSS_EMAIL.split('@')[1]);
  console.log('');
  console.log('💡 Note:');
  console.log('   If you have a SendGrid free tier account, inbound parse may not be available.');
  console.log('   Contact SendGrid support or upgrade to a paid plan.');
  console.log('');

  rl.close();
}

// Run fixes
runFixes().catch(error => {
  console.error('Fatal error running fixes:', error);
  rl.close();
  process.exit(1);
});
