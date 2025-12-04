#!/usr/bin/env node

/**
 * Asset Manager Server
 * Development utility for browsing, validating, and managing game assets
 * Integrates with Google Gemini for AI-powered asset review
 * Integrates with ElevenLabs for voice generation
 */

import express from 'express';
import { readFileSync, readdirSync, statSync, existsSync, writeFileSync, mkdirSync } from 'fs';
import { resolve, dirname, join, extname, basename } from 'path';
import { fileURLToPath } from 'url';
import multer from 'multer';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '../..');
const ASSETS_DIR = resolve(PROJECT_ROOT, 'assets');

// Load environment variables
const loadEnv = () => {
  const envPath = resolve(PROJECT_ROOT, '.env');
  if (!existsSync(envPath)) {
    console.error('Error: .env file not found. Run from project root.');
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
const app = express();
const PORT = 3000;

// Middleware
app.use(express.json({ limit: '50mb' }));
app.use(express.static(__dirname));
app.use('/assets', express.static(ASSETS_DIR));
app.use('/demo-editor', express.static(resolve(__dirname, '../demo-editor')));

// File upload setup
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const category = req.body.category || 'images';
    const destPath = resolve(ASSETS_DIR, category);
    if (!existsSync(destPath)) {
      mkdirSync(destPath, { recursive: true });
    }
    cb(null, destPath);
  },
  filename: (req, file, cb) => {
    cb(null, file.originalname);
  }
});
const upload = multer({ storage });

// ============================================================
// ASSET LISTING ENDPOINTS
// ============================================================

// Get all image assets organized by category
app.get('/api/images', (req, res) => {
  const imagesDir = resolve(ASSETS_DIR, 'images');
  const assets = {};

  const scanDir = (dir, category = '') => {
    if (!existsSync(dir)) return;

    const items = readdirSync(dir);
    for (const item of items) {
      const fullPath = join(dir, item);
      const stat = statSync(fullPath);

      if (stat.isDirectory()) {
        scanDir(fullPath, category ? `${category}/${item}` : item);
      } else if (/\.(png|jpg|jpeg|webp|gif|svg)$/i.test(item)) {
        const cat = category || 'root';
        if (!assets[cat]) assets[cat] = [];

        assets[cat].push({
          filename: item,
          path: `/assets/images/${category ? category + '/' : ''}${item}`,
          fullPath,
          size: stat.size,
          modified: stat.mtime,
          category: cat
        });
      }
    }
  };

  scanDir(imagesDir);
  res.json(assets);
});

// Get all audio assets
app.get('/api/audio', (req, res) => {
  const audioDir = resolve(ASSETS_DIR, 'audio');
  const assets = [];

  if (!existsSync(audioDir)) {
    return res.json({ files: [], manifest: null });
  }

  const items = readdirSync(audioDir);
  for (const item of items) {
    const fullPath = join(audioDir, item);
    const stat = statSync(fullPath);

    if (stat.isFile() && /\.(mp3|wav|ogg|m4a)$/i.test(item)) {
      assets.push({
        filename: item,
        path: `/assets/audio/${item}`,
        fullPath,
        size: stat.size,
        modified: stat.mtime
      });
    }
  }

  // Load manifest if exists
  const manifestPath = resolve(audioDir, 'audio-manifest.json');
  let manifest = null;
  if (existsSync(manifestPath)) {
    manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
  }

  res.json({ files: assets, manifest });
});

// ============================================================
// GEMINI API ENDPOINTS
// ============================================================

// Analyze an image with Gemini
app.post('/api/gemini/analyze', async (req, res) => {
  const { imagePath, prompt } = req.body;

  if (!env.GEMINI_API_KEY) {
    return res.status(500).json({ error: 'GEMINI_API_KEY not configured' });
  }

  try {
    // Read image and convert to base64
    const fullPath = imagePath.startsWith('/assets')
      ? resolve(PROJECT_ROOT, imagePath.substring(1))
      : resolve(ASSETS_DIR, imagePath);

    if (!existsSync(fullPath)) {
      return res.status(404).json({ error: 'Image not found' });
    }

    const imageData = readFileSync(fullPath);
    const base64Image = imageData.toString('base64');
    const mimeType = getMimeType(fullPath);

    // Call Gemini API
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=${env.GEMINI_API_KEY}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{
            parts: [
              { text: prompt || 'Describe this image and suggest improvements for a retro CRT terminal-style game.' },
              {
                inline_data: {
                  mime_type: mimeType,
                  data: base64Image
                }
              }
            ]
          }]
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json({ error: error.error?.message || 'Gemini API error' });
    }

    const data = await response.json();
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text || 'No response';

    res.json({ response: text });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// Chat with Gemini about an asset
app.post('/api/gemini/chat', async (req, res) => {
  const { messages, imagePath } = req.body;

  if (!env.GEMINI_API_KEY) {
    return res.status(500).json({ error: 'GEMINI_API_KEY not configured' });
  }

  try {
    const parts = [];

    // Add image if provided
    if (imagePath) {
      const fullPath = imagePath.startsWith('/assets')
        ? resolve(PROJECT_ROOT, imagePath.substring(1))
        : resolve(ASSETS_DIR, imagePath);

      if (existsSync(fullPath)) {
        const imageData = readFileSync(fullPath);
        const base64Image = imageData.toString('base64');
        const mimeType = getMimeType(fullPath);

        parts.push({
          inline_data: {
            mime_type: mimeType,
            data: base64Image
          }
        });
      }
    }

    // Add conversation context
    const conversationText = messages.map(m => `${m.role}: ${m.content}`).join('\n\n');
    parts.push({ text: conversationText });

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=${env.GEMINI_API_KEY}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts }],
          systemInstruction: {
            parts: [{
              text: `You are an assistant helping review game assets for "Omarchy Defender", a retro CRT terminal-style game.
The game has a green phosphor glow aesthetic with scanlines.
All images should use SEO-friendly names with "xswarm" prefix.
Be concise and specific with suggestions.`
            }]
          }
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json({ error: error.error?.message || 'Gemini API error' });
    }

    const data = await response.json();
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text || 'No response';

    res.json({ response: text });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ============================================================
// ELEVENLABS API ENDPOINTS
// ============================================================

// Get available voices
app.get('/api/elevenlabs/voices', async (req, res) => {
  if (!env.ELEVENLABS_API_KEY) {
    return res.status(500).json({ error: 'ELEVENLABS_API_KEY not configured' });
  }

  try {
    const response = await fetch('https://api.elevenlabs.io/v1/voices', {
      headers: { 'xi-api-key': env.ELEVENLABS_API_KEY }
    });

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json({ error: error.detail?.message || 'ElevenLabs API error' });
    }

    const data = await response.json();
    res.json(data);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// Generate voice audio
app.post('/api/elevenlabs/generate', async (req, res) => {
  const { text, voiceId, settings, filename } = req.body;

  if (!env.ELEVENLABS_API_KEY) {
    return res.status(500).json({ error: 'ELEVENLABS_API_KEY not configured' });
  }

  try {
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
          model_id: settings?.model || 'eleven_multilingual_v2',
          voice_settings: {
            stability: settings?.stability ?? 0.5,
            similarity_boost: settings?.similarityBoost ?? 0.75,
            style: settings?.style ?? 0.3,
            use_speaker_boost: settings?.useSpeakerBoost ?? true
          }
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json({ error: error.detail?.message || 'ElevenLabs API error' });
    }

    // Save audio file
    const audioBuffer = await response.arrayBuffer();
    const audioDir = resolve(ASSETS_DIR, 'audio');
    if (!existsSync(audioDir)) {
      mkdirSync(audioDir, { recursive: true });
    }

    const outputPath = resolve(audioDir, filename || `generated-${Date.now()}.mp3`);
    writeFileSync(outputPath, Buffer.from(audioBuffer));

    res.json({
      success: true,
      filename: basename(outputPath),
      path: `/assets/audio/${basename(outputPath)}`
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// Get subscription info
app.get('/api/elevenlabs/subscription', async (req, res) => {
  if (!env.ELEVENLABS_API_KEY) {
    return res.status(500).json({ error: 'ELEVENLABS_API_KEY not configured' });
  }

  try {
    const response = await fetch('https://api.elevenlabs.io/v1/user/subscription', {
      headers: { 'xi-api-key': env.ELEVENLABS_API_KEY }
    });

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json({ error: error.detail?.message || 'ElevenLabs API error' });
    }

    const data = await response.json();
    res.json(data);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ============================================================
// FILE MANAGEMENT ENDPOINTS
// ============================================================

// Upload asset
app.post('/api/upload', upload.single('file'), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' });
  }

  res.json({
    success: true,
    filename: req.file.filename,
    path: `/assets/${req.body.category || 'images'}/${req.file.filename}`
  });
});

// Delete asset
app.delete('/api/asset', (req, res) => {
  const { path: assetPath } = req.body;

  const fullPath = assetPath.startsWith('/assets')
    ? resolve(PROJECT_ROOT, assetPath.substring(1))
    : resolve(ASSETS_DIR, assetPath);

  if (!existsSync(fullPath)) {
    return res.status(404).json({ error: 'Asset not found' });
  }

  try {
    const { unlinkSync } = require('fs');
    unlinkSync(fullPath);
    res.json({ success: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

const getMimeType = (filePath) => {
  const ext = extname(filePath).toLowerCase();
  const mimeTypes = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.svg': 'image/svg+xml'
  };
  return mimeTypes[ext] || 'application/octet-stream';
};

// ============================================================
// START SERVER
// ============================================================

app.listen(PORT, () => {
  console.log(`
╔══════════════════════════════════════════════════════════════╗
║           OMARCHY DEFENDER - ASSET MANAGER                  ║
╠══════════════════════════════════════════════════════════════╣
║  Image Assets:  http://localhost:${PORT}/                       ║
║  Audio Assets:  http://localhost:${PORT}/audio.html             ║
║  Demo Editor:   http://localhost:${PORT}/demo-editor/           ║
╠══════════════════════════════════════════════════════════════╣
║  APIs Available:                                             ║
║    • Gemini Vision (image analysis)                         ║
║    • ElevenLabs (voice generation)                          ║
╚══════════════════════════════════════════════════════════════╝
  `);
});
