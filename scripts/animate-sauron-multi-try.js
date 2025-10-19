#!/usr/bin/env node

/**
 * Animate the Eye of Sauron with multiple seed attempts
 *
 * Since Stable Video Diffusion doesn't have motion control,
 * we'll try multiple random seeds hoping to get outward fire motion.
 *
 * This script generates 5 variations and lets you pick the best one.
 *
 * Requirements:
 * - REPLICATE_API_KEY in .env
 * - ffmpeg installed
 *
 * Usage:
 *   node scripts/animate-sauron-multi-try.js
 */

import Replicate from 'replicate';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { exec } from 'child_process';
import { promisify } from 'util';
import dotenv from 'dotenv';

dotenv.config();

const execAsync = promisify(exec);
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const REPLICATE_API_KEY = process.env.REPLICATE_API_KEY;

if (!REPLICATE_API_KEY) {
  console.error('❌ Error: REPLICATE_API_KEY not found in environment');
  process.exit(1);
}

const replicate = new Replicate({
  auth: REPLICATE_API_KEY,
});

const INPUT_IMAGE = path.join(__dirname, '../assets/sauron.jpg');
const OUTPUT_DIR = path.join(__dirname, '../assets/sauron-variations');

// Create output directory
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

async function generateVariation(seedNumber) {
  console.log(`\n🎬 Generating variation ${seedNumber}/5...`);

  const imageBuffer = fs.readFileSync(INPUT_IMAGE);
  const imageBase64 = `data:image/jpeg;base64,${imageBuffer.toString('base64')}`;

  try {
    const output = await replicate.run(
      "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
      {
        input: {
          input_image: imageBase64,
          video_length: "25_frames_with_svd_xt",
          sizing_strategy: "maintain_aspect_ratio",
          frames_per_second: 8,
          motion_bucket_id: 127, // Default motion
          cond_aug: 0.02, // Default augmentation
          seed: seedNumber * 1000, // Different seed each time
        }
      }
    );

    // Download the video
    const response = await fetch(output);
    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    const outputFile = path.join(OUTPUT_DIR, `variation-${seedNumber}.mp4`);
    fs.writeFileSync(outputFile, buffer);

    console.log(`✅ Variation ${seedNumber} saved: variation-${seedNumber}.mp4`);
    console.log(`   Preview: open ${outputFile}`);

    return outputFile;

  } catch (error) {
    console.error(`❌ Error generating variation ${seedNumber}:`, error.message);
    return null;
  }
}

async function convertToFormats(videoPath, variationNumber) {
  const baseName = `variation-${variationNumber}`;
  const apngPath = path.join(OUTPUT_DIR, `${baseName}.apng`);
  const webpPath = path.join(OUTPUT_DIR, `${baseName}.webp`);

  try {
    // APNG
    await execAsync(`ffmpeg -i "${videoPath}" -f apng -plays 0 "${apngPath}" -y`);

    // WebP
    await execAsync(`ffmpeg -i "${videoPath}" -vcodec libwebp -lossless 0 -compression_level 6 -q:v 80 -loop 0 -preset default -an -vsync 0 "${webpPath}" -y`);

    const apngSize = (fs.statSync(apngPath).size / 1024 / 1024).toFixed(2);
    const webpSize = (fs.statSync(webpPath).size / 1024 / 1024).toFixed(2);

    console.log(`   APNG: ${apngSize} MB | WebP: ${webpSize} MB`);
  } catch (error) {
    console.error(`   Error converting: ${error.message}`);
  }
}

// Main
(async () => {
  console.log('╔════════════════════════════════════════╗');
  console.log('║  Eye of Sauron - Multi Seed Attempt   ║');
  console.log('╚════════════════════════════════════════╝');
  console.log('\n🎲 Generating 5 variations with different random seeds...');
  console.log('   This will take 5-15 minutes total.\n');

  const variations = [];

  for (let i = 1; i <= 5; i++) {
    const videoPath = await generateVariation(i);
    if (videoPath) {
      variations.push(videoPath);
      await convertToFormats(videoPath, i);
    }

    // Small delay between requests
    if (i < 5) {
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }

  console.log('\n\n🎉 All variations generated!');
  console.log(`\n📁 Output directory: ${OUTPUT_DIR}`);
  console.log('\n🎬 Review the videos:');
  variations.forEach((path, idx) => {
    console.log(`   ${idx + 1}. open ${path}`);
  });

  console.log('\n💡 Once you find the best one:');
  console.log('   cp assets/sauron-variations/variation-N.webp packages/personas/sauron/icon.webp');
  console.log('   cp assets/sauron-variations/variation-N.apng packages/personas/sauron/icon.apng');

})();
