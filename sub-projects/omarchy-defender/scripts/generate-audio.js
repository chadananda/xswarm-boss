#!/usr/bin/env node

/**
 * Audio Generation Script
 * Batch generates all voice lines from manifest using ElevenLabs
 * Supports multiple voice settings per category
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '..');
const ASSETS_DIR = resolve(PROJECT_ROOT, 'assets');
const AUDIO_DIR = resolve(ASSETS_DIR, 'audio');

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

// Load config
const loadConfig = () => {
  const configPath = resolve(PROJECT_ROOT, 'config.json');
  if (!existsSync(configPath)) {
    console.error('Error: config.json not found');
    process.exit(1);
  }
  return JSON.parse(readFileSync(configPath, 'utf-8'));
};

const env = loadEnv();
const config = loadConfig();

// Voice line categories with their scripts
const VOICE_LINES = {
  // Stage 1: Terminal Warfare
  stage1_intro: [
    { id: 'stage1-intro-1', text: 'Welcome to Omarchy Defender, Commander. The Gnome cavalry approaches.' },
    { id: 'stage1-intro-2', text: 'Terminal warfare begins. Show these mice the power of the keyboard.' },
    { id: 'stage1-intro-3', text: 'Attention Commander! Hostile Gnomes detected. Prepare for battle.' }
  ],

  stage1_spawn: [
    { id: 'spawn-hint-1', text: 'Super Enter spawns a terminal.' },
    { id: 'spawn-hint-2', text: 'Hit Super Enter to deploy a terminal.' },
    { id: 'spawn-hint-3', text: 'Quick! Super Enter creates terminals.' }
  ],

  stage1_close: [
    { id: 'close-hint-1', text: 'Super Q closes the active window.' },
    { id: 'close-hint-2', text: 'Use Super Q to eliminate that terminal.' },
    { id: 'close-hint-3', text: 'Close it! Super Q!' }
  ],

  stage1_navigate: [
    { id: 'nav-hint-1', text: 'Navigate with Super H, J, K, L.' },
    { id: 'nav-hint-2', text: 'Vim keys! Super plus direction.' },
    { id: 'nav-hint-3', text: 'Super H J K L moves your focus.' }
  ],

  stage1_move: [
    { id: 'move-hint-1', text: 'Super Shift moves windows.' },
    { id: 'move-hint-2', text: 'Add Shift to move instead of focus.' },
    { id: 'move-hint-3', text: 'Super Shift H J K L repositions windows.' }
  ],

  // Commander emotions - Calm
  calm: [
    { id: 'calm-1', text: 'Good work Commander. Keep it up.' },
    { id: 'calm-2', text: 'The defense holds strong.' },
    { id: 'calm-3', text: 'Excellent execution.' },
    { id: 'calm-4', text: 'Precisely done.' },
    { id: 'calm-5', text: 'Your keyboard skills impress me.' }
  ],

  // Commander emotions - Patient hint
  hint: [
    { id: 'hint-1', text: 'Commander, remember your training.' },
    { id: 'hint-2', text: 'Check your bindings, Commander.' },
    { id: 'hint-3', text: 'The correct key combination awaits.' },
    { id: 'hint-4', text: 'Think, Commander. What would Vim do?' },
    { id: 'hint-5', text: 'Stay focused. You know this.' }
  ],

  // Commander emotions - Urgent
  urgent: [
    { id: 'urgent-1', text: 'Quickly Commander! Time runs out!' },
    { id: 'urgent-2', text: 'Faster! The Gnomes advance!' },
    { id: 'urgent-3', text: 'No time for hesitation!' },
    { id: 'urgent-4', text: 'Move it Commander!' },
    { id: 'urgent-5', text: 'They are almost through!' }
  ],

  // Commander emotions - Angry
  angry: [
    { id: 'angry-1', text: 'What are you doing Commander!' },
    { id: 'angry-2', text: 'This is unacceptable!' },
    { id: 'angry-3', text: 'Did you forget your keyboard training?' },
    { id: 'angry-4', text: 'The Gnomes will overrun us at this rate!' },
    { id: 'angry-5', text: 'Get it together Commander!' }
  ],

  // Mouse contamination warnings
  mouse_warning: [
    { id: 'mouse-1', text: 'Mouse detected! Contamination level rising!' },
    { id: 'mouse-2', text: 'Put down that rodent, Commander!' },
    { id: 'mouse-3', text: 'Mouse contact detected! Your purity falters!' },
    { id: 'mouse-4', text: 'The mouse corrupts! Use the keyboard!' },
    { id: 'mouse-5', text: 'Warning! Mouse contamination spreading!' }
  ],

  // Victory lines
  victory: [
    { id: 'victory-1', text: 'Outstanding victory Commander!' },
    { id: 'victory-2', text: 'The Gnome cavalry retreats in shame!' },
    { id: 'victory-3', text: 'Keyboard supremacy established!' },
    { id: 'victory-4', text: 'Another sector secured. Well fought.' },
    { id: 'victory-5', text: 'The mice flee! Total victory!' }
  ],

  // Defeat lines
  defeat: [
    { id: 'defeat-1', text: 'We have lost this sector, Commander.' },
    { id: 'defeat-2', text: 'The Gnomes have breached our defenses.' },
    { id: 'defeat-3', text: 'Fall back! The mice have won this battle.' },
    { id: 'defeat-4', text: 'This defeat stings. Ready for another attempt?' },
    { id: 'defeat-5', text: 'Even the best commanders lose sometimes. Try again.' }
  ],

  // Stage 2: Sector Command
  stage2_intro: [
    { id: 'stage2-intro-1', text: 'Sector Command begins. Multiple workspaces require your attention.' },
    { id: 'stage2-intro-2', text: 'The battlefield expands. Nine sectors, one Commander.' },
    { id: 'stage2-intro-3', text: 'Workspace warfare. Master it or fall to the Gnomes.' }
  ],

  stage2_workspace: [
    { id: 'workspace-hint-1', text: 'Super plus a number switches workspaces.' },
    { id: 'workspace-hint-2', text: 'One through nine. Pick your sector.' },
    { id: 'workspace-hint-3', text: 'Super Shift moves windows between workspaces.' }
  ],

  // Stage 3: Full Arsenal
  stage3_intro: [
    { id: 'stage3-intro-1', text: 'Full Arsenal unlocked. Every application at your fingertips.' },
    { id: 'stage3-intro-2', text: 'Twenty shortcuts. One keyboard. Total control.' },
    { id: 'stage3-intro-3', text: 'The complete Omarchy arsenal awaits your command.' }
  ],

  stage3_apps: [
    { id: 'app-browser', text: 'Super Shift B launches the browser.' },
    { id: 'app-email', text: 'Super Shift E opens your email.' },
    { id: 'app-files', text: 'Super Shift F for the file manager.' },
    { id: 'app-terminal', text: 'Super Enter. Always returns you to the terminal.' },
    { id: 'app-ai', text: 'Super Shift A summons the AI assistant.' },
    { id: 'app-music', text: 'Super Shift M plays your music.' },
    { id: 'app-notes', text: 'Super Shift O opens Obsidian.' }
  ],

  // Combo achievements
  combo: [
    { id: 'combo-2', text: 'Double kill!' },
    { id: 'combo-3', text: 'Triple threat!' },
    { id: 'combo-5', text: 'Keyboard warrior!' },
    { id: 'combo-10', text: 'Unstoppable!' },
    { id: 'combo-perfect', text: 'Perfect defense! Flawless execution!' }
  ]
};

// Voice settings per category
const CATEGORY_SETTINGS = {
  calm: { stability: 0.7, similarityBoost: 0.75, style: 0.2 },
  hint: { stability: 0.6, similarityBoost: 0.75, style: 0.3 },
  urgent: { stability: 0.3, similarityBoost: 0.8, style: 0.6 },
  angry: { stability: 0.2, similarityBoost: 0.85, style: 0.7 },
  mouse_warning: { stability: 0.4, similarityBoost: 0.8, style: 0.5 },
  victory: { stability: 0.6, similarityBoost: 0.75, style: 0.4 },
  defeat: { stability: 0.7, similarityBoost: 0.7, style: 0.3 },
  combo: { stability: 0.3, similarityBoost: 0.85, style: 0.6 },
  default: { stability: 0.5, similarityBoost: 0.75, style: 0.3 }
};

// Rate limiting
const DELAY_BETWEEN_REQUESTS = 1500; // ms

/**
 * Sleep for specified milliseconds
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Generate voice audio using ElevenLabs
 */
async function generateVoice(text, filename, settings) {
  // Get voice ID from config - supports both old and new config formats
  const elevenLabsConfig = config.elevenLabs || config.elevenlabs;
  let voiceId;

  if (elevenLabsConfig?.defaultVoiceId) {
    // Old format: elevenlabs.defaultVoiceId
    voiceId = elevenLabsConfig.defaultVoiceId;
  } else if (elevenLabsConfig?.voices) {
    // New format: elevenLabs.voices[selectedVoice].id
    const selectedVoice = elevenLabsConfig.selectedVoice || 'primary';
    voiceId = elevenLabsConfig.voices[selectedVoice]?.id;
  }

  if (!voiceId) {
    throw new Error('No default voice ID configured');
  }

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
          stability: settings.stability,
          similarity_boost: settings.similarityBoost,
          style: settings.style,
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

/**
 * Main generation function
 */
async function main() {
  console.log('\n╔══════════════════════════════════════════════════════════════╗');
  console.log('║           OMARCHY DEFENDER - AUDIO GENERATOR                ║');
  console.log('╚══════════════════════════════════════════════════════════════╝\n');

  // Check API key
  if (!env.ELEVENLABS_API_KEY) {
    console.error('❌ ELEVENLABS_API_KEY not configured in .env');
    process.exit(1);
  }

  // Ensure audio directory exists
  if (!existsSync(AUDIO_DIR)) {
    mkdirSync(AUDIO_DIR, { recursive: true });
    console.log(`Created directory: ${AUDIO_DIR}\n`);
  }

  // Check subscription
  console.log('Checking ElevenLabs subscription...');
  const subscription = await checkSubscription();
  const remaining = subscription.character_limit - subscription.character_count;

  console.log(`  Plan: ${subscription.tier}`);
  console.log(`  Characters used: ${subscription.character_count.toLocaleString()} / ${subscription.character_limit.toLocaleString()}`);
  console.log(`  Remaining: ${remaining.toLocaleString()}`);

  // Calculate total characters needed
  let totalChars = 0;
  let totalLines = 0;

  for (const category of Object.keys(VOICE_LINES)) {
    for (const line of VOICE_LINES[category]) {
      totalChars += line.text.length;
      totalLines++;
    }
  }

  console.log(`\n  Voice lines to generate: ${totalLines}`);
  console.log(`  Total characters needed: ${totalChars.toLocaleString()}`);

  if (totalChars > remaining) {
    console.error(`\n❌ Not enough characters remaining! Need ${totalChars - remaining} more.`);
    console.log('   Consider upgrading your ElevenLabs plan or generating fewer lines.');

    // Ask for confirmation
    const args = process.argv.slice(2);
    if (!args.includes('--force')) {
      console.log('\n   Use --force to generate what we can with remaining characters.');
      process.exit(1);
    }
  }

  // Parse command line args
  const args = process.argv.slice(2);
  const skipExisting = !args.includes('--overwrite');
  const dryRun = args.includes('--dry-run');
  const categoryFilter = args.find(a => a.startsWith('--category='))?.split('=')[1];

  if (dryRun) {
    console.log('\n🔍 DRY RUN - No files will be generated\n');
  }

  // Generate manifest
  const elevenLabsConfig = config.elevenLabs || config.elevenlabs;
  const selectedVoice = elevenLabsConfig?.selectedVoice || 'primary';
  const voiceId = elevenLabsConfig?.defaultVoiceId ||
                  elevenLabsConfig?.voices?.[selectedVoice]?.id;

  const manifest = {
    generated: new Date().toISOString(),
    voice: voiceId,
    voiceName: elevenLabsConfig?.voices?.[selectedVoice]?.name || 'Unknown',
    categories: {}
  };

  // Results tracking
  const results = {
    generated: 0,
    skipped: 0,
    failed: 0,
    chars: 0
  };

  console.log('\n' + '═'.repeat(60));
  console.log(' Starting Generation');
  console.log('═'.repeat(60) + '\n');

  // Process each category
  for (const [category, lines] of Object.entries(VOICE_LINES)) {
    // Filter by category if specified
    if (categoryFilter && category !== categoryFilter) {
      continue;
    }

    console.log(`\n📁 Category: ${category} (${lines.length} lines)`);

    manifest.categories[category] = [];
    const settings = CATEGORY_SETTINGS[category] || CATEGORY_SETTINGS.default;

    for (const line of lines) {
      const filename = `${line.id}.mp3`;
      const filepath = resolve(AUDIO_DIR, filename);

      // Skip if exists
      if (skipExisting && existsSync(filepath)) {
        console.log(`   ⏭️  Skipped (exists): ${filename}`);
        results.skipped++;
        manifest.categories[category].push({
          id: line.id,
          text: line.text,
          file: filename
        });
        continue;
      }

      if (dryRun) {
        console.log(`   🔍 Would generate: ${filename} (${line.text.length} chars)`);
        results.chars += line.text.length;
        continue;
      }

      // Generate voice
      try {
        console.log(`   ⏳ Generating: ${filename}...`);

        const audioBuffer = await generateVoice(line.text, filename, settings);
        writeFileSync(filepath, Buffer.from(audioBuffer));

        console.log(`   ✅ Generated: ${filename} (${formatSize(audioBuffer.byteLength)})`);

        results.generated++;
        results.chars += line.text.length;

        manifest.categories[category].push({
          id: line.id,
          text: line.text,
          file: filename,
          settings
        });

        // Rate limiting
        await sleep(DELAY_BETWEEN_REQUESTS);

      } catch (err) {
        console.error(`   ❌ Failed: ${filename} - ${err.message}`);
        results.failed++;
      }
    }
  }

  // Save manifest
  const manifestPath = resolve(AUDIO_DIR, 'audio-manifest.json');
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  console.log(`\n📄 Manifest saved: ${manifestPath}`);

  // Results summary
  console.log('\n' + '═'.repeat(60));
  console.log(' Generation Complete');
  console.log('═'.repeat(60));
  console.log(`\n  ✅ Generated: ${results.generated}`);
  console.log(`  ⏭️  Skipped:   ${results.skipped}`);
  console.log(`  ❌ Failed:    ${results.failed}`);
  console.log(`  📊 Characters: ${results.chars.toLocaleString()}`);

  if (dryRun) {
    console.log(`\n  This was a dry run. Use without --dry-run to generate files.`);
  }

  console.log('\n');
}

/**
 * Format file size
 */
function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// Show help
if (process.argv.includes('--help')) {
  console.log(`
Omarchy Defender - Audio Generator

Usage: node generate-audio.js [options]

Options:
  --dry-run          Show what would be generated without creating files
  --overwrite        Regenerate existing files
  --category=NAME    Only generate files for specified category
  --force            Continue even if not enough characters remaining
  --help             Show this help message

Categories:
  ${Object.keys(VOICE_LINES).join(', ')}

Examples:
  node generate-audio.js --dry-run
  node generate-audio.js --category=calm
  node generate-audio.js --overwrite --category=urgent
`);
  process.exit(0);
}

// Run
main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
