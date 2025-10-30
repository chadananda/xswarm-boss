#!/usr/bin/env node

/**
 * Local Development Webhook Forwarding
 *
 * Forwards Stripe webhooks to your local development server.
 * Supports multiple forwarding methods:
 *   1. Stripe CLI (default, easiest)
 *   2. Cloudflare Tunnel (persistent URLs)
 *
 * Usage:
 *   pnpm dev:webhooks                    # Use Stripe CLI (default)
 *   pnpm dev:webhooks --method stripe    # Explicit Stripe CLI
 *   pnpm dev:webhooks --method cloudflare # Use Cloudflare Tunnel
 *   pnpm dev:webhooks --port 3000        # Custom local port
 *
 * The script will:
 *   1. Start the forwarding service
 *   2. Display the webhook signing secret
 *   3. Show example .env configuration
 */

import { spawn, execSync } from 'child_process';
import { existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const stripeCliPath = join(__dirname, 'bin', 'stripe');

// Parse command line arguments
const args = process.argv.slice(2);
const method = args.find(arg => arg.startsWith('--method='))?.replace('--method=', '') || 'stripe';
const port = args.find(arg => arg.startsWith('--port='))?.replace('--port=', '') || '8787';
const localUrl = `http://localhost:${port}/stripe/webhook`;

console.log('🔗 Local Webhook Forwarding\n');
console.log(`📍 Local server: ${localUrl}`);
console.log(`🔧 Method: ${method}\n`);

/**
 * Check if Stripe CLI is available (local binary)
 */
function checkStripeCLI() {
  return existsSync(stripeCliPath);
}

/**
 * Start Stripe CLI webhook forwarding
 */
function startStripeCLI() {
  console.log('🚀 Starting Stripe CLI webhook forwarding...\n');

  // Check if Stripe CLI is installed (local binary)
  if (!checkStripeCLI()) {
    console.error('❌ Stripe CLI not found');
    console.error('\n📦 Install dependencies:');
    console.error('   pnpm install');
    console.error('\n   (This will download Stripe CLI automatically)\n');
    process.exit(1);
  }

  // Check if logged in
  try {
    execSync(`"${stripeCliPath}" config --list`, { stdio: 'ignore' });
  } catch {
    console.error('❌ Not logged in to Stripe CLI');
    console.error('\n🔐 Login to Stripe:');
    console.error(`   "${stripeCliPath}" login\n`);
    process.exit(1);
  }

  console.log('✓ Stripe CLI ready\n');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('⚠️  IMPORTANT: Copy the webhook signing secret below to your .env file:');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  // Start Stripe listen using local binary
  const stripeProcess = spawn(stripeCliPath, ['listen', '--forward-to', localUrl], {
    stdio: 'inherit',
  });

  stripeProcess.on('error', (error) => {
    console.error('❌ Failed to start Stripe CLI:', error.message);
    process.exit(1);
  });

  stripeProcess.on('close', (code) => {
    if (code !== 0) {
      console.error(`\n❌ Stripe CLI exited with code ${code}`);
      process.exit(code);
    }
  });

  // Handle graceful shutdown
  process.on('SIGINT', () => {
    console.log('\n\n👋 Stopping webhook forwarding...');
    stripeProcess.kill();
    process.exit(0);
  });

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('💡 Testing webhooks:');
  console.log(`   "${stripeCliPath}" trigger customer.subscription.created`);
  console.log(`   "${stripeCliPath}" trigger invoice.payment_succeeded`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
}

/**
 * Start Cloudflare Tunnel forwarding
 */
function startCloudflareTunnel() {
  console.log('🚀 Starting Cloudflare Tunnel...\n');

  // Check if cloudflared is installed
  if (!commandExists('cloudflared')) {
    console.error('❌ cloudflared not found');
    console.error('\n📦 Install cloudflared:');
    console.error('   macOS:   brew install cloudflared');
    console.error('   Linux:   Download from https://github.com/cloudflare/cloudflared/releases');
    console.error('   Windows: winget install --id Cloudflare.cloudflared\n');
    process.exit(1);
  }

  console.log('✓ cloudflared ready\n');
  console.log('🌐 Starting tunnel...\n');

  // Start cloudflared tunnel
  const tunnelProcess = spawn('cloudflared', ['tunnel', '--url', `http://localhost:${port}`], {
    stdio: 'inherit',
  });

  tunnelProcess.on('error', (error) => {
    console.error('❌ Failed to start cloudflared:', error.message);
    process.exit(1);
  });

  tunnelProcess.on('close', (code) => {
    if (code !== 0) {
      console.error(`\n❌ cloudflared exited with code ${code}`);
      process.exit(code);
    }
  });

  // Handle graceful shutdown
  process.on('SIGINT', () => {
    console.log('\n\n👋 Stopping tunnel...');
    tunnelProcess.kill();
    process.exit(0);
  });

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('⚠️  NEXT STEPS:');
  console.log('1. Copy the public URL shown above (e.g., https://xxxxx.trycloudflare.com)');
  console.log('2. Go to Stripe Dashboard → Developers → Webhooks');
  console.log('3. Add endpoint: https://xxxxx.trycloudflare.com/stripe/webhook');
  console.log('4. Copy the webhook signing secret to .env');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
}

// Main execution
switch (method) {
  case 'stripe':
    startStripeCLI();
    break;

  case 'cloudflare':
    startCloudflareTunnel();
    break;

  default:
    console.error(`❌ Unknown method: ${method}`);
    console.error('\nSupported methods:');
    console.error('  --method=stripe      Stripe CLI (default)');
    console.error('  --method=cloudflare  Cloudflare Tunnel\n');
    process.exit(1);
}
