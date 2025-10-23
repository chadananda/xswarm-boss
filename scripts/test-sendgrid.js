#!/usr/bin/env node

/**
 * SendGrid Email Test Script
 *
 * Tests SendGrid API credentials and sends a test email
 *
 * Usage:
 *   node scripts/test-sendgrid.js
 */

import 'dotenv/config';
import sgMail from '@sendgrid/mail';

const {
  SENDGRID_API_KEY,
  USER_EMAIL,
  XSWARM_EMAIL,
  TEST_USER_EMAIL = USER_EMAIL,
  TEST_XSWARM_EMAIL = XSWARM_EMAIL || 'test@xswarm.ai'
} = process.env;

// Validate environment variables
function validateEnv() {
  const missing = [];

  if (!SENDGRID_API_KEY) {
    missing.push('SENDGRID_API_KEY');
  }
  if (!TEST_USER_EMAIL) {
    missing.push('USER_EMAIL or TEST_USER_EMAIL');
  }

  if (missing.length > 0) {
    console.error('❌ Missing or unconfigured environment variables:');
    missing.forEach(key => console.error(`   - ${key}`));
    console.error('\nPlease update your .env file with SendGrid credentials.');
    console.error('See planning/SENDGRID_SETUP.md for setup instructions.');
    process.exit(1);
  }
}

async function testSendGridConnection() {
  console.log('📧 SendGrid Email Test\n');

  // Validate environment
  validateEnv();

  console.log('✓ Environment variables configured');
  console.log(`  API Key: ${SENDGRID_API_KEY.substring(0, 15)}...`);
  console.log(`  From Email: ${TEST_XSWARM_EMAIL}`);
  console.log(`  To Email: ${TEST_USER_EMAIL}\n`);

  // Initialize SendGrid client
  sgMail.setApiKey(SENDGRID_API_KEY);

  try {
    // Test 1: Verify API key by fetching user profile
    console.log('🔑 Test 1: Verifying SendGrid API key...');

    const response = await fetch('https://api.sendgrid.com/v3/user/profile', {
      headers: {
        'Authorization': `Bearer ${SENDGRID_API_KEY}`
      }
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Invalid API key (401 Unauthorized)');
      } else if (response.status === 403) {
        throw new Error('API key lacks required permissions (403 Forbidden)');
      } else {
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
      }
    }

    const profile = await response.json();
    console.log(`✓ API key verified for user: ${profile.email}`);
    console.log(`  Username: ${profile.username}`);
    console.log(`  Account Type: ${profile.user_type || 'free'}\n`);

    // Test 2: Check sender authentication (domain verification)
    console.log('🔐 Test 2: Checking domain authentication...');

    const authResponse = await fetch('https://api.sendgrid.com/v3/whitelabel/domains', {
      headers: {
        'Authorization': `Bearer ${SENDGRID_API_KEY}`
      }
    });

    if (authResponse.ok) {
      const domains = await authResponse.json();
      const xswarmDomain = domains.find(d => d.domain === 'xswarm.ai');

      if (xswarmDomain) {
        console.log(`✓ Domain verified: ${xswarmDomain.domain}`);
        console.log(`  Valid: ${xswarmDomain.valid}`);
        console.log(`  Default: ${xswarmDomain.default}\n`);
      } else {
        console.warn(`⚠️  Domain 'xswarm.ai' not verified yet`);
        console.warn('   You can still send from verified email addresses.');
        console.warn('   See planning/SENDGRID_SETUP.md for domain verification.\n');
      }
    } else {
      console.warn(`⚠️  Could not check domain authentication (API key may lack permission)\n`);
    }

    // Test 3: Check account stats
    console.log('📊 Test 3: Checking account statistics...');

    const statsResponse = await fetch('https://api.sendgrid.com/v3/stats?limit=1', {
      headers: {
        'Authorization': `Bearer ${SENDGRID_API_KEY}`
      }
    });

    if (statsResponse.ok) {
      const stats = await statsResponse.json();
      if (stats.length > 0) {
        const latestStats = stats[0].stats[0]?.metrics || {};
        console.log(`✓ Recent statistics:`);
        console.log(`  Requests: ${latestStats.requests || 0}`);
        console.log(`  Delivered: ${latestStats.delivered || 0}`);
        console.log(`  Bounces: ${latestStats.bounces || 0}\n`);
      } else {
        console.log(`✓ No email statistics yet (new account)\n`);
      }
    }

    // Test 4: Prepare test email
    console.log('✉️  Test 4: Ready to send test email!');
    console.log(`   From: HAL 9000 <${TEST_XSWARM_EMAIL}>`);
    console.log(`   To: ${TEST_USER_EMAIL}`);
    console.log(`   Subject: xSwarm Email System Test\n`);

    console.log('Do you want to send a test email? (yes/no)');

    // Simple prompt for confirmation
    const readline = await import('readline');
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    rl.question('> ', async (answer) => {
      if (answer.toLowerCase() === 'yes' || answer.toLowerCase() === 'y') {
        console.log('\n📤 Sending test email...');

        const msg = {
          to: TEST_USER_EMAIL,
          from: {
            email: TEST_XSWARM_EMAIL,
            name: 'HAL 9000'
          },
          subject: 'xSwarm Email System Test',
          text: `
Hello!

This is a test email from your xSwarm email communication system.

I'm sorry Dave, I mean... this is HAL 9000 testing the email integration.

If you received this message, your SendGrid integration is working perfectly!

System Details:
- From: ${TEST_XSWARM_EMAIL}
- To: ${TEST_USER_EMAIL}
- Channel: Email
- Urgency: Low (test message)

All systems operational.

Best regards,
HAL 9000
xSwarm AI CTO
          `.trim(),
          html: `
            <h2>Hello!</h2>
            <p>This is a test email from your <strong>xSwarm email communication system</strong>.</p>
            <p><em>I'm sorry Dave</em>, I mean... this is <strong>HAL 9000</strong> testing the email integration.</p>
            <p>If you received this message, your SendGrid integration is working perfectly!</p>
            <hr>
            <h3>System Details:</h3>
            <ul>
              <li><strong>From:</strong> ${TEST_XSWARM_EMAIL}</li>
              <li><strong>To:</strong> ${TEST_USER_EMAIL}</li>
              <li><strong>Channel:</strong> Email</li>
              <li><strong>Urgency:</strong> Low (test message)</li>
            </ul>
            <p><em>All systems operational.</em></p>
            <hr>
            <p>
              Best regards,<br>
              <strong>HAL 9000</strong><br>
              <em>xSwarm AI CTO</em>
            </p>
          `
        };

        try {
          const result = await sgMail.send(msg);

          console.log(`✓ Email sent successfully!`);
          console.log(`  Message ID: ${result[0].headers['x-message-id']}`);
          console.log(`  Status Code: ${result[0].statusCode}`);
          console.log(`\n📬 Check your inbox at ${TEST_USER_EMAIL}\n`);

          // Poll for delivery status (SendGrid doesn't provide immediate status)
          console.log('Note: Email delivery may take a few seconds.');
          console.log('Check your spam folder if you don\'t see it in your inbox.\n');

          rl.close();

        } catch (err) {
          console.error(`\n❌ Email send failed: ${err.message}`);

          if (err.response) {
            console.error(`  Status: ${err.response.statusCode}`);
            console.error(`  Body: ${JSON.stringify(err.response.body, null, 2)}`);
          }

          if (err.code === 403) {
            console.error('\nPossible causes:');
            console.error('- API key lacks "Mail Send" permission');
            console.error('- Sender email not verified (required for free accounts)');
            console.error('- Daily sending limit exceeded (100 emails/day on free tier)');
          } else if (err.code === 401) {
            console.error('\nAPI key is invalid or expired.');
            console.error('Generate a new API key in SendGrid Console.');
          }

          rl.close();
        }
      } else {
        console.log('\n✓ Skipping test email.');
        console.log('\n✅ All SendGrid connection tests passed!');
        console.log('   You can run this script again to send a test email.\n');
        rl.close();
      }
    });

  } catch (error) {
    console.error(`\n❌ SendGrid API Error: ${error.message}`);

    if (error.message.includes('401')) {
      console.error('\nAuthentication failed. Check your API key.');
      console.error('Generate a new key: SendGrid Console → Settings → API Keys');
    } else if (error.message.includes('403')) {
      console.error('\nAPI key lacks required permissions.');
      console.error('Create a new key with "Full Access" or "Mail Send" permission.');
    }

    process.exit(1);
  }
}

// Run tests
testSendGridConnection().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
