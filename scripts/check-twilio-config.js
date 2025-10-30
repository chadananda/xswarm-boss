#!/usr/bin/env node
/**
 * Check Twilio Phone Number Configuration
 */

import twilio from 'twilio';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { parse as parseToml } from 'smol-toml';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

import 'dotenv/config';

const configPath = join(projectRoot, 'config.toml');
const configContent = readFileSync(configPath, 'utf-8');
const config = parseToml(configContent);

const accountSid = config.twilio.account_sid;
const authToken = process.env.TWILIO_AUTH_TOKEN;
const phoneNumber = config.users[0].boss_phone;

if (!authToken) {
  console.error('Error: TWILIO_AUTH_TOKEN not found');
  process.exit(1);
}

async function checkConfig() {
  const client = twilio(accountSid, authToken);

  const phoneNumbers = await client.incomingPhoneNumbers.list();
  const targetNumber = phoneNumbers.find(n => n.phoneNumber === phoneNumber);

  if (!targetNumber) {
    console.error(`❌ Phone number ${phoneNumber} not found`);
    return;
  }

  console.log('📱 Twilio Phone Number Configuration');
  console.log('=====================================\n');
  console.log(`Phone: ${targetNumber.phoneNumber}`);
  console.log(`Friendly Name: ${targetNumber.friendlyName}`);
  console.log(`\n🔔 Voice Webhooks:`);
  console.log(`  URL: ${targetNumber.voiceUrl || '(not set)'}`);
  console.log(`  Method: ${targetNumber.voiceMethod || 'POST'}`);
  console.log(`\n💬 SMS Webhooks:`);
  console.log(`  URL: ${targetNumber.smsUrl || '(not set)'}`);
  console.log(`  Method: ${targetNumber.smsMethod || 'POST'}`);
  console.log(`\n📋 Status:`);
  console.log(`  Status: ${targetNumber.status}`);
  console.log(`  Capabilities: Voice=${targetNumber.capabilities.voice}, SMS=${targetNumber.capabilities.sms}`);
}

checkConfig();
