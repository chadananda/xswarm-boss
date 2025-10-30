#!/usr/bin/env node
/**
 * Boss AI - Simple Environment Setup
 *
 * Creates .env file from .env.example and guides user through configuration.
 * This is a simple, unified setup script that configures everything in one go.
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { resolve } from 'path';
import { createInterface } from 'readline';

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logSection(title) {
  console.log('');
  log('='.repeat(80), 'cyan');
  log(title, 'cyan');
  log('='.repeat(80), 'cyan');
  console.log('');
}

// Create readline interface for user input
const rl = createInterface({
  input: process.stdin,
  output: process.stdout,
});

function ask(question) {
  return new Promise((resolve) => {
    rl.question(`${colors.blue}${question}${colors.reset} `, resolve);
  });
}

async function main() {
  log('\n🤖 Boss AI - Environment Setup', 'green');
  log('This script will help you configure your Boss AI environment.\n', 'green');

  const envPath = resolve(process.cwd(), '.env');
  const envExamplePath = resolve(process.cwd(), '.env.example');

  // Check if .env already exists
  if (existsSync(envPath)) {
    log('⚠️  .env file already exists', 'yellow');
    const overwrite = await ask('Do you want to overwrite it? (yes/no): ');
    if (overwrite.toLowerCase() !== 'yes') {
      log('Setup cancelled.', 'yellow');
      rl.close();
      return;
    }
  }

  // Read .env.example
  if (!existsSync(envExamplePath)) {
    log('❌ .env.example file not found!', 'red');
    log('Please make sure you are in the project root directory.', 'red');
    rl.close();
    process.exit(1);
  }

  const envExample = readFileSync(envExamplePath, 'utf-8');
  let envContent = envExample;

  logSection('Environment Configuration');

  log('We will now configure your environment variables.', 'cyan');
  log('Press Enter to keep the default value shown in brackets.', 'cyan');
  log('You can skip optional values by pressing Enter.\n', 'cyan');

  // Required secrets
  const secrets = [
    {
      key: 'ANTHROPIC_API_KEY',
      description: 'Anthropic API Key (Claude)',
      required: true,
      url: 'https://console.anthropic.com/',
      example: 'sk-ant-xxxxx...',
    },
    {
      key: 'OPENAI_API_KEY',
      description: 'OpenAI API Key (for embeddings)',
      required: true,
      url: 'https://platform.openai.com/',
      example: 'sk-xxxxx...',
    },
    {
      key: 'TWILIO_AUTH_TOKEN_TEST',
      description: 'Twilio Test Auth Token',
      required: true,
      url: 'https://console.twilio.com/',
      example: 'your_test_auth_token_here',
    },
    {
      key: 'SENDGRID_API_KEY_TEST',
      description: 'SendGrid Test API Key',
      required: true,
      url: 'https://sendgrid.com/',
      example: 'SG.xxxxx...',
    },
    {
      key: 'STRIPE_SECRET_KEY_TEST',
      description: 'Stripe Test Secret Key',
      required: true,
      url: 'https://dashboard.stripe.com/',
      example: 'sk_test_xxxxx...',
    },
    {
      key: 'TURSO_AUTH_TOKEN',
      description: 'Turso Database Auth Token',
      required: true,
      url: 'https://turso.tech/',
      example: 'eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...',
    },
    {
      key: 'S3_ACCESS_KEY_ID',
      description: 'Cloudflare R2 Access Key ID',
      required: true,
      url: 'https://dash.cloudflare.com/',
      example: 'your_access_key_here',
    },
    {
      key: 'S3_SECRET_ACCESS_KEY',
      description: 'Cloudflare R2 Secret Access Key',
      required: true,
      url: 'https://dash.cloudflare.com/',
      example: 'your_secret_access_key_here',
    },
    {
      key: 'CLOUDFLARE_API_TOKEN',
      description: 'Cloudflare API Token (for deployment)',
      required: true,
      url: 'https://dash.cloudflare.com/',
      example: 'your_cloudflare_api_token_here',
    },
  ];

  // Production secrets (optional)
  const productionSecrets = [
    {
      key: 'TWILIO_AUTH_TOKEN_LIVE',
      description: 'Twilio Live Auth Token (production)',
      required: false,
      url: 'https://console.twilio.com/',
      example: 'your_live_auth_token_here',
    },
    {
      key: 'SENDGRID_API_KEY_LIVE',
      description: 'SendGrid Live API Key (production)',
      required: false,
      url: 'https://sendgrid.com/',
      example: 'SG.xxxxx...',
    },
    {
      key: 'STRIPE_SECRET_KEY_LIVE',
      description: 'Stripe Live Secret Key (production)',
      required: false,
      url: 'https://dashboard.stripe.com/',
      example: 'sk_live_xxxxx...',
    },
  ];

  // Configure required secrets
  logSection('Required Secrets');
  log('These are required for Boss AI to function.\n', 'cyan');

  for (const secret of secrets) {
    log(`${secret.description}`, 'yellow');
    log(`Get it from: ${secret.url}`, 'cyan');
    log(`Example: ${secret.example}\n`, 'cyan');

    const value = await ask(`Enter ${secret.key}: `);

    if (value.trim()) {
      // Replace the placeholder in envContent
      const regex = new RegExp(`${secret.key}=.*`, 'g');
      envContent = envContent.replace(regex, `${secret.key}=${value.trim()}`);
      log(`✅ ${secret.key} configured\n`, 'green');
    } else if (secret.required) {
      log(`⚠️  ${secret.key} is required but not provided. You'll need to set it later.\n`, 'yellow');
    }
  }

  // Ask about production secrets
  logSection('Production Secrets (Optional)');
  log('These are only needed when you are ready to go live.\n', 'cyan');

  const setupProduction = await ask('Do you want to configure production secrets now? (yes/no): ');

  if (setupProduction.toLowerCase() === 'yes') {
    for (const secret of productionSecrets) {
      log(`\n${secret.description}`, 'yellow');
      log(`Get it from: ${secret.url}`, 'cyan');
      log(`Example: ${secret.example}\n`, 'cyan');

      const value = await ask(`Enter ${secret.key}: `);

      if (value.trim()) {
        const regex = new RegExp(`# ${secret.key}=.*`, 'g');
        envContent = envContent.replace(regex, `${secret.key}=${value.trim()}`);
        log(`✅ ${secret.key} configured`, 'green');
      } else {
        log(`⏭️  Skipping ${secret.key}`, 'yellow');
      }
    }
  } else {
    log('Skipping production secrets. You can add them later.', 'yellow');
  }

  // Write .env file
  writeFileSync(envPath, envContent, 'utf-8');

  logSection('Setup Complete!');
  log('✅ .env file created successfully', 'green');
  log(`📁 Location: ${envPath}\n`, 'cyan');

  log('Next steps:', 'yellow');
  log('  1. Review your .env file and add any missing values', 'cyan');
  log('  2. Run: pnpm install', 'cyan');
  log('  3. Run: pnpm --filter @xswarm/server run setup-db', 'cyan');
  log('  4. Run: ./deploy.sh', 'cyan');
  log('', 'reset');

  log('💡 Pro tip: Never commit your .env file to version control!', 'yellow');
  log('', 'reset');

  rl.close();
}

main().catch((error) => {
  log(`\n❌ Error: ${error.message}`, 'red');
  rl.close();
  process.exit(1);
});
