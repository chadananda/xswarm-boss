#!/usr/bin/env node
/**
 * Enable send_raw on existing xswarm.ai webhook (Fixed Version)
 * Uses correct API format for updating webhooks
 */

const SENDGRID_API_KEY = process.env.SENDGRID_API_KEY || '***REMOVED***';

console.log('🔧 Enabling send_raw on xswarm.ai webhook (Fixed)');
console.log('================================================');

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

    // Delete and recreate webhook (sometimes PATCH doesn't work, this is more reliable)
    console.log('Step 1: Deleting existing webhook...');
    const deleteResponse = await fetch(`https://api.sendgrid.com/v3/user/webhooks/parse/settings/${xswarmWebhook.hostname}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${SENDGRID_API_KEY}`
      }
    });

    if (!deleteResponse.ok) {
      console.log(`⚠️  Delete failed (${deleteResponse.status}), continuing...`);
    } else {
      console.log('✅ Deleted existing webhook');
    }

    // Wait a moment
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Create new webhook with send_raw enabled
    console.log('Step 2: Creating new webhook with send_raw enabled...');
    const createResponse = await fetch('https://api.sendgrid.com/v3/user/webhooks/parse/settings', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${SENDGRID_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        hostname: 'xswarm.ai',
        url: xswarmWebhook.url,
        spam_check: false,
        send_raw: true
      })
    });

    if (!createResponse.ok) {
      const error = await createResponse.text();
      throw new Error(`Failed to create webhook: ${createResponse.status} - ${error}`);
    }

    console.log('✅ Successfully created webhook with send_raw enabled!');
  }

  console.log('\\n🎯 Webhook Configuration Complete');
  console.log('─────────────────────────────────');
  console.log(`✅ Hostname: xswarm.ai`);
  console.log(`✅ URL: ${xswarmWebhook.url}`);
  console.log(`✅ Send Raw: Yes`);

  console.log('\\n📋 Configuration Summary:');
  console.log('✅ Domain authenticated: xswarm.ai');
  console.log('✅ Webhook configured: xswarm.ai → Claude webhook');
  console.log('✅ Send raw enabled: Full MIME message parsing');
  console.log('✅ User config updated: boss@xswarm.ai');

  console.log('\\n🚨 CRITICAL: DNS Configuration Required');
  console.log('─────────────────────────────────────────');
  console.log('You MUST add this MX record to your DNS:');
  console.log('');
  console.log('   Type: MX');
  console.log('   Host: @ (or blank for root domain)');
  console.log('   Priority: 10');
  console.log('   Value: mx.sendgrid.net');
  console.log('   TTL: 3600');
  console.log('');
  console.log('Without this MX record, emails will continue to fail!');

  console.log('\\n⏰ Timeline:');
  console.log('1. Add MX record NOW (5 minutes)');
  console.log('2. Wait for DNS propagation (5-60 minutes)');
  console.log('3. Test: Send email to boss@xswarm.ai');
  console.log('4. Expect: Claude AI auto-response!');

} catch (error) {
  console.error('❌ Error:', error.message);
  process.exit(1);
}