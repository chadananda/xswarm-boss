#!/usr/bin/env node

/**
 * Animate the Eye of Sauron using AI image-to-video
 *
 * This script:
 * 1. Takes the static sauron.jpg image
 * 2. Uses Replicate API (Stable Video Diffusion) to create animated fire
 * 3. Downloads the video
 * 4. Converts to looping APNG
 *
 * Requirements:
 * - REPLICATE_API_TOKEN in .env
 * - ffmpeg installed
 *
 * Usage:
 *   node scripts/animate-sauron.js
 */

import Replicate from 'replicate';
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

// Load environment variables
const REPLICATE_API_KEY = process.env.REPLICATE_API_KEY;

if (!REPLICATE_API_KEY) {
  console.error('❌ Error: REPLICATE_API_KEY not found in environment');
  console.error('   Please add it to your .env file:');
  console.error('   REPLICATE_API_KEY=r8_your_token_here');
  console.error('\n   Get your token at: https://replicate.com/account/api-tokens');
  process.exit(1);
}

const replicate = new Replicate({
  auth: REPLICATE_API_KEY,
});

const INPUT_IMAGE = path.join(__dirname, '../assets/sauron.jpg');
const OUTPUT_VIDEO = path.join(__dirname, '../assets/sauron-animated.mp4');
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
    console.error('   Linux: sudo apt-get install ffmpeg');
    return false;
  }
}

async function animateImage() {
  console.log('🔥 Animating Eye of Sauron...\n');

  // Check if input exists
  if (!fs.existsSync(INPUT_IMAGE)) {
    console.error(`❌ Input image not found: ${INPUT_IMAGE}`);
    process.exit(1);
  }

  console.log('📤 Uploading image to Replicate...');

  // Read image as base64
  const imageBuffer = fs.readFileSync(INPUT_IMAGE);
  const imageBase64 = `data:image/jpeg;base64,${imageBuffer.toString('base64')}`;

  console.log('🎬 Generating animated video with Stable Video Diffusion...');
  console.log('   (This may take 1-3 minutes)\n');

  try {
    const output = await replicate.run(
      "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
      {
        input: {
          input_image: imageBase64,
          video_length: "14_frames_with_svd", // Short loop (14 frames)
          sizing_strategy: "maintain_aspect_ratio",
          frames_per_second: 6, // Slow, dramatic fire movement
          motion_bucket_id: 127, // Medium motion (good for fire)
          cond_aug: 0.02, // Low noise (preserve detail)
        }
      }
    );

    console.log('✅ Video generated!');
    console.log(`   URL: ${output}`);

    // Download the video
    console.log('\n📥 Downloading video...');
    const response = await fetch(output);
    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    fs.writeFileSync(OUTPUT_VIDEO, buffer);
    console.log(`✅ Saved: ${OUTPUT_VIDEO}`);

    // Convert to APNG
    await convertToAPNG();

    // Convert to WebP (smaller)
    await convertToWebP();

    console.log('\n🎉 Done! Animated eye created:');
    console.log(`   APNG: ${OUTPUT_APNG}`);
    console.log(`   WebP: ${OUTPUT_WEBP}`);
    console.log('\n💡 Use in SVG with:');
    console.log('   <image href="icon.apng" width="256" height="256"/>');

  } catch (error) {
    console.error('❌ Error generating video:', error);
    process.exit(1);
  }
}

async function convertToAPNG() {
  console.log('\n🔄 Converting to APNG (looping animation)...');

  try {
    // Convert to APNG with infinite loop
    await execAsync(`ffmpeg -i "${OUTPUT_VIDEO}" -f apng -plays 0 "${OUTPUT_APNG}" -y`);

    const stats = fs.statSync(OUTPUT_APNG);
    const sizeMB = (stats.size / 1024 / 1024).toFixed(2);
    console.log(`✅ APNG created (${sizeMB} MB)`);

    if (stats.size > 1024 * 1024 * 2) {
      console.log('⚠️  APNG is large, consider using WebP instead');
    }
  } catch (error) {
    console.error('❌ Error converting to APNG:', error.message);
  }
}

async function convertToWebP() {
  console.log('\n🔄 Converting to WebP (smaller file size)...');

  try {
    // Convert to animated WebP
    await execAsync(`ffmpeg -i "${OUTPUT_VIDEO}" -vcodec libwebp -lossless 0 -compression_level 6 -q:v 80 -loop 0 -preset default -an -vsync 0 "${OUTPUT_WEBP}" -y`);

    const stats = fs.statSync(OUTPUT_WEBP);
    const sizeMB = (stats.size / 1024 / 1024).toFixed(2);
    console.log(`✅ WebP created (${sizeMB} MB)`);
  } catch (error) {
    console.error('❌ Error converting to WebP:', error.message);
  }
}

// Main execution
(async () => {
  console.log('╔════════════════════════════════════════╗');
  console.log('║  Eye of Sauron Animation Generator    ║');
  console.log('╚════════════════════════════════════════╝\n');

  const hasFFmpeg = await checkFFmpeg();
  if (!hasFFmpeg) {
    process.exit(1);
  }

  await animateImage();
})();
