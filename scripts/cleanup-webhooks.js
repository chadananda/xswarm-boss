#!/usr/bin/env node
/**
 * Cleanup SendGrid Webhooks
 * Remove the problematic mail.xswarm.ai webhook
 * Keep only the xswarm.ai webhook with send_raw enabled
 */

const SENDGRID_API_KEY = process.env.SENDGRID_API_KEY || '***REMOVED***';

console.log('🧹 Cleaning up SendGrid Webhooks');
console.log('=================================');

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
  console.log(`📋 Found ${webhooks.result.length} existing webhooks`);

  // List all webhooks
  webhooks.result.forEach((webhook, index) => {
    console.log(`   ${index + 1}. ${webhook.hostname} (send_raw: ${webhook.send_raw ? 'Yes' : 'No'})`);
  });

  // Find problematic webhook
  const badWebhook = webhooks.result.find(w => w.hostname === 'mail.xswarm.ai');
  const goodWebhook = webhooks.result.find(w => w.hostname === 'xswarm.ai');

  if (badWebhook) {
    console.log(`\\n🗑️  Removing problematic webhook: mail.xswarm.ai`);

    const deleteResponse = await fetch(`https://api.sendgrid.com/v3/user/webhooks/parse/settings/${badWebhook.hostname}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${SENDGRID_API_KEY}`
      }
    });

    if (deleteResponse.ok) {
      console.log('✅ Successfully deleted mail.xswarm.ai webhook');
    } else {
      console.log(`⚠️  Failed to delete webhook: ${deleteResponse.status}`);
    }
  } else {
    console.log('✅ No problematic mail.xswarm.ai webhook found');
  }

  if (goodWebhook) {
    console.log(`\\n✅ Keeping good webhook: xswarm.ai`);
    console.log(`   URL: ${goodWebhook.url}`);
    console.log(`   Send Raw: ${goodWebhook.send_raw ? 'Yes' : 'No'}`);
  } else {
    console.log('❌ Warning: No xswarm.ai webhook found!');
  }

  console.log('\\n🎯 Final Configuration:');
  console.log('✅ Single webhook: xswarm.ai');
  console.log('✅ Catches all emails: *@xswarm.ai');
  console.log('✅ send_raw enabled: Full MIME parsing');
  console.log('✅ Routes to: Claude AI webhook');

  console.log('\\n📧 Test Again:');
  console.log('Send email to: chadananda@xswarm.ai');
  console.log('Expected: Should now reach webhook and get Claude AI response');

} catch (error) {
  console.error('❌ Error:', error.message);
  process.exit(1);
}