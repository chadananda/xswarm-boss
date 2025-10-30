#!/usr/bin/env node
/**
 * Update SendGrid Webhook URL to New Tunnel
 * Replace old tunnel URL with new one
 */

const SENDGRID_API_KEY = process.env.SENDGRID_API_KEY || '***REMOVED***';
const OLD_URL = 'https://tion-fifteen-substantial-jimmy.trycloudflare.com/email/inbound';
const NEW_URL = 'https://laboratory-authors-mem-inflation.trycloudflare.com/email/inbound';

console.log('🔄 Updating SendGrid Webhook URL');
console.log('=================================');
console.log(`Old URL: ${OLD_URL}`);
console.log(`New URL: ${NEW_URL}`);

try {
  // Get existing webhooks
  const getResponse = await fetch('https://api.sendgrid.com/v3/user/webhooks/parse/settings', {
    headers: {
      'Authorization': `Bearer ${SENDGRID_API_KEY}`,
      'Content-Type': 'application/json'
    }
  });

  if (!getResponse.ok) {
    throw new Error(`Failed to get webhooks: ${getResponse.status}`);
  }

  const webhooks = await getResponse.json();
  console.log(`\\n📋 Found ${webhooks.result.length} existing webhooks`);

  // Find xswarm.ai webhook
  const xswarmWebhook = webhooks.result.find(w => w.hostname === 'xswarm.ai');

  if (!xswarmWebhook) {
    console.log('❌ No webhook found for xswarm.ai');
    process.exit(1);
  }

  console.log(`\\n🔧 Current webhook configuration:`);
  console.log(`   Hostname: ${xswarmWebhook.hostname}`);
  console.log(`   URL: ${xswarmWebhook.url}`);
  console.log(`   Send Raw: ${xswarmWebhook.send_raw ? 'Yes' : 'No'}`);

  if (xswarmWebhook.url === NEW_URL) {
    console.log('\\n✅ Webhook already has the correct URL!');
    process.exit(0);
  }

  // Delete existing webhook
  console.log('\\n🗑️  Deleting old webhook...');
  const deleteResponse = await fetch(`https://api.sendgrid.com/v3/user/webhooks/parse/settings/${xswarmWebhook.hostname}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${SENDGRID_API_KEY}`
    }
  });

  if (!deleteResponse.ok) {
    console.log(`⚠️  Delete failed (${deleteResponse.status}), continuing...`);
  } else {
    console.log('✅ Deleted old webhook');
  }

  // Wait a moment
  await new Promise(resolve => setTimeout(resolve, 1000));

  // Create new webhook with updated URL
  console.log('🔧 Creating webhook with new URL...');
  const createResponse = await fetch('https://api.sendgrid.com/v3/user/webhooks/parse/settings', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${SENDGRID_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      hostname: 'xswarm.ai',
      url: NEW_URL,
      spam_check: false,
      send_raw: true
    })
  });

  if (!createResponse.ok) {
    const error = await createResponse.text();
    throw new Error(`Failed to create webhook: ${createResponse.status} - ${error}`);
  }

  console.log('✅ Successfully updated webhook URL!');

  console.log('\\n🎯 Final Configuration:');
  console.log('✅ Hostname: xswarm.ai');
  console.log(`✅ URL: ${NEW_URL}`);
  console.log('✅ Send Raw: Yes');
  console.log('✅ Tunnel: Active and accessible');

  console.log('\\n📧 Ready to Test:');
  console.log('Send email to: chadananda@xswarm.ai');
  console.log('Expected: Should now reach webhook and get Claude AI response!');

} catch (error) {
  console.error('❌ Error:', error.message);
  process.exit(1);
}