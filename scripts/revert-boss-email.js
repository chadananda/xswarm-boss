#!/usr/bin/env node
/**
 * Revert Boss Email to Username-Based Format
 * Changes back from boss@xswarm.ai to chadananda@xswarm.ai
 * And creates the correct SendGrid configuration for dynamic usernames
 */

import { readFileSync, writeFileSync } from 'fs';

const CONFIG_PATH = 'packages/server/src/config/users.json';

console.log('🔄 Reverting to Username-Based Email Configuration');
console.log('================================================');

try {
  // Read current configuration
  const configData = readFileSync(CONFIG_PATH, 'utf8');
  const config = JSON.parse(configData);

  console.log('📋 Current Configuration:');
  console.log(`Boss Email: ${config.users[0].boss_email}`);

  // Revert to username-based email
  const username = config.users[0].username;
  const oldEmail = config.users[0].boss_email;
  const newEmail = `${username}@xswarm.ai`;

  config.users[0].boss_email = newEmail;

  // Update phoneToUser mapping as well
  const userPhone = config.users[0].phone;
  if (config.phoneToUser[userPhone]) {
    config.phoneToUser[userPhone].boss_email = newEmail;
  }

  // Write updated configuration
  writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));

  console.log('✅ Configuration Reverted Successfully');
  console.log(`Old Email: ${oldEmail}`);
  console.log(`New Email: ${newEmail}`);

  console.log('\\n🎯 Multi-User Email System:');
  console.log('• Each user gets [username]@xswarm.ai');
  console.log('• Currently configured: chadananda@xswarm.ai');
  console.log('• Future users: [theirusername]@xswarm.ai');
  console.log('• All route to the same Boss assistant');

  console.log('\\n📋 Correct SendGrid Configuration Needed:');
  console.log('1. MX Record: *.xswarm.ai → mx.sendgrid.net (wildcard)');
  console.log('   OR: xswarm.ai → mx.sendgrid.net (catches all subdomains)');
  console.log('2. Webhook: xswarm.ai (catches all @xswarm.ai emails)');
  console.log('3. send_raw: enabled (already done)');

} catch (error) {
  console.error('❌ Error reverting configuration:', error.message);
  process.exit(1);
}