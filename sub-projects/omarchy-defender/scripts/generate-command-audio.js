#!/usr/bin/env node

/**
 * Generate Command Audio from Manifest
 * Reads audio-manifest.json and generates missing audio files using ElevenLabs
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '..');
const AUDIO_DIR = resolve(PROJECT_ROOT, 'assets/audio');
const MANIFEST_PATH = resolve(AUDIO_DIR, 'audio-manifest.json');

// Rate limiting
const DELAY_BETWEEN_REQUESTS = 1500;

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

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

/**
 * Generate voice audio using ElevenLabs
 */
async function generateVoice(text, voiceId, settings = {}) {
  const response = await fetch(
    `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`,
    {
      method: 'POST',
      headers: {
        'xi-api-key': env.ELEVENLABS_API_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text,
        model_id: 'eleven_multilingual_v2',
        voice_settings: {
          stability: settings.stability || 0.5,
          similarity_boost: settings.similarityBoost || 0.85,
          style: settings.style || 0.6,
          use_speaker_boost: true
        }
      })
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || `HTTP ${response.status}`);
  }

  return await response.arrayBuffer();
}

/**
 * Check subscription status
 */
async function checkSubscription() {
  const response = await fetch('https://api.elevenlabs.io/v1/user/subscription', {
    headers: { 'xi-api-key': env.ELEVENLABS_API_KEY }
  });

  if (!response.ok) {
    throw new Error('Failed to check subscription');
  }

  return await response.json();
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

async function main() {
  console.log('\n╔══════════════════════════════════════════════════════════════╗');
  console.log('║       OMARCHY DEFENDER - COMMAND AUDIO GENERATOR            ║');
  console.log('╚══════════════════════════════════════════════════════════════╝\n');

  // Check API key
  if (!env.ELEVENLABS_API_KEY) {
    console.error('❌ ELEVENLABS_API_KEY not configured in .env');
    process.exit(1);
  }

  // Load manifest
  if (!existsSync(MANIFEST_PATH)) {
    console.error('❌ audio-manifest.json not found');
    process.exit(1);
  }

  const manifest = JSON.parse(readFileSync(MANIFEST_PATH, 'utf-8'));
  const radioSettings = manifest.radioSettings || {};

  // Parse args
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const overwrite = args.includes('--overwrite');
  const categoryFilter = args.find(a => a.startsWith('--category='))?.split('=')[1];
  const limitArg = args.find(a => a.startsWith('--limit='))?.split('=')[1];
  const limit = limitArg ? parseInt(limitArg, 10) : Infinity;

  // Categories to process
  const targetCategories = ['stage_intro', 'commands'];

  // Check subscription
  console.log('Checking ElevenLabs subscription...');
  const subscription = await checkSubscription();
  const remaining = subscription.character_limit - subscription.character_count;

  console.log(`  Plan: ${subscription.tier}`);
  console.log(`  Characters remaining: ${remaining.toLocaleString()}`);

  // Collect items to generate
  const toGenerate = [];

  for (const category of targetCategories) {
    if (categoryFilter && category !== categoryFilter) continue;

    const items = manifest.categories[category] || [];

    for (const item of items) {
      // Skip sound effects (not voice)
      if (item.type === 'sound-generation') continue;

      const filepath = resolve(AUDIO_DIR, item.file);

      if (!overwrite && existsSync(filepath)) {
        continue; // Skip existing
      }

      toGenerate.push({
        category,
        ...item,
        filepath
      });
    }
  }

  // Apply limit
  const itemsToProcess = toGenerate.slice(0, limit);

  console.log(`\n📊 Found ${toGenerate.length} audio files to generate`);
  if (limit < toGenerate.length) {
    console.log(`   (limited to ${limit})`);
  }

  // Calculate characters needed
  const totalChars = itemsToProcess.reduce((sum, item) => sum + item.text.length, 0);
  console.log(`   Characters needed: ${totalChars.toLocaleString()}`);

  if (totalChars > remaining) {
    console.warn(`\n⚠️  Warning: Need ${totalChars - remaining} more characters than available`);
    if (!args.includes('--force')) {
      console.log('   Use --force to proceed anyway');
      process.exit(1);
    }
  }

  if (dryRun) {
    console.log('\n🔍 DRY RUN - Would generate:\n');
    for (const item of itemsToProcess) {
      console.log(`   [${item.category}] ${item.id}: "${item.text.substring(0, 50)}..."`);
    }
    console.log(`\n   Total: ${itemsToProcess.length} files, ${totalChars} characters`);
    process.exit(0);
  }

  if (itemsToProcess.length === 0) {
    console.log('\n✅ All audio files already exist!');
    process.exit(0);
  }

  // Generate audio
  console.log('\n' + '═'.repeat(60));
  console.log(' Starting Generation');
  console.log('═'.repeat(60) + '\n');

  const results = { generated: 0, failed: 0, chars: 0 };

  for (let i = 0; i < itemsToProcess.length; i++) {
    const item = itemsToProcess[i];
    const progress = `[${i + 1}/${itemsToProcess.length}]`;

    console.log(`${progress} Generating: ${item.id}`);
    console.log(`         Text: "${item.text.substring(0, 60)}${item.text.length > 60 ? '...' : ''}"`);

    try {
      // Use item-specific voice or default
      const voiceId = item.voice || manifest.voice;
      const settings = item.settings || radioSettings;

      const audioBuffer = await generateVoice(item.text, voiceId, settings);
      writeFileSync(item.filepath, Buffer.from(audioBuffer));

      console.log(`         ✅ Saved: ${item.file} (${formatSize(audioBuffer.byteLength)})\n`);

      results.generated++;
      results.chars += item.text.length;

      // Rate limiting
      if (i < itemsToProcess.length - 1) {
        await sleep(DELAY_BETWEEN_REQUESTS);
      }

    } catch (err) {
      console.error(`         ❌ Failed: ${err.message}\n`);
      results.failed++;
    }
  }

  // Summary
  console.log('═'.repeat(60));
  console.log(' Generation Complete');
  console.log('═'.repeat(60));
  console.log(`\n  ✅ Generated: ${results.generated}`);
  console.log(`  ❌ Failed:    ${results.failed}`);
  console.log(`  📊 Characters used: ${results.chars.toLocaleString()}\n`);
}

// Help
if (process.argv.includes('--help')) {
  console.log(`
Omarchy Defender - Command Audio Generator

Usage: node generate-command-audio.js [options]

Options:
  --dry-run              Show what would be generated
  --overwrite            Regenerate existing files
  --category=NAME        Only generate for category (stage_intro, commands)
  --limit=N              Generate at most N files
  --force                Continue even if not enough characters
  --help                 Show this help

Examples:
  node generate-command-audio.js --dry-run
  node generate-command-audio.js --category=stage_intro
  node generate-command-audio.js --limit=10
`);
  process.exit(0);
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
