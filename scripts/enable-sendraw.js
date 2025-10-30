#!/usr/bin/env node
/**
 * Enable send_raw on existing xswarm.ai webhook
 * This is needed for full MIME message parsing
 */

const SENDGRID_API_KEY = process.env.SENDGRID_API_KEY || '***REMOVED***';

console.log('🔧 Enabling send_raw on xswarm.ai webhook');
console.log('==========================================');

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

  // Find xswarm.ai webhook
  const xswarmWebhook = webhooks.result.find(w => w.hostname === 'xswarm.ai');

  if (!xswarmWebhook) {
    console.log('❌ No webhook found for xswarm.ai');
    console.log('Available webhooks:');
    webhooks.result.forEach(w => {
      console.log(`   - ${w.hostname}: ${w.url}`);
    });
    process.exit(1);
  }

  console.log(`✅ Found xswarm.ai webhook`);
  console.log(`   URL: ${xswarmWebhook.url}`);
  console.log(`   Send Raw: ${xswarmWebhook.send_raw ? 'Yes' : 'No'}`);

  if (xswarmWebhook.send_raw) {
    console.log('✅ send_raw is already enabled!');
  } else {
    console.log('🔧 Enabling send_raw...');

    // Update webhook to enable send_raw
    const updateResponse = await fetch(`https://api.sendgrid.com/v3/user/webhooks/parse/settings/${xswarmWebhook.hostname}`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${SENDGRID_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        hostname: xswarmWebhook.hostname,
        url: xswarmWebhook.url,
        spam_check: xswarmWebhook.spam_check,
        send_raw: true
      })
    });

    if (!updateResponse.ok) {
      const error = await updateResponse.text();
      throw new Error(`Failed to update webhook: ${updateResponse.status} - ${error}`);
    }

    console.log('✅ Successfully enabled send_raw!');
  }

  console.log('\\n🎯 Webhook Configuration Complete');
  console.log('─────────────────────────────────');
  console.log(`✅ Hostname: ${xswarmWebhook.hostname}`);
  console.log(`✅ URL: ${xswarmWebhook.url}`);
  console.log(`✅ Send Raw: Yes`);

  console.log('\\n📋 Next Steps:');
  console.log('1. Add MX record: xswarm.ai → mx.sendgrid.net (priority 10)');
  console.log('2. Wait 5-60 minutes for DNS propagation');
  console.log('3. Test by sending email to: boss@xswarm.ai');

} catch (error) {
  console.error('❌ Error:', error.message);
  process.exit(1);
}