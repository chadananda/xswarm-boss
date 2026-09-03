#!/usr/bin/env node

/**
 * Upload Assets to R2
 * Uploads all assets from /assets to Cloudflare R2 bucket
 */

import { readFileSync, readdirSync, statSync, existsSync } from 'fs';
import { resolve, dirname, join, extname, basename } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '..');
const ASSETS_DIR = resolve(PROJECT_ROOT, 'assets');

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

const MIME_TYPES = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
  '.mp3': 'audio/mpeg',
  '.wav': 'audio/wav',
  '.ogg': 'audio/ogg',
  '.json': 'application/json'
};

// Get all files recursively
function getAllFiles(dir, baseDir = dir) {
  const files = [];

  if (!existsSync(dir)) return files;

  const items = readdirSync(dir);
  for (const item of items) {
    if (item.startsWith('.')) continue;

    const fullPath = join(dir, item);
    const stat = statSync(fullPath);

    if (stat.isDirectory()) {
      files.push(...getAllFiles(fullPath, baseDir));
    } else {
      const relativePath = fullPath.slice(baseDir.length + 1);
      files.push({
        localPath: fullPath,
        key: relativePath.replace(/\\/g, '/'), // Normalize for URLs
        size: stat.size
      });
    }
  }

  return files;
}

// Upload a single file
async function uploadFile(file, accountId, apiToken) {
  const mimeType = MIME_TYPES[extname(file.localPath).toLowerCase()] || 'application/octet-stream';
  const fileBuffer = readFileSync(file.localPath);

  const response = await fetch(
    `https://api.cloudflare.com/client/v4/accounts/${accountId}/r2/buckets/${BUCKET_NAME}/objects/${encodeURIComponent(file.key)}`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${apiToken}`,
        'Content-Type': mimeType
      },
      body: fileBuffer
    }
  );

  return response.ok;
}

async function main() {
  console.log(`
╔══════════════════════════════════════════════════════════════╗
║           OMARCHY DEFENDER - ASSET UPLOAD                   ║
╚══════════════════════════════════════════════════════════════╝
`);

  if (!env.CLOUDFLARE_ACCOUNT_ID || !env.CLOUDFLARE_API_TOKEN) {
    console.error('Error: Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN in .env');
    process.exit(1);
  }

  const accountId = env.CLOUDFLARE_ACCOUNT_ID;
  const apiToken = env.CLOUDFLARE_API_TOKEN;

  // Get all asset files
  const files = getAllFiles(ASSETS_DIR);

  if (files.length === 0) {
    console.log('No assets found to upload.');
    process.exit(0);
  }

  console.log(`Found ${files.length} files to upload\n`);

  const results = {
    success: 0,
    failed: 0,
    bytes: 0
  };

  // Upload files
  for (const file of files) {
    process.stdout.write(`  Uploading: ${file.key}...`);

    try {
      const success = await uploadFile(file, accountId, apiToken);
      if (success) {
        results.success++;
        results.bytes += file.size;
        console.log(` ✅ (${formatSize(file.size)})`);
      } else {
        results.failed++;
        console.log(' ❌');
      }
    } catch (e) {
      results.failed++;
      console.log(` ❌ (${e.message})`);
    }

    // Rate limiting
    await new Promise(r => setTimeout(r, 100));
  }

  console.log(`
════════════════════════════════════════════════════════════════

Upload Complete!

  ✅ Uploaded: ${results.success}
  ❌ Failed:   ${results.failed}
  📊 Total:    ${formatSize(results.bytes)}

Bucket URL: https://r2.xswarm.ai/${BUCKET_NAME}/

════════════════════════════════════════════════════════════════
`);
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

main().catch(console.error);
