#!/usr/bin/env node

/**
 * Setup Cloudflare Workers Secrets
 *
 * Reads secrets from root .env file and pushes them to Cloudflare Workers.
 * This is a one-time setup script for production deployment.
 *
 * Usage:
 *   pnpm setup:secrets
 */

import 'dotenv/config';
import { execSync } from 'child_process';
import { existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '..');
const serverDir = join(rootDir, 'packages', 'server');

// Secrets to push to Workers (must exist in .env)
// Note: Account SIDs and database URLs come from config.toml (not secrets)
const REQUIRED_SECRETS = [
  'TWILIO_AUTH_TOKEN_TEST',
  'TWILIO_AUTH_TOKEN_LIVE',
  'SENDGRID_API_KEY_TEST',
  'SENDGRID_API_KEY_LIVE',
  'STRIPE_SECRET_KEY_TEST',
  'STRIPE_WEBHOOK_SECRET_TEST',
  'STRIPE_SECRET_KEY_LIVE',
  'STRIPE_WEBHOOK_SECRET_LIVE',
  'TURSO_AUTH_TOKEN',
  'S3_ACCESS_KEY_ID',
  'S3_SECRET_ACCESS_KEY',
];

// Optional secrets (won't fail if missing)
const OPTIONAL_SECRETS = [
  'CLOUDFLARE_API_TOKEN',
];

console.log('🔐 Cloudflare Workers Secret Setup\n');

// Validate environment
if (!existsSync(join(rootDir, '.env'))) {
  console.error('❌ .env file not found in project root');
  console.error('   Please create .env from .env.example and fill in your secrets.');
  process.exit(1);
}

if (!existsSync(serverDir)) {
  console.error('❌ packages/server directory not found');
  console.error('   Please run this script from the project root.');
  process.exit(1);
}

// Check if wrangler is installed
try {
  execSync('which wrangler', { stdio: 'ignore' });
} catch (error) {
  console.error('❌ Wrangler CLI not found');
  console.error('   Install with: pnpm install');
  process.exit(1);
}

// Collect secrets from environment
const secrets = {};
const missing = [];

// Required secrets
for (const key of REQUIRED_SECRETS) {
  const value = process.env[key];
  if (value && value !== `your_${key.toLowerCase()}_here` && !value.includes('xxxxx')) {
    secrets[key] = value;
  } else {
    missing.push(key);
  }
}

// Optional secrets (don't fail if missing)
for (const key of OPTIONAL_SECRETS) {
  const value = process.env[key];
  if (value && value !== `your_${key.toLowerCase()}_here` && !value.includes('xxxxx')) {
    secrets[key] = value;
  }
}

// Report status
console.log('📋 Found secrets in .env:');
Object.keys(secrets).forEach(key => {
  const value = secrets[key];
  const preview = value.substring(0, 10) + '...';
  console.log(`  ✓ ${key}: ${preview}`);
});

if (missing.length > 0) {
  console.log('\n⚠️  Missing or unconfigured secrets:');
  missing.forEach(key => console.log(`  - ${key}`));
  console.log('\n⚠️  These secrets will NOT be pushed to Workers.');
  console.log('   Update your .env file and run this script again.\n');
}

// Confirm before pushing
console.log(`\n📤 Ready to push ${Object.keys(secrets).length} secrets to Cloudflare Workers.`);
console.log('   This will overwrite any existing secrets with the same names.\n');

// Auto-confirm in CI or non-interactive mode
const autoConfirm = process.env.CI === 'true' || process.argv.includes('--yes');

if (!autoConfirm) {
  const readline = await import('readline');
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  const answer = await new Promise(resolve => {
    rl.question('Continue? (yes/no): ', resolve);
  });
  rl.close();

  if (answer.toLowerCase() !== 'yes' && answer.toLowerCase() !== 'y') {
    console.log('\n❌ Aborted. No secrets were pushed.');
    process.exit(0);
  }
}

// Push secrets to Workers
console.log('\n🚀 Pushing secrets to Cloudflare Workers...\n');

let successCount = 0;
let failCount = 0;

for (const [key, value] of Object.entries(secrets)) {
  try {
    console.log(`  Pushing ${key}...`);

    // Use wrangler secret put with echo piping
    execSync(
      `echo "${value}" | wrangler secret put ${key}`,
      {
        cwd: serverDir,
        stdio: 'pipe',
      }
    );

    console.log(`  ✓ ${key} pushed successfully`);
    successCount++;

  } catch (error) {
    console.error(`  ✗ Failed to push ${key}: ${error.message}`);
    failCount++;
  }
}

// Summary
console.log(`\n${successCount === Object.keys(secrets).length ? '✅' : '⚠️'} Secret setup complete!`);
console.log(`  Success: ${successCount}`);
if (failCount > 0) {
  console.log(`  Failed: ${failCount}`);
}

if (missing.length > 0) {
  console.log(`\n⚠️  ${missing.length} secrets were not configured.`);
  console.log('   Your Worker may fail at runtime if these secrets are required.');
}

console.log('\n📝 Next steps:');
console.log('  1. Deploy your Worker: pnpm deploy:server');
console.log('  2. Test webhooks: curl https://your-worker.workers.dev/health');
console.log('  3. Configure webhook URLs in Twilio and Stripe dashboards\n');
