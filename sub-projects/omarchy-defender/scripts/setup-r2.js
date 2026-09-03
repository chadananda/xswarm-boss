#!/usr/bin/env node

/**
 * R2 Bucket Setup Script
 * Creates and configures Cloudflare R2 bucket for Omarchy Defender assets
 */

import { readFileSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '..');

// Load environment
const loadEnv = () => {
  const envPath = resolve(PROJECT_ROOT, '.env');
  if (!existsSync(envPath)) {
    console.error('Error: .env file not found');
    process.exit(1);
  }

  const envContent = readFileSync(envPath, 'utf-8');
  const env = {};

  for (const line of envContent.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    const eqIndex = trimmed.indexOf('=');
    if (eqIndex === -1) continue;

    const key = trimmed.substring(0, eqIndex).trim();
    let value = trimmed.substring(eqIndex + 1).trim();

    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    env[key] = value;
  }

  return env;
};

const env = loadEnv();
const BUCKET_NAME = 'omarchy-defender-assets';

async function main() {
  console.log(`
╔══════════════════════════════════════════════════════════════╗
║           OMARCHY DEFENDER - R2 BUCKET SETUP                ║
╚══════════════════════════════════════════════════════════════╝
`);

  if (!env.CLOUDFLARE_ACCOUNT_ID || !env.CLOUDFLARE_API_TOKEN) {
    console.error('Error: Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN in .env');
    process.exit(1);
  }

  const accountId = env.CLOUDFLARE_ACCOUNT_ID;
  const apiToken = env.CLOUDFLARE_API_TOKEN;

  // Check if bucket exists
  console.log(`Checking for existing bucket: ${BUCKET_NAME}...`);

  const listResponse = await fetch(
    `https://api.cloudflare.com/client/v4/accounts/${accountId}/r2/buckets`,
    {
      headers: {
        'Authorization': `Bearer ${apiToken}`
      }
    }
  );

  if (!listResponse.ok) {
    const error = await listResponse.json().catch(() => ({}));
    console.error('Failed to list buckets:', error.errors?.[0]?.message || listResponse.statusText);
    process.exit(1);
  }

  const bucketsData = await listResponse.json();
  const existingBucket = bucketsData.result?.buckets?.find(b => b.name === BUCKET_NAME);

  if (existingBucket) {
    console.log(`✅ Bucket "${BUCKET_NAME}" already exists`);
    console.log(`   Created: ${existingBucket.creation_date}`);
    console.log(`   Location: ${existingBucket.location || 'auto'}`);
  } else {
    // Create bucket
    console.log(`Creating bucket: ${BUCKET_NAME}...`);

    const createResponse = await fetch(
      `https://api.cloudflare.com/client/v4/accounts/${accountId}/r2/buckets`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: BUCKET_NAME,
          locationHint: 'wnam' // Western North America
        })
      }
    );

    if (!createResponse.ok) {
      const error = await createResponse.json().catch(() => ({}));
      console.error('Failed to create bucket:', error.errors?.[0]?.message || createResponse.statusText);
      process.exit(1);
    }

    console.log(`✅ Bucket "${BUCKET_NAME}" created successfully`);
  }

  // Configure CORS for the bucket
  console.log('\nConfiguring CORS...');

  const corsResponse = await fetch(
    `https://api.cloudflare.com/client/v4/accounts/${accountId}/r2/buckets/${BUCKET_NAME}/cors`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${apiToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        cors_rules: [
          {
            allowed_origins: ['*'],
            allowed_methods: ['GET', 'HEAD'],
            allowed_headers: ['*'],
            max_age_seconds: 86400
          }
        ]
      })
    }
  );

  if (corsResponse.ok) {
    console.log('✅ CORS configured');
  } else {
    const error = await corsResponse.json().catch(() => ({}));
    console.warn('⚠️  CORS config failed (may require manual setup):', error.errors?.[0]?.message);
  }

  console.log(`
════════════════════════════════════════════════════════════════

✅ R2 Bucket Setup Complete!

Bucket Name: ${BUCKET_NAME}
Public URL:  https://r2.xswarm.ai/${BUCKET_NAME}/

Next Steps:
1. Configure a custom domain in Cloudflare Dashboard if needed
2. Run 'npm run upload-assets' to upload assets
3. Update config.json to use production asset URLs

════════════════════════════════════════════════════════════════
`);
}

main().catch(console.error);
