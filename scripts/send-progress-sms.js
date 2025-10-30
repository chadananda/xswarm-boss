#!/usr/bin/env node
/**
 * Send Boss Progress SMS
 *
 * Sends an SMS progress update to the user about development status
 *
 * Usage:
 *   node scripts/send-progress-sms.js "Your progress message here"
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
const from = config.users[0].boss_phone; // Boss phone: +18447472899
const to = config.users[0].phone; // User phone: +19167656913

if (!authToken) {
  console.error('Error: TWILIO_AUTH_TOKEN not found in .env');
  process.exit(1);
}

const message = process.argv[2] || 'Boss here. Development progress update coming soon.';

async function sendSMS() {
  try {
    const client = twilio(accountSid, authToken);

    const sms = await client.messages.create({
      body: `🤖 Boss Update:\n\n${message}`,
      from: from,
      to: to,
    });

    console.log(`✓ SMS sent successfully`);
    console.log(`  SID: ${sms.sid}`);
    console.log(`  From: ${from}`);
    console.log(`  To: ${to}`);
    console.log(`  Status: ${sms.status}`);

    return sms;
  } catch (error) {
    console.error('✗ Failed to send SMS:', error.message);
    throw error;
  }
}

sendSMS();
