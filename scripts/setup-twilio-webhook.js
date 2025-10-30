#!/usr/bin/env node
/**
 * Configure Twilio Phone Number Webhook
 *
 * Sets up the voice webhook for incoming calls to Boss
 *
 * Usage:
 *   node scripts/setup-twilio-webhook.js
 *   pnpm setup:twilio
 */

import 'dotenv/config';
import twilio from 'twilio';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { parse as parseToml } from 'smol-toml';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

// Load config.toml
const configPath = join(projectRoot, 'config.toml');
const configContent = readFileSync(configPath, 'utf-8');
const config = parseToml(configContent);

// Get Twilio credentials from environment
const {
  TWILIO_AUTH_TOKEN,
  TWILIO_AUTH_TOKEN_TEST,
  TWILIO_AUTH_TOKEN_LIVE,
} = process.env;

const authToken = TWILIO_AUTH_TOKEN_TEST || TWILIO_AUTH_TOKEN_LIVE || TWILIO_AUTH_TOKEN;
const accountSid = config.twilio.account_sid;
const phoneNumber = config.twilio.test_receive_number;

if (!accountSid || !authToken || !phoneNumber) {
  console.error('❌ Missing required configuration:');
  if (!accountSid) console.error('  - TWILIO_ACCOUNT_SID in config.toml');
  if (!authToken) console.error('  - TWILIO_AUTH_TOKEN in .env');
  if (!phoneNumber) console.error('  - test_receive_number in config.toml');
  process.exit(1);
}

async function configureTwilioWebhook() {
  console.log('🔧 Configuring Twilio Phone Number Webhook\n');

  // Initialize Twilio client
  const client = twilio(accountSid, authToken);

  try {
    // Find the phone number
    console.log(`Looking for phone number: ${phoneNumber}`);
    const phoneNumbers = await client.incomingPhoneNumbers.list();
    const targetNumber = phoneNumbers.find(n => n.phoneNumber === phoneNumber);

    if (!targetNumber) {
      console.error(`❌ Phone number ${phoneNumber} not found in your account!`);
      console.error('   Available numbers:');
      phoneNumbers.forEach(n => console.error(`   - ${n.phoneNumber}`));
      process.exit(1);
    }

    console.log(`✓ Found phone number: ${targetNumber.friendlyName}\n`);

    // Configure webhook
    const webhookUrl = 'https://xswarm-webhooks.chadananda.workers.dev/voice/inbound';
    console.log(`Setting voice webhook to: ${webhookUrl}`);

    await client.incomingPhoneNumbers(targetNumber.sid).update({
      voiceUrl: webhookUrl,
      voiceMethod: 'POST',
    });

    console.log('✓ Voice webhook configured!\n');
    console.log('=' .repeat(60));
    console.log('SUCCESS');
    console.log('=' .repeat(60));
    console.log(`You can now call ${phoneNumber} and Boss will answer!`);
    console.log('Boss will greet you and help with technical questions.');

  } catch (error) {
    console.error('❌ Failed to configure webhook:', error.message);
    process.exit(1);
  }
}

configureTwilioWebhook();
