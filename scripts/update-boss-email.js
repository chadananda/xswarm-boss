#!/usr/bin/env node
/**
 * Update Boss Email Configuration
 * Changes from chadananda@xswarm.ai to boss@xswarm.ai
 *
 * This fixes the SendGrid "554 5.7.1: Relay access denied" error by:
 * 1. Using the root domain (xswarm.ai) instead of subdomain
 * 2. Matching the existing authenticated domain
 * 3. Using the existing webhook configuration
 */

import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';

const CONFIG_PATH = 'packages/server/src/config/users.json';

console.log('🔧 Updating Boss Email Configuration');
console.log('====================================');

try {
  // Read current configuration
  const configData = readFileSync(CONFIG_PATH, 'utf8');
  const config = JSON.parse(configData);

  console.log('📋 Current Configuration:');
  console.log(`Boss Email: ${config.users[0].boss_email}`);

  // Update boss email
  const oldEmail = config.users[0].boss_email;
  const newEmail = 'boss@xswarm.ai';

  config.users[0].boss_email = newEmail;

  // Update phoneToUser mapping as well
  const userPhone = config.users[0].phone;
  if (config.phoneToUser[userPhone]) {
    config.phoneToUser[userPhone].boss_email = newEmail;
  }

  // Write updated configuration
  writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));

  console.log('✅ Configuration Updated Successfully');
  console.log(`Old Email: ${oldEmail}`);
  console.log(`New Email: ${newEmail}`);

  console.log('\\n🎯 Why This Fixes the Issue:');
  console.log('• Uses root domain (xswarm.ai) instead of subdomain');
  console.log('• Matches existing authenticated domain in SendGrid');
  console.log('• Uses existing webhook configuration');
  console.log('• Eliminates subdomain MX record requirement');

  console.log('\\n📋 Next Steps:');
  console.log('1. Add MX record: xswarm.ai → mx.sendgrid.net (priority 10)');
  console.log('2. Run: node scripts/fix-sendgrid.js');
  console.log('3. Wait 5-60 minutes for DNS propagation');
  console.log('4. Test by sending email to: boss@xswarm.ai');

} catch (error) {
  console.error('❌ Error updating configuration:', error.message);
  process.exit(1);
}