#!/usr/bin/env node
/**
 * SendGrid Configuration Diagnostics
 *
 * Comprehensive diagnostic tool to identify SendGrid configuration issues
 * causing "554 5.7.1: Relay access denied" errors for inbound email.
 *
 * This script checks:
 * 1. API Key validity and permissions
 * 2. Account tier and limitations
 * 3. Inbound Parse webhook configuration
 * 4. Domain authentication status
 * 5. Mail settings and restrictions
 * 6. IP whitelisting requirements
 */

import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { parse as parseToml } from 'smol-toml';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

// Load environment variables
import 'dotenv/config';

const SENDGRID_API_KEY = process.env.SENDGRID_API_KEY;

// Load config from users.json (actual runtime config)
const usersConfigPath = join(projectRoot, 'packages/server/src/config/users.json');
const usersConfig = JSON.parse(readFileSync(usersConfigPath, 'utf-8'));

const BOSS_EMAIL = usersConfig.users[0].boss_email; // chadananda@xswarm.ai
const DOMAIN = BOSS_EMAIL.split('@')[1]; // xswarm.ai

console.log('╔══════════════════════════════════════════════════════════════════╗');
console.log('║       SendGrid Configuration Diagnostics                         ║');
console.log('╚══════════════════════════════════════════════════════════════════╝\n');

if (!SENDGRID_API_KEY) {
  console.error('❌ SENDGRID_API_KEY not found in environment');
  process.exit(1);
}

const diagnosticResults = {
  apiKey: null,
  accountInfo: null,
  parseWebhooks: null,
  domainAuth: null,
  mailSettings: null,
  ipAccessManagement: null,
  enforced2FA: null,
  issues: [],
  warnings: [],
  recommendations: [],
};

/**
 * Make SendGrid API request
 */
async function sendgridRequest(endpoint, method = 'GET', body = null) {
  const options = {
    method,
    headers: {
      'Authorization': `Bearer ${SENDGRID_API_KEY}`,
      'Content-Type': 'application/json',
    },
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`https://api.sendgrid.com/v3${endpoint}`, options);

  return {
    ok: response.ok,
    status: response.status,
    data: response.ok ? await response.json() : null,
    error: !response.ok ? await response.text() : null,
  };
}

/**
 * Test 1: Verify API Key and Permissions
 */
async function testApiKey() {
  console.log('📋 Test 1: API Key Validation');
  console.log('─────────────────────────────────────────────────────────────────');

  try {
    const result = await sendgridRequest('/user/profile');

    if (!result.ok) {
      diagnosticResults.issues.push('API key is invalid or expired');
      console.log('❌ API Key: INVALID');
      console.log(`   Status: ${result.status}`);
      console.log(`   Error: ${result.error}\n`);
      return false;
    }

    diagnosticResults.apiKey = result.data;
    console.log('✅ API Key: VALID');
    console.log(`   Email: ${result.data.email}`);
    console.log(`   Account Type: ${result.data.type || 'unknown'}`);

    // Check API key scopes
    const scopesResult = await sendgridRequest('/scopes');
    if (scopesResult.ok) {
      const scopes = scopesResult.data.scopes || [];
      console.log(`   Scopes: ${scopes.length} permissions`);

      // Check for critical permissions
      const requiredScopes = ['mail.send', 'user.profile.read'];
      const missingScopes = requiredScopes.filter(s => !scopes.includes(s));

      if (missingScopes.length > 0) {
        diagnosticResults.warnings.push(`API key missing scopes: ${missingScopes.join(', ')}`);
        console.log(`   ⚠️  Missing scopes: ${missingScopes.join(', ')}`);
      }
    }

    console.log('');
    return true;
  } catch (error) {
    diagnosticResults.issues.push(`API key test failed: ${error.message}`);
    console.log('❌ API Key test failed:', error.message, '\n');
    return false;
  }
}

/**
 * Test 2: Check Account Information and Tier
 */
async function testAccountInfo() {
  console.log('📋 Test 2: Account Information');
  console.log('─────────────────────────────────────────────────────────────────');

  try {
    const result = await sendgridRequest('/user/account');

    if (!result.ok) {
      console.log('⚠️  Could not retrieve account information');
      console.log(`   Status: ${result.status}\n`);
      return;
    }

    diagnosticResults.accountInfo = result.data;
    const account = result.data;

    console.log('✅ Account Information Retrieved');
    console.log(`   Type: ${account.type || 'unknown'}`);
    console.log(`   Reputation: ${account.reputation || 'N/A'}`);

    // Check if free tier has inbound parse limitations
    if (account.type === 'free') {
      diagnosticResults.warnings.push('Free tier account - may have inbound parse limitations');
      console.log('   ⚠️  FREE TIER ACCOUNT');
      console.log('   Note: Free tier may have limitations on inbound email parsing');
      diagnosticResults.recommendations.push(
        'Consider upgrading to paid tier for full inbound parse functionality'
      );
    }

    console.log('');
  } catch (error) {
    console.log('⚠️  Account info test failed:', error.message, '\n');
  }
}

/**
 * Test 3: Check Inbound Parse Webhook Configuration
 */
async function testParseWebhooks() {
  console.log('📋 Test 3: Inbound Parse Webhook Configuration');
  console.log('─────────────────────────────────────────────────────────────────');

  try {
    const result = await sendgridRequest('/user/webhooks/parse/settings');

    if (!result.ok) {
      diagnosticResults.issues.push('Could not retrieve inbound parse settings');
      console.log('❌ Failed to retrieve parse webhook settings');
      console.log(`   Status: ${result.status}`);
      console.log(`   Error: ${result.error}\n`);
      return;
    }

    diagnosticResults.parseWebhooks = result.data;
    const settings = result.data.result || [];

    if (settings.length === 0) {
      diagnosticResults.issues.push('No inbound parse webhooks configured');
      console.log('❌ No inbound parse webhooks configured');
      console.log('   This is likely the root cause of the relay access denied error\n');
      diagnosticResults.recommendations.push(
        'Configure inbound parse webhook at https://app.sendgrid.com/settings/parse'
      );
      return;
    }

    console.log(`✅ Found ${settings.length} parse webhook(s):`);

    for (let i = 0; i < settings.length; i++) {
      const webhook = settings[i];
      console.log(`\n   Webhook ${i + 1}:`);
      console.log(`   Hostname: ${webhook.hostname || 'N/A'}`);
      console.log(`   URL: ${webhook.url || 'N/A'}`);
      console.log(`   Spam Check: ${webhook.spam_check ? 'Enabled' : 'Disabled'}`);
      console.log(`   Send Raw: ${webhook.send_raw ? 'Yes' : 'No'}`);

      // Check if webhook matches our expected configuration
      const expectedHost = BOSS_EMAIL.split('@')[0]; // 'chadananda'
      const expectedDomain = BOSS_EMAIL.split('@')[1]; // 'xswarm.ai'

      if (!webhook.hostname.includes(expectedHost)) {
        diagnosticResults.warnings.push(
          `Webhook hostname '${webhook.hostname}' doesn't match expected '${expectedHost}'`
        );
        console.log(`   ⚠️  Hostname doesn't match expected value: ${expectedHost}`);
      }

      if (!webhook.send_raw) {
        diagnosticResults.warnings.push(
          `Webhook '${webhook.hostname}' should have send_raw enabled for full MIME message`
        );
        console.log(`   ⚠️  Send Raw should be enabled for full email parsing`);
      }
    }

    console.log('');
  } catch (error) {
    diagnosticResults.issues.push(`Parse webhook test failed: ${error.message}`);
    console.log('❌ Parse webhook test failed:', error.message, '\n');
  }
}

/**
 * Test 4: Check Domain Authentication
 */
async function testDomainAuth() {
  console.log('📋 Test 4: Domain Authentication');
  console.log('─────────────────────────────────────────────────────────────────');

  try {
    const result = await sendgridRequest('/whitelabel/domains');

    if (!result.ok) {
      console.log('⚠️  Could not retrieve domain authentication settings');
      console.log(`   Status: ${result.status}\n`);
      return;
    }

    diagnosticResults.domainAuth = result.data;
    const domains = result.data || [];

    if (domains.length === 0) {
      diagnosticResults.warnings.push('No authenticated domains found');
      console.log('⚠️  No authenticated domains');
      console.log('   Domain authentication improves deliverability\n');
      diagnosticResults.recommendations.push(
        'Authenticate your domain at https://app.sendgrid.com/settings/sender_auth'
      );
      return;
    }

    console.log(`✅ Found ${domains.length} authenticated domain(s):`);

    for (const domain of domains) {
      console.log(`\n   Domain: ${domain.domain}`);
      console.log(`   Valid: ${domain.valid ? 'Yes' : 'No'}`);
      console.log(`   Default: ${domain.default ? 'Yes' : 'No'}`);

      if (!domain.valid) {
        diagnosticResults.warnings.push(`Domain '${domain.domain}' is not validated`);
        console.log('   ⚠️  Domain validation incomplete - check DNS records');
      }

      // Check if our domain is authenticated
      if (domain.domain === DOMAIN) {
        console.log('   ✅ Your domain is configured');
      }
    }

    console.log('');
  } catch (error) {
    console.log('⚠️  Domain auth test failed:', error.message, '\n');
  }
}

/**
 * Test 5: Check Mail Settings
 */
async function testMailSettings() {
  console.log('📋 Test 5: Mail Settings');
  console.log('─────────────────────────────────────────────────────────────────');

  try {
    // Check various mail settings that could affect inbound parsing
    const settings = [
      { endpoint: '/mail_settings/bounce_purge', name: 'Bounce Purge' },
      { endpoint: '/mail_settings/forward_spam', name: 'Forward Spam' },
      { endpoint: '/mail_settings/address_whitelist', name: 'Address Whitelist' },
    ];

    diagnosticResults.mailSettings = {};

    for (const setting of settings) {
      const result = await sendgridRequest(setting.endpoint);

      if (result.ok) {
        diagnosticResults.mailSettings[setting.name] = result.data;
        console.log(`✅ ${setting.name}:`);
        console.log(`   Enabled: ${result.data.enabled ? 'Yes' : 'No'}`);

        if (setting.name === 'Address Whitelist' && result.data.enabled) {
          const list = result.data.list || [];
          if (list.length > 0) {
            console.log(`   Whitelisted: ${list.join(', ')}`);
          }
        }
      } else {
        console.log(`⚠️  ${setting.name}: Could not retrieve`);
      }
    }

    console.log('');
  } catch (error) {
    console.log('⚠️  Mail settings test failed:', error.message, '\n');
  }
}

/**
 * Test 6: Check IP Access Management
 */
async function testIpAccessManagement() {
  console.log('📋 Test 6: IP Access Management');
  console.log('─────────────────────────────────────────────────────────────────');

  try {
    const result = await sendgridRequest('/access_settings/whitelist');

    if (!result.ok) {
      console.log('⚠️  Could not retrieve IP whitelist settings');
      console.log(`   Status: ${result.status}\n`);
      return;
    }

    diagnosticResults.ipAccessManagement = result.data;
    const whitelist = result.data.result || [];

    if (whitelist.length === 0) {
      console.log('✅ No IP whitelist restrictions (API accessible from any IP)');
    } else {
      console.log(`⚠️  IP Whitelist Active (${whitelist.length} entries)`);
      diagnosticResults.warnings.push('IP whitelist is active - may affect webhook delivery');

      for (const entry of whitelist) {
        console.log(`   ${entry.ip}: ${entry.description || 'No description'}`);
      }

      diagnosticResults.recommendations.push(
        'Ensure webhook server IP is in whitelist or disable IP restrictions'
      );
    }

    console.log('');
  } catch (error) {
    console.log('⚠️  IP access test failed:', error.message, '\n');
  }
}

/**
 * Test 7: Check MX Records via DNS
 */
async function testMxRecords() {
  console.log('📋 Test 7: MX Record Configuration');
  console.log('─────────────────────────────────────────────────────────────────');

  try {
    // Note: This requires DNS resolution which isn't available in Node.js fetch API
    // We'll provide instructions instead

    const subdomain = BOSS_EMAIL.split('@')[0];
    const domain = BOSS_EMAIL.split('@')[1];
    const fullHostname = `${subdomain}.${domain}`;

    console.log(`Expected MX Record Configuration:`);
    console.log(`   Host: ${subdomain} (or ${fullHostname})`);
    console.log(`   Type: MX`);
    console.log(`   Priority: 10`);
    console.log(`   Value: mx.sendgrid.net`);
    console.log('');
    console.log('⚠️  DNS MX record must be configured for inbound email to work');
    console.log('   Check your DNS settings at your domain registrar');
    console.log('   You can verify with: dig MX ' + fullHostname);
    console.log('');

    diagnosticResults.recommendations.push(
      `Verify MX record is configured: dig MX ${fullHostname}`
    );
  } catch (error) {
    console.log('⚠️  MX record check failed:', error.message, '\n');
  }
}

/**
 * Generate diagnostic report
 */
function generateReport() {
  console.log('╔══════════════════════════════════════════════════════════════════╗');
  console.log('║                    DIAGNOSTIC SUMMARY                            ║');
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');

  // Critical Issues
  if (diagnosticResults.issues.length > 0) {
    console.log('🚨 CRITICAL ISSUES:');
    diagnosticResults.issues.forEach((issue, i) => {
      console.log(`   ${i + 1}. ${issue}`);
    });
    console.log('');
  } else {
    console.log('✅ No critical issues found\n');
  }

  // Warnings
  if (diagnosticResults.warnings.length > 0) {
    console.log('⚠️  WARNINGS:');
    diagnosticResults.warnings.forEach((warning, i) => {
      console.log(`   ${i + 1}. ${warning}`);
    });
    console.log('');
  }

  // Recommendations
  if (diagnosticResults.recommendations.length > 0) {
    console.log('💡 RECOMMENDATIONS:');
    diagnosticResults.recommendations.forEach((rec, i) => {
      console.log(`   ${i + 1}. ${rec}`);
    });
    console.log('');
  }

  // Root Cause Analysis
  console.log('🔍 ROOT CAUSE ANALYSIS:');
  console.log('─────────────────────────────────────────────────────────────────');
  console.log('Error: "554 5.7.1: Relay access denied"');
  console.log('');
  console.log('This error occurs when SendGrid receives an email but:');
  console.log('1. No inbound parse webhook is configured for the recipient, OR');
  console.log('2. The MX record is not pointing to mx.sendgrid.net, OR');
  console.log('3. The subdomain in the inbound parse doesn\'t match the email, OR');
  console.log('4. Free tier account limitations prevent inbound parsing');
  console.log('');

  // Specific diagnosis
  if (!diagnosticResults.parseWebhooks ||
      (diagnosticResults.parseWebhooks.result && diagnosticResults.parseWebhooks.result.length === 0)) {
    console.log('⚠️  PRIMARY ISSUE: No inbound parse webhook configured');
    console.log('   Solution: Configure webhook at https://app.sendgrid.com/settings/parse');
    console.log('');
  }

  if (diagnosticResults.accountInfo && diagnosticResults.accountInfo.type === 'free') {
    console.log('⚠️  POTENTIAL ISSUE: Free tier account');
    console.log('   Some SendGrid free tier accounts have inbound parse disabled');
    console.log('   Solution: Upgrade to paid plan or contact SendGrid support');
    console.log('');
  }

  console.log('📖 NEXT STEPS:');
  console.log('─────────────────────────────────────────────────────────────────');
  console.log('1. Review the issues and warnings above');
  console.log('2. Run: node scripts/fix-sendgrid.js (to apply automated fixes)');
  console.log('3. If issues persist, contact SendGrid support with this report');
  console.log('');
}

/**
 * Main diagnostic routine
 */
async function runDiagnostics() {
  const apiKeyValid = await testApiKey();

  if (!apiKeyValid) {
    console.log('Cannot continue diagnostics without valid API key.');
    process.exit(1);
  }

  await testAccountInfo();
  await testParseWebhooks();
  await testDomainAuth();
  await testMailSettings();
  await testIpAccessManagement();
  await testMxRecords();

  generateReport();
}

// Run diagnostics
runDiagnostics().catch(error => {
  console.error('Fatal error running diagnostics:', error);
  process.exit(1);
});
