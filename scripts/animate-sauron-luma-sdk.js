#!/usr/bin/env node

/**
 * Animate the Eye of Sauron using Luma AI Dream Machine (Official SDK)
 *
 * Requirements:
 * - LUMA_API_KEY in .env
 * - ffmpeg installed
 * - Image must be publicly accessible via URL (not local file)
 *
 * Usage:
 *   node scripts/animate-sauron-luma-sdk.js <image_url>
 */

import { LumaAI } from 'lumaai';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { exec } from 'child_process';
import { promisify } from 'util';
import dotenv from 'dotenv';

dotenv.config();

const execAsync = promisify(exec);
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const LUMA_API_KEY = process.env.LUMA_API_KEY;

if (!LUMA_API_KEY) {
  console.error('❌ Error: LUMA_API_KEY not found in environment');
  console.error('   Please add it to your .env file');
  process.exit(1);
}

// Use test image or custom URL
const IMAGE_URL = process.argv[2] || 'https://storage.cdn-luma.com/dream_machine/7e4fe07f-1dfd-4921-bc97-4bcf5adea39a/video_0_thumb.jpg';

const OUTPUT_VIDEO = path.join(__dirname, '../assets/sauron-animated-luma.mp4');
const OUTPUT_APNG = path.join(__dirname, '../packages/personas/sauron/icon.apng');
const OUTPUT_WEBP = path.join(__dirname, '../packages/personas/sauron/icon.webp');

const client = new LumaAI({ authToken: LUMA_API_KEY });

async function generateVideo() {
  console.log('╔════════════════════════════════════════╗');
  console.log('║  Eye of Sauron - Luma Dream Machine   ║');
  console.log('╚════════════════════════════════════════╝\n');

  console.log('🔥 Creating animated Eye of Sauron...\n');
  console.log(`📷 Image URL: ${IMAGE_URL}`);
  console.log('🎬 Model: ray-2 (HD quality, loop optimized)\n');

  try {
    // Create generation
    let generation = await client.generations.create({
      model: 'ray-2',
      prompt: 'Fire and flames radiating outward from the center pupil, dramatic orange fire flowing from the dark vertical slit, intense heat waves emanating outward in all directions, cinematic fire effect, realistic flames',
      aspect_ratio: '1:1',
      loop: true,
      keyframes: {
        frame0: {
          type: 'image',
          url: IMAGE_URL,
        },
      },
    });

    console.log(`✅ Generation started: ${generation.id}`);
    console.log('⏳ Generating video (typically 2-4 minutes)...\n');

    // Poll for completion
    let completed = false;
    while (!completed) {
      await new Promise(resolve => setTimeout(resolve, 5000));

      generation = await client.generations.get(generation.id);

      if (generation.state === 'completed') {
        completed = true;
        console.log('✅ Generation complete!\n');
      } else if (generation.state === 'failed') {
        throw new Error(`Generation failed: ${generation.failure_reason}`);
      } else {
        console.log(`   Status: ${generation.state}...`);
      }
    }

    // Download video
    const videoUrl = generation.assets.video;
    console.log(`📥 Downloading from: ${videoUrl}`);

    const response = await fetch(videoUrl);
    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    fs.writeFileSync(OUTPUT_VIDEO, buffer);

    console.log(`✅ Saved: ${OUTPUT_VIDEO}\n`);

    // Convert to formats
    await convertToAPNG();
    await convertToWebP();

    console.log('\n🎉 Done! Animated eye created:');
    console.log(`   APNG: ${OUTPUT_APNG}`);
    console.log(`   WebP: ${OUTPUT_WEBP}`);

  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

async function convertToAPNG() {
  console.log('🔄 Converting to APNG...');
  try {
    await execAsync(`ffmpeg -i "${OUTPUT_VIDEO}" -f apng -plays 0 "${OUTPUT_APNG}" -y`);
    const stats = fs.statSync(OUTPUT_APNG);
    console.log(`✅ APNG created (${(stats.size / 1024 / 1024).toFixed(2)} MB)`);
  } catch (error) {
    console.error('❌ Error converting to APNG:', error.message);
  }
}

async function convertToWebP() {
  console.log('🔄 Converting to WebP...');
  try {
    await execAsync(`ffmpeg -i "${OUTPUT_VIDEO}" -vcodec libwebp -lossless 0 -compression_level 6 -q:v 80 -loop 0 -preset default -an -vsync 0 "${OUTPUT_WEBP}" -y`);
    const stats = fs.statSync(OUTPUT_WEBP);
    console.log(`✅ WebP created (${(stats.size / 1024 / 1024).toFixed(2)} MB)`);
  } catch (error) {
    console.error('❌ Error converting to WebP:', error.message);
  }
}

generateVideo();
