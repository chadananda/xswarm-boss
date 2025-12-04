# Omarchy Defender

A keyboard-only defense game designed to teach Hyprland/Omarchy window manager hotkeys through engaging gameplay. Players defend against "Gnome cavalry" riding mice while learning keyboard shortcuts.

## Quick Start

### 1. Configure Environment

```bash
# Copy environment template and fill in your API keys
cp .env.example .env

# Edit .env with your credentials
# Priority order:
# 1. GEMINI_API_KEY (for Asset Manager)
# 2. ELEVENLABS_API_KEY (for voice generation)
# 3. STRIPE_* keys (for donations)
# 4. TURSO_* keys (for database)
# 5. CLOUDFLARE_* keys (for deployment)
```

### 2. Development Server

```bash
cd src/
python3 -m http.server 8000
# Open http://localhost:8000
```

### 3. Asset Manager (Development Tool)

```bash
cd scripts/asset-manager/
node server.js
# Opens http://localhost:3000
```

## Project Structure

```
omarchy-defender/
├── .env.example          # API key template (commit this)
├── .env                  # Actual keys (gitignored)
├── config.json           # Game configuration
├── src/                  # Source files (flat structure)
│   ├── index.html        # Main HTML
│   ├── splash.css        # Splash styling (inlined in build)
│   ├── game.css          # Game styling
│   ├── splash.js         # Splash screen logic
│   ├── game.js           # Phaser game logic
│   └── sw.js             # Service worker
├── api/                  # Serverless API routes
├── db/                   # Database schemas
├── assets/               # Audio/images (gitignored, stored on R2)
├── scripts/              # Build tools & utilities
├── demos/                # Demo script files
└── build/                # Production output (gitignored)
```

## Game Stages

### Stage 1: Terminal Warfare
- 20 challenges teaching window manipulation
- Hotkeys: Super+Enter, Super+Q, Super+H/J/K/L, Super+Shift+H/J/K/L

### Stage 2: Sector Command
- 25 challenges teaching workspace navigation
- Hotkeys: Super+1-9, Super+Shift+1-9, Super+Tab

### Stage 3: Full Arsenal
- 30 challenges teaching all 20 Omarchy application shortcuts
- Complete keyboard-only workflow mastery

## Development Utilities

### Asset Manager
- Browse and validate image assets
- AI-powered review with Gemini vision
- Upload/replace functionality

### Audio Manager
- Browse 200+ voice lines
- One-click ElevenLabs regeneration
- A/B comparison between versions

### Demo Editor
- Create automated gameplay scripts
- Record actions with timestamps
- Export JSON for promotional videos

## Scripts

```bash
# Development
npm run dev              # Start local server

# Asset Management
npm run asset-manager    # Launch asset browser
npm run generate-audio   # Batch generate voice lines
npm run scrape-screens   # Scrape Omarchy screenshots

# Build & Deploy
npm run build            # Build for production
npm run upload-assets    # Upload to R2
npm run deploy           # Deploy to Cloudflare Pages

# Demo System
npm run demo <script>    # Play demo script
npm run demo --record    # Record new demo
```

## Technology Stack

- **Game Engine:** Phaser.js 3.90.0
- **Styling:** Pure CSS with CRT terminal aesthetic
- **Audio:** ElevenLabs for voice generation
- **AI:** Google Gemini for asset validation and moderation
- **Database:** Turso (libSQL)
- **Payments:** Stripe
- **Hosting:** Cloudflare Pages + R2

## License

Copyright (c) 2024 xSwarm.ai - All rights reserved
