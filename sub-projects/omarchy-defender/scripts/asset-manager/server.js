#!/usr/bin/env node

/**
 * Asset Manager Server
 * Development utility for browsing, validating, and managing game assets
 * Integrates with Google Gemini for AI-powered asset review
 * Integrates with ElevenLabs for voice generation
 */

import express from 'express';
import { readFileSync, readdirSync, statSync, existsSync, writeFileSync, mkdirSync, watch } from 'fs';
import { resolve, dirname, join, extname, basename } from 'path';
import { fileURLToPath } from 'url';
import multer from 'multer';
import { VideoExporter } from '../video-export/exporter.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '../..');
const ASSETS_DIR = resolve(PROJECT_ROOT, 'assets');
const SRC_ASSETS_DIR = resolve(PROJECT_ROOT, 'src/assets'); // For images during dev
const SRC_DIR = resolve(PROJECT_ROOT, 'src'); // Game source for live preview

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

// Serve preview.html as default, other tool pages
app.get('/', (req, res) => res.sendFile(resolve(__dirname, 'preview.html')));
app.use(express.static(__dirname));

// Serve the game at /app/ for live preview
app.use('/app', express.static(SRC_DIR));

// Serve assets from both locations
app.use('/assets', express.static(ASSETS_DIR));
app.use('/assets', express.static(SRC_ASSETS_DIR));

// Demo editor
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

// Get all image assets from manifest with generation status
app.get('/api/images', (req, res) => {
  // Check both assets/images and src/assets/images for images (flat structure)
  const imagesDir = resolve(ASSETS_DIR, 'images');
  const srcImagesDir = resolve(SRC_ASSETS_DIR, 'images');
  const categories = {};
  let totalCount = 0;
  let generatedCount = 0;

  // Build categories from manifest with file status (flat folder structure)
  for (const [category, items] of Object.entries(IMAGE_MANIFEST)) {
    categories[category] = items.map(item => {
      const filename = item.filename;

      // Check both possible locations (flat structure - no subfolders)
      const assetsPath = join(imagesDir, filename);
      const srcPath = join(srcImagesDir, filename);

      // Check if file exists in either location
      let exists = false;
      let fullPath = null;
      let fileInfo = null;

      if (existsSync(srcPath)) {
        exists = true;
        fullPath = srcPath;
      } else if (existsSync(assetsPath)) {
        exists = true;
        fullPath = assetsPath;
      }

      if (exists && fullPath) {
        const stat = statSync(fullPath);
        fileInfo = {
          size: stat.size,
          modified: stat.mtime
        };
        generatedCount++;
      }

      totalCount++;
      return {
        id: item.id,
        filename,
        description: item.description,
        prompt: item.prompt,
        size: item.size,
        style: IMAGE_STYLES[category] || IMAGE_STYLES.ui,
        path: `/assets/images/${filename}`,
        generated: exists,
        fileInfo
      };
    });
  }

  res.json({
    categories,
    styles: IMAGE_STYLES,
    stats: {
      total: totalCount,
      generated: generatedCount,
      pending: totalCount - generatedCount
    }
  });
});

// Get all audio assets from manifest with generation status
app.get('/api/audio', (req, res) => {
  const audioDir = resolve(ASSETS_DIR, 'audio');
  const categories = {};
  let totalCount = 0;
  let generatedCount = 0;

  // Build categories from manifest with file status
  for (const [category, lines] of Object.entries(VOICE_LINES)) {
    const settings = CATEGORY_SETTINGS[category] || CATEGORY_SETTINGS.default;
    categories[category] = lines.map(line => {
      const filename = `${line.id}.mp3`;
      const fullPath = join(audioDir, filename);
      const exists = existsSync(fullPath);
      let fileInfo = null;

      if (exists) {
        const stat = statSync(fullPath);
        fileInfo = {
          size: stat.size,
          modified: stat.mtime
        };
        generatedCount++;
      }

      totalCount++;
      return {
        id: line.id,
        text: line.text,
        filename,
        path: `/assets/audio/${filename}`,
        generated: exists,
        fileInfo,
        settings
      };
    });
  }

  res.json({
    categories,
    settings: CATEGORY_SETTINGS,
    stats: {
      total: totalCount,
      generated: generatedCount,
      pending: totalCount - generatedCount
    }
  });
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
// IMAGE GENERATION & EDITING ENDPOINTS
// ============================================================

// Generate image with GPT-4o (gpt-image-1 model)
app.post('/api/openai/generate', async (req, res) => {
  const { prompt, style, size, filename, category } = req.body;

  if (!env.OPENAI_API_KEY) {
    return res.status(500).json({ error: 'OPENAI_API_KEY not configured' });
  }

  try {
    // Combine prompt with global style
    const fullPrompt = `${style || IMAGE_STYLE}\n\n${prompt}`;

    // Map size string to supported sizes (gpt-image-1 supports: 1024x1024, 1536x1024, 1024x1536, auto)
    const sizeMap = {
      '16x16': '1024x1024',
      '32x32': '1024x1024',
      '64x64': '1024x1024',
      '128x128': '1024x1024',
      '180x180': '1024x1024',
      '192x192': '1024x1024',
      '256x256': '1024x1024',
      '512x512': '1024x1024',
      '1024x1024': '1024x1024',
      '1200x630': '1536x1024',  // Landscape
      '1200x600': '1536x1024'   // Landscape
    };
    const imageSize = sizeMap[size] || '1024x1024';

    const response = await fetch('https://api.openai.com/v1/images/generations', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.OPENAI_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'gpt-image-1',
        prompt: fullPrompt,
        n: 1,
        size: imageSize,
        quality: 'high',
        output_format: 'png'
      })
    });

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json({ error: error.error?.message || 'OpenAI API error' });
    }

    const data = await response.json();
    const imageBase64 = data.data[0].b64_json;

    // Determine save path (flat folder structure - no category subfolders)
    const imagesDir = resolve(SRC_ASSETS_DIR, 'images');
    if (!existsSync(imagesDir)) {
      mkdirSync(imagesDir, { recursive: true });
    }
    const savePath = resolve(imagesDir, filename);

    // Save the image
    writeFileSync(savePath, Buffer.from(imageBase64, 'base64'));

    res.json({
      success: true,
      filename,
      path: `/assets/images/${filename}`,
      revisedPrompt: data.data[0].revised_prompt || prompt
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// Edit existing image with Gemini (using Imagen 3 via Gemini API)
app.post('/api/gemini/edit', async (req, res) => {
  const { imagePath, editPrompt, style } = req.body;

  if (!env.GEMINI_API_KEY) {
    return res.status(500).json({ error: 'GEMINI_API_KEY not configured' });
  }

  try {
    // Read existing image
    const fullPath = imagePath.startsWith('/assets')
      ? resolve(PROJECT_ROOT, imagePath.substring(1))
      : resolve(ASSETS_DIR, imagePath);

    if (!existsSync(fullPath)) {
      return res.status(404).json({ error: 'Image not found' });
    }

    const imageData = readFileSync(fullPath);
    const base64Image = imageData.toString('base64');
    const mimeType = getMimeType(fullPath);

    // Use Gemini 2.0 Flash with image generation capability
    const fullPrompt = `Edit this image according to these instructions: ${editPrompt}

Style requirements: ${style || IMAGE_STYLE}

Generate a new version of the image with the requested changes applied.`;

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=${env.GEMINI_API_KEY}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{
            parts: [
              { text: fullPrompt },
              {
                inline_data: {
                  mime_type: mimeType,
                  data: base64Image
                }
              }
            ]
          }],
          generationConfig: {
            responseModalities: ['image', 'text'],
            responseMimeType: 'image/png'
          }
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json({ error: error.error?.message || 'Gemini API error' });
    }

    const data = await response.json();

    // Find the image part in the response
    const parts = data.candidates?.[0]?.content?.parts || [];
    let editedImageBase64 = null;
    let responseText = '';

    for (const part of parts) {
      if (part.inline_data?.data) {
        editedImageBase64 = part.inline_data.data;
      }
      if (part.text) {
        responseText = part.text;
      }
    }

    if (!editedImageBase64) {
      // If no image was generated, return an error with any text response
      return res.status(400).json({
        error: 'No image generated. ' + (responseText || 'Try a different edit prompt.')
      });
    }

    // Overwrite the existing image
    writeFileSync(fullPath, Buffer.from(editedImageBase64, 'base64'));

    res.json({
      success: true,
      path: imagePath,
      response: responseText || 'Image edited successfully'
    });
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
    '.svg': 'image/svg+xml',
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg'
  };
  return mimeTypes[ext] || 'application/octet-stream';
};

// ============================================================
// ASSET MANIFESTS (source of truth for required assets)
// ============================================================

// Voice lines from Central Command to remote outpost defender
// Style: Brief, distant, static-laced military transmissions
const VOICE_LINES = {
  stage1_intro: [
    { id: 'stage1-intro-1', text: 'Outpost Seven, come in. [static] Gnome cavalry spotted in your quadrant. This is not a drill.' },
    { id: 'stage1-intro-2', text: '[static] Command to Outpost. Hostile forces approaching your sector. Prepare terminal defenses.' },
    { id: 'stage1-intro-3', text: 'All units... [static] ...Gnome cavalry inbound. Outpost Seven, you are in their path. Hold the line.' }
  ],
  stage1_spawn: [
    { id: 'spawn-hint-1', text: 'Deploy terminal. Super Enter. [static] Now.' },
    { id: 'spawn-hint-2', text: '[static] Terminal deployment: Super Enter.' },
    { id: 'spawn-hint-3', text: 'Outpost, spawn terminal. Super... [static] ...Enter.' }
  ],
  stage1_close: [
    { id: 'close-hint-1', text: 'Close window. Super Q. [static] Confirm.' },
    { id: 'close-hint-2', text: '[static] Terminate with Super Q.' },
    { id: 'close-hint-3', text: 'Super Q... [static] ...closes active window.' }
  ],
  stage1_navigate: [
    { id: 'nav-hint-1', text: 'Navigation: Super plus H J K L. [static] Vim style.' },
    { id: 'nav-hint-2', text: '[static] Focus control. Super and direction keys.' },
    { id: 'nav-hint-3', text: 'Move focus... [static] ...Super H J K L.' }
  ],
  stage1_move: [
    { id: 'move-hint-1', text: 'Window relocation: add Shift. [static] Super Shift and direction.' },
    { id: 'move-hint-2', text: '[static] Shift modifier moves windows, not focus.' },
    { id: 'move-hint-3', text: 'Super Shift... [static] ...H J K L. Repositions window.' }
  ],
  calm: [
    { id: 'calm-1', text: 'Solid work, Outpost. [static] Keep it tight.' },
    { id: 'calm-2', text: '[static] Defense holding. Good.' },
    { id: 'calm-3', text: 'Clean execution. [static] Continue.' },
    { id: 'calm-4', text: '[static] Confirmed. Sector stable.' },
    { id: 'calm-5', text: 'Command acknowledges. [static] Maintain position.' }
  ],
  hint: [
    { id: 'hint-1', text: 'Outpost, check your training. [static] Think.' },
    { id: 'hint-2', text: '[static] Review your bindings.' },
    { id: 'hint-3', text: 'The key is there. [static] Focus.' },
    { id: 'hint-4', text: '[static] Remember Vim, Outpost.' },
    { id: 'hint-5', text: 'You know this. [static] Execute.' }
  ],
  urgent: [
    { id: 'urgent-1', text: '[static] Outpost! Time critical! Move!' },
    { id: 'urgent-2', text: 'Gnomes advancing! [static] Faster!' },
    { id: 'urgent-3', text: '[static] No time! Execute NOW!' },
    { id: 'urgent-4', text: 'Command to Outpost: MOVE! [static]' },
    { id: 'urgent-5', text: '[static] They are breaching! Respond!' }
  ],
  angry: [
    { id: 'angry-1', text: '[static] Outpost! What is happening down there!' },
    { id: 'angry-2', text: 'Unacceptable! [static] Get it together!' },
    { id: 'angry-3', text: '[static] Did your training mean nothing!' },
    { id: 'angry-4', text: 'Command is watching! [static] Perform!' },
    { id: 'angry-5', text: '[static] Outpost Seven! Respond properly!' }
  ],
  mouse_warning: [
    { id: 'mouse-1', text: '[static] Contamination alert! Mouse signature detected!' },
    { id: 'mouse-2', text: 'Outpost! Drop the rodent! [static] Keyboard only!' },
    { id: 'mouse-3', text: '[static] Mouse contact! Purity compromised!' },
    { id: 'mouse-4', text: 'The mouse corrupts! [static] Cease contact!' },
    { id: 'mouse-5', text: '[static] Warning! Contamination spreading in your sector!' }
  ],
  victory: [
    { id: 'victory-1', text: 'Sector cleared. [static] Well done, Outpost.' },
    { id: 'victory-2', text: '[static] Gnome forces retreating. Victory confirmed.' },
    { id: 'victory-3', text: 'Keyboard superiority demonstrated. [static] Command approves.' },
    { id: 'victory-4', text: '[static] Sector secured. Stand down.' },
    { id: 'victory-5', text: 'Hostiles eliminated. [static] Good work, Seven.' }
  ],
  defeat: [
    { id: 'defeat-1', text: '[static] Outpost Seven... sector lost. Regroup.' },
    { id: 'defeat-2', text: 'Breach confirmed. [static] We will try again.' },
    { id: 'defeat-3', text: '[static] Fall back. The sector has fallen.' },
    { id: 'defeat-4', text: 'Defeat logged. [static] Ready for redeployment?' },
    { id: 'defeat-5', text: '[static] Lost this one, Outpost. Reset and engage.' }
  ],
  stage2_intro: [
    { id: 'stage2-intro-1', text: '[static] Outpost Seven. Multiple sectors now under your watch. Gnomes spreading.' },
    { id: 'stage2-intro-2', text: 'Command expanding your zone. [static] Nine workspaces. One defender.' },
    { id: 'stage2-intro-3', text: '[static] Sector Command protocols active. Multi-zone defense begins.' }
  ],
  stage2_workspace: [
    { id: 'workspace-hint-1', text: 'Workspace switch: Super plus number. [static] One through nine.' },
    { id: 'workspace-hint-2', text: '[static] Pick your sector. Super and digit.' },
    { id: 'workspace-hint-3', text: 'Move windows between zones... [static] ...Super Shift and number.' }
  ],
  stage3_intro: [
    { id: 'stage3-intro-1', text: '[static] Full arsenal unlocked, Outpost. Every app at your disposal.' },
    { id: 'stage3-intro-2', text: 'Twenty shortcuts authorized. [static] Total control granted.' },
    { id: 'stage3-intro-3', text: '[static] Command releasing all Omarchy weapons. Engage at will.' }
  ],
  stage3_apps: [
    { id: 'app-browser', text: '[static] Browser: Super Shift B.' },
    { id: 'app-email', text: 'Email access: Super Shift E. [static]' },
    { id: 'app-files', text: '[static] File manager: Super Shift F.' },
    { id: 'app-terminal', text: 'Terminal always ready. [static] Super Enter.' },
    { id: 'app-ai', text: '[static] AI assist: Super Shift A.' },
    { id: 'app-music', text: 'Audio systems: Super Shift M. [static]' },
    { id: 'app-notes', text: '[static] Obsidian: Super Shift O.' }
  ],
  combo: [
    { id: 'combo-2', text: '[static] Double contact!' },
    { id: 'combo-3', text: 'Triple elimination! [static]' },
    { id: 'combo-5', text: '[static] Five down! Impressive, Outpost!' },
    { id: 'combo-10', text: 'Ten confirmed! [static] Unstoppable!' },
    { id: 'combo-perfect', text: '[static] Flawless sector defense. Command acknowledges.' }
  ],
  intro_narration: [
    { id: 'intro-narration', text: 'A long time ago, in a desktop far, far away... The desktop wars rage on. The Gnome cavalry, riding their mouse-dependent steeds, threaten to overrun the last bastion of keyboard efficiency. You are a newly recruited Omarchy Defender, trained in the ancient art of Hyprland window management. Your weapons: vim-style navigation, workspace mastery, and lightning-fast application launching. The mice grow restless. The Gnomes approach. Master Super plus H, J, K, L to navigate. Spawn terminals with Super Enter. Close windows with Super Q. Only the keyboard-pure shall survive. Only your keyboard skills can save us now.' }
  ]
};

const CATEGORY_SETTINGS = {
  calm: { stability: 0.7, similarityBoost: 0.75, style: 0.2 },
  hint: { stability: 0.6, similarityBoost: 0.75, style: 0.3 },
  urgent: { stability: 0.3, similarityBoost: 0.8, style: 0.6 },
  angry: { stability: 0.2, similarityBoost: 0.85, style: 0.7 },
  mouse_warning: { stability: 0.4, similarityBoost: 0.8, style: 0.5 },
  victory: { stability: 0.6, similarityBoost: 0.75, style: 0.4 },
  defeat: { stability: 0.7, similarityBoost: 0.7, style: 0.3 },
  combo: { stability: 0.3, similarityBoost: 0.85, style: 0.6 },
  intro_narration: { stability: 0.6, similarityBoost: 0.7, style: 0.4 }, // Dramatic movie trailer style
  default: { stability: 0.5, similarityBoost: 0.75, style: 0.3 }
};

// Category-specific styles for image generation
const IMAGE_STYLES = {
  ui: `Retro CRT terminal UI aesthetic. Dark background (#0a0a0a to #1a1a1a).
Bright green (#00ff41) as primary color with subtle glow/bloom effect.
Horizontal scanline texture visible but not distracting.
Clean, technical appearance like an old military radar or terminal display.
Subtle phosphor persistence effect on bright elements.
Transparent PNG with alpha channel for compositing.
Crisp edges, no blur or anti-aliasing artifacts.`,

  enemies: `Sci-fi alien creature style with pixel art quality, 16-bit era with modern polish.
Gnomes are alien invaders: green-grey skin, glowing eyes, otherworldly features.
Weapons are triangular/angular designs resembling the Arch Linux logo - sleek, minimalist, deadly.
Characters should be expressive and readable at small sizes.
Slight cel-shading effect with clean outlines.
Humorous and slightly menacing tone - not scary, but threatening.
Transparent PNG background for game sprite use.
Consistent lighting from upper-left.`,

  effects: `VFX overlay style optimized for additive blending.
Bright glowing elements on transparent or dark backgrounds.
Soft gradients and particle-like qualities.
Green phosphor glow (#00ff41) as primary effect color.
Red/orange for warnings and alerts.
High contrast for visibility during gameplay.
Transparent PNG with alpha gradients.`,

  apps: `Flat icon design in monochrome green (#00ff41) on transparent background.
Simple, recognizable silhouettes - must read clearly at 64x64 pixels.
Consistent stroke weight and visual density across all icons.
Slight inner glow or highlight for depth.
Rounded square container shape implied (not drawn).
Pixel-perfect alignment, no anti-aliasing blur.
Minimalist style - single concept per icon.`,

  icons: `Game branding and marketing imagery.
CRT terminal aesthetic with green phosphor glow on dark (#0a0a0a).
"OMARCHY DEFENDER" title treatment in retro computing font.
Keyboard keys and terminal cursor as recurring motifs.
Professional quality suitable for app stores and social sharing.
Strong contrast and legibility at various sizes.
Conveys: retro computing, keyboard gaming, tower defense.`
};

const IMAGE_MANIFEST = {
  ui: [
    {
      id: 'grid-cell',
      filename: 'grid-cell.png',
      description: '3x3 grid cell background',
      size: '128x128',
      prompt: `Single square grid cell for a 3x3 defense grid layout.
Subtle green (#00ff41) border lines, 2-3 pixels thick, with corner brackets.
Interior is dark (#0a0a0a) with very subtle radial gradient darker at center.
Faint grid texture or circuit-board pattern barely visible in the background.
Corners have small technical markers like targeting brackets.
Should tile seamlessly when placed in a 3x3 arrangement.
Transparent areas outside the cell borders.`
    },
    {
      id: 'grid-cell-focused',
      filename: 'grid-cell-focused.png',
      description: 'Grid cell with focus indicator',
      size: '128x128',
      prompt: `Same grid cell as base but with active focus state.
Brighter green border (#00ff41) with visible glow/bloom effect.
Pulsing energy effect suggested by brighter center gradient.
Corner brackets more prominent with additional detail.
Slight scanline effect more visible in this state.
Conveys: this cell is selected, ready for action.`
    },
    {
      id: 'grid-cell-occupied',
      filename: 'grid-cell-occupied.png',
      description: 'Grid cell with terminal window',
      size: '128x128',
      prompt: `Grid cell containing an active terminal window.
Terminal window frame in green with title bar showing ">_".
Dark interior with a few lines of green "code" text (abstract, not readable).
Blinking cursor at bottom of terminal content.
Window has subtle drop shadow within the cell.
Conveys: defensive position established, terminal deployed.`
    },
    {
      id: 'grid-cell-target',
      filename: 'grid-cell-target.png',
      description: 'Grid cell being targeted by enemy',
      size: '128x128',
      prompt: `Grid cell under attack - warning state.
Red/orange pulsing border replacing the green.
Targeting reticle or crosshair overlay in center.
Warning stripes or hazard pattern at corners.
Flickering/unstable appearance suggested by double-lines.
Conveys: enemy approaching this cell, urgent action needed.`
    },
    {
      id: 'grid-cell-breach',
      filename: 'grid-cell-breach.png',
      description: 'Grid cell after enemy breach',
      size: '128x128',
      prompt: `Grid cell that has been breached by enemy.
Damaged appearance - broken border lines, corruption artifacts.
Red warning color dominant, green elements flickering/failing.
Crack or shatter pattern emanating from center.
Smoke or static noise effect overlay.
Conveys: defense failed here, damage taken.`
    },
    {
      id: 'terminal-window',
      filename: 'terminal-window.png',
      description: 'Deployable terminal window sprite',
      size: '96x96',
      prompt: `Standalone terminal window for placement on grid.
Classic terminal window chrome - title bar with buttons, frame border.
Title bar shows ">_ TERM" or similar in small text.
Dark interior with 3-4 lines of green monospace "code" (abstract characters).
Blinking cursor block at the end of last line.
Subtle scanlines across the terminal content.
Green phosphor glow around the entire window.
Transparent background for sprite overlay.`
    },
    {
      id: 'command-panel-bg',
      filename: 'command-panel-bg.png',
      description: 'Command center side panel background',
      size: '320x600',
      prompt: `Vertical sidebar panel for game UI - command center aesthetic.
Dark metal/tech frame border with rivets and panel lines.
Interior darker with subtle tech texture - circuit traces, hex patterns.
Green accent lines separating logical sections (3-4 horizontal dividers).
Top section has "COMMAND" or military designation look.
Scanline overlay across entire panel.
Worn, used equipment aesthetic - not pristine, battle-tested.
CRT monitor edge effect at borders - slight curve/vignette.`
    },
    {
      id: 'scanline-overlay',
      filename: 'scanline-overlay.png',
      description: 'CRT scanline effect overlay',
      size: '4x256',
      prompt: `Tileable vertical strip for CRT scanline effect.
Alternating horizontal lines - one dark, one transparent.
Very subtle - opacity around 10-15% for the dark lines.
Creates authentic CRT monitor appearance when tiled horizontally.
Pure technical asset - no decorative elements.`
    },
    {
      id: 'vignette-overlay',
      filename: 'vignette-overlay.png',
      description: 'Screen edge vignette effect',
      size: '512x512',
      prompt: `Radial vignette for CRT screen edge darkening.
Transparent center, gradually darkening toward edges.
Corners are darkest - simulating CRT curvature shadow.
Very subtle green tint in the dark areas.
Slight barrel distortion suggested by the gradient shape.
Tileable/stretchable to any screen size.`
    }
  ],
  enemies: [
    {
      id: 'gnome-cavalry-idle',
      filename: 'gnome-cavalry-idle.png',
      description: 'Alien Gnome riding mouse - idle stance',
      size: '64x64',
      prompt: `Alien creature called a "Gnome" riding a computer mouse like a cavalry mount.
Gnome: green-grey alien skin, bulbous head, glowing cyan eyes, small pointy ears.
Wears high-tech visor on forehead, metallic collar, dark space suit.
Expression: smug, confident, calculating alien menace.
Pose: sitting upright on mouse, one hand on "reins" (USB cable), other hand holding triangular blaster (Arch Linux logo shaped).
Mouse: gray/white computer mouse body, red glowing LED eyes, cable as tail.
Mouse pose: standing alert, all four "feet" (mouse feet/pads) on ground.
Facing right, ready to charge leftward toward the player's grid.
Pixel art style with clean outlines, 16-bit quality.
Slight bounce animation suggested by pose.`
    },
    {
      id: 'gnome-cavalry-charge',
      filename: 'gnome-cavalry-charge.png',
      description: 'Alien Gnome riding mouse - charging attack',
      size: '64x64',
      prompt: `Same alien Gnome cavalry in aggressive charging pose.
Gnome: leaning forward, alien features intense, eyes glowing brighter.
Expression: aggressive alien battle cry, mouth open showing small fangs.
One hand pulling USB cable reins, other hand aiming triangular energy blaster (Arch Linux logo shaped - angular, minimalist).
Triangular weapon glowing with green energy beam charging.
Mouse: front legs up in rearing/galloping pose, eyes glowing brighter red.
Speed lines or motion blur effect behind them.
More dynamic, aggressive energy than idle pose.
Conveys: incoming alien attack, urgent threat.`
    },
    {
      id: 'gnome-cavalry-victory',
      filename: 'gnome-cavalry-victory.png',
      description: 'Alien Gnome celebrating breach success',
      size: '64x64',
      prompt: `Alien Gnome cavalry celebrating after breaching defenses.
Gnome: alien arms raised in triumph, antenna-like ears vibrating with joy.
Expression: alien victory screech, glowing eyes pulsing brighter.
Holding captured "trophy" - small keyboard key or terminal fragment.
Triangular blaster holstered, celebrating unarmed.
Mouse: prancing proudly, chest puffed out.
Small sparkles or victory effects around them.
Smug alien energy - they won this round.`
    },
    {
      id: 'gnome-cavalry-defeated',
      filename: 'gnome-cavalry-defeated.png',
      description: 'Alien Gnome knocked off mouse - defeated',
      size: '64x64',
      prompt: `Alien Gnome cavalry defeated by terminal defense.
Gnome: falling or fallen off mouse, visor cracked, expression of alien shock.
Green-grey skin sparking with static from terminal shock.
Arms flailing, classic cartoon defeat pose.
Triangular weapon spinning away from grip.
Mouse: sparking, glitching, LED eyes flickering.
Small "zap" effects or command-line characters floating around.
Comedic alien defeat - not violent, just thoroughly outmatched by keyboard skills.`
    },
    {
      id: 'gnome-infantry',
      filename: 'gnome-infantry.png',
      description: 'Foot soldier alien gnome without mount',
      size: '48x48',
      prompt: `Smaller alien Gnome soldier without mouse mount - infantry unit.
Same alien design: green-grey skin, glowing eyes, small ears.
Wearing lighter space suit armor, carrying small triangular pistol (Arch logo shape).
Small energy shield generator on arm.
Marching pose, determined alien expression.
Smaller and weaker looking than cavalry - easier enemy type.
Still menacing but clearly less threatening.`
    },
    {
      id: 'gnome-commander',
      filename: 'gnome-commander.png',
      description: 'Elite alien gnome commander - boss enemy',
      size: '96x96',
      prompt: `Elite alien Gnome commander - larger, more imposing boss character.
Riding a larger gaming mouse with RGB lighting effects (not just red eyes).
Alien features more pronounced: larger head, multiple glowing eyes, ornate visor.
Wearing decorated armor with triangular Arch logo emblems, flowing energy cape.
Holding large triangular staff weapon - the "Arch Scepter" - glowing with power.
Expression: intelligent, calculating, true alien villain energy.
Accompanied by floating "minion" drones or smaller mice.
More detailed, higher quality than regular gnomes.
Conveys: serious alien threat, requires skill to defeat.`
    },
    {
      id: 'cursor-swarm',
      filename: 'cursor-swarm.png',
      description: 'Group of hostile mouse cursors',
      size: '64x64',
      prompt: `Swarm of corrupted mouse cursor arrows.
5-7 cursors in formation, varying sizes.
White/gray base color with red corruption/glitch effects.
Some cursors more distorted than others - pixelation, color bleeding.
Moving as a group, coordinated threat.
Trailing glitch artifacts and static noise.
Minor enemy type - numerous but weak.`
    },
    {
      id: 'cursor-single',
      filename: 'cursor-single.png',
      description: 'Single corrupted mouse cursor',
      size: '32x32',
      prompt: `Single corrupted mouse cursor arrow - detailed view.
Standard arrow cursor shape but infected/corrupted.
White base with red veins/cracks spreading from tip.
Pixelated distortion at edges, slight double-vision effect.
Small glitch particles emanating from it.
Unsettling, virus-like appearance.
Basic fodder enemy.`
    }
  ],
  effects: [
    {
      id: 'phosphor-glow',
      filename: 'phosphor-glow.png',
      description: 'Green phosphor glow for highlights',
      size: '256x256',
      prompt: `Soft circular glow effect in CRT phosphor green.
Center is bright green (#00ff41) at about 80% opacity.
Smooth radial gradient to fully transparent at edges.
Slight noise/grain texture for authentic CRT feel.
Used as additive blend overlay on terminals and UI elements.
Should create halo effect when placed behind objects.`
    },
    {
      id: 'terminal-spawn',
      filename: 'terminal-spawn.png',
      description: 'Terminal deployment animation frame',
      size: '128x128',
      prompt: `Visual effect for terminal appearing on grid.
Boot-up sequence aesthetic - lines of "code" rapidly scrolling.
Green characters materializing from top to bottom.
Bright flash at center, CRT warm-up glow.
Electrical/digital energy crackling at edges.
Single frame suggesting rapid deployment animation.
Conveys: terminal is being spawned/deployed.`
    },
    {
      id: 'terminal-destroy',
      filename: 'terminal-destroy.png',
      description: 'Terminal destruction effect',
      size: '128x128',
      prompt: `Visual effect for terminal being closed/destroyed.
Implosion effect - content collapsing to center point.
Green pixels scattering outward.
CRT power-down line (horizontal line shrinking to dot).
Small spark/zap effects.
Glitch artifacts and screen tear as it closes.
Conveys: terminal eliminated, satisfying destruction.`
    },
    {
      id: 'gnome-hit',
      filename: 'gnome-hit.png',
      description: 'Enemy taking damage effect',
      size: '64x64',
      prompt: `Impact effect when gnome takes damage.
White flash at impact point.
Small keyboard key symbols flying out (K, J, H, L).
Electrical zap effects in green.
Motion lines indicating knockback.
Comic-style impact star or burst.
Quick, punchy visual feedback.`
    },
    {
      id: 'gnome-defeat',
      filename: 'gnome-defeat.png',
      description: 'Enemy defeated explosion',
      size: '96x96',
      prompt: `Explosion effect when gnome is fully defeated.
Burst of green terminal characters and code fragments.
Gnome hat spinning away as separate element.
Pixel scatter effect in character colors.
Victory sparkles in green and gold.
"CHMOD 777" or funny terminal command fragments visible.
Satisfying defeat celebration.`
    },
    {
      id: 'breach-warning',
      filename: 'breach-warning.png',
      description: 'Grid cell breach warning indicator',
      size: '128x128',
      prompt: `Urgent warning indicator for incoming breach.
Flashing red/orange hazard pattern.
Exclamation mark or warning triangle in center.
Radar sweep or pulse effect emanating outward.
Glitchy, unstable appearance.
High contrast for visibility during action.
Conveys: DANGER, act now or take damage.`
    },
    {
      id: 'breach-impact',
      filename: 'breach-impact.png',
      description: 'Grid breach damage effect',
      size: '128x128',
      prompt: `Visual effect when gnome breaches undefended cell.
Red damage burst, screen shake implied by offset elements.
Crack or shatter pattern.
Sparks and debris flying outward.
Screen static/corruption at edges.
Alarm indicator elements.
Conveys: damage taken, defense failed.`
    },
    {
      id: 'combo-indicator',
      filename: 'combo-indicator.png',
      description: 'Combo counter effect background',
      size: '128x64',
      prompt: `Background effect for combo counter display.
Energetic frame with lightning/electricity effects.
Green neon glow border.
Space in center for number overlay.
More intense/bright as combo increases (this is high combo version).
Speed lines and excitement energy.
Conveys: player is doing great, keep it up!`
    },
    {
      id: 'purity-warning',
      filename: 'purity-warning.png',
      description: 'Mouse contamination warning effect',
      size: '256x256',
      prompt: `Full-screen warning overlay for mouse usage detection.
Red vignette pulsing at screen edges.
"CONTAMINATION" or biohazard symbol in corners.
Static noise increasing toward edges.
Corrupted scan lines.
Sirens/alarm visual indicators.
Conveys: stop using mouse, keyboard purity compromised!`
    },
    {
      id: 'workspace-transition',
      filename: 'workspace-transition.png',
      description: 'Workspace switch effect',
      size: '256x256',
      prompt: `Visual effect for switching between workspaces.
Sliding/wiping motion blur effect.
Grid cells motion-streaked horizontally.
Ghost images of leaving and entering workspaces.
Brief flash at transition point.
Quick, smooth transition energy.
Conveys: rapid workspace navigation.`
    }
  ],
  apps: [
    {
      id: 'app-terminal',
      filename: 'terminal.png',
      description: 'Terminal app icon',
      size: '64x64',
      prompt: `Terminal/console application icon.
Simple ">_" command prompt symbol, large and centered.
Blinking cursor block after the underscore.
Bright green (#00ff41) on transparent background.
Clean geometric shapes, monospace character feel.
Slight inner glow for depth.
Instantly recognizable as terminal/command line.`
    },
    {
      id: 'app-browser',
      filename: 'browser.png',
      description: 'Web browser app icon',
      size: '64x64',
      prompt: `Web browser application icon.
Simple globe or compass rose design.
Meridian and parallel lines suggesting world map.
Green monochrome (#00ff41) on transparent.
Clean geometric construction.
Alternatively: window frame with navigation elements.
Conveys: internet, web browsing, world access.`
    },
    {
      id: 'app-browser-private',
      filename: 'browser-private.png',
      description: 'Private/incognito browser icon',
      size: '64x64',
      prompt: `Private browsing mode icon.
Same globe/browser base as regular browser.
Added: mask, hat, or incognito indicator overlay.
Slightly different shade or dotted line style.
Green monochrome on transparent.
Conveys: private, anonymous, incognito browsing.`
    },
    {
      id: 'app-file-manager',
      filename: 'file-manager.png',
      description: 'File manager app icon',
      size: '64x64',
      prompt: `File manager/folder application icon.
Classic folder shape in three-quarter view.
Tab at top, slight 3D perspective depth.
Small document corner peeking from inside folder.
Green monochrome (#00ff41) on transparent.
Clean, minimal design.
Conveys: files, documents, organization.`
    },
    {
      id: 'app-email',
      filename: 'email.png',
      description: 'Email (HEY) app icon',
      size: '64x64',
      prompt: `Email application icon.
Classic envelope shape, slightly open/unsealed.
Letter or notification dot peeking out.
Green monochrome (#00ff41) on transparent.
Simple geometric construction.
Clean, professional appearance.
Conveys: email, messages, communication.`
    },
    {
      id: 'app-calendar',
      filename: 'calendar.png',
      description: 'Calendar app icon',
      size: '64x64',
      prompt: `Calendar application icon.
Calendar page with date grid visible.
Binding rings or spiral at top edge.
Generic day number "15" or similar shown.
Green monochrome (#00ff41) on transparent.
Clean grid lines for date squares.
Conveys: scheduling, dates, time management.`
    },
    {
      id: 'app-ai-chat',
      filename: 'ai-chat.png',
      description: 'AI Chat (ChatGPT) app icon',
      size: '64x64',
      prompt: `AI assistant/chat application icon.
Speech bubble containing brain or neural network symbol.
Alternatively: sparkle/magic wand with chat bubble.
Suggests intelligence and conversation combined.
Green monochrome (#00ff41) on transparent.
Modern, clean design.
Conveys: AI, assistant, intelligent chat.`
    },
    {
      id: 'app-twitter',
      filename: 'twitter.png',
      description: 'X/Twitter app icon',
      size: '64x64',
      prompt: `X/Twitter social media icon.
Bold "X" letter design, geometric construction.
Alternatively: simplified bird silhouette.
Green monochrome (#00ff41) on transparent.
Clean, recognizable shape.
Thick strokes for visibility at small size.
Conveys: social media, posts, public communication.`
    },
    {
      id: 'app-music',
      filename: 'music.png',
      description: 'Music/Spotify app icon',
      size: '64x64',
      prompt: `Music streaming application icon.
Sound waves radiating from center, or musical note.
Could include headphones element.
Three curved lines (like Spotify) or eighth note.
Green monochrome (#00ff41) on transparent.
Dynamic, rhythmic feeling.
Conveys: music, audio, streaming.`
    },
    {
      id: 'app-obsidian',
      filename: 'obsidian.png',
      description: 'Obsidian notes app icon',
      size: '64x64',
      prompt: `Obsidian note-taking application icon.
Gem/crystal shape suggesting obsidian stone.
Alternatively: connected nodes forming knowledge graph.
Faceted geometric crystal design.
Green monochrome (#00ff41) on transparent.
Sharp, precise angles.
Conveys: notes, knowledge, connections.`
    },
    {
      id: 'app-neovim',
      filename: 'neovim.png',
      description: 'Neovim editor app icon',
      size: '64x64',
      prompt: `Neovim/Vim code editor icon.
Stylized "N" letter with vim aesthetic.
Could incorporate code brackets { } or cursor.
Angular, efficient design matching vim philosophy.
Green monochrome (#00ff41) on transparent.
Technical, developer-focused appearance.
Conveys: code editing, vim, programming.`
    },
    {
      id: 'app-btop',
      filename: 'btop.png',
      description: 'System monitor (btop) app icon',
      size: '64x64',
      prompt: `System/resource monitor application icon.
Performance graph with bars or line chart.
CPU usage meter or speedometer design.
Multiple metrics suggested (CPU, RAM, etc).
Green monochrome (#00ff41) on transparent.
Technical, dashboard aesthetic.
Conveys: monitoring, performance, system health.`
    },
    {
      id: 'app-docker',
      filename: 'docker.png',
      description: 'Docker container app icon',
      size: '64x64',
      prompt: `Docker/container management icon.
Whale silhouette carrying containers (classic Docker logo style).
Alternatively: stacked container boxes.
Simple, recognizable shape.
Green monochrome (#00ff41) on transparent.
Clean geometric construction.
Conveys: containers, deployment, DevOps.`
    },
    {
      id: 'app-password',
      filename: 'password.png',
      description: 'Password manager app icon',
      size: '64x64',
      prompt: `Password/security manager icon.
Key shape, or padlock/vault door.
Shield with keyhole could work.
Suggests security and secret protection.
Green monochrome (#00ff41) on transparent.
Trustworthy, secure appearance.
Conveys: passwords, security, secrets.`
    },
    {
      id: 'app-signal',
      filename: 'signal.png',
      description: 'Signal messenger app icon',
      size: '64x64',
      prompt: `Signal secure messenger icon.
Speech bubble with signal wave inside.
Alternatively: chat bubble with lock/shield.
Emphasizes privacy and encryption.
Green monochrome (#00ff41) on transparent.
Clean, trustworthy design.
Conveys: secure messaging, privacy, encryption.`
    },
    {
      id: 'app-whatsapp',
      filename: 'whatsapp.png',
      description: 'WhatsApp messenger app icon',
      size: '64x64',
      prompt: `WhatsApp messaging application icon.
Phone handset inside speech bubble.
Classic WhatsApp logo composition.
Simple, recognizable silhouette.
Green monochrome (#00ff41) on transparent.
Friendly, communication-focused.
Conveys: messaging, calls, chat.`
    },
    {
      id: 'app-messages',
      filename: 'messages.png',
      description: 'Google Messages app icon',
      size: '64x64',
      prompt: `SMS/text messaging icon.
Chat bubble with text lines or dots inside.
Could show two overlapping bubbles for conversation.
Simple, universal messaging symbol.
Green monochrome (#00ff41) on transparent.
Friendly, approachable design.
Conveys: texting, SMS, conversation.`
    },
    {
      id: 'app-launcher',
      filename: 'launcher.png',
      description: 'App launcher/search icon',
      size: '64x64',
      prompt: `Application launcher/spotlight icon.
Grid of small squares suggesting app grid.
Alternatively: magnifying glass with apps.
Rocket or launch symbol could work.
Green monochrome (#00ff41) on transparent.
Suggests quick access and search.
Conveys: launch apps, search, quick access.`
    },
    {
      id: 'app-omarchy-menu',
      filename: 'omarchy-menu.png',
      description: 'Omarchy system menu icon',
      size: '64x64',
      prompt: `Omarchy system menu icon.
Hamburger menu (three horizontal lines) base.
Could incorporate "O" or Omarchy branding.
System settings/control panel feel.
Green monochrome (#00ff41) on transparent.
Clean, functional design.
Conveys: system menu, settings, control.`
    },
    {
      id: 'app-share',
      filename: 'share.png',
      description: 'Share menu icon',
      size: '64x64',
      prompt: `Share/export menu icon.
Classic share symbol - dot with radiating connections.
Alternatively: arrow pointing outward from box.
Network/distribution feeling.
Green monochrome (#00ff41) on transparent.
Clean, universally understood symbol.
Conveys: share, send, export.`
    },
    {
      id: 'app-mouse-cursor',
      filename: 'mouse-cursor.png',
      description: 'Evil computer mouse - the enemy within',
      size: '64x64',
      prompt: `Evil computer mouse (the hardware peripheral device you click with).
Sinister-looking wireless or wired mouse with glowing red LED eyes.
Dark/black plastic body with menacing face features embedded in the design.
Cable looks like a serpent tail if wired, or evil aura if wireless.
Two button "eyes" glowing red, scroll wheel as angry mouth/nose.
Sci-fi/military art style matching game aesthetic.
Transparent background.
Conveys: the enemy within, your mouse addiction personified, click addiction.`
    }
  ],
  icons: [
    {
      id: 'favicon-16',
      filename: 'favicon-16.png',
      description: 'Favicon 16x16',
      size: '16x16',
      prompt: `Tiny favicon for browser tabs - must read at 16x16 pixels.
Single terminal cursor block ">_" simplified to bare minimum.
Bright green (#00ff41) on dark background (#0a0a0a).
Maximum contrast, no fine details - they won't be visible.
Consider just a green square with corner notch or ">" shape.
Must be instantly recognizable as "terminal/code" even at tiny size.`
    },
    {
      id: 'favicon-32',
      filename: 'favicon-32.png',
      description: 'Favicon 32x32',
      size: '32x32',
      prompt: `Small favicon for higher-res displays.
Terminal cursor ">_" more defined than 16px version.
Bright green (#00ff41) on dark background (#0a0a0a).
Slight glow effect possible at this size.
Could include subtle grid pattern in background.
Clean, sharp pixels - no anti-aliasing blur.
Recognizable as terminal/command line.`
    },
    {
      id: 'apple-touch-icon',
      filename: 'apple-touch-icon.png',
      description: 'Apple touch icon 180x180',
      size: '180x180',
      prompt: `iOS home screen app icon - 180x180 pixels.
Full "OMARCHY DEFENDER" branding possible.
"OD" monogram or terminal window with game elements.
Green phosphor glow on dark background.
Include subtle keyboard key or gnome silhouette hint.
iOS will apply rounded corners automatically.
Should look great on iPhone home screen.
Professional app quality.`
    },
    {
      id: 'icon-192',
      filename: 'icon-192.png',
      description: 'PWA icon 192x192',
      size: '192x192',
      prompt: `Progressive Web App icon - 192x192 pixels.
Game logo with terminal aesthetic.
Central element: terminal window or ">_" cursor.
Keyboard keys arranged decoratively around edge.
Green phosphor glow (#00ff41) on dark (#0a0a0a).
Could hint at 3x3 grid pattern.
Clean and recognizable for PWA install.`
    },
    {
      id: 'icon-512',
      filename: 'icon-512.png',
      description: 'PWA icon 512x512',
      size: '512x512',
      prompt: `Large PWA icon with full detail - 512x512 pixels.
Complete game branding and logo.
"OMARCHY DEFENDER" title or "OD" prominent.
Terminal window graphic as central element.
Keyboard keys: H, J, K, L visible as design elements.
Small gnome cavalry silhouette lurking in corner or background.
Green phosphor glow with scanline effects.
CRT screen frame aesthetic.
Highest quality, this is the hero icon.`
    },
    {
      id: 'og-image',
      filename: 'og-image.png',
      description: 'Open Graph social share image 1200x630',
      size: '1200x630',
      prompt: `Social media share preview image - 1200x630 pixels.
"OMARCHY DEFENDER" title large and prominent, retro terminal font.
Subtitle: "Learn Keyboard Shortcuts Through Combat" or similar.
Visual scene: 3x3 grid with terminal windows defending against gnome cavalry.
Keyboard keys SUPER, H, J, K, L highlighted as game elements.
CRT monitor frame around the entire image.
Green phosphor color scheme with scanlines.
Should make people want to click and play.
Explains the game concept visually.`
    },
    {
      id: 'twitter-card',
      filename: 'twitter-card.png',
      description: 'Twitter card image 1200x600',
      size: '1200x600',
      prompt: `Twitter/X card preview image - 1200x600 pixels.
Similar to OG image but slightly different aspect ratio.
"OMARCHY DEFENDER" title with action scene.
Gnome cavalry charging toward terminal defenses.
Keyboard shortcut hints visible: "SUPER+ENTER to Deploy".
More action-focused than OG image.
CRT aesthetic with green phosphor glow.
Compelling call-to-action feeling.
"Free • Browser-based • Keyboard Only" text possible.`
    }
  ]
};

// ============================================================
// FILE WATCHER & AUTO-REFRESH (SSE)
// ============================================================

// Track SSE clients
const sseClients = new Set();

// SSE endpoint for auto-refresh
app.get('/api/events', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('Access-Control-Allow-Origin', '*');

  // Send initial connected message
  res.write('data: {"type":"connected"}\n\n');

  // Add to clients
  sseClients.add(res);

  // Remove on disconnect
  req.on('close', () => {
    sseClients.delete(res);
  });
});

// Broadcast to all SSE clients
const broadcast = (data) => {
  const message = `data: ${JSON.stringify(data)}\n\n`;
  for (const client of sseClients) {
    client.write(message);
  }
};

// Watch asset directories for changes
const watchDirs = ['images', 'audio'];
for (const dir of watchDirs) {
  const watchPath = resolve(ASSETS_DIR, dir);
  if (existsSync(watchPath)) {
    watch(watchPath, { recursive: true }, (eventType, filename) => {
      if (filename && !filename.startsWith('.')) {
        broadcast({
          type: 'fileChange',
          event: eventType,
          file: filename,
          dir: dir,
          timestamp: Date.now()
        });
      }
    });
  }
}

// Watch src/assets/images for image changes
const srcImagesPath = resolve(SRC_ASSETS_DIR, 'images');
if (existsSync(srcImagesPath)) {
  watch(srcImagesPath, { recursive: true }, (eventType, filename) => {
    if (filename && !filename.startsWith('.')) {
      broadcast({
        type: 'fileChange',
        event: eventType,
        file: filename,
        dir: 'images',
        timestamp: Date.now()
      });
    }
  });
}

// Watch src/ for game code changes (hot reload)
if (existsSync(SRC_DIR)) {
  watch(SRC_DIR, { recursive: true }, (eventType, filename) => {
    if (filename && !filename.startsWith('.') && !filename.includes('assets')) {
      broadcast({
        type: 'fileChange',
        event: eventType,
        file: filename,
        dir: 'src',
        timestamp: Date.now()
      });
    }
  });
}

// ============================================================
// R2 UPLOAD ENDPOINT
// ============================================================

app.post('/api/r2/upload', async (req, res) => {
  const { filePath, bucket } = req.body;

  if (!env.CLOUDFLARE_ACCOUNT_ID || !env.CLOUDFLARE_API_TOKEN) {
    return res.status(500).json({ error: 'Cloudflare credentials not configured' });
  }

  const bucketName = bucket || 'omarchy-defender-assets';

  try {
    const fullPath = filePath.startsWith('/')
      ? filePath
      : resolve(ASSETS_DIR, filePath);

    if (!existsSync(fullPath)) {
      return res.status(404).json({ error: 'File not found' });
    }

    const fileBuffer = readFileSync(fullPath);
    const mimeType = getMimeType(fullPath);
    const key = basename(fullPath);

    // Upload to R2 via Cloudflare API
    const uploadUrl = `https://api.cloudflare.com/client/v4/accounts/${env.CLOUDFLARE_ACCOUNT_ID}/r2/buckets/${bucketName}/objects/${key}`;

    const response = await fetch(uploadUrl, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${env.CLOUDFLARE_API_TOKEN}`,
        'Content-Type': mimeType
      },
      body: fileBuffer
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      return res.status(response.status).json({ error: error.errors?.[0]?.message || 'R2 upload failed' });
    }

    res.json({
      success: true,
      key,
      url: `https://r2.xswarm.ai/${bucketName}/${key}`
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// List R2 bucket contents
app.get('/api/r2/list', async (req, res) => {
  const bucket = req.query.bucket || 'omarchy-defender-assets';

  if (!env.CLOUDFLARE_ACCOUNT_ID || !env.CLOUDFLARE_API_TOKEN) {
    return res.status(500).json({ error: 'Cloudflare credentials not configured' });
  }

  try {
    const listUrl = `https://api.cloudflare.com/client/v4/accounts/${env.CLOUDFLARE_ACCOUNT_ID}/r2/buckets/${bucket}/objects`;

    const response = await fetch(listUrl, {
      headers: {
        'Authorization': `Bearer ${env.CLOUDFLARE_API_TOKEN}`
      }
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      return res.status(response.status).json({ error: error.errors?.[0]?.message || 'Failed to list R2 bucket' });
    }

    const data = await response.json();
    res.json(data);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ============================================================
// VIDEO EXPORT ENDPOINTS
// ============================================================

// Serve demo files
const DEMOS_DIR = resolve(PROJECT_ROOT, 'demos');
app.use('/demos', express.static(DEMOS_DIR));

// List available demos
app.get('/api/demos', (req, res) => {
  const demos = [];

  const scanDir = (dir, prefix = '') => {
    if (!existsSync(dir)) return;
    const entries = readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      if (entry.isDirectory()) {
        scanDir(join(dir, entry.name), `${prefix}${entry.name}/`);
      } else if (entry.name.endsWith('.json')) {
        try {
          const content = readFileSync(join(dir, entry.name), 'utf-8');
          const data = JSON.parse(content);
          demos.push({
            path: `${prefix}${entry.name}`,
            name: data.name || entry.name.replace('.json', ''),
            description: data.description || '',
            duration: data.duration || 60000,
            stage: data.stage || 1
          });
        } catch (e) {
          // Skip invalid JSON files
        }
      }
    }
  };

  scanDir(DEMOS_DIR);
  res.json({ demos });
});

// Export video from demo
app.post('/api/export-video', async (req, res) => {
  const { demoPath, format } = req.body;

  if (!demoPath) {
    return res.status(400).json({ error: 'demoPath is required' });
  }

  try {
    const exporter = new VideoExporter({
      serverUrl: `http://localhost:${PORT}`,
      demoPath,
      format: format || 'full',
      fps: 30,
      onProgress: (progress) => {
        // Broadcast progress to SSE clients
        broadcast({
          type: 'exportProgress',
          ...progress
        });
      }
    });

    const result = await exporter.export();

    res.json({
      success: true,
      file: result.file,
      path: result.path,
      frames: result.frames,
      duration: result.duration,
      downloadUrl: `/api/download-video?file=${encodeURIComponent(result.file)}`
    });
  } catch (e) {
    console.error('Video export error:', e);
    res.status(500).json({ error: e.message });
  }
});

// Download exported video
app.get('/api/download-video', (req, res) => {
  const { file } = req.query;

  if (!file) {
    return res.status(400).json({ error: 'file parameter is required' });
  }

  const videosDir = resolve(__dirname, '../../tmp/videos');
  const videoPath = resolve(videosDir, file);

  // Security: ensure path is within videos directory
  if (!videoPath.startsWith(videosDir)) {
    return res.status(403).json({ error: 'Invalid file path' });
  }

  if (!existsSync(videoPath)) {
    return res.status(404).json({ error: 'Video not found' });
  }

  res.download(videoPath, file);
});

// List exported videos
app.get('/api/videos', (req, res) => {
  const videosDir = resolve(__dirname, '../../tmp/videos');

  if (!existsSync(videosDir)) {
    return res.json({ videos: [] });
  }

  const files = readdirSync(videosDir)
    .filter(f => f.endsWith('.mp4'))
    .map(f => {
      const stat = statSync(join(videosDir, f));
      return {
        file: f,
        size: stat.size,
        created: stat.mtime,
        downloadUrl: `/api/download-video?file=${encodeURIComponent(f)}`
      };
    })
    .sort((a, b) => b.created - a.created);

  res.json({ videos: files });
});

// Get available export formats
app.get('/api/export-formats', (req, res) => {
  res.json({
    formats: VideoExporter.getFormats()
  });
});

// ============================================================
// START SERVER
// ============================================================

app.listen(PORT, () => {
  console.log(`
╔══════════════════════════════════════════════════════════════╗
║           OMARCHY DEFENDER - DEV PREVIEW                    ║
╠══════════════════════════════════════════════════════════════╣
║  Dev Preview:   http://localhost:${PORT}/                       ║
║                                                              ║
║  Tabs:                                                       ║
║    • Game     - Live game preview with hot reload           ║
║    • Images   - Image asset manager                         ║
║    • Audio    - Audio asset manager                         ║
║    • Demos    - Demo script editor                          ║
╠══════════════════════════════════════════════════════════════╣
║  Direct URLs:                                                ║
║    • Game:      http://localhost:${PORT}/app/                   ║
║    • Images:    http://localhost:${PORT}/images.html            ║
║    • Audio:     http://localhost:${PORT}/audio.html             ║
║    • Demos:     http://localhost:${PORT}/demo-editor/           ║
║    • Video:     http://localhost:${PORT}/video-export.html      ║
╠══════════════════════════════════════════════════════════════╣
║  APIs: Gemini Vision, ElevenLabs, OpenAI (gpt-image-1)      ║
║  Hot Reload: Watching src/, assets/ for changes             ║
╚══════════════════════════════════════════════════════════════╝
  `);
});
