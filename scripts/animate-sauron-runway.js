#!/usr/bin/env node

/**
 * Animate the Eye of Sauron using Runway Gen-2 (with text prompt control)
 *
 * Runway Gen-2 allows text prompts to control motion direction,
 * so we can specify "fire flowing outward from center"
 *
 * Requirements:
 * - RUNWAY_API_TOKEN in .env
 * - ffmpeg installed
 *
 * Usage:
 *   node scripts/animate-sauron-runway.js
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

const RUNWAY_API_KEY = process.env.RUNWAY_API_KEY;

if (!RUNWAY_API_KEY) {
  console.error('❌ Error: RUNWAY_API_KEY not found in environment');
  console.error('   Please add it to your .env file:');
  console.error('   RUNWAY_API_KEY=your_key_here');
  console.error('\n   Get your key at: https://app.runwayml.com/');
  process.exit(1);
}

const INPUT_IMAGE = path.join(__dirname, '../assets/sauron.jpg');
const OUTPUT_VIDEO = path.join(__dirname, '../assets/sauron-animated-runway.mp4');
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

async function animateWithRunway() {
  console.log('🔥 Animating Eye of Sauron with Runway Gen-2...\n');

  if (!fs.existsSync(INPUT_IMAGE)) {
    console.error(`❌ Input image not found: ${INPUT_IMAGE}`);
    process.exit(1);
  }

  // Read image as base64
  const imageBuffer = fs.readFileSync(INPUT_IMAGE);
  const imageBase64 = imageBuffer.toString('base64');

  console.log('🎬 Creating animation task with motion prompt...');
  console.log('   Prompt: "Fire and flames flowing outward from the center pupil slit, dramatic fire radiating outward"\n');

  try {
    // Create task
    const createResponse = await fetch('https://api.runwayml.com/v1/tasks', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${RUNWAY_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        taskType: 'gen2',
        internal: false,
        options: {
          name: 'Eye of Sauron Animation',
          seconds: 4,
          gen2Options: {
            mode: 'gen2',
            seed: 0,
            interpolate: true,
            upscale: false,
            watermark: false,
            motion_score: 24, // Higher motion
            text_prompt: 'Fire and flames flowing outward from the center eye pupil, dramatic orange and yellow fire radiating from the dark vertical slit, intense heat waves emanating outward, cinematic fire effect',
            init_image: `data:image/jpeg;base64,${imageBase64}`,
          },
        },
      }),
    });

    if (!createResponse.ok) {
      const error = await createResponse.text();
      console.error('❌ Error creating task:', error);
      process.exit(1);
    }

    const task = await createResponse.json();
    const taskId = task.id;

    console.log(`✅ Task created: ${taskId}`);
    console.log('⏳ Generating video (this may take 2-5 minutes)...\n');

    // Poll for completion
    let taskStatus = 'PENDING';
    while (taskStatus === 'PENDING' || taskStatus === 'RUNNING') {
      await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds

      const statusResponse = await fetch(`https://api.runwayml.com/v1/tasks/${taskId}`, {
        headers: {
          'Authorization': `Bearer ${RUNWAY_API_KEY}`,
        },
      });

      const statusData = await statusResponse.json();
      taskStatus = statusData.status;

      if (taskStatus === 'RUNNING') {
        const progress = statusData.progress || 0;
        console.log(`   Progress: ${Math.round(progress * 100)}%`);
      }
    }

    if (taskStatus !== 'SUCCEEDED') {
      console.error(`❌ Task failed with status: ${taskStatus}`);
      process.exit(1);
    }

    // Get result
    const resultResponse = await fetch(`https://api.runwayml.com/v1/tasks/${taskId}`, {
      headers: {
        'Authorization': `Bearer ${RUNWAY_API_KEY}`,
      },
    });

    const result = await resultResponse.json();
    const videoUrl = result.artifacts[0].url;

    console.log('✅ Video generated!');
    console.log(`   URL: ${videoUrl}\n`);

    // Download video
    console.log('📥 Downloading video...');
    const videoResponse = await fetch(videoUrl);
    const arrayBuffer = await videoResponse.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    fs.writeFileSync(OUTPUT_VIDEO, buffer);
    console.log(`✅ Saved: ${OUTPUT_VIDEO}`);

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

// Main
(async () => {
  console.log('╔════════════════════════════════════════╗');
  console.log('║  Eye of Sauron - Runway Gen-2         ║');
  console.log('╚════════════════════════════════════════╝\n');

  const hasFFmpeg = await checkFFmpeg();
  if (!hasFFmpeg) process.exit(1);

  await animateWithRunway();
})();
