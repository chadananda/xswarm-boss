#!/usr/bin/env node
/**
 * SendGrid Configuration Setup
 *
 * This script helps configure SendGrid for Boss email communication:
 * 1. Verify SendGrid API key
 * 2. Configure domain authentication (xswarm.ai)
 * 3. Set up Inbound Parse webhook
 * 4. Test email sending
 */

import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { parse as parseToml } from 'smol-toml';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

// Load environment variables
import 'dotenv/config';

const SENDGRID_API_KEY = process.env.SENDGRID_API_KEY;
const WORKER_URL = 'https://xswarm-webhooks.chadananda.workers.dev';

// Load config
const configPath = join(projectRoot, 'config.toml');
const configContent = readFileSync(configPath, 'utf-8');
const config = parseToml(configContent);

const DOMAIN = config.sendgrid.domain; // xswarm.ai
const USER_EMAIL = config.users[0].email; // chadananda@gmail.com
const BOSS_EMAIL = config.users[0].boss_email; // chadananda@xswarm.ai

console.log('🔧 SendGrid Configuration Setup');
console.log('================================\n');

// Step 1: Verify API Key
console.log('Step 1: Verifying SendGrid API Key...');
if (!SENDGRID_API_KEY) {
  console.error('❌ SENDGRID_API_KEY not found in .env file');
  console.log('\nTo get your SendGrid API key:');
  console.log('1. Go to https://app.sendgrid.com/');
  console.log('2. Navigate to Settings > API Keys');
  console.log('3. Create a new API key with "Full Access"');
  console.log('4. Add to .env file: SENDGRID_API_KEY=SG.xxxxxx');
  console.log('5. Run: pnpm setup:secrets (to sync to Cloudflare Workers)');
  process.exit(1);
}

try {
  const response = await fetch('https://api.sendgrid.com/v3/user/profile', {
    headers: {
      'Authorization': `Bearer ${SENDGRID_API_KEY}`,
    },
  });

  if (!response.ok) {
    throw new Error('Invalid API key');
  }

  const profile = await response.json();
  console.log(`✓ API Key verified for user: ${profile.email}\n`);
} catch (error) {
  console.error('❌ Failed to verify API key:', error.message);
  process.exit(1);
}

// Step 2: Domain Authentication
console.log('Step 2: Domain Authentication');
console.log('-----------------------------');
console.log(`Domain: ${DOMAIN}`);
console.log('\nTo authenticate your domain with SendGrid:');
console.log('1. Go to https://app.sendgrid.com/settings/sender_auth');
console.log('2. Click "Authenticate Your Domain"');
console.log('3. Enter domain: xswarm.ai');
console.log('4. Follow DNS configuration instructions');
console.log('5. Wait for DNS propagation (can take up to 48 hours)');
console.log('\nDNS Records Required:');
console.log('- SPF record (TXT)');
console.log('- DKIM records (CNAME)');
console.log('- Mail CNAME record\n');

// Step 3: Inbound Parse Configuration
console.log('Step 3: Inbound Parse Webhook');
console.log('------------------------------');
console.log(`Webhook URL: ${WORKER_URL}/email/inbound`);
console.log(`Boss Email: ${BOSS_EMAIL}`);
console.log('\nTo configure inbound email parsing:');
console.log('1. Go to https://app.sendgrid.com/settings/parse');
console.log('2. Click "Add Host & URL"');
console.log('3. Host: chadananda (subdomain of xswarm.ai)');
console.log('4. URL: https://xswarm-webhooks.chadananda.workers.dev/email/inbound');
console.log('5. Check "POST the raw, full MIME message"');
console.log('6. Save\n');

console.log('MX Record Configuration:');
console.log('Add this MX record to your xswarm.ai DNS:');
console.log('  Host: chadananda');
console.log('  Type: MX');
console.log('  Priority: 10');
console.log('  Value: mx.sendgrid.net\n');

// Step 4: Test Email Sending
console.log('Step 4: Test Email Sending');
console.log('--------------------------');
console.log(`Sending test email from ${BOSS_EMAIL} to ${USER_EMAIL}...\n`);

try {
  const emailData = {
    personalizations: [{
      to: [{ email: USER_EMAIL }],
      subject: 'Boss Email System - Test Message',
    }],
    from: { email: BOSS_EMAIL },
    content: [{
      type: 'text/plain',
      value: `Hello from Boss!

This is a test message to verify that email communication is working correctly.

Your Boss assistant can now:
- Send you progress reports via email
- Receive directions from you when you reply to chadananda@xswarm.ai
- Communicate about development tasks

To test the full system:
1. Reply to this email with a message
2. Your reply should be processed by the Boss webhook
3. You'll receive an acknowledgment

Best,
Boss Assistant`,
    }],
  };

  const response = await fetch('https://api.sendgrid.com/v3/mail/send', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${SENDGRID_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(emailData),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error);
  }

  const messageId = response.headers.get('x-message-id');
  console.log(`✓ Test email sent successfully!`);
  console.log(`  Message ID: ${messageId}`);
  console.log(`  From: ${BOSS_EMAIL}`);
  console.log(`  To: ${USER_EMAIL}\n`);

  console.log('Check your inbox (may take 1-2 minutes).\n');
} catch (error) {
  console.error('❌ Failed to send test email:', error.message);
  console.log('\nThis may be because domain authentication is not complete.');
  console.log('Complete Steps 2 and 3 above, then try again.\n');
}

// Summary
console.log('Summary');
console.log('=======');
console.log('\n✅ Email routes added to worker');
console.log('   - POST /email/inbound (SendGrid Parse webhook)');
console.log('   - POST /api/boss/email (Boss progress reports)\n');

console.log('📋 Next Steps:');
console.log('1. Complete domain authentication (Step 2)');
console.log('2. Configure Inbound Parse (Step 3)');
console.log('3. Deploy worker: pnpm wrangler deploy');
console.log('4. Test inbound email by replying to test message\n');

console.log('📧 Email Rules:');
console.log(`   ${BOSS_EMAIL} ↔️ ${USER_EMAIL} (bidirectional only)`);
console.log('   All other emails are silently dropped for security.\n');
