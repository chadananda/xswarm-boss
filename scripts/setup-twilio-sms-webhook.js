#!/usr/bin/env node
/**
 * Configure Twilio SMS Webhook
 *
 * Sets up the SMS webhook for incoming messages to the Boss phone number
 */

import twilio from 'twilio';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { parse as parseToml } from 'smol-toml';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

// Load environment variables
import 'dotenv/config';

// Load config
const configPath = join(projectRoot, 'config.toml');
const configContent = readFileSync(configPath, 'utf-8');
const config = parseToml(configContent);

const accountSid = config.twilio.account_sid;
const authToken = process.env.TWILIO_AUTH_TOKEN;
const phoneNumber = config.users[0].boss_phone; // Boss phone: +18447472899

if (!authToken) {
  console.error('Error: TWILIO_AUTH_TOKEN not found in .env');
  process.exit(1);
}

console.log('🔧 Configuring Twilio SMS Webhook');
console.log('==================================\n');
console.log(`Phone Number: ${phoneNumber}`);
console.log(`Account SID: ${accountSid}\n`);

async function setupSmsWebhook() {
  try {
    const client = twilio(accountSid, authToken);

    // Find the phone number in Twilio
    const phoneNumbers = await client.incomingPhoneNumbers.list();
    const targetNumber = phoneNumbers.find(n => n.phoneNumber === phoneNumber);

    if (!targetNumber) {
      console.error(`❌ Phone number ${phoneNumber} not found in Twilio account`);
      process.exit(1);
    }

    console.log(`✓ Found phone number: ${targetNumber.friendlyName}`);

    // Set SMS webhook URL (use username from config)
    const username = config.users[0].username;
    const webhookUrl = `https://xswarm-webhooks.chadananda.workers.dev/sms/${username}`;

    await client.incomingPhoneNumbers(targetNumber.sid).update({
      smsUrl: webhookUrl,
      smsMethod: 'POST',
    });

    console.log(`\n✓ SMS webhook configured successfully!`);
    console.log(`  URL: ${webhookUrl}`);
    console.log(`  Method: POST`);
    console.log(`\n✅ Your Boss can now receive SMS messages at ${phoneNumber}`);
    console.log(`   Replies will be sent back automatically.`);

  } catch (error) {
    console.error('❌ Error configuring webhook:', error.message);
    process.exit(1);
  }
}

setupSmsWebhook();
