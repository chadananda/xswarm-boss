#!/usr/bin/env node

/**
 * Animate the Eye of Sauron using Luma AI Dream Machine
 *
 * Luma Dream Machine v1.6 - High quality image-to-video generation
 * - 1080p resolution, cinematic quality
 * - 120 frames in 120 seconds
 * - Official API with good accessibility
 *
 * Requirements:
 * - LUMA_API_KEY in .env (get from: https://lumalabs.ai/dream-machine/api/keys)
 * - ffmpeg installed
 *
 * Usage:
 *   node scripts/animate-sauron-luma.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { exec } from 'child_process';
import { promisify } from 'util';
import dotenv from 'dotenv';

// Load environment variables from .env
dotenv.config();

const execAsync = promisify(exec);
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const LUMA_API_KEY = process.env.LUMA_API_KEY;

if (!LUMA_API_KEY) {
  console.error('❌ Error: LUMA_API_KEY not found in environment');
  console.error('   Please add it to your .env file:');
  console.error('   LUMA_API_KEY=luma_your_key_here');
  console.error('\n   Get your key at: https://lumalabs.ai/dream-machine/api/keys');
  process.exit(1);
}

const INPUT_IMAGE = path.join(__dirname, '../assets/sauron.jpg');
const OUTPUT_VIDEO = path.join(__dirname, '../assets/sauron-animated-luma.mp4');
const OUTPUT_APNG = path.join(__dirname, '../packages/personas/sauron/icon.apng');
const OUTPUT_WEBP = path.join(__dirname, '../packages/personas/sauron/icon.webp');

async function checkFFmpeg() {
  try {
    await execAsync('ffmpeg -version');
    console.log('✅ FFmpeg found');
    return true;
  } catch (error) {
    console.error('❌ FFmpeg not found. Please install it:');
    console.error('   macOS: brew install ffmpeg');
    return false;
  }
}

async function uploadImage() {
  console.log('📤 Preparing image for Luma AI...');

  // Read image as base64
  const imageBuffer = fs.readFileSync(INPUT_IMAGE);
  const imageBase64 = imageBuffer.toString('base64');
  const imageDataUrl = `data:image/jpeg;base64,${imageBase64}`;

  return imageDataUrl;
}

async function createGeneration(imageDataUrl) {
  console.log('🎬 Creating video generation with Luma Dream Machine...');
  console.log('   Model: v1.6 (1080p, cinematic quality)');
  console.log('   Prompt: Fire radiating outward from center\n');

  const response = await fetch('https://api.lumalabs.ai/dream-machine/v1/generations', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${LUMA_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      generation_type: 'video',
      model: 'ray-2',
      prompt: 'Fire and flames radiating outward from the center pupil, dramatic orange fire flowing from the dark vertical slit, intense heat waves emanating outward in all directions, cinematic fire effect, realistic flames',
      aspect_ratio: '1:1',
      loop: true,
      keyframes: {
        frame0: {
          type: 'image',
          url: imageDataUrl,
        },
      },
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Generation failed: ${error}`);
  }

  const data = await response.json();
  console.log(`✅ Generation started: ${data.id}`);
  return data.id;
}

async function pollForCompletion(generationId) {
  console.log('⏳ Generating video (typically 2-4 minutes)...\n');

  let attempts = 0;
  const maxAttempts = 120; // 10 minutes max

  while (attempts < maxAttempts) {
    await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds

    const response = await fetch(`https://api.lumalabs.ai/dream-machine/v1/generations/${generationId}`, {
      headers: {
        'Authorization': `Bearer ${LUMA_API_KEY}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to check generation status');
    }

    const data = await response.json();

    if (data.state === 'completed') {
      console.log('✅ Generation complete!');

      if (data.assets && data.assets.video) {
        return data.assets.video;
      } else {
        throw new Error('No video URL found in response');
      }
    } else if (data.state === 'failed') {
      throw new Error(`Generation failed: ${data.failure_reason || 'Unknown error'}`);
    }

    attempts++;
    console.log(`   Status: ${data.state}...`);
  }

  throw new Error('Generation timed out');
}

async function downloadVideo(url) {
  console.log('\n📥 Downloading video...');
  const response = await fetch(url);
  const arrayBuffer = await response.arrayBuffer();
  const buffer = Buffer.from(arrayBuffer);
  fs.writeFileSync(OUTPUT_VIDEO, buffer);
  console.log(`✅ Saved: ${OUTPUT_VIDEO}`);
}

async function convertToAPNG() {
  console.log('\n🔄 Converting to APNG...');
  try {
    await execAsync(`ffmpeg -i "${OUTPUT_VIDEO}" -f apng -plays 0 "${OUTPUT_APNG}" -y`);
    const stats = fs.statSync(OUTPUT_APNG);
    console.log(`✅ APNG created (${(stats.size / 1024 / 1024).toFixed(2)} MB)`);
  } catch (error) {
    console.error('❌ Error converting to APNG:', error.message);
  }
}

async function convertToWebP() {
  console.log('\n🔄 Converting to WebP...');
  try {
    await execAsync(`ffmpeg -i "${OUTPUT_VIDEO}" -vcodec libwebp -lossless 0 -compression_level 6 -q:v 80 -loop 0 -preset default -an -vsync 0 "${OUTPUT_WEBP}" -y`);
    const stats = fs.statSync(OUTPUT_WEBP);
    console.log(`✅ WebP created (${(stats.size / 1024 / 1024).toFixed(2)} MB)`);
  } catch (error) {
    console.error('❌ Error converting to WebP:', error.message);
  }
}

async function animateWithLuma() {
  console.log('🔥 Animating Eye of Sauron with Luma AI Dream Machine...\n');

  if (!fs.existsSync(INPUT_IMAGE)) {
    console.error(`❌ Input image not found: ${INPUT_IMAGE}`);
    process.exit(1);
  }

  try {
    const imageDataUrl = await uploadImage();
    const generationId = await createGeneration(imageDataUrl);
    const videoUrl = await pollForCompletion(generationId);

    console.log(`   URL: ${videoUrl}\n`);

    await downloadVideo(videoUrl);
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

// Main
(async () => {
  console.log('╔════════════════════════════════════════╗');
  console.log('║  Eye of Sauron - Luma Dream Machine   ║');
  console.log('╚════════════════════════════════════════╝\n');

  const hasFFmpeg = await checkFFmpeg();
  if (!hasFFmpeg) process.exit(1);

  await animateWithLuma();
})();
