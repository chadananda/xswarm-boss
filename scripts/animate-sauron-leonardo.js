#!/usr/bin/env node

/**
 * Animate the Eye of Sauron using Leonardo.ai
 *
 * Leonardo.ai has motion control and accessible API access.
 *
 * Requirements:
 * - LEONARDO_API_KEY in .env (get from: https://app.leonardo.ai/settings)
 * - ffmpeg installed
 *
 * Usage:
 *   node scripts/animate-sauron-leonardo.js
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

const LEONARDO_API_KEY = process.env.LEONARDO_API_KEY;

if (!LEONARDO_API_KEY) {
  console.error('❌ Error: LEONARDO_API_KEY not found in environment');
  console.error('   Please add it to your .env file:');
  console.error('   LEONARDO_API_KEY=your_key_here');
  console.error('\n   Get your key at: https://app.leonardo.ai/settings');
  console.error('   (Go to User Settings → API Keys)');
  process.exit(1);
}

const INPUT_IMAGE = path.join(__dirname, '../assets/sauron.jpg');
const OUTPUT_VIDEO = path.join(__dirname, '../assets/sauron-animated-leonardo.mp4');
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
  console.log('📤 Uploading image to Leonardo.ai...');

  const formData = new FormData();
  const imageBuffer = fs.readFileSync(INPUT_IMAGE);
  const blob = new Blob([imageBuffer], { type: 'image/jpeg' });
  formData.append('file', blob, 'sauron.jpg');

  const uploadResponse = await fetch('https://cloud.leonardo.ai/api/rest/v1/init-image', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${LEONARDO_API_KEY}`,
      'accept': 'application/json',
    },
    body: formData,
  });

  if (!uploadResponse.ok) {
    const error = await uploadResponse.text();
    throw new Error(`Upload failed: ${error}`);
  }

  const uploadData = await uploadResponse.json();
  console.log(`✅ Image uploaded: ${uploadData.uploadInitImage.id}`);
  return uploadData.uploadInitImage.id;
}

async function createMotionGeneration(imageId) {
  console.log('🎬 Creating motion generation...');
  console.log('   Motion: High strength for dramatic fire effect\n');

  const response = await fetch('https://cloud.leonardo.ai/api/rest/v1/generations-motion-svd', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${LEONARDO_API_KEY}`,
      'Content-Type': 'application/json',
      'accept': 'application/json',
    },
    body: JSON.stringify({
      imageId: imageId,
      motionStrength: 8, // High motion for dramatic fire (1-10 scale)
      isPublic: false,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Generation failed: ${error}`);
  }

  const data = await response.json();
  const generationId = data.motionSvdGenerationJob.generationId;
  console.log(`✅ Generation started: ${generationId}`);
  return generationId;
}

async function pollForCompletion(generationId) {
  console.log('⏳ Waiting for generation to complete (1-3 minutes)...\n');

  let attempts = 0;
  const maxAttempts = 60; // 5 minutes max

  while (attempts < maxAttempts) {
    await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds

    const response = await fetch(`https://cloud.leonardo.ai/api/rest/v1/generations/${generationId}`, {
      headers: {
        'Authorization': `Bearer ${LEONARDO_API_KEY}`,
        'accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to check generation status');
    }

    const data = await response.json();
    const generation = data.generations_by_pk;

    if (generation.status === 'COMPLETE') {
      console.log('✅ Generation complete!');

      // The video URL is in the generated_images array
      if (generation.generated_images && generation.generated_images.length > 0) {
        const videoUrl = generation.generated_images[0].url;
        return videoUrl;
      } else {
        throw new Error('No video URL found in response');
      }
    } else if (generation.status === 'FAILED') {
      throw new Error('Generation failed');
    }

    attempts++;
    console.log(`   Status: ${generation.status}...`);
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

async function animateWithLeonardo() {
  console.log('🔥 Animating Eye of Sauron with Leonardo.ai...\n');

  if (!fs.existsSync(INPUT_IMAGE)) {
    console.error(`❌ Input image not found: ${INPUT_IMAGE}`);
    process.exit(1);
  }

  try {
    const imageId = await uploadImage();
    const generationId = await createMotionGeneration(imageId);
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
  console.log('║  Eye of Sauron - Leonardo.ai Motion  ║');
  console.log('╚════════════════════════════════════════╝\n');

  const hasFFmpeg = await checkFFmpeg();
  if (!hasFFmpeg) process.exit(1);

  await animateWithLeonardo();
})();
