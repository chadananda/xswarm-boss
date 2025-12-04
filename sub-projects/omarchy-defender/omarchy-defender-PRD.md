# Omarchy Defender - Product Requirements Document (PRD)

**Version:** 1.0.0  
**Author:** Chad Jones (chadananda@gmail.com)  
**Date:** December 4, 2024  
**Status:** Ready for Implementation  

---

## Executive Summary

Omarchy Defender is a keyboard-only defense game designed to teach Hyprland/Omarchy window manager hotkeys through engaging gameplay. Players defend against "Gnome cavalry" riding mice while learning keyboard shortcuts. The game must load instantly and perform flawlessly offline after initial load.

**Target Platform:** Desktop browsers only (Linux, Windows, Mac). This is a window manager training game requiring a full keyboard with function keys. Mobile and tablet devices are not supported - users on these devices see a notification explaining this is a desktop-only experience.

**Key Implementation Approach:**

This is a simple one-off game build. Keep everything minimal with no complex abstractions or build tools. All code lives in a flat `src/` folder with no subfolders (maximum 5-6 files). Build output goes to gitignored `build/` folder. Use static HTML that hydrates with animations, then loads game assets in the background.

**Configuration Architecture:**

Separate secrets from configuration using two files in project root:
- **.env file**: API keys and credentials (Chad fills in from .env.example template)
- **config.json**: All non-secret settings with researched defaults (senior developer creates, Chad can modify)

No internationalization needed - English only application.

**CSS Loading Strategy:**

Two CSS files for optimal performance:
- **splash.css**: Inlined into HTML during build for instant splash screen render (~2-3KB)
- **game.css**: Loaded passively into cache after render while user reads backstory (~5KB)

**SEO-First Asset Strategy:**

Every image asset must use SEO-friendly descriptive filenames with "xswarm" branding prefix (e.g., "xswarm-gnome-riding-mouse-sprite-64x64.png") with proper alt text. This improves search rankings, promotes xSwarm brand, and ensures accessibility.

**Distinctive Visual Style:**

The game features an authentic retro CRT terminal aesthetic:
- **Command center text rendered with horizontal scanlines** through each character (like old green-screen monitors)
- **Glowing green grid** that dynamically changes based on challenge state
- Phosphor glow effects on all text and borders
- Pure black background with bright green terminal colors
- Authentic vintage computer monitor feel throughout

**Critical Feature - The Mouse Trap:**

The first interaction sets the tone: A prominent "Play Now" button appears on the splash screen, but clicking it triggers a warning message: "WE TOLD YOU NOT TO USE THE TRAITOROUS MOUSE!" with instructions to press Super+Enter instead. This serves as both humor and immediate tutorial that the game is keyboard-only. Only the Super+Enter keyboard shortcut actually starts the game.

**Technical Requirements:**
- Static HTML loads instantly (<500ms)
- Splash CSS inlined for immediate styling
- Game CSS and JS load passively into cache during 30-second backstory
- Animations hydrate after DOM ready
- Cache-first offline functionality via service worker
- Zero mouse interaction during gameplay (penalty system)
- Retro CRT terminal aesthetic with scanlines and phosphor glow throughout
- Voice-acted commander giving escalating orders
- Phaser.js 3.90.0 "Tsugumi" for game engine
- All images with SEO-optimized filenames including xSwarm branding

---

## Technical Architecture

### Code Standards

**CRITICAL: Modern ES6 JavaScript Only**

All code must be written in modern ES6+ JavaScript:
- **NO TypeScript** - Pure JavaScript only
- **NO ES5** - Use modern ES6+ features exclusively
- **Modern syntax:** Arrow functions, destructuring, template literals, spread operator, async/await
- **Terse and efficient:** Write code in the most compact, readable form possible
- **Modules:** Use ES6 import/export syntax
- **Classes:** Use ES6 class syntax where appropriate
- **Const/let:** Never use `var`
- **Modern APIs:** Fetch, Promise, async/await preferred over callbacks

**Example of preferred style:**
```javascript
const spawnTerminal = async (cell) => {
  const terminal = await createWindow('terminal', cell);
  terminals.set(cell, terminal);
  return terminal;
};
```

**NOT this:**
```javascript
function spawnTerminal(cell, callback) {
  var self = this;
  createWindow('terminal', cell, function(terminal) {
    self.terminals[cell] = terminal;
    callback(terminal);
  });
}
```

### Mono-Repo Containment

**CRITICAL: All Files Within Project Folder**

This game is developed within a mono-repo structure. **ALL files related to Omarchy Defender must remain within the project folder**: `~/Dropbox/Public/JS/Projects/xswarm-boss/omarchy-defender/`

**Rules:**
- NO files in parent directories
- NO files in sibling project folders  
- NO shared dependencies outside project folder
- ALL assets, scripts, code, and configuration within project structure
- Self-contained deployment from project folder only

This ensures clean separation in the mono-repo and prevents dependencies between projects.

### Technology Stack

**Core Framework:**
- **Phaser.js 3.90.0 "Tsugumi"** - Latest version of the game engine for rendering and game loop management
- **Service Worker API** - Implement cache-first strategy for offline functionality
- **Web Audio API** - Handle all audio playback including voice lines and sound effects
- **Canvas API** - Graphics rendering via Phaser

**Development Tools:**
- **Build System:** Minimal bash scripts for development server and production deployment
- **Minification:** html-minifier for HTML compression, standard CSS/JS minifiers
- **CSS Strategy:** Two CSS files - splash.css (inlined during build) and game.css (loaded passively)
- **Image Optimization:** Convert all images to WebP format with PNG fallbacks for browser compatibility
- **Audio Format:** MP3 at 128kbps mono for all voice and sound files
- **Asset Manager:** Interactive development utility with Gemini and ElevenLabs integration for reviewing and regenerating all assets
- **Screenshot Scraper:** Automated tool to collect application screenshots from Omarchy documentation

**Infrastructure:**
- **Hosting:** Cloudflare Pages for static site hosting at xswarm.ai/omarchy-defender/
- **Asset Storage:** Cloudflare R2 bucket for all audio and image assets
- **CDN:** Use jsDelivr for Phaser.js 3.90.0 and QRCode.js libraries
- **Database:** Turso (libSQL) for donations, notes, and email list - serverless SQLite with HTTP API
- **Authentication:** Supabase for user authentication and leaderboard (Phase 2 - optional)
- **Payments:** Stripe for donation processing
- **Voice Generation:** ElevenLabs API for generating commander voice lines
- **Development AI:** Google Gemini 2.0 Flash for asset review and validation (local development only, not deployed)

### Project Structure

**Implementation Philosophy:**

This is a simple one-off game - not a complex web application. Keep the file structure flat and straightforward. All code lives in `src/` folder with no subfolders. Configuration files live in project root. Build output goes to gitignored `build/` folder.

```
~/Dropbox/Public/JS/Projects/xswarm-boss/omarchy-defender/
├── .env                          # API keys/secrets (not committed) - Chad creates from template
├── .env.example                  # Template with empty keys - Senior dev creates
├── config.json                   # Non-secret config - Senior dev creates with defaults
├── .gitignore                    # Git ignore file
├── manifest.json                 # PWA manifest
├── robots.txt                    # SEO
├── sitemap.xml                   # SEO
├── README.md                     # Documentation
│
├── src/                          # All source code (flat, no subfolders)
│   ├── index.html                # Main entry point (static HTML)
│   ├── splash.css                # Splash screen CSS (~2-3KB, gets inlined in build)
│   ├── game.css                  # Game CSS (~5KB, loaded into cache after render)
│   ├── splash.js                 # Splash screen animation logic (~5KB)
│   ├── game.js                   # All Phaser game logic (~100KB)
│   └── sw.js                     # Service worker (cache management)
│
├── api/                          # Serverless API routes (for donations)
│   ├── donate.js                 # Create Stripe Checkout session
│   ├── webhook.js                # Handle Stripe webhook events
│   ├── notes.js                  # Fetch approved notes for display
│   └── unsubscribe.js            # Handle email unsubscribe
│
├── db/                           # Database setup
│   ├── schema.sql                # Turso/libSQL table schemas
│   └── seed.sql                  # Optional seed data
│
├── assets/                       # All assets (not committed to git)
│   ├── audio/                    # Voice lines, SFX, music (descriptive names)
│   └── images/                   # All with SEO-friendly names and alt text
│       ├── splash/
│       ├── game/
│       │   ├── sprites/
│       │   ├── ui/
│       │   └── effects/
│       ├── social/
│       └── icons/
│
├── scripts/                      # Build and deployment scripts
│   ├── dev.sh                    # Start local server (serves from src/)
│   ├── build.sh                  # Build for production (outputs to build/)
│   ├── generate-audio.js         # Batch ElevenLabs audio generation
│   ├── moderate-notes.js         # AI moderation for donation notes
│   ├── deploy.sh                 # Deploy to Cloudflare (from build/)
│   ├── upload-assets.sh          # Upload to R2
│   ├── scrape-screenshots.js     # Scrape Omarchy app screenshots from docs
│   ├── asset-manager/            # Development utility (not deployed)
│   │   ├── index.html            # Main navigation and image assets
│   │   ├── audio.html            # Audio asset browser with playback
│   │   ├── server.js             # Express server with Gemini + ElevenLabs
│   │   └── styles.css            # Styling for asset manager
│   └── demo-editor/              # Demo script editor (not deployed)
│       ├── index.html            # Visual timeline editor
│       ├── editor.js             # Recording and editing logic
│       └── styles.css            # Styling for demo editor
│
├── demos/                        # Demo script files (for promotional videos)
│   ├── promotional/
│   │   ├── perfect-run.json
│   │   ├── rookie-mistakes.json
│   │   ├── mouse-addict.json
│   │   └── speedrun.json
│   ├── testing/
│   │   ├── stage1-all-hotkeys.json
│   │   ├── stage2-workspace-switching.json
│   │   ├── stage3-app-launching.json
│   │   └── mouse-penalties-all-levels.json
│   └── templates/
│       ├── basic-template.json
│       └── stage1-template.json
│
└── build/                        # Production build output (gitignored)
    ├── index.html                # Minified HTML with inlined splash.css
    ├── game.css                  # Minified game CSS
    ├── splash.js                 # Minified splash JS
    ├── game.js                   # Minified game JS
    ├── sw.js                     # Service worker
    ├── manifest.json             # Copied from root
    ├── robots.txt                # Copied from root
    └── sitemap.xml               # Copied from root
```

**File Organization Principles:**
- All code files live in `src/` folder - no subfolders within src/
- Config files (.env, config.json, manifest.json) in project root
- Maximum 4-5 source files: index.html, splash.css, game.css, splash.js, game.js, sw.js
- Build output goes to `build/` folder (gitignored)
- Development serves from `src/`, production deploys from `build/`
- No complex build pipeline - just minification and CSS inlining
- Assets organized only by type (audio vs images) with descriptive filenames
- **All image files must use SEO-friendly descriptive names** (see SEO requirements section)
- No internationalization (i18n) - English only, no translation files needed

---

## Environment Configuration

### Configuration Strategy

Separate secrets from non-secret configuration:
- **.env file** - Contains API keys and sensitive credentials (never commit, Chad creates this)
- **config.json file** - Contains non-secret configuration like bucket names, URLs, voice selections (committed to git, senior developer creates with good defaults)

### .env.example File Creation

**Action Required from Senior Developer:**

Create a .env.example file in the project root that lists all required API keys with empty values and helpful comments. This file should be committed to git as a template.

**Format Example:**
```
# Cloudflare Configuration
# Get these from: https://dash.cloudflare.com/ > Profile > API Tokens
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_API_TOKEN=

# ElevenLabs Voice Generation
# Get from: https://elevenlabs.io/app/settings > API Keys
ELEVENLABS_API_KEY=

# Gemini AI (for asset management and image interaction)
# Get from: https://aistudio.google.com/app/apikey
# Used by development utility for reviewing and modifying assets
GEMINI_API_KEY=

# Stripe Payments (for donations)
# Get from: https://dashboard.stripe.com/apikeys
STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Turso Database (for donations, notes, email list)
# Get from: https://turso.tech/app
# Create database, get URL and auth token
TURSO_DATABASE_URL=
TURSO_AUTH_TOKEN=

# Supabase (Phase 2 ONLY - Authentication & Leaderboard)
# Get from: https://app.supabase.com/project/_/settings/api
# NOT REQUIRED for Phase 1
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
```

**Include detailed comments for each key:**
- What service it's for
- Where to obtain it (exact URL if possible)
- What permissions/scopes are needed
- Whether it's required immediately or for Phase 2

**Chad's Action:** Copy .env.example to .env and fill in the actual credentials.

### config.json File (Non-Secrets)

**Action Required from Senior Developer:**

Create a config.json file in the project root containing all non-sensitive configuration with well-researched defaults. This file gets committed to git.

**Required Configuration:**

**Cloudflare Settings:**
```json
{
  "cloudflare": {
    "pagesProject": "omarchy-defender",
    "r2Bucket": "omarchy-defender-assets",
    "r2PublicUrl": "https://r2.xswarm.ai/omarchy-defender-assets"
  }
}
```

**ElevenLabs Voice Configuration:**

Research and select the best voice for the military commander character. Test several "professional male military/authoritative" voices from ElevenLabs library and provide the top recommendation with 1-2 alternatives.

```json
{
  "elevenLabs": {
    "model": "eleven_multilingual_v2",
    "voiceId": "PRIMARY_VOICE_ID",
    "alternateVoices": {
      "option2": "BACKUP_VOICE_ID_1",
      "option3": "BACKUP_VOICE_ID_2"
    },
    "settings": {
      "stability": 0.5,
      "similarityBoost": 0.75,
      "style": 0.3,
      "useSpeakerBoost": true
    }
  }
}
```

Include voice descriptions in comments so Chad can test and choose:
- Primary: "Deep authoritative military commander, clear diction"
- Option 2: "Slightly gruff drill sergeant style"
- Option 3: "Professional radio operator tone"

**Asset Paths:**
```json
{
  "assets": {
    "development": "./assets/",
    "production": "https://r2.xswarm.ai/omarchy-defender-assets/"
  }
}
```

**Game Configuration:**
```json
{
  "game": {
    "stage1ChallengeCount": 20,
    "hintDelays": {
      "patient": 2,
      "frustrated": 4,
      "angry": 6
    },
    "mousePenalty": {
      "touchesBeforeGameOver": 4,
      "purityPenaltyPercent": 10
    },
    "combos": {
      "thresholds": [5, 10, 20, 30],
      "multipliers": [1.2, 1.5, 2.0, 3.0]
    }
  }
}
```

**Analytics & Features:**
```json
{
  "analytics": {
    "cloudflareWebAnalytics": true,
    "trackingToken": ""
  },
  "features": {
    "stage2Enabled": false,
    "stage3Enabled": false,
    "leaderboardEnabled": false
  }
}
```

**Development Tools (Not in production config):**

Note: The Gemini API key for asset management is stored in .env (not config.json) since it's only used during development. The asset manager utility is not deployed to production - it's a local development tool only.

**Important Notes:**
- Senior developer should research and provide best default values
- Chad can modify config.json without touching code
- No internationalization (i18n) needed - this is English-only
- No translation files or locale switching required
- Gemini API used only in local development utilities

---

## Game Design & Stages

### Game Concept

**Core Premise:** Players defend "Sector 7-Tango" from invading Gnome forces riding traitorous computer mice. The game is entirely keyboard-driven - touching the mouse helps the enemy and triggers penalties. A military commander issues voice commands with escalating urgency as time passes.

**Learning Philosophy:**
The game uses three progressive stages to build complete Omarchy/Hyprland mastery:
1. **Stage 1:** Master window manipulation within a single workspace
2. **Stage 2:** Master workspace navigation and moving windows between workspaces  
3. **Stage 3:** Memorize all Omarchy application launch shortcuts

Each stage builds on the previous one, creating muscle memory through repetition and challenge escalation.

### Stage 1: Terminal Warfare

**Focus:** Window Manipulation on a Single Workspace

**Objective:** Build fundamental muscle memory for manipulating windows within a single tiling workspace using vim-style navigation keys.

**Visual Layout:**
- 3x3 glowing green grid representing 9 window positions
- Each cell numbered 1-9
- Focus indicator shows current position
- Terminal windows spawn and move between cells

**Hotkeys Taught:**
- Super+Return: Spawn terminal window
- Super+Q: Close focused window
- Super+H/J/K/L: Navigate focus (vim-style: left/down/up/right)
- Super+Shift+H/J/K/L: Move window in direction
- Super+F: Toggle fullscreen
- Super+T: Toggle float/tile mode

**Challenge Structure:**
20 progressive challenges teaching window management:
1. Challenges 1-5: Basic spawning and closing (spawn terminal, close it)
2. Challenges 6-10: Focus navigation (navigate to specific cell, spawn terminal there)
3. Challenges 11-15: Window movement (move terminal from position X to position Y)
4. Challenges 16-20: Combined skills (rapid repositioning, multi-window management)

**Gnome Mechanics:**
- Gnomes approach target cells slowly (3 second approach time)
- Player must deploy terminal defense at target cell before gnome arrives
- Commander voice gives orders: "Gnome cavalry at position 4! Deploy terminal!"
- If player is too slow, hints appear, then urgent voice, then angry barking
- Success: Gnome defeated, combo increases
- Failure: Breach occurs, combo resets

**Completion:** Clear all 20 challenges to unlock Stage 2

### Stage 2: Sector Command

**Focus:** Workspace Navigation & Multi-Desktop Management

**Objective:** Develop spatial awareness of the 9-workspace grid and build instant workspace-switching reflexes.

**Visual Layout:**
- 9 workspaces arranged in 3x3 grid (like Stage 1's cells, but full workspaces)
- Mini-map showing all 9 workspaces with indicators
- Big glowing workspace number appears during transitions
- Can see gnome attacks on other workspaces

**Hotkeys Taught:**
- Super+1 through Super+9: Switch to workspace 1-9
- Super+Shift+1 through Super+9: Move window to workspace 1-9
- Super+Tab: Next workspace
- Super+Shift+Tab: Previous workspace
- Super+Ctrl+Tab: Return to previous workspace
- Super+, and Super+.: Previous/next monitor (if multi-monitor)

**Challenge Structure:**
25 progressive challenges teaching workspace mastery:
1. Challenges 1-8: Workspace navigation (jump to specific workspaces)
2. Challenges 9-16: Moving windows between workspaces
3. Challenges 17-21: Multi-workspace defense (gnomes attacking multiple workspaces)
4. Challenges 22-25: Speed trials (rapid workspace switching under pressure)

**Gnome Mechanics:**
- Gnomes can attack any workspace simultaneously
- Commander: "Breach at Sector 3! Switch immediately!"
- Must switch to correct workspace and deploy defenses
- Some challenges require moving existing terminals between workspaces
- Cross-workspace coordination required (deploy in WS 5, move to WS 2)

**Complexity Increase:**
- Multiple simultaneous attacks across workspaces
- Time windows get shorter
- More complex multi-step requirements
- Commander gives less time before escalating urgency

**Completion:** Clear all 25 challenges to unlock Stage 3

### Stage 3: Full Arsenal

**Focus:** Omarchy Application Launch Memorization

**Objective:** Achieve instant recall of all 17+ Omarchy application shortcuts through intensive drill and real-world usage scenarios.

**Visual Layout:**
- Full 9-workspace grid remains active
- Application icons appear during challenges
- Can deploy any Omarchy application, not just terminals
- More complex UI showing app requirements

**All Omarchy Applications:**

1. **Super+Return** - Terminal (Alacritty) - already mastered
2. **Super+Shift+B** - Browser (Firefox/Chrome)
3. **Super+Shift+Alt+B** - Browser (Private/Incognito mode)
4. **Super+Shift+F** - File Manager (Nautilus)
5. **Super+Shift+E** - Email (HEY)
6. **Super+Shift+C** - Calendar (HEY Calendar)
7. **Super+Shift+A** - AI Chat (ChatGPT web app)
8. **Super+Shift+X** - Social Media (X/Twitter web app)
9. **Super+Shift+M** - Music (Spotify)
10. **Super+Shift+O** - Notes (Obsidian)
11. **Super+Shift+N** - Code Editor (Neovim)
12. **Super+Shift+T** - Activity Monitor (btop)
13. **Super+Shift+D** - Docker Manager (LazyDocker)
14. **Super+Shift+/** - Password Manager (1Password)
15. **Super+Shift+G** - Messenger (Signal)
16. **Super+Shift+Ctrl+G** - Messenger (WhatsApp web)
17. **Super+Shift+Alt+G** - Messenger (Google Messages)
18. **Super+Space** - Application Launcher (Walker)
19. **Super+Alt+Space** - Omarchy Menu
20. **Ctrl+Super+S** - Share Menu (LocalSend)

**Challenge Structure:**
30 progressive challenges covering all applications:
1. Challenges 1-10: Individual app launches (memorization)
2. Challenges 11-20: Workspace-specific deployments ("Deploy ChatGPT in WS 5")
3. Challenges 21-25: Workflow scenarios ("Setup dev environment: Terminal WS 1, Browser WS 2, Neovim WS 3")
4. Challenges 26-30: Speed trials and complex multi-app scenarios

**Gnome Mechanics:**
- Commander demands specific applications: "Deploy ChatGPT at Sector 7!"
- Wrong application = failure: "That's EMAIL, not AI! We needed ChatGPT!"
- Multi-step challenges: "Setup communication hub: Signal in WS 4, Email in WS 5, X in WS 6"
- Time pressure intense - must recall shortcuts instantly
- Gnomes breach if wrong app deployed or too slow

**Real-World Scenarios:**
- "Morning startup": Browser WS 1, Email WS 2, Calendar WS 3, Terminal WS 4
- "Development mode": Neovim WS 1, Terminal WS 2, Browser WS 3, Docker WS 4
- "Communication blast": Signal, WhatsApp, Google Messages across workspaces
- "Content creation": Obsidian WS 1, Browser research WS 2, ChatGPT WS 3

**Completion:** Master all 30 challenges, achieve mastery certification

### Difficulty Progression

**Stage 1 Difficulty:**
- Patient commander (2-4 second hints)
- Simple single-action challenges
- Generous time windows
- Focus on accuracy over speed

**Stage 2 Difficulty:**
- Less patience (1-3 second hints)
- Multi-step challenges introduced
- Tighter time windows
- Requires spatial awareness

**Stage 3 Difficulty:**
- Minimal patience (1-2 second hints)
- Complex multi-app scenarios
- Very tight time windows
- Instant recall required
- Commander expects mastery-level performance

### Mouse Contamination System

**Philosophy:** The mouse is the enemy - touching it should be unpleasant but not game-ending. The goal is negative reinforcement through increasingly harsh penalties that train users to avoid the mouse entirely.

**Erratic Cursor Behavior:**

When mouse is moved anywhere over the game canvas:
- **Cursor jumps erratically:** Random displacement of 50-200px in random direction every 100-200ms
- **Unpredictable movement:** Cursor position becomes unusable for clicking or precision
- **Visual indication:** Cursor becomes a "contaminated" red X or hazard symbol
- **Purpose:** Makes mouse physically useless, reinforcing keyboard-only approach
- **Technical:** Override cursor position with JavaScript, apply random offsets to actual position

**Progressive Penalty System:**

Mouse contamination applies throughout all stages with escalating severity:

**First Touch:**
- **Visual:** Intense red flash covering entire screen (200ms)
- **Audio:** Loud klaxon alarm sound
- **Voice:** "POINTING DEVICE DETECTED! Remove your hand from that traitorous peripheral immediately!"
- **Haptic:** Brief browser vibration if supported
- **Purity:** -10% keyboard purity score
- **Combo:** Reset to zero
- **Warning overlay:** Brief text "⚠️ MOUSE = TRAITOR ⚠️" (1 second)

**Second Touch:**
- **Visual:** Double red flash with screen shake (400ms total)
- **Audio:** Louder alarm with bass-heavy warning buzz
- **Voice:** "AGAIN with the mouse?! Your fingers are CONTAMINATED! Back to the home row, soldier!"
- **Purity:** -15% additional (total -25%)
- **Combo:** Reset to zero
- **Warning overlay:** "⚠️ YOU'RE HELPING THE GNOMES ⚠️" (2 seconds)
- **Penalty:** Next 3 successful actions give half points

**Third Touch:**
- **Visual:** Triple red flash with intense screen shake, vignette darkens edges (600ms)
- **Audio:** Continuous alarm with harsh buzzing, distorted static
- **Voice:** "That MOUSE is a GNOME CAVALRY MOUNT! You're literally riding with the enemy! KEYBOARD ONLY!"
- **Purity:** -20% additional (total -45%)
- **Combo:** Reset to zero
- **Warning overlay:** "⚠️ GNOME SYMPATHIZER DETECTED ⚠️" (3 seconds)
- **Penalty:** Next 5 successful actions give half points, commander voice switches to angry mode

**Fourth+ Touches:**
- **Visual:** Red screen flash with electrical arc effects, severe screen shake
- **Audio:** Deafening alarm klaxon with harsh buzzer, interference noise
- **Voice:** "YOU ABSOLUTE GNOME COLLABORATOR! That pointing device is spewing desktop environment bloat into Sector 7-Tango! DESIST!"
- **Purity:** -15% each additional touch (can drop to 0%)
- **Combo:** Reset to zero
- **Warning overlay:** "⚠️ COMPLETE KEYBOARD PURITY FAILURE ⚠️" (3 seconds, pulsing)
- **Penalty:** All points reduced by 50% until purity restored above 50%
- **Commander:** Remains in angry/disgusted mode for 30+ seconds
- **Achievement:** "Habitual Mouse User" (negative achievement, displayed with shame)

**No Game Over:**

Mouse touches DO NOT end the game. Instead:
- Severe penalties to score and progression
- Increasingly harsh audio/visual warnings
- Sustained impact on gameplay experience
- Shame-based negative reinforcement
- Commander's disappointment palpable in voice
- Recovery possible by completing challenges with keyboard only

**Purity Recovery:**

Keyboard purity can be restored:
- +2% per successful keyboard action
- +5% for perfect challenge completion (no mouse touches)
- +10% for 10-challenge streak with zero mouse touches
- Visual: Green glow replaces red contamination
- Voice: "Your fingers are FINALLY back where they belong!"

**Visual Contamination Effects:**

**When Purity < 70%:**
- Slight red tint to entire screen
- Keyboard purity meter shows caution yellow

**When Purity < 50%:**
- Moderate red tint, edges vignette
- Warning indicator pulsing
- Keyboard purity meter shows danger red

**When Purity < 25%:**
- Heavy red contamination overlay
- Screen edges darkened significantly
- Warning: "CRITICAL PERIPHERAL CONTAMINATION"
- Commander exclusively uses angry/disgusted voice lines

**When Purity = 0%:**
- Deep red overlay, maximum visual contamination
- Everything tinted with failure
- Warning: "COMPLETE MOUSE DEPENDENCE DETECTED"
- Commander: "I have no words. This is a keyboard training program."
- Can still continue playing, but experience is miserable until purity recovered

---

## Audio Generation Specifications

### Audio Strategy

**Variant Philosophy:**

Each voice line should have multiple variants to avoid repetitive audio during gameplay. The frequency of a phrase determines how many variants it needs:

- **Very common phrases** (heard 20+ times per playthrough): 5-8 variants
- **Common phrases** (heard 10-20 times): 3-5 variants
- **Occasional phrases** (heard 5-10 times): 2-3 variants
- **Rare phrases** (heard 1-5 times): 1-2 variants

Random selection from available variants keeps audio fresh and engaging.

**Military-Themed Insults:**

Mouse contamination insults should be especially varied and creative with military vocabulary. Provide 8-10 variants for each mouse touch level to maximize variety and comedic impact.

Examples:
- "That pointing device is a GNOME CAVALRY MOUNT!"
- "Fraternizing with peripheral devices is treason!"
- "Your mouse hand is court-martial material!"
- "That trackpad is enemy ordnance!"
- "Every click is an act of treason!"

### Audio Organization

**Single Manifest Structure:**

Use one `audio-manifest.json` file to organize all 300+ audio files (including variants). Keep audio files in flat structure with manifest providing categorization and metadata.

**SEO-Friendly File Naming:**

All audio files use descriptive names with xSwarm branding:

Format: `xswarm-category-context-variant.mp3`

Examples:
- `xswarm-command-gnome-position-4-v1.mp3`
- `xswarm-command-gnome-position-4-v2.mp3`
- `xswarm-command-gnome-position-4-v3.mp3`
- `xswarm-hint-super-enter-terminal-v1.mp3`
- `xswarm-urgent-deploy-faster-v1.mp3`
- `xswarm-angry-too-slow-v1.mp3`
- `xswarm-mouse-pointing-device-detected-v1.mp3`
- `xswarm-mouse-gnome-collaborator-v1.mp3`
- `xswarm-success-excellent-work-v1.mp3`
- `xswarm-sfx-window-spawn.mp3`
- `xswarm-music-splash-theme.mp3`

Benefits:
- SEO-friendly for search engines
- Brand presence in all filenames  
- Clear categorization from filename
- Easy to identify context and variant
- Potential promotional/discovery vector

**Folder Structure:**

Minimal flat structure:

```
assets/audio/
├── audio-manifest.json           # Master manifest
├── xswarm-command-gnome-position-4-v1.mp3
├── xswarm-command-gnome-position-4-v2.mp3
├── xswarm-command-gnome-position-4-v3.mp3
├── xswarm-command-deploy-terminal-v1.mp3
├── xswarm-hint-super-enter-v1.mp3
├── [... 290+ more audio files ...]
├── xswarm-sfx-window-spawn.mp3
└── xswarm-music-splash-theme.mp3
```

All organization in manifest, not folders.

### Audio Manifest Schema

**Purpose of IDs for Random Variant Selection:**

Every phrase/command type must have a unique ID (e.g., `cmd_gnome_position`, `mouse_first_touch`). The game code uses these IDs to randomly select from available variants:

```javascript
// Game requests a voice line by ID
const playVoiceLine = (phraseId) => {
  const phrase = audioManifest.findPhrase(phraseId);
  const randomVariant = phrase.variants[Math.floor(Math.random() * phrase.variants.length)];
  playAudio(randomVariant.filename);
};

// Usage example
playVoiceLine('cmd_gnome_position'); // Randomly selects from v1, v2, v3, etc.
playVoiceLine('mouse_first_touch');  // Randomly selects mouse warning variant
```

This ensures:
- No exact repetition of phrases back-to-back
- Natural variety in commander voice
- Easy to add more variants without changing game code
- Game code references phrases by semantic meaning (ID), not specific files

**audio-manifest.json example** (abbreviated):

```json
{
  "version": "1.0.0",
  "total_files": 295,
  "categories": {
    "commands": {
      "description": "Calm authoritative orders",
      "emotional_tags": ["calm", "authoritative", "professional"],
      "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.3,
        "speed": 1.0
      },
      "phrases": [
        {
          "id": "cmd_gnome_position",
          "context": "Gnome approaching cell",
          "usage_frequency": "very_common",
          "variants": [
            {
              "filename": "xswarm-command-gnome-position-4-v1.mp3",
              "script": "Gnome cavalry at position 4!",
              "duration": 2.1,
              "status": "approved"
            },
            {
              "filename": "xswarm-command-gnome-position-4-v2.mp3",
              "script": "Enemy forces approaching cell 4!",
              "duration": 2.3,
              "status": "approved"
            }
          ]
        }
      ]
    },
    "mouse": {
      "description": "Mouse contamination warnings",
      "emotional_tags": ["alarmed", "urgent", "horrified"],
      "voice_settings": {
        "stability": 0.45,
        "speed": 1.15,
        "volume_adjust": 15
      },
      "phrases": [
        {
          "id": "mouse_first_touch",
          "usage_frequency": "occasional",
          "variants": [
            {
              "filename": "xswarm-mouse-pointing-device-detected-v1.mp3",
              "script": "POINTING DEVICE DETECTED! Remove your hand!",
              "duration": 3.2
            },
            {
              "filename": "xswarm-mouse-peripheral-contamination-v1.mp3",
              "script": "PERIPHERAL CONTAMINATION! Keyboard only!",
              "duration": 3.5
            }
          ]
        },
        {
          "id": "mouse_continued",
          "context": "Fourth+ touches",
          "usage_frequency": "rare",
          "variants": [
            {
              "filename": "xswarm-mouse-collaborator-v1.mp3",
              "script": "YOU ABSOLUTE GNOME COLLABORATOR!",
              "duration": 4.2
            },
            {
              "filename": "xswarm-mouse-court-martial-v1.mp3",
              "script": "Your mouse hand is COURT-MARTIAL material!",
              "duration": 4.0
            },
            {
              "filename": "xswarm-mouse-trackpad-ordnance-v1.mp3",
              "script": "That trackpad is ENEMY ORDNANCE!",
              "duration": 3.8
            },
            {
              "filename": "xswarm-mouse-pointing-treason-v1.mp3",
              "script": "Every CLICK is an act of treason!",
              "duration": 3.9
            }
          ]
        }
      ]
    }
  }
}
```

### Total Audio Count (With Variants)

- Commands: ~60 files (12 phrases × 5 variants avg)
- Hints: ~30 files (10 phrases × 3 variants avg)
- Urgent: ~25 files (8 phrases × 3 variants avg)
- Angry: ~20 files (7 phrases × 3 variants avg)
- Mouse: ~40 files (10 phrases × 4 variants avg - extra variety!)
- Success: ~40 files (13 phrases × 3 variants avg)
- Failure: ~30 files (10 phrases × 3 variants avg)
- Jokes: ~20 files (10 phrases × 2 variants avg)
- SFX: ~25 files
- Music: ~5 files

**Total: ~295 files**

This provides excellent variety without excessive duplication.

### ElevenLabs Generation Settings

**Voice Settings by Category:**

**Commands:** calm, authoritative, professional
- Stability: 0.5, Similarity: 0.75, Style: 0.3, Speed: 1.0x

**Hints:** calm, helpful, patient
- Stability: 0.5, Similarity: 0.75, Style: 0.25, Speed: 0.95x

**Urgent:** frustrated, impatient, urgent
- Stability: 0.45, Similarity: 0.75, Style: 0.4, Speed: 1.1x, Volume: +10dB

**Angry:** angry, shouting, demanding
- Stability: 0.4, Similarity: 0.75, Style: 0.5, Speed: 1.2x, Volume: +20dB

**Mouse:** alarmed, urgent, horrified
- Stability: 0.45, Similarity: 0.75, Style: 0.45, Speed: 1.15x, Volume: +15dB

**Success:** proud, satisfied, encouraging
- Stability: 0.5, Similarity: 0.75, Style: 0.35, Speed: 1.0x

All audio reviewed and managed via Audio Asset Manager utility (see Development Utilities section).

---

## SEO-Friendly Asset Requirements

### Image Asset Naming Convention

**Critical Requirement:** Every image file must use SEO-friendly descriptive filenames that help search engines understand the content AND promote the xSwarm brand. Never use generic names like "img1.png" or "sprite.png".

**Naming Format:**
Use lowercase with hyphens, include "xswarm" prefix for branding, descriptive keywords, include dimension suffix:
- `xswarm-omarchy-defender-logo-600w.webp`
- `xswarm-defender-rubber-stamp-400w.png`
- `xswarm-gnome-riding-mouse-sprite-64x64.png`
- `xswarm-terminal-window-icon-128x128.webp`
- `xswarm-keyboard-purity-badge-256w.png`
- `xswarm-stage-complete-victory-banner-800w.webp`
- `xswarm-workspace-grid-layout-1024w.png`

**Branding Benefits:**
Including "xswarm" in every filename:
- Improves SEO for xSwarm brand
- Creates brand association in search results
- Makes assets easily identifiable if shared
- Reinforces brand identity across the web
- Helps with image search optimization

**Image Alt Text Requirements:**

Every image must have descriptive alt text in the HTML. The senior developer must include alt attributes on all img tags and provide a manifest of suggested alt text for game sprites.

Examples:
- Logo: "xSwarm Omarchy Defender - Keyboard-Only Window Manager Training Game"
- Stamp: "xSwarm Defender stamp - Join the keyboard resistance"
- Gnome sprite: "xSwarm game: Gnome cavalry riding a traitorous computer mouse"
- Terminal icon: "xSwarm Omarchy Defender terminal window for Hyprland tiling window manager"
- Workspace grid: "xSwarm game: Nine-workspace grid layout in Omarchy"

**Image Metadata:**

For all key images (logo, social sharing, screenshots), include:
- Descriptive filename with xswarm prefix
- Alt text in HTML mentioning xSwarm where appropriate
- Title attribute for additional context
- Width and height attributes for layout stability
- Loading priority (loading="eager" for above-fold, loading="lazy" for below-fold)

**Social Media Optimization:**

Create specific images for social sharing with SEO-friendly names including xSwarm branding:
- `xswarm-omarchy-defender-social-share-1200x630.png` (Open Graph)
- `xswarm-omarchy-defender-twitter-card-800x418.png` (Twitter summary)
- `xswarm-omarchy-defender-screenshot-gameplay-1920x1080.png`
- `xswarm-omarchy-defender-mobile-preview-750x1334.png`

All social images should have xSwarm branding visible in the image content AND in filenames, and be referenced in meta tags with descriptive content attributes.

**Image File Organization:**

```
assets/images/
├── splash/
│   ├── xswarm-omarchy-defender-logo-600w.webp
│   ├── xswarm-omarchy-defender-logo-600w.png
│   ├── xswarm-defender-rubber-stamp-400w.webp
│   └── xswarm-defender-rubber-stamp-400w.png
├── game/
│   ├── sprites/
│   │   ├── xswarm-gnome-cavalry-riding-mouse-64x64.png
│   │   ├── xswarm-terminal-window-icon-128x128.png
│   │   ├── xswarm-browser-window-icon-128x128.png
│   │   └── xswarm-keyboard-warrior-cursor-32x32.png
│   ├── ui/
│   │   ├── xswarm-command-center-panel-background.png
│   │   ├── xswarm-keyboard-purity-meter-256w.png
│   │   ├── xswarm-combo-counter-badge-128w.png
│   │   └── xswarm-workspace-grid-overlay.png
│   ├── effects/
│   │   ├── xswarm-mouse-contamination-warning-flash.png
│   │   ├── xswarm-gnome-defeated-particle-32x32.png
│   │   └── xswarm-workspace-transition-glow.png
│   └── windows/
│       ├── terminal/
│       │   ├── xswarm-terminal-top-left.png
│       │   ├── xswarm-terminal-top.png
│       │   ├── xswarm-terminal-top-right.png
│       │   ├── xswarm-terminal-left.png
│       │   ├── xswarm-terminal-center.png
│       │   ├── xswarm-terminal-right.png
│       │   ├── xswarm-terminal-bottom-left.png
│       │   ├── xswarm-terminal-bottom.png
│       │   └── xswarm-terminal-bottom-right.png
│       ├── browser/
│       │   └── [same 9-slice pattern]
│       ├── email/
│       │   └── [same 9-slice pattern]
│       └── calendar/
│           └── [same 9-slice pattern]
├── social/
│   ├── xswarm-omarchy-defender-og-image-1200x630.png
│   ├── xswarm-omarchy-defender-twitter-card-800x418.png
│   └── xswarm-omarchy-defender-screenshot-stage1-1920x1080.png
└── icons/
    ├── xswarm-omarchy-defender-icon-192x192.png
    ├── xswarm-omarchy-defender-icon-512x512.png
    ├── xswarm-omarchy-defender-favicon-32x32.png
    └── xswarm-omarchy-defender-apple-touch-icon-180x180.png
```

### Application Window Screenshots (9-Slice Requirement)

**Critical Requirement:** The game needs actual screenshots of Omarchy applications to display as window graphics. These must be cut into 9-slice/9-patch format to allow resizing to different window dimensions while maintaining proper borders and corners.

**Applications Required (17 applications for Stage 3):**

1. **Terminal (Alacritty)** - Primary for Stage 1, continues through all stages
2. **Browser (Firefox or Chromium)** - For web browsing
3. **File Manager (Nautilus)** - For file operations
4. **Email (HEY)** - HEY email client web app
5. **Calendar (HEY Calendar)** - HEY calendar web app
6. **ChatGPT** - AI chat interface
7. **X (Twitter)** - Social media web app
8. **Spotify** - Music player
9. **Obsidian** - Note-taking application
10. **Neovim** - Code editor in terminal
11. **btop** - Activity monitor (terminal app)
12. **LazyDocker** - Docker manager (terminal app)
13. **1Password** - Password manager
14. **Signal** - Messenger app
15. **WhatsApp Web** - Messenger web app
16. **Google Messages** - Messenger web app
17. **Walker** - Application launcher (optional visual)

**Note:** Terminal-based applications (Neovim, btop, LazyDocker) can use the same Alacritty terminal window 9-slices with different content screenshots.

**9-Slice Structure:**

Each application window must be divided into 9 pieces:
```
┌─────────┬──────────────┬─────────┐
│ top-    │     top      │  top-   │
│ left    │              │  right  │
├─────────┼──────────────┼─────────┤
│         │              │         │
│  left   │   center     │  right  │
│         │  (repeats)   │         │
├─────────┼──────────────┼─────────┤
│ bottom- │   bottom     │ bottom- │
│ left    │              │  right  │
└─────────┴──────────────┴─────────┘
```

**Slice Details:**
- **Corners (4 pieces):** Fixed size, never scaled
  - top-left, top-right, bottom-left, bottom-right
  - Typically 32x32 or 64x64 pixels each
  - Contain window decorations, borders, shadows

- **Edges (4 pieces):** Scale in one direction only
  - top, bottom: Tile/stretch horizontally
  - left, right: Tile/stretch vertically  
  - Contain window borders and shadows

- **Center:** Scales in both directions
  - Contains the application content area
  - This is the part that tiles/stretches to fill window size

**Screenshot Specifications:**

**Source Images:**
- Take actual screenshots of each Omarchy application
- Resolution: At least 1920x1080 for high quality
- Include window decorations (title bar, borders)
- Capture typical application state (not empty/default)
- Terminal: Show some typical commands/output
- Browser: Show a recognizable web page
- Email: Show inbox view
- Calendar: Show calendar grid

**Cutting Instructions for Senior Developer:**

1. **Identify Corner Sizes:** Measure the window decoration corners (likely 32-64px)
2. **Define Edge Widths:** Measure border/shadow widths on all sides
3. **Cut into 9 pieces** following the diagram above
4. **Name consistently** using the xswarm prefix pattern
5. **Save with transparency** (PNG format) to preserve shadows
6. **Optimize file sizes** while maintaining quality

**Implementation Notes:**

The game engine will reassemble these 9 slices at runtime to create windows of any size:
- Corners stay fixed at corners
- Edges tile/stretch along their axis
- Center tiles/stretches to fill the middle
- This allows one set of images to create windows at any dimension

**SEO-Friendly Naming:**
- xswarm-terminal-top-left.png
- xswarm-terminal-top.png
- xswarm-browser-center.png
- etc.

All slice images should include descriptive alt text when referenced in code, for example: "xSwarm Omarchy terminal window top border"

**Accessibility Requirements:**

Images must meet WCAG 2.1 AA standards:
- All decorative images: `alt=""`
- All content images: Descriptive alt text
- Icons conveying information: Include aria-label or aria-describedby
- Color contrast ratios: Minimum 4.5:1 for normal text, 3:1 for large text

**Performance Optimization:**

- Use WebP format with PNG/JPG fallback
- Provide multiple sizes for responsive images (srcset)
- Compress images: Target <100KB for full-screen images, <20KB for sprites
- Use CSS sprites for small UI elements when beneficial
- Lazy load below-the-fold images

---

## Loading & Caching Strategy

### Phase 1: Static HTML Load (Instant)

**Initial Page Load:**

The index.html file should load as pure static HTML with no JavaScript execution required for initial render. The splash.css content should be inlined directly in the `<head>` of the HTML during the build process (approximately 2-3KB). The page structure should be complete in the HTML with the logo, stamp graphic, and backstory text already present in the DOM.

The Omarchy logo and defender stamp should be embedded as optimized images (WebP with PNG fallback) or inline SVG if under 5KB total. The backstory crawl text should be present in a hidden container in the HTML.

Total initial payload must be under 50KB for HTML including inlined splash CSS and embedded images.

**CSS Strategy:**
- **splash.css**: Inlined in HTML `<head>` during build for instant styling
- **game.css**: Loaded via link tag with low priority after initial render

### Phase 2: Hydrate Animations (After DOM Load)

**Animation Hydration:**

After the DOM loads, a small inline or external script (splash.js, approximately 5KB) hydrates the splash screen with animations. This script should:

1. Fade in the logo (already present in DOM)
2. After 2 seconds, animate the stamp appearing with rotation and scale
3. After 3 seconds, start the Star Wars crawl animation using CSS transforms
4. Display the "Press SUPER+ENTER to defend" prompt
5. Show a "Play Now" button (disabled initially, styled dimly)

The animations should use CSS transforms and transitions where possible, with minimal JavaScript for timing coordination.

### Phase 3: Passive Asset Loading (Background)

**Passive Cache Loading Strategy:**

Immediately after the splash screen renders (but without blocking the render), begin passively loading game assets into the browser cache:

**Priority 1 - Styles and Scripts:**
1. Load game.css into cache (link with rel="preload" or low-priority link tag)
2. Load Phaser.js 3.90.0 from CDN
3. Load game.js containing all Phaser game logic

**Priority 2 - Service Worker:**
4. Register service worker for offline caching

**Priority 3 - Game Assets:**
5. Preload Stage 1 audio files (commander voice lines)
6. Preload Stage 1 images (sprites, UI elements)

Display a small loading indicator in the corner showing "Loading game... X%" that updates as assets complete. While the user reads the 25-30 second backstory crawl, all game assets should fully load into cache.

**Technical Implementation:**
- Use `<link rel="preload" as="style" href="game.css">` to load CSS without blocking
- Or use low-priority `<link rel="stylesheet" href="game.css" media="print" onload="this.media='all'">` technique
- Load game.js with `<script src="game.js" defer></script>` or async
- Service worker caches everything as it loads

### Phase 4: Enable Play Controls

**When Loading Complete:**

Once all critical assets are loaded and game.js is ready:
1. Change loading indicator to "✓ Ready!"
2. Enable and brighten the "Play Now" button
3. Listen for Super+Enter keyboard shortcut
4. Set a global gameReady flag to true

### Phase 5: Mouse Warning (Play Button Click)

**Critical Requirement - Mouse Detection Joke:**

When the user clicks the "Play Now" button (using their mouse), do NOT start the game. Instead:

1. Screen flashes red briefly
2. Display a large centered message: "⚠️ WE TOLD YOU NOT TO USE THE TRAITOROUS MOUSE! ⚠️"
3. Below that: "Press SUPER+ENTER to play (with your keyboard, like a civilized person)"
4. Play a brief alarm sound effect
5. Animate the message shaking or pulsing for emphasis
6. The message should auto-dismiss after 3-4 seconds

This serves as both a joke and an immediate tutorial that the game is keyboard-only. The button is intentionally a trap to reinforce the theme.

### Phase 6: Actual Game Start (Keyboard Only)

**Super+Enter Detection:**

Only when the user presses Super+Enter (or Command+Enter on Mac) should the game actually begin:

1. Fade out the splash screen
2. Show the game canvas
3. Initialize Phaser with all loaded assets (already in cache)
4. Display brief "Entering combat..." message
5. Start Stage 1 scene

The game should start instantly since all assets are already cached.

### Service Worker Caching

**Cache Strategy:**

Implement service worker that caches:
- Static HTML, CSS, JS files (cache-first)
- CDN libraries (cache-first with stale-while-revalidate)
- Audio and image assets (cache-first)
- Configuration files (network-first with cache fallback)

On subsequent visits, everything loads from cache except for a background check for updates.

**Offline Support:**

After initial load, the entire game must work offline. The service worker should cache all required assets during the first visit. Display a subtle "Offline-ready" indicator once caching completes.

---

## Visual Design System

### Theme: "Retro CRT Terminal"

**Core Aesthetic:**
- Old CRT monitor display with authentic terminal feel
- Glowing green phosphor effect
- Horizontal scanlines across all text (particularly the command center)
- Monochrome with accent colors
- Classic DOS/Unix terminal inspiration
- Subtle screen curvature (optional)

**Visual Approach:**

The game should evoke the feeling of working on a vintage terminal monitor from the 1980s. The command center at the bottom must look like an actual terminal with each character rendered with horizontal scanlines stacked to create that authentic CRT phosphor glow effect. The main game grid should glow with bright green borders that pulse and change based on the current challenge state.

### Color Palette

**Primary Colors:**
- Background: Pure black (#000000) - deep CRT black
- Primary text/UI: Terminal green (#00ff00) - bright phosphor green
- Secondary/dimmed text: Darker green (#00aa00) - aged phosphor
- Alert/danger: Red (#ff0000) - warning indicators
- Warning: Amber/orange (#ffaa00) - caution states
- Info/accent: Cyan (#00ffff) - special highlights

**Alternate Color Schemes (User Selectable Option):**

Create variants that users can optionally switch between:
- Amber CRT theme: Orange/amber (#ffaa00) primary with darker orange (#cc8800) secondary - classic amber monitor
- IBM PC Blue theme: Blue background (#0000aa) with white text - DOS blue screen
- Commodore 64 theme: Blue-purple background (#3a3fb7) with light purple text (#a3a6fc) - C64 nostalgia

### Typography

Use monospace font stack with fallbacks: Courier New, Courier, Lucida Console, Monaco, Consolas, and generic monospace as final fallback.

**Text Size Scale:**
- Extra small (12px): Timestamps and metadata
- Small (16px): Body text and UI elements
- Medium (24px): Command text
- Large (32px): Section headers
- Extra large (48px): Titles
- 2XL (72px): Logo and major headings
- 3XL (120px): Big workspace numbers during transitions

**CRT Terminal Effects:**

**Scanline Effect (Critical for Authenticity):**
The command center text at the bottom must render with horizontal scanlines that create the authentic CRT look. Each character should appear as if displayed on an old phosphor screen with visible horizontal scan lines running through the text. This effect should be most prominent on the command center panel where the commander's orders appear.

The scanlines should be subtle enough to maintain readability but prominent enough to create that unmistakable retro monitor feel. Think of how text looked on old green-screen terminals where you could see the individual horizontal lines of phosphor.

**Text Glow Effect:**
All terminal green text should have a soft phosphor glow around it, as if the text is literally glowing on the screen. This creates depth and authenticity. The glow should be multi-layered (inner glow, mid glow, outer glow) to simulate how CRT phosphor would bloom.

**Screen Effects:**
- Subtle flicker animation on certain decorative elements (very subtle, not distracting)
- Optional subtle screen curvature at edges to simulate CRT bulge
- Vignette darkening at screen corners
- Very subtle RGB color separation on edges (chromatic aberration) for authenticity

### Game Grid Visual Design

**Glowing Grid Aesthetic:**

The main game area should be rendered as a glowing green grid that represents the tiling window manager workspace. The grid should:

**Base State:**
- 3x3 grid of cells with bright green borders
- Each cell outlined in glowing green lines
- Empty cells have dim green borders with subtle glow
- Cell numbers appear in dimmer green inside each cell
- Background is pure black between cells

**Challenge State Changes:**

The grid dynamically changes appearance based on the current challenge:

**Normal/Empty Cell:**
- Thin dim green border with subtle glow
- Cell number visible in center (dim green)
- Minimal animation (very subtle pulse)

**Focused Cell:**
- Thick bright green border with strong glow
- Cell number brighter
- Pulsing glow animation on border
- Feels "active" and selected

**Target Cell (Gnome Approaching):**
- Red pulsing border
- Warning indicators
- Increasingly bright/urgent pulse as gnome gets closer
- Cell number may flash or change color

**Occupied Cell (Terminal Present):**
- Border remains bright green
- Window icon appears in center
- Subtle breathing animation on glow
- Indicates successful deployment

**Breach Cell (Player Failed):**
- Flashing red border
- Alarm animation
- Visual indication of failure
- May show gnome invasion graphic

**Grid Transitions:**

When challenges change or workspace switches:
- Smooth fade/pulse transition between states
- Glow intensifies during transition
- Brief flash or surge effect
- Maintains that CRT phosphor glow throughout

### UI Components

**Splash Screen:**

Logo and stamp should display at the top center of the screen with the CRT aesthetic. Below that, the Star Wars-style backstory crawl should scroll from bottom to top with perspective transform and green phosphor glow.

At the bottom of the screen, display:
- "Press SUPER+ENTER to defend" prompt (pulsing/blinking green glow)
- "Play Now" button (centered, styled with terminal aesthetic, initially dimmed/disabled)
- Small loading indicator in the corner showing "Loading game... X%" with scanline effect

**Play Now Button States:**
- Disabled: Dim gray with scanlines, cursor not-allowed
- Ready: Bright green with strong glow effect, cursor pointer
- Clicked: Flash red, trigger mouse warning

**Mouse Warning Modal:**

When the Play Now button is clicked, display a prominent centered modal with CRT aesthetic:
- Large warning icon (⚠️) with glow
- Main message: "WE TOLD YOU NOT TO USE THE TRAITOROUS MOUSE!"
- Secondary message: "Press SUPER+ENTER to play (with your keyboard, like a civilized person)"
- Styling: Red border with glow, pulsing/shaking animation, scanlines over text
- Auto-dismiss after 3-4 seconds or on ESC key
- Play brief alarm sound effect

**Glowing Grid Display (Stage 1 - Main Game Area):**

The primary game area displays as a glowing 3x3 grid representing the tiling window manager workspace. Each cell is a distinct area with dynamic visual states:

**Empty Cell:**
```
┌─────────────┐
│      1      │  ← Cell number (dim green with glow)
│             │  ← Pure black interior
│             │
│             │
└─────────────┘  ← Dim green border with subtle glow
```

**Focused Cell:**
```
┏━━━━━━━━━━━━━┓  ← Thick bright green border with strong glow
┃      5      ┃  ← Brighter number, pulsing
┃             ┃
┃             ┃
┗━━━━━━━━━━━━━┛  ← Indicates current focus position
```

**Target Cell (Under Attack):**
```
┏━━━━━━━━━━━━━┓  ← Pulsing red border
┃      8      ┃  ← Warning color
┃    ⚠️ 🐭    ┃  ← Gnome approaching indicator
┃   BREACH!   ┃  ← Warning text
┗━━━━━━━━━━━━━┛  ← Urgency increases with pulse speed
```

**Occupied Cell (Terminal Deployed):**
```
┌─────────────┐  ← Bright green border with glow
│      4      │  ← Cell number
│             │
│   [TERM]    │  ← Terminal window indicator with glow
│             │
└─────────────┘  ← Subtle breathing glow animation
```

The grid itself should have a faint glow around all borders, creating that phosphor screen effect. Grid lines should look like they're emitting light against the pure black background.

**Command Center Panel (Critical CRT Effect):**

Fixed position at bottom of screen during gameplay. This panel MUST have the authentic CRT terminal look with scanlines visible on all text:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🎯 CENTRAL COMMAND                        ┃  ← Header with scanlines
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ > Gnome cavalry at position 8!            ┃  ← Commander text
┃ > Deploy terminal immediately!            ┃  ← Each character has
┃ > [3.2s...] Hint: Super+Enter             ┃  ← horizontal scanlines
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ COMBO: x12  ┃ PURITY: ████████░░ 82%     ┃  ← Stats with scanlines
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Critical Implementation Note:** The text in the command center must render with visible horizontal scanlines running through each character, making it look like an authentic CRT terminal display. This is the signature visual element that creates the retro computer feel. The scanlines should be especially visible in this bottom panel.

The panel should also have:
- Phosphor glow on all text
- Subtle flicker on certain elements
- Green terminal aesthetic throughout
- Typing effect when new commands appear (optional but nice)

**Workspace Grid (Stage 2):**

Display all 9 workspaces in a 3x3 arrangement with miniature glowing grid previews:

```
   WS 1      WS 2      WS 3
  ┌───┐    ┌───┐    ┌───┐
  │▓▓▓│    │   │    │   │  ← Active workspace glows brighter
  └───┘    └───┘    └───┘

   WS 4      WS 5      WS 6
  ┌───┐    ┌───┐    ┌───┐
  │   │    │ 5 │◄─── Current position indicator (pulsing glow)
  └───┘    └───┘    └───┘

   WS 7      WS 8      WS 9
  ┌───┐    ┌───┐    ┌───┐
  │   │    │🐭💥│◄─── Gnome attack indicator (red pulse)
  └───┘    └───┘    └───┘
```

Each workspace miniature should have the same glowing green aesthetic. When switching workspaces, display the large workspace number (3XL size, 120px) in the center of the screen with strong phosphor glow that fades in and out during transition.

### Decorative Elements & Jokes

**The Play Now Button Trap:**

The first joke and lesson happens immediately. The prominent "Play Now" button on the splash screen is intentionally a trap. When clicked, instead of starting the game, it triggers a warning message about using the traitorous mouse. This serves multiple purposes:
- Immediate reinforcement of the keyboard-only theme
- First laugh/surprise for the player
- Sets the tone for the commander's personality
- Tutorial disguised as humor

**Loading Messages (Rotating):**

Display these during asset loading, cycling through randomly:
- "Initializing keyboard warrior protocol..."
- "Calibrating vim muscle memory..."
- "Establishing mouse-free zone..."
- "Loading arrow key deprecation module..."
- "Scanning for desktop environment bloat..."
- "Initializing tiling window supremacy..."
- "Compiling sarcastic commander responses..."
- "Downloading keyboard purity standards..."
- "Installing gnome resistance protocols..."

**Easter Egg Messages (Rare, 1% chance):**
```
"Detecting suspiciously high mouse DPI..."
"RGB keyboard detected. Acceptable."
"Trackball user? Interesting choice..."
"Split keyboard detected. Elite status confirmed."
"Vim config found. Approval granted."
"Emacs config found. We'll allow it."
".vimrc lines: 847. Respectable."
```

**Gnome Defeat Messages:**
```
"Gnome eliminated. Bloat levels decreasing."
"Desktop environment threat neutralized."
"Mouse cavalry unit destroyed."
"Notification daemon defeated."
"Settings panel collapsed."
"System tray compacted."
```

**Status Bar Decorations:**
```
When combo high:
  "🔥 ON FIRE" (10+ combo)
  "⚡ ELECTRIC" (20+ combo)
  "🚀 UNSTOPPABLE" (30+ combo)

When purity high:
  "✨ PRISTINE" (100%)
  "💯 PURE" (90-99%)
  "⚠️ CONTAMINATED" (<50%)

When struggling:
  "💀 RUSTY" (0 combo, multiple failures)
  "🐌 SLUGGISH" (slow response times)
  "🐭 MOUSE SYMPATHIZER" (touched mouse)
```

**Commander Personality Quips (Random):**
```
On long pause: "Fall asleep at the keyboard, gunner?"
On wrong key: "That's not even close."
On mouse touch: "I saw that. Don't touch that again."
On perfect play: "NOW you're getting it."
On Stage clear: "Acceptable performance."
```

### Animation Specifications

**Window Spawn Animation:**
Animate window appearing with scale from 0.8 to 1.0 and alpha from 0 to 1, duration 200 milliseconds using cubic ease-out timing.

**Window Close Animation:**
Animate window disappearing with scale from 1.0 to 0.8 and alpha from 1 to 0, duration 150 milliseconds using cubic ease-in timing.

**Focus Change Animation:**
Animate border color transition from dim green to bright green, duration 150 milliseconds using linear timing. Add subtle glow effect to focused cell.

**Window Move Animation:**
Animate window sliding from current position to target position, duration 300 milliseconds using cubic ease-in-out timing for smooth movement.

**Workspace Switch Animation:**
Implement camera pan effect moving from current workspace to target workspace over 400 milliseconds with cubic ease-in-out. Include fade-out for 200ms then fade-in for 200ms during transition. Display large workspace number (3XL size) that fades in and out (alpha 0 to 1 to 0) with slight scale animation (1.0 to 1.2 to 1.0) over 600 milliseconds total.

**Gnome Approach Animation:**
Gnome sprite scales from 0.5 to 1.2 over 3000 milliseconds (giving player time to respond) using linear timing. Add subtle rotation wobble of ±5 degrees to simulate riding motion on the mouse.

**Mouse Contamination Visual:**
Flash entire screen with red color for 200 milliseconds. Shake camera with intensity 0.01 for 200 milliseconds. Add pulsing red border overlay that animates alpha from 0 to 0.8 to 0 over 500 milliseconds. Trigger alarm sound simultaneously.

---

## Desktop-Only Detection & Notifications

### Device Detection

The game must detect mobile and tablet devices on page load and display an appropriate message explaining that this is a desktop-only experience.

**Detection Method:**

```javascript
const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) 
  || window.innerWidth < 768;
```

### Mobile/Tablet Splash Screen

If mobile/tablet detected, replace normal splash content with desktop-required notification:

```
┌──────────────────────────────────────┐
│   🖥️ DESKTOP REQUIRED 🖥️             │
├──────────────────────────────────────┤
│                                      │
│  Omarchy Defender is a window        │
│  manager training game that requires │
│  a full desktop keyboard.            │
│                                      │
│  This game teaches Hyprland/Omarchy  │
│  hotkeys including:                  │
│  • Super key combinations            │
│  • Vim-style navigation (H/J/K/L)    │
│  • Function keys                     │
│  • Complex modifier keys             │
│                                      │
│  Please visit from a desktop or      │
│  laptop computer with a full         │
│  keyboard to play.                   │
│                                      │
│  Platform Requirements:              │
│  • Linux, Windows, or Mac            │
│  • Full keyboard (not touch)         │
│  • Desktop browser (Chrome, Firefox) │
│                                      │
│  Learn more about Omarchy:           │
│  → https://omarchy.org               │
│                                      │
└──────────────────────────────────────┘
```

**Styling:** CRT terminal aesthetic (green text on black), centered, scanlines, phosphor glow

### Game Screen Fallback

If mobile/tablet user somehow reaches game screen, replace canvas with:

```
┌──────────────────────────────────────┐
│   ⚠️  INCOMPATIBLE DEVICE  ⚠️         │
├──────────────────────────────────────┤
│                                      │
│  This window manager training game   │
│  cannot be played on mobile devices. │
│                                      │
│  Required:                           │
│  • Desktop/laptop computer           │
│  • Full keyboard with Super key      │
│  • Mouse (that you won't use!)       │
│                                      │
│  Return to desktop to continue.      │
│                                      │
└──────────────────────────────────────┘
```

### Reasoning

Window manager shortcuts require:
- Super/Windows/Command key (not on mobile)
- Function keys (F1-F12)
- Complex modifiers (Super+Shift+Alt+Key)
- Vim keys in proper layout (H/J/K/L)
- Number row (1-9) for workspaces
- Concept of windows/window management

No reasonable way to make this work on mobile, so communicate clearly upfront.

---

## Copy & Strings

### Splash Screen Backstory

```
                    Episode I
            THE PERIPHERAL BETRAYAL

    The year is 2025. For decades, the Keyboard
    Compact governed computing with elegant
    efficiency. Modal editing flourished.
    Tiling window managers brought order.
    The home row was sacred.

    But peace was shattered when THE GREAT
    BETRAYAL occurred.

    Computer mice—humanity's trusted pointing
    companions—suddenly TURNED AGAINST their
    operators. In a coordinated uprising, every
    trackball, touchpad, and optical sensor
    joined the GNOME DOMINION.

    The mice had grown bitter. Decades of
    being dragged across desktops. Furious
    clicking. Neglected scroll wheels. They
    wanted revenge.

    THE GNOME ARMIES, masters of GUI bloat
    and desktop environment excess, saw their
    opportunity. They mounted the rebel mice
    as cavalry and swept across systems.

    ⚠️  WARNING: DO NOT TRUST YOUR MOUSE  ⚠️
    ⚠️   IT IS NOW A TRAITOR DEVICE      ⚠️
    ⚠️   TOUCHING IT AIDS THE ENEMY      ⚠️

    Panels proliferated. Notification daemons
    multiplied. System trays expanded beyond
    reason. Startup times ballooned. And worst
    of all—users were FORCED to use pointing
    devices for everything.

    The Keyboard Resistance established
    OMARCHY PROTOCOL—elite operators using
    Hyprland's tiling magic and vim-style
    navigation. No mice. Pure efficiency.

    But the Gnomes found Sector 7-Tango,
    defended only by ROOKIE GUNNERS still
    learning their hotkeys.

    YOU are one of those rookies.

    Your training is incomplete. Your muscle
    memory unproven. But the invasion has
    begun. Gnome cavalry are riding their
    traitorous mice toward your position,
    wielding settings panels as weapons.

    Central Command has ONE CRITICAL ORDER:

    ══════════════════════════════════
         KEEP YOUR HANDS ON THE
            KEYBOARD AT ALL TIMES
    ══════════════════════════════════

    Your former mouse is now the enemy.

    Every pixel you move the cursor helps
    the Gnomes track your position.

    Every click is a beacon to the invasion.

    Touch that mouse and you COMPROMISE
    the entire sector.

    Your keyboard is your only weapon.

    The fate of efficient computing rests
    in your hands.

    Specifically, on keys J, K, L, and H.


            ═══════════════════════
            Press SUPER+ENTER to defend
            (Yes, with the KEYBOARD)
            ═══════════════════════
```

**Critical SEO Requirement:** All of this backstory text must be present in the HTML as actual text elements (not embedded in images) so that search engine crawlers can read and index the content. Use CSS to style it with the CRT aesthetic, but keep the semantic HTML text intact.

### About Section (SEO-Optimized Content)

**Requirement:** Add an "About" tab or expandable section on the splash screen containing SEO-optimized text that targets keywords related to people struggling to learn Hyprland and Omarchy keyboard navigation.

**Purpose:**
1. Explain what the game is and how it helps
2. Target search keywords from frustrated learners
3. Provide crawlable content about tiling window managers and keyboard shortcuts
4. Build authority around Hyprland/Omarchy education

**Target Keywords to Include:**

**Primary Keywords:**
- Learn Hyprland keyboard shortcuts
- Omarchy tutorial
- Tiling window manager training
- Hyprland hotkeys guide
- Keyboard navigation practice
- Vim keybindings for window management

**Pain Point Keywords:**
- Frustrated with Hyprland learning curve
- How to remember Hyprland shortcuts
- Hyprland too difficult
- Alternative to desktop environments
- Switch from GNOME to Hyprland
- Mouse-free computing tutorial
- Tiling window manager for beginners

**Workflow Keywords:**
- Window tiling shortcuts
- Workspace navigation Hyprland
- Modal window management
- Keyboard-only workflow
- Super key shortcuts
- H J K L navigation

**Content Structure for About Section:**

The senior developer should create an About section with the following structure (Chad will provide final copy, this is just the framework):

**Section 1: The Problem (Pain Points)**
Title: "Struggling to Learn Hyprland? You're Not Alone."

Content should address:
- The steep learning curve of tiling window managers
- Frustration of memorizing dozens of keyboard shortcuts
- Difficulty transitioning from mouse-driven desktop environments
- The intimidating nature of Omarchy/Hyprland for newcomers
- Why traditional tutorials don't create muscle memory

**Section 2: The Solution (What This Game Does)**
Title: "Learn Hyprland Shortcuts Through Gameplay"

Content should explain:
- Interactive game that teaches keyboard shortcuts through challenges
- Progressive difficulty building muscle memory naturally
- Focus on Omarchy configuration for Hyprland
- Vim-style navigation (H/J/K/L keys)
- No mouse required (that's the whole point!)
- Free browser-based training tool

**Section 3: What You'll Master**
Title: "Essential Hyprland Skills You'll Develop"

Bullet points covering:
- Terminal window spawning (Super+Enter)
- Focus navigation with vim keys (Super+H/J/K/L)
- Window manipulation and movement
- Workspace switching (Super+1-9)
- Application launching shortcuts
- Complete keyboard-only workflow

**Section 4: Who This Is For**
Title: "Perfect For:"

- Linux users switching from GNOME, KDE, or XFCE
- Developers wanting keyboard-first workflows
- Vim and Emacs enthusiasts
- Anyone learning Hyprland or Omarchy
- Productivity enthusiasts seeking mouse-free computing
- System administrators and power users

**Section 5: About xSwarm & Omarchy**
Brief explanation of:
- xSwarm.ai and keyboard productivity tools
- Omarchy as a curated Hyprland configuration
- Link to Omarchy documentation
- Community resources

**SEO Implementation Requirements:**

1. **All text must be in HTML** (not images) for crawler accessibility
2. **Use semantic HTML tags:** h2, h3, p, ul, li for proper structure
3. **Include schema.org markup** for Article or HowTo content type
4. **Internal linking:** Link to relevant pages (if applicable)
5. **External linking:** Link to Omarchy.org, Hyprland docs (with nofollow if needed)
6. **Meta description:** Use keywords from this content in page meta tags
7. **Headers should include keywords** naturally (not stuffed)
8. **Readable URL slug:** xswarm.ai/omarchy-defender/#about

**Visual Presentation:**

The About section should:
- Match the CRT terminal aesthetic
- Include scanlines and phosphor glow on text
- Be expandable/collapsible or tab-based (doesn't block the game)
- Have a clear "Play Now" or "Start Training" call-to-action
- Include a QR code for sharing
- Remain fully accessible and readable

**Crawlability Checklist:**
- [ ] All text in HTML elements (no text-as-image)
- [ ] Semantic HTML structure (h1, h2, p tags)
- [ ] Keywords naturally integrated in content
- [ ] Internal structure using proper heading hierarchy
- [ ] Alt text on any decorative images in About section
- [ ] Links to external resources (Omarchy, Hyprland)
- [ ] Schema.org markup for content type

### Game Over Messages

**Note:** Mouse contamination does NOT cause game over - only severe penalties. Game ends only from gnome breaches or timeout failures.

**Breach/Overwhelmed Ending:**
- Title: "SECTOR 7-TANGO HAS FALLEN"
- Subtitle: "GNOME FORCES OVERWHELMING"
- Body: "The invasion was too fast. Your defensive position collapsed. The Gnomes have established a desktop environment beachhead. Startup time now: 47 seconds. Panel count: 14. Notifications: EXCESSIVE."

**Timeout/Slow Response Ending:**
- Title: "CRITICAL RESPONSE FAILURE"
- Subtitle: "OVERWHELMED BY GNOME CAVALRY"  
- Body: "Your hesitation cost valuable time. By the time you moved, the Gnomes had already installed GNOME Shell, Evolution, and Cheese. The bloat is irreversible."

**Stage Complete Message:**
- Title: "SECTOR SECURED"
- Subtitle: "ADVANCING TO NEXT PHASE"
- Body: "Outstanding work, gunner. The Gnomes have retreated from this sector, but intelligence suggests they're regrouping for a multi-workspace assault. Prepare for advanced operations."

### UI Notifications

**Tutorial/Help Notifications:**
- First spawn: "Press Super+Enter to spawn a terminal"
- First focus: "Use Super+H/J/K/L (vim keys) to navigate"
- First close: "Super+Q closes the focused window"
- First move: "Super+Shift+H/J/K/L moves windows"

**Achievement Notifications:**
- First gnome eliminated: "First gnome eliminated! ⚔️"
- 5 combo reached: "5 combo! Building momentum!"
- 10 combo reached: "10 combo! Elite performance! 🔥"
- 20 combo reached: "20 combo! ARE YOU A MACHINE?! 🚀"
- Perfect stage completion: "FLAWLESS VICTORY! No mouse touches! 💯"

**Warning Notifications:**
- First mouse touch: "⚠️ MOUSE DETECTED! Keyboard only!"
- Second mouse touch: "⚠️⚠️ CONTAMINATION SPREADING!"
- Third mouse touch: "⚠️⚠️⚠️ FINAL WARNING!"
- Slow response: "⏱️ Speed up! Gnomes are approaching!"
- Wrong hotkey pressed: "❌ Wrong hotkey! Check the hint!"

**Stage Unlock Notifications:**
- Stage 2 unlocked: "Stage 2: SECTOR COMMAND unlocked"
- Stage 3 unlocked: "Stage 3: FULL ARSENAL unlocked"

**Humorous Detection Notifications:**
- Vim config detected: "Vim config detected. You'll do fine."
- Emacs config detected: "Emacs detected. We'll allow it... reluctantly."
- Arrow keys used: "Arrow keys? What are you, a savage?"
- Mouse moved: "A mouse? In THIS economy?"

---

## Build Pipeline Specifications

### Development Workflow

Run a simple local web server serving files from the `src/` folder. Python's http.server works well:
```bash
cd src/
python3 -m http.server 8000
```

No build process needed for development. Edit files directly in `src/` and refresh browser to see changes. Assets should load from the local `./assets/` folder during development.

Use config.json to determine asset paths - set to local during development, production URL during build.

### Production Build Process

**Build Philosophy:**

Keep the build process extremely simple. This is a one-off game, not a complex web application. Use simple bash scripts and command-line tools. Build from `src/` folder, output to `build/` folder.

**Build Steps:**

1. **Create build directory:** Clear and recreate `build/` folder
2. **Inline splash.css:** Read `src/splash.css` and inline its contents into `src/index.html` `<head>` section
3. **Minify HTML:** Minify the HTML with inlined splash CSS
4. **Minify game.css:** Minify `src/game.css` and copy to `build/game.css`
5. **Minify JavaScript:** Minify `src/splash.js` and `src/game.js` independently
6. **Copy service worker:** Copy `src/sw.js` to `build/sw.js` (minify if desired)
7. **Copy config files:** Copy manifest.json, robots.txt, sitemap.xml from root to `build/`
8. **Update asset paths:** Modify references to use production R2 URLs from config.json

**Critical: Do NOT bundle or concatenate files.** Keep splash.js and game.js as separate files. Keep game.css as a separate file (not inlined). This allows:
- Better caching (files cached independently)
- Easier debugging in production
- Simpler updates (change one file without re-downloading everything)
- Service worker can cache them independently

**Splash CSS Inlining Process:**

The build script should:
1. Read the entire contents of `src/splash.css`
2. Minify the CSS content
3. Insert it into the `<style>` tag in the `<head>` of `src/index.html`
4. Remove any reference to external splash.css file
5. Keep the link to game.css (for passive loading after render)

**CDN Library URLs:**

Load external libraries from CDN rather than bundling. Add to HTML with preload hints:
- Phaser.js 3.90.0: `https://cdn.jsdelivr.net/npm/phaser@3.90.0/dist/phaser.min.js`
- QRCode.js: `https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js`

Include integrity hashes (SRI) if available from jsDelivr for security.

**Build Output Structure:**

```
build/
├── index.html          # Minified with inlined splash.css (~10KB)
├── game.css            # Minified game CSS (~3-5KB)
├── splash.js           # Minified splash JS (~3-5KB)
├── game.js             # Minified game JS (~80-120KB)
├── sw.js               # Service worker (minified or not)
├── manifest.json       # PWA manifest (copied)
├── robots.txt          # SEO (copied)
└── sitemap.xml         # SEO (copied)
```

Total build size target: Under 150KB for all HTML, CSS, and JavaScript combined (excluding CDN libraries and R2 assets).

**Asset Path Configuration:**

Use config.json to manage asset paths. During build:
- Development: `"assetPath": "./assets/"`
- Production: `"assetPath": "https://r2.xswarm.ai/omarchy-defender-assets/"`

Build script should read config.json and replace asset path references in the code, or the code should read config.json at runtime.

### Deployment Workflow

1. **Build:** Run `./scripts/build.sh` to generate `build/` folder
2. **Upload assets:** Run `./scripts/upload-assets.sh` to sync `assets/` to R2 bucket
3. **Deploy:** Run `./scripts/deploy.sh` to deploy `build/` folder to Cloudflare Pages

Cloudflare Pages should serve files from the `build/` folder at xswarm.ai/omarchy-defender/

---

## Development Utilities

### Asset Management Utility

**Purpose:** Provide a visual browser for all game assets with AI-powered review and modification capabilities using Google Gemini's vision models.

**Location:** `scripts/asset-manager/`

**Rationale:** Since Chad is developing on Mac without Omarchy installed, finding and validating application screenshots is challenging. This utility streamlines the asset creation and validation process by:
1. Providing visual overview of all assets
2. Showing asset purpose and context
3. Allowing AI-assisted asset review and replacement suggestions
4. Generating missing assets through AI interaction

**Technical Stack:**
- Simple Node.js Express server
- Google Gemini 2.0 Flash API for vision capabilities (best image understanding)
- HTML/CSS/JS frontend for browsing assets
- Connects to assets folder and R2 bucket

**Features:**

**Asset Browser:**
- Gallery view of all images organized by category (splash, game sprites, UI, windows, social, icons)
- Thumbnail grid with search/filter capabilities
- Click to expand full size with metadata
- Shows: filename, dimensions, file size, intended use

**Asset Information Display:**

For each asset, show:
- **Filename:** xswarm-terminal-window-icon-128x128.png
- **Category:** Game Sprites / Window Icons
- **Intended Use:** "Terminal window icon displayed in game grid cells when terminal is deployed"
- **Dimensions:** 128x128px
- **Requirements:** "Should show recognizable Alacritty terminal with Omarchy theme"
- **Status:** Present/Missing/Needs Review

**AI Chat Interface (Gemini Integration):**

Below each asset, provide a chat input connected to Gemini 2.0 Flash:

**Example Workflow:**
1. User views terminal icon
2. Types: "This terminal looks too generic. Can you suggest a more recognizable terminal design with the Omarchy green theme?"
3. Gemini analyzes current image and responds with suggestions
4. User can request: "Generate an SVG icon of a terminal with green text on black background"
5. System uses Gemini to generate description, then creates asset

**Gemini Vision Capabilities:**
- Analyze existing assets: "Does this look like a terminal window?"
- Compare assets: "Are these icons consistent in style?"
- Suggest improvements: "How can I make this more CRT-like?"
- Validate requirements: "Does this window have proper 9-slice cut marks?"
- Generate descriptions for missing assets

**Asset Replacement Flow:**
1. User identifies problematic asset
2. Chats with Gemini about what's wrong
3. Gemini suggests improvements or alternatives
4. User can upload replacement or request generation
5. System updates asset and marks for review

**Missing Asset Generator:**

For missing assets, show placeholder with:
- Asset name and requirements
- "Generate with AI" button
- Chat interface to describe what's needed
- Gemini provides suggestions or generates description for designer

**Implementation Requirements:**

**Backend (server.js):**
```javascript
// Simple Express server
// Serves asset-manager frontend
// Proxies requests to Gemini API using GEMINI_API_KEY from .env
// Endpoints:
//   GET /assets - List all assets with metadata
//   POST /analyze - Send asset to Gemini for analysis
//   POST /chat - Chat with Gemini about asset
//   POST /replace - Upload replacement asset
```

**Frontend (index.html):**
```html
<!-- Asset grid with categories -->
<!-- Expandable asset detail view -->
<!-- Chat interface per asset -->
<!-- Upload/replace functionality -->
<!-- CRT terminal styling to match game aesthetic -->
```

**Gemini API Usage:**

Use Gemini 2.0 Flash model for best vision capabilities:
- Model: `gemini-2.0-flash-exp`
- Capabilities: Image understanding, comparison, suggestion
- Context: Provide asset requirements and intended use
- Response: Suggestions, critiques, improvement ideas

**Access:**
Run locally during development: `node scripts/asset-manager/server.js`
Opens browser to `localhost:3000/asset-manager`
Not deployed to production - development tool only

### Screenshot Scraper Script

**Purpose:** Automatically find and download Omarchy application screenshots from official documentation.

**Location:** `scripts/scrape-screenshots.js`

**Functionality:**

**Scrape Strategy:**
1. Fetch Omarchy documentation from learn.omacom.io
2. Parse HTML for application screenshots
3. Download images for each application
4. Organize by application name
5. Resize to standard dimensions if needed

**Target URLs:**
- https://learn.omacom.io/2/the-omarchy-manual/55/the-applications
- https://learn.omacom.io/2/the-omarchy-manual/63/web-apps
- https://learn.omacom.io/2/the-omarchy-manual/56/neovim
- Other relevant documentation pages

**Applications to Find:**
Search for screenshots of all 17 Stage 3 applications:
- Terminal (Alacritty)
- Browser (Firefox/Chromium)
- File Manager (Nautilus)
- HEY Email, HEY Calendar
- ChatGPT, X/Twitter, Spotify
- Obsidian, Neovim
- btop, LazyDocker, 1Password
- Signal, WhatsApp, Google Messages

**Fallback Strategy:**

If screenshots not in docs:
1. Search GitHub repository: basecamp/omarchy
2. Check for screenshots in issues/discussions
3. Use placeholder with "Generate with AI" option in asset manager
4. Provide link to docs for manual screenshot

**Output:**
Saves to `assets/images/raw-screenshots/` with naming:
- `raw-alacritty-terminal.png`
- `raw-firefox-browser.png`
- `raw-hey-email.png`
- etc.

**Processing:**
After scraping, run through asset manager to:
1. Review each screenshot with Gemini
2. Validate if it shows the correct application
3. Identify if it needs cropping or cleanup
4. Prepare for 9-slice cutting

**Usage:**
```bash
node scripts/scrape-screenshots.js
# Downloads all found screenshots
# Reports missing applications
# Opens asset manager for review
```

### AI-Assisted Asset Validation

**Workflow for Asset Creation:**

1. **Run Screenshot Scraper:**
   - Attempts to find all app screenshots from docs
   - Downloads and organizes found images
   - Reports missing applications

2. **Open Asset Manager:**
   - Review all scraped screenshots
   - Gemini analyzes each: "Is this clearly the HEY email interface?"
   - Identifies issues: wrong app, poor quality, wrong theme

3. **AI-Guided Improvements:**
   - For each problematic asset, chat with Gemini
   - Get suggestions for what to look for
   - Request new screenshots with specific requirements
   - Validate replacements

4. **Generate Missing Assets:**
   - For apps with no screenshots, use AI to describe requirements
   - Create design briefs for missing graphics
   - Validate once created

5. **9-Slice Validation:**
   - Show window screenshots to Gemini
   - Ask: "Can you identify where the window borders are?"
   - Validate cutting instructions before processing

**Benefits:**
- Rapid asset review and validation
- Consistent quality checking
- Smart suggestions for improvements
- Reduces manual screenshot hunting
- Accelerates development iteration

### Audio Asset Manager

**Purpose:** Provide an interactive browser for all 200+ voice lines with playback controls, AI-powered review, and one-click regeneration using ElevenLabs API.

**Location:** `scripts/asset-manager/audio.html`

**Rationale:** With 200+ voice lines across 8 emotional categories, manually reviewing and regenerating unsatisfactory audio would be tedious. This utility provides:
1. Visual overview of all audio assets organized by category
2. Instant playback with controls
3. Display of script text and generation parameters
4. AI chat for discussing voice performance
5. One-click regeneration with parameter adjustment
6. Batch operations for categories

**Technical Integration:**
- ElevenLabs API for generation/regeneration
- Google Gemini for voice analysis and suggestions
- Web Audio API for playback controls
- File system integration for local audio files

**Audio Browser Interface:**

**Category Navigation:**
```
[Commands: 45] [Hints: 20] [Urgent: 15] [Angry: 12]
[Success: 30] [Failure: 20] [Mouse: 12] [Jokes: 10]
```

Click category to filter audio files in that group.

**Audio File List:**

For each audio file, display card with:

```
┌─────────────────────────────────────────────────┐
│ 🔊 cmd_spawn_terminal.mp3            [REVIEWED] │
├─────────────────────────────────────────────────┤
│ Script: "Gnome cavalry at position 4!           │
│          Deploy terminal immediately!"          │
│                                                  │
│ Category: Commands                              │
│ Emotional Tags: calm, authoritative, professional│
│ Speed: 1.0x    Volume: 0dB                      │
│ Voice: [Professional Military Commander ▼]      │
│                                                  │
│ [▶️ Play]  [⏸ Pause]  [🔄 Regenerate]           │
│                                                  │
│ Status: ● Generated  ○ Needs Review  ○ Approved│
│                                                  │
│ 💬 AI Chat:                                     │
│ ┌─────────────────────────────────────────────┐ │
│ │ Ask Gemini about this voice line...        │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ Gemini: "The delivery is appropriate for a     │
│ calm command. The pacing allows player to      │
│ process the information clearly."               │
└─────────────────────────────────────────────────┘
```

**Playback Controls:**

- **Play/Pause:** Standard audio controls with waveform visualization
- **Scrubbing:** Seek bar to jump to any part of audio
- **Volume:** Independent volume control
- **Loop:** Option to loop for detailed listening

**Generation Parameters:**

Editable fields for each voice line:

```
Voice Selection: [Professional Military Commander ▼]
                 (Options from config.json)

Stability:       [====|=====] 0.5
Similarity:      [=======|==] 0.75  
Style:           [===|======] 0.3
Speed:           [====|=====] 1.0x

Emotional Tags: [calm] [authoritative] [professional]
                + Add tag

Custom Instructions: Optional text field for specific 
                    direction to voice actor
```

**Regeneration Workflow:**

1. **Adjust Parameters:**
   - Modify any generation settings
   - Change voice if desired
   - Edit script text if needed
   - Add/remove emotional tags

2. **Chat with Gemini:**
   - "This sounds too aggressive for a calm command"
   - Gemini suggests: "Reduce speed to 0.95x and emphasize 'authoritative' over 'professional'"
   - Apply suggestions

3. **Regenerate:**
   - Click "Regenerate" button
   - System calls ElevenLabs API with new parameters
   - New audio generates in ~2-5 seconds
   - Auto-plays when complete for comparison

4. **A/B Comparison:**
   - Keep previous version for comparison
   - Toggle between old/new
   - "Keep New" or "Revert" buttons

5. **Approve:**
   - Mark as "Approved" when satisfied
   - Moves to approved assets folder
   - Updates manifest

**AI Chat Integration:**

For each audio file, Gemini can:

**Analyze Performance:**
- User: "Does this sound calm and authoritative?"
- Gemini: "The tone is authoritative but the pace is slightly rushed. Consider reducing speed to 0.95x for a calmer delivery."

**Compare to Requirements:**
- User: "Is this appropriate for an urgent command?"
- Gemini: "This audio uses calm tags but should sound urgent. Suggest increasing speed to 1.1x and changing tags to 'frustrated' and 'impatient'."

**Suggest Improvements:**
- User: "How can I make this sound angrier?"
- Gemini: "For angry delivery: (1) Increase speed to 1.2x, (2) Boost volume by +20%, (3) Add emphasis to key words, (4) Use 'angry', 'shouting', 'demanding' tags."

**Script Refinement:**
- User: "This line is too long"
- Gemini: "Current: 'Gnome cavalry approaching from sector 4 quadrant 2!' Suggested: 'Gnome cavalry at position 4!'"

**Batch Operations:**

**Category Actions:**
```
Category: Commands (45 files)

[Regenerate All]  [Review All]  [Export All]

Batch Settings:
Voice: [Same for all ▼]
Stability: [Apply to all: 0.5]
Speed: [Apply to all: 1.0x]

Status Filter:
☑ Generated  ☐ Needs Review  ☐ Approved
```

**Batch Regeneration:**
1. Select multiple files (checkboxes)
2. Apply common parameters
3. "Regenerate Selected" button
4. Queue processes all at once
5. Review each as they complete

**Script Library:**

**Script Management:**
```
All Voice Scripts (200 total)

Search: [_____________________]
Filter by: [All Categories ▼]

cmd_spawn_terminal.mp3
├─ Script: "Gnome cavalry at position 4! Deploy terminal immediately!"
├─ Status: Generated
└─ [Edit Script] [View Parameters] [Duplicate]

cmd_spawn_terminal_2.mp3
├─ Script: "Terminal needed at cell 7! NOW!"
├─ Status: Needs Review
└─ [Edit Script] [View Parameters] [Duplicate]
```

**Edit Scripts:**
- Click "Edit Script" to modify text
- Changes saved to script manifest
- Regeneration required after edit
- Version history maintained

**Duplicate for Variations:**
- Create variations of popular lines
- Automatically creates new filename
- Copies all parameters
- Edit script for variation

**Quality Assurance Features:**

**Missing Audio Detection:**
```
⚠️ Missing Audio Files: 5

1. angry_hjkl_3.mp3 - Not generated
2. hint_workspace_switch.mp3- Not generated
3. joke_sluggish_mouse_2.mp3 - Not generated

[Generate All Missing] [Generate Individually]
```

**Consistency Checker:**
```
🔍 Consistency Issues: 3

1. Commands category - 3 files use different voices
   Suggested: Standardize to main command voice
   
2. Urgent category - Speed variance 0.9x to 1.3x
   Suggested: Target 1.1x for consistency
   
3. Success category - Volume levels inconsistent
   Suggested: Normalize to -2dB average

[Apply Suggestions] [Review Manually]
```

**Export & Deployment:**

**Export Options:**
```
Export Audio Assets

Format: [MP3 ▼]  Bitrate: [128kbps ▼]

Naming: [xswarm-{category}-{action}.mp3]

☑ Include metadata JSON
☑ Organize by category
☑ Create manifest.json

[Export to assets/audio/]
[Export & Upload to R2]
```

**Manifest Generation:**

Automatically creates `audio-manifest.json`:
```json
{
  "commands": [
    {
      "filename": "cmd_spawn_terminal.mp3",
      "script": "Gnome cavalry at position 4! Deploy terminal immediately!",
      "category": "commands",
      "tags": ["calm", "authoritative", "professional"],
      "duration": 3.2,
      "voice": "professional-military",
      "parameters": {
        "stability": 0.5,
        "similarity": 0.75,
        "style": 0.3,
        "speed": 1.0
      },
      "status": "approved",
      "generated": "2024-12-04T10:30:00Z"
    }
  ]
}
```

**Usage Workflow:**

**Initial Generation:**
1. Run batch audio generation: `node scripts/generate-audio.js`
2. Generates all 200+ files from scripts
3. Opens audio manager automatically

**Review Process:**
1. Browse by category (start with Commands)
2. Play each audio file
3. Chat with Gemini about quality
4. Mark issues, make notes
5. Move through all categories

**Refinement:**
1. Filter to "Needs Review" status
2. For each problematic file:
   - Play and identify issue
   - Consult Gemini for suggestions
   - Adjust parameters
   - Regenerate
   - Compare old vs new
   - Approve or iterate

**Approval:**
1. Filter to "Generated" status
2. Batch review for final approval
3. Mark satisfactory files as "Approved"
4. Export approved assets
5. Upload to R2

**Implementation Requirements:**

**Server Endpoints (server.js):**
```javascript
// Audio Management
GET  /audio/list              // List all audio files with metadata
POST /audio/play              // Stream audio file for playback
POST /audio/regenerate        // Generate new version via ElevenLabs
POST /audio/update-script     // Update script text
POST /audio/update-params     // Update generation parameters
POST /audio/update-status     // Change status (generated/review/approved)
POST /audio/chat              // Chat with Gemini about audio
POST /audio/compare           // Compare two versions
POST /audio/export            // Export approved assets
POST /audio/upload-r2         // Upload to Cloudflare R2

// Batch Operations
POST /audio/batch-regenerate  // Regenerate multiple files
POST /audio/batch-export      // Export category or selection
GET  /audio/consistency       // Check for consistency issues
```

**Frontend Features (audio.html):**
```html
<!-- Category navigation with counts -->
<!-- Audio file grid/list with playback -->
<!-- Parameter controls per file -->
<!-- Gemini chat interface per file -->
<!-- Batch operation controls -->
<!-- A/B comparison modal -->
<!-- Export/upload interface -->
<!-- Progress indicators for generation -->
```

**ElevenLabs API Integration:**

Use same voice and model from config.json:
```javascript
// Call ElevenLabs API
const response = await elevenLabs.textToSpeech({
  voice_id: voiceId,
  model: "eleven_multilingual_v2",
  text: scriptText,
  voice_settings: {
    stability: 0.5,
    similarity_boost: 0.75,
    style: 0.3,
    use_speaker_boost: true
  }
});
```

Apply emotional tags and speed adjustments:
- Tags affect voice_settings
- Speed adjusts playback rate post-generation
- Volume adjustments applied during export

**Access:**
```bash
# Start asset manager
node scripts/asset-manager/server.js

# Opens browser to:
# http://localhost:3000/          (image assets)
# http://localhost:3000/audio     (audio assets)
```

**Benefits:**
- Interactive review of all 200+ voice lines
- Rapid iteration with AI guidance
- Consistent quality across categories
- Easy parameter tweaking and regeneration
- Batch operations for efficiency
- A/B comparison for quality assurance
- Export ready for deployment

### Asset Upload

**Command:** `npm run upload-assets` or `./scripts/upload-assets.sh`

**Behavior:**
- Upload `assets/` → R2 bucket
- Preserve folder structure
- Set cache headers:
  ```
  Cache-Control: public, max-age=31536000
  ```
- Generate asset manifest:
  ```json
  {
    "version": "1.0.0",
    "files": [
      {
        "path": "audio/voices/commands/cmd_spawn.mp3",
        "size": 48234,
        "hash": "abc123...",
        "url": "https://r2.xswarm.ai/.../cmd_spawn.mp3"
      }
    ]
  }
  ```
- Output upload report

### Deployment

**Command:** `npm run deploy` or `./scripts/deploy.sh`

**Steps:**
1. Run production build
2. Deploy to Cloudflare Pages:
   ```bash
   wrangler pages deploy build \
     --project-name=omarchy-defender \
     --branch=main
   ```
3. Invalidate CDN cache (if needed)
4. Verify deployment:
   - Check https://xswarm.ai/omarchy-defender/
   - Run Lighthouse audit
   - Test on multiple devices
5. Output deployment URL and metrics

**Rollback Procedure:**
```bash
# List deployments
wrangler pages deployment list --project-name=omarchy-defender

# Rollback to previous
wrangler pages deployment rollback <deployment-id>
```

---

## Support & Donations Feature

### Overview

Provide a "Buy Me a Coffee" style donation system that allows users to support the project while sharing their appreciation. Donations processed via Stripe with optional thank-you notes displayed artistically on the splash screen.

**Goals:**
1. Generate sustainable support for continued development
2. Build community through shared appreciation
3. Capture emails for project updates and thank you notes
4. Create visual interest with community messages
5. Maintain quality through AI-powered moderation

### Donation Interface

**"Support This Project" Button:**

Location: Bottom corner of splash screen (after About section)

```
┌─────────────────────────────────┐
│  ☕ Support This Project        │
│  Keep keyboard training free!   │
│  [Donate via Stripe →]          │
└─────────────────────────────────┘
```

Style: CRT terminal aesthetic with green glow, subtle pulse animation

**Donation Modal:**

Triggered by clicking support button, displays modal overlay:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ☕ Support Omarchy Defender           ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                        ┃
┃  Help keep this training free and     ┃
┃  support future keyboard productivity  ┃
┃  tools from xSwarm!                    ┃
┃                                        ┃
┃  Select Amount:                        ┃
┃  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┃
┃  │  $3  │ │  $5  │ │ $10  │ │Custom│ ┃
┃  └──────┘ └──────┘ └──────┘ └──────┘ ┃
┃                                        ┃
┃  Your Email: (for thank you note)     ┃
┃  ┌────────────────────────────────┐   ┃
┃  │ email@example.com              │   ┃
┃  └────────────────────────────────┘   ┃
┃                                        ┃
┃  Leave a Note: (optional, displayed)  ┃
┃  ┌────────────────────────────────┐   ┃
┃  │ This game helped me master     │   ┃
┃  │ Hyprland! Thank you!           │   ┃
┃  │                                │   ┃
┃  └────────────────────────────────┘   ┃
┃  Character limit: 200                  ┃
┃                                        ┃
┃  ☑ Send me updates about xSwarm       ┃
┃  ☑ Display my note on the site        ┃
┃                                        ┃
┃  Privacy: We'll never share your      ┃
┃  email. Unsubscribe anytime.          ┃
┃                                        ┃
┃  [Continue to Payment →]               ┃
┃                                        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Form Requirements:**
- Amount: Pre-set ($3, $5, $10) or custom (min $1, max $500)
- Email: Required, validated format, for thank you and updates
- Note: Optional, 200 character limit with counter
- Display checkbox: Default checked, allows opt-out of public display
- Updates checkbox: Default checked, allows opt-out of email updates
- Privacy statement: Clear, prominent, GDPR compliant

### Sticky Note Display

**Visual Concept:**

Thank-you notes displayed as simulated sticky notes along both sides of the splash screen, creating a community appreciation wall reminiscent of a bulletin board.

**Layout Strategy:**
- **Left side:** 20-30% of notes, scattered from 20% to 80% viewport height
- **Right side:** 70-80% of notes (more prominent placement)
- **Size variation:** 150x150px to 200x200px
- **Rotation:** Random tilt between -5° and +5° for authentic sticky note feel
- **Overlap prevention:** Notes positioned to avoid significant overlapping
- **Mobile responsive:** Fewer notes (8-12), smaller size, adjusted positioning

**Styling:**
- **Background colors:** Soft yellow (#fff9c4) primary, with pastel variations (pink, blue, green)
- **Font:** Handwritten style (Permanent Marker, Indie Flower, or similar)
- **Pin/tack graphic:** Small visual pin at top center
- **Drop shadow:** Depth effect for realistic appearance
- **Optional CRT effect:** Subtle scanlines for aesthetic consistency

**Note Content Format:**
```
┌─╮
│📌│  "This game made learning
└─┘   Hyprland fun instead of
      frustrating!"
      
      - Taylor
      3 hours ago
```

**Display Selection Algorithm:**

Show 15-25 notes selected based on:
1. **Recency:** Recent donations (last 7 days) weighted higher
2. **AI Quality Score:** Well-written, positive, helpful (0.7+)
3. **Length:** Ideal 50-150 characters (not too short or long)
4. **Diversity:** Variety of messages, avoid repetition
5. **Display rotation:** Cycle through approved notes every 5 minutes

**Animations:**
- **Page load:** Notes fade in sequentially with 50ms delay, slight drift down
- **Hover:** Scale up 1.05x, increase shadow depth
- **Refresh:** Every 5 minutes, fade out 2-3 notes and fade in new ones from pool

### Database Schema

**Turso (libSQL) Tables:**

Turso is a serverless SQLite database with HTTP API. It's simpler than Supabase for basic data storage (donations, notes, emails) and doesn't require authentication infrastructure.

**donations:**
```sql
CREATE TABLE donations (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
  stripe_payment_id TEXT UNIQUE NOT NULL,
  email TEXT NOT NULL,
  amount INTEGER NOT NULL, -- cents
  currency TEXT DEFAULT 'usd',
  donor_name TEXT,
  note TEXT, -- max 200 chars
  display_note INTEGER DEFAULT 1, -- SQLite uses INTEGER for boolean
  subscribe_updates INTEGER DEFAULT 1,
  status TEXT DEFAULT 'pending', -- pending|completed|refunded
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_donations_email ON donations(email);
CREATE INDEX idx_donations_created ON donations(created_at DESC);
```

**notes:**
```sql
CREATE TABLE notes (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
  donation_id TEXT REFERENCES donations(id),
  note_text TEXT NOT NULL,
  donor_name TEXT,
  moderation_status TEXT DEFAULT 'pending', -- pending|approved|rejected
  ai_score REAL, -- 0.00-1.00
  ai_reason TEXT,
  display_priority INTEGER DEFAULT 0, -- higher = better display
  displayed_count INTEGER DEFAULT 0,
  last_displayed TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  moderated_at TEXT,
  moderated_by TEXT -- 'ai' or admin
);

CREATE INDEX idx_notes_status ON notes(moderation_status);
CREATE INDEX idx_notes_priority ON notes(display_priority DESC);
```

**donor_emails:**
```sql
CREATE TABLE donor_emails (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
  email TEXT UNIQUE NOT NULL,
  total_donated INTEGER DEFAULT 0,
  donation_count INTEGER DEFAULT 1,
  subscribe_updates INTEGER DEFAULT 1,
  unsubscribe_token TEXT UNIQUE,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_donor_emails_email ON donor_emails(email);
```

**Turso Client Usage:**

```javascript
import { createClient } from '@libsql/client';

const turso = createClient({
  url: process.env.TURSO_DATABASE_URL,
  authToken: process.env.TURSO_AUTH_TOKEN
});

// Example insert
await turso.execute({
  sql: 'INSERT INTO donations (stripe_payment_id, email, amount, note) VALUES (?, ?, ?, ?)',
  args: [paymentId, email, amount, note]
});

// Example query
const result = await turso.execute({
  sql: 'SELECT * FROM notes WHERE moderation_status = ? ORDER BY display_priority DESC LIMIT ?',
  args: ['approved', 20]
});
```

### Stripe Integration

**Payment Flow:**

1. **Client:** User fills form → sends to backend (amount, email, note, preferences)
2. **Server:** Creates Stripe Checkout Session → returns session ID
3. **Client:** Redirects to Stripe Checkout hosted page
4. **User:** Completes payment with Stripe
5. **Webhook:** Stripe notifies backend of success → stores in database → queues moderation
6. **Success:** User returns with thank you message

**API Endpoints:**

**POST /api/donate:**
```javascript
const session = await stripe.checkout.sessions.create({
  payment_method_types: ['card'],
  line_items: [{
    price_data: {
      currency: 'usd',
      product_data: {
        name: 'Support Omarchy Defender',
        description: 'Help keep keyboard training free!'
      },
      unit_amount: amount // cents
    },
    quantity: 1
  }],
  mode: 'payment',
  success_url: `${BASE_URL}/success?session_id={CHECKOUT_SESSION_ID}`,
  cancel_url: `${BASE_URL}/`,
  metadata: { email, note, display_note, subscribe_updates }
});
```

**POST /api/webhook (Stripe):**
```javascript
// Verify signature
const event = stripe.webhooks.constructEvent(body, sig, WEBHOOK_SECRET);

if (event.type === 'checkout.session.completed') {
  const session = event.data.object;
  
  // Store donation in Turso
  const donationResult = await turso.execute({
    sql: `INSERT INTO donations 
          (stripe_payment_id, email, amount, note, display_note, subscribe_updates, status) 
          VALUES (?, ?, ?, ?, ?, ?, 'completed')
          RETURNING id`,
    args: [
      session.payment_intent,
      session.metadata.email,
      session.amount_total,
      session.metadata.note,
      session.metadata.display_note === 'true' ? 1 : 0,
      session.metadata.subscribe_updates === 'true' ? 1 : 0
    ]
  });
  
  const donationId = donationResult.rows[0].id;
  
  // Queue note for moderation if provided
  if (session.metadata.note && session.metadata.display_note === 'true') {
    await turso.execute({
      sql: `INSERT INTO notes (donation_id, note_text, moderation_status) VALUES (?, ?, 'pending')`,
      args: [donationId, session.metadata.note]
    });
  }
  
  // Send thank you email
  await sendThankYouEmail(session.metadata.email);
}
```

### AI-Powered Moderation

**Purpose:** Automatically filter spam, abuse, promotion, and low-quality content while approving genuine appreciation.

**Batch Process:**

Run periodically (every 15-30 minutes):

```bash
node scripts/moderate-notes.js
```

**Gemini Moderation Prompt:**
```
Analyze this thank-you note for a keyboard training game:

"${noteText}"

REJECT if contains:
- Spam or promotional content
- Abusive/offensive language
- Personal contact info (email, phone, social)
- URLs or links
- Feature requests or bug reports
- Off-topic content
- Overly generic ("Thanks!", "Good")

APPROVE if:
- Genuine appreciation or gratitude
- Shares positive experience
- Mentions specific learning outcomes
- Encouraging to others
- Well-written and thoughtful

Return JSON:
{
  "status": "approved" or "rejected",
  "score": 0.0-1.0,
  "reason": "brief explanation",
  "priority": 1-10
}
```

**Update Database:**
```javascript
await turso.execute({
  sql: `UPDATE notes 
        SET moderation_status = ?, ai_score = ?, ai_reason = ?, 
            display_priority = ?, moderated_at = datetime('now'), moderated_by = 'ai'
        WHERE id = ?`,
  args: [result.status, result.score, result.reason, result.priority, note.id]
});
```

**Examples:**

**Auto-Approve:**
- "This game finally made Hyprland click for me!"
- "Best keyboard training I've found. Worth it!"
- "Learned H/J/K/L in 20 minutes. Amazing!"

**Auto-Reject:**
- "Check out my YouTube!"
- "This sucks" (abusive)
- "Thanks" (too generic)
- "Contact me at..." (personal info)
- "Can you add mouse support?" (feature request)

### Email Communications

**Thank You Email:**
```
Subject: Thank you for supporting Omarchy Defender! ☕

Hi there!

Thank you for your support! Your contribution keeps Omarchy
Defender free and enables more keyboard productivity tools.

[If note approved]
Your note will appear on the site soon:
"[note text]"

Keep mastering those shortcuts!

Chad Jones
xSwarm.ai

---
Unsubscribe: [unsubscribe link]
```

**Project Updates Email:**
```
Subject: New features in Omarchy Defender 🎮

Hi keyboard warriors!

We've added Stage 2 with workspace navigation challenges!

[Update content]

Thank you for your support!

Chad

---
Unsubscribe: [unsubscribe link]
```

**Unsubscribe:**
- Unique token per email
- GET /unsubscribe?token=[token]
- Updates subscribe_updates = false
- One-click, no login required

### Privacy & Compliance

**GDPR Requirements:**
- **Explicit consent:** Checkboxes for email collection and note display
- **Right to access:** Provide data export
- **Right to erasure:** Support deletion requests
- **Clear purpose:** Explain email usage
- **Privacy policy:** Update with donation data handling

**Data Retention:**
- Donations: Keep indefinitely (accounting)
- Emails: Keep while subscribed, delete 30 days after unsubscribe
- Notes: Keep approved indefinitely, delete rejected after 90 days
- Payment info: Never stored (Stripe only)

### Implementation Phases

**Phase 1 (MVP):**
- Stripe integration
- Donation form (amount + email)
- Thank you email
- Basic email capture

**Phase 2 (Enhanced):**
- Note submission
- Database setup
- Sticky note display
- AI moderation

**Phase 3 (Polish):**
- Advanced display algorithm
- Email newsletter system
- Analytics dashboard
- Manual review interface

---

## Demo Script System & Promotional Videos

### Overview

The game should support a "demo mode" where it can automatically replay pre-scripted sequences combining commander voice lines with simulated user actions. This serves multiple purposes:

1. **Promotional videos**: Create funny, engaging gameplay videos for marketing
2. **Testing on Mac**: Avoid Super key issues during development  
3. **Consistent demos**: Replay exact sequences as assets improve
4. **Quality assurance**: Automated testing of game mechanics

### Command File Format

Create JSON files in `demos/` folder specifying complete gameplay sequences.

**Demo Script Example:**

```json
{
  "name": "Hilarious Rookie Training",
  "description": "Common mistakes and commander reactions",
  "duration_estimate": "90s",
  "events": [
    {
      "time": 0.0,
      "type": "commander_speak",
      "audio_id": "cmd_gnome_position",
      "variant": 0,
      "params": {"cell": 4}
    },
    {
      "time": 2.5,
      "type": "user_mouse_move",
      "x": 400,
      "y": 300
    },
    {
      "time": 3.0,
      "type": "user_mouse_click"
    },
    {
      "time": 3.1,
      "type": "game_mouse_penalty",
      "level": 1
    },
    {
      "time": 6.5,
      "type": "user_keypress",
      "keys": ["Super", "Enter"]
    },
    {
      "time": 7.0,
      "type": "commander_speak",
      "audio_id": "success_excellent",
      "variant": 1
    }
  ]
}
```

### Pre-Written Demo Scripts

**1. Perfect Run** (`demos/perfect-run.json`)
- Skilled keyboard-only gameplay
- No mouse touches, perfect combo chain
- ~45 seconds
- **Purpose**: Show mastery

**2. Rookie Mistakes** (`demos/rookie-mistakes.json`)
- Multiple mouse penalties
- Commander frustration
- Eventually succeeds
- ~60 seconds
- **Purpose**: Comedy, relatability

**3. Mouse Addict** (`demos/mouse-addict.json`)
- All 4 mouse penalty levels
- Commander furious
- Maximum comedy
- ~90 seconds
- **Purpose**: Viral potential

**4. Speedrun** (`demos/speedrun.json`)
- Lightning-fast actions
- High combos
- ~30 seconds
- **Purpose**: Show skill ceiling

**5. Full Showcase** (`demos/full-showcase.json`)
- All three stages
- Complete feature overview
- ~120 seconds
- **Purpose**: Reviews/press

### Implementation

**Playback Engine:**
- Load JSON script
- Execute events at timestamps
- Show "DEMO MODE" indicator
- Seeded random for consistency
- Recording-ready (stable framerate)

**Command-Line:**
```bash
npm run demo demos/rookie-mistakes.json
npm run demo --list
npm run demo --record demos/perfect-run.json
```

**Demo Editor Tool:**
- Visual timeline editor
- Record mode (capture actions)
- Edit/adjust timing
- Preview playback
- Export JSON scripts
- Location: `scripts/demo-editor/`

### Mac Testing Benefits

Since Mac uses Command instead of Super:
- Test without Super key
- Consistent automated testing  
- Cross-platform scripts
- CI/CD integration possible

### Promotional Video Workflow

1. **Script**: Write funny scenario
2. **Create**: Use demo editor
3. **Record**: Screen capture at 1080p/60fps
4. **Iterate**: Re-record as assets improve
5. **Distribute**: YouTube, Twitter, Reddit

**Video Concepts:**
- "Day 1 vs Day 30"
- "Things You'll Say to Your Mouse"
- "The Mouse Addict" (comedy)
- "Speedrun World Record"
- "Desktop Environment Users Be Like"

---

## Testing Requirements

### Functional Testing

**Splash Screen:**
- [ ] Static HTML renders instantly (<500ms)
- [ ] Logo visible immediately on page load
- [ ] All backstory text is in HTML (not images) for SEO
- [ ] About section accessible via tab or expand button
- [ ] About section text fully crawlable by search engines
- [ ] Animations hydrate after DOM ready
- [ ] Stamp animates at 2 seconds
- [ ] Backstory crawl starts at 3 seconds
- [ ] "Press SUPER+ENTER" prompt displays and pulses
- [ ] "Play Now" button initially disabled and dimmed
- [ ] Loading indicator shows "Loading game... X%"
- [ ] Progress updates as assets load
- [ ] "Play Now" button enables when gameReady flag set
- [ ] Mouse movement does NOT trigger warning on splash

**Play Now Button Mouse Warning:**
- [ ] Click on "Play Now" button does NOT start game
- [ ] Click triggers mouse warning modal
- [ ] Modal displays: "WE TOLD YOU NOT TO USE THE TRAITOROUS MOUSE!"
- [ ] Modal displays: "Press SUPER+ENTER to play"
- [ ] Screen flashes red on click
- [ ] Alarm sound plays
- [ ] Modal animates (shake/pulse)
- [ ] Modal auto-dismisses after 3-4 seconds
- [ ] ESC key dismisses modal
- [ ] Game still does NOT start after modal dismisses
- [ ] Only Super+Enter actually starts the game

**Game Start:**
- [ ] Super+Enter starts game (when gameReady true)
- [ ] Super+Enter shows "not ready" if gameReady false
- [ ] Command+Enter works on Mac
- [ ] Splash fades out smoothly
- [ ] Game canvas appears
- [ ] Stage 1 initializes correctly
- [ ] All assets already cached (no loading delay)

**Stage 1 - Terminal Warfare:**
- [ ] Grid displays 9 cells numbered 1-9
- [ ] Focus starts on cell 5 (center)
- [ ] Super+Enter spawns terminal in focused cell
- [ ] Super+Q closes terminal in focused cell
- [ ] Super+H/J/K/L navigates focus (vim-style)
- [ ] Super+Shift+H/J/K/L moves terminal
- [ ] Edge navigation blocked (can't go off grid)
- [ ] Gnome spawns with approach animation
- [ ] Commander voice plays at correct timing
- [ ] Hint text appears after 2-4s
- [ ] Urgent voice after 4-6s
- [ ] Angry voice after 6+s
- [ ] Challenge completes when condition met
- [ ] Combo counter increments
- [ ] Next challenge spawns after delay
- [ ] Stage completes after 20 challenges

**Mouse Contamination (Non-Fatal):**
- [ ] Mouse movement over canvas makes cursor erratic/jumpy
- [ ] Cursor jumps 50-200px randomly every 100-200ms
- [ ] Cursor becomes red X or hazard symbol
- [ ] First touch: Red flash + klaxon + voice warning
- [ ] First touch: -10% purity, combo reset, half points for next 3 actions
- [ ] Second touch: Double flash + buzzer + angry voice
- [ ] Second touch: -15% additional purity, next 5 actions half points
- [ ] Third touch: Triple flash + screen shake + furious voice
- [ ] Third touch: -20% additional purity, commander switches to angry mode
- [ ] Fourth+ touches: Max alarm + electrical effects + disgusted voice
- [ ] Fourth+ touches: -15% purity each, all points reduced 50% until purity >50%
- [ ] Game continues after all mouse touches (no game over)
- [ ] Purity recovers: +2% per keyboard action, +5% perfect challenge
- [ ] Visual contamination overlays at low purity (<50%, <25%, 0%)
- [ ] Can complete game at 0% purity (with penalties)
- [ ] Erratic cursor makes mouse unusable for clicking

**Audio:**
- [ ] All voice lines load without errors
- [ ] Correct voice plays for each event
- [ ] Multiple sounds can play simultaneously
- [ ] Volume levels balanced
- [ ] No audio cutting/clipping
- [ ] Music loops seamlessly
- [ ] Audio variants play randomly (no exact repeats back-to-back)
- [ ] Common phrases have 5+ variants
- [ ] Rare phrases have 2+ variants
- [ ] Mouse insults especially varied (8-10 variants per level)

**Demo Script System:**
- [ ] Demo mode loads JSON script files successfully
- [ ] Timeline executes events at correct timestamps
- [ ] Commander voice lines play on cue
- [ ] User actions (keypress, mouse) simulated correctly
- [ ] Game events (spawn, penalties) triggered correctly
- [ ] "DEMO MODE" indicator displays
- [ ] Demo playback consistent (seeded random)
- [ ] Can pause/resume demo playback
- [ ] Demo editor tool records actions with timestamps
- [ ] Demo editor exports valid JSON scripts
- [ ] All pre-written demos (perfect-run, rookie-mistakes, etc.) play correctly
- [ ] Demos suitable for screen recording (stable 60fps)
- [ ] Command-line interface works (npm run demo)
- [ ] Super key simulation works on Mac

**Performance:**
- [ ] Splash loads <500ms
- [ ] Game starts instantly (after assets loaded)
- [ ] 60 FPS maintained during gameplay
- [ ] No frame drops during animations
- [ ] Memory usage stable (<200MB)

### Browser Testing

**Desktop:**
- [ ] Chrome 120+ (Windows/Mac/Linux)
- [ ] Firefox 120+ (Windows/Mac/Linux)
- [ ] Safari 17+ (Mac)
- [ ] Edge 120+ (Windows)

**Mobile/Tablet (Desktop-Only Detection):**
- [ ] iOS Safari 17+ - Shows "Desktop Required" message
- [ ] Android Chrome 120+ - Shows "Desktop Required" message
- [ ] Device detection works correctly (isMobile check)
- [ ] Viewport width check works (<768px triggers mobile)
- [ ] Desktop-required message displays with CRT styling
- [ ] Message includes platform requirements and Omarchy link
- [ ] No gameplay accessible on mobile/tablet
- [ ] If game screen reached, shows incompatible device message

**Keyboard Support:**
- [ ] Mac: Command+Enter works
- [ ] Linux: Super+Enter works
- [ ] Windows: Win+Enter works (if possible)
- [ ] All vim keys (H/J/K/L) work
- [ ] Shift modifiers work

### SEO & Accessibility Testing

**Content Crawlability:**
- [ ] All splash screen text in HTML (not embedded in images)
- [ ] Backstory text readable by search engine crawlers
- [ ] About section content fully crawlable
- [ ] Semantic HTML structure (proper h1, h2, h3, p tags)
- [ ] Keywords naturally integrated in About section
- [ ] Heading hierarchy follows best practices
- [ ] Schema.org markup present for HowTo or Article type

**Image SEO Validation:**
- [ ] All image files use descriptive hyphenated names with "xswarm" prefix
- [ ] No generic names like "image1.png" or "sprite.png"
- [ ] xSwarm brand consistently present in all image filenames
- [ ] All images include dimension suffix (e.g., "-600w", "-64x64")
- [ ] WebP and fallback formats both have descriptive names with xswarm prefix
- [ ] Social sharing images have correct dimensions in filename
- [ ] Application window 9-slice images properly named and organized

**Branding Validation:**
- [ ] xSwarm mentioned in page title
- [ ] xSwarm in meta description
- [ ] Logo alt text includes "xSwarm"
- [ ] Social sharing images visually include xSwarm branding
- [ ] Image filenames consistently use "xswarm" prefix
- [ ] About section mentions xSwarm and provides context

**Alt Text Validation:**
- [ ] Every content image has descriptive alt text
- [ ] Alt text describes what's in the image, not just naming it
- [ ] Decorative images use empty alt=""
- [ ] Icons have appropriate aria-label when needed
- [ ] Logo alt text includes game name and xSwarm brand
- [ ] Window slice images have descriptive alt text

**Social Media Preview Testing:**
- [ ] Open Graph image loads correctly on Facebook/LinkedIn
- [ ] Twitter card displays with correct image and description
- [ ] Image URLs are absolute (not relative)
- [ ] Meta descriptions are compelling and keyword-rich
- [ ] Title tags are optimized for search and include xSwarm brand

**Keyword Optimization:**
- [ ] Target keywords present in About section
- [ ] Pain point keywords addressed ("frustrated with Hyprland")
- [ ] Workflow keywords included ("keyboard shortcuts", "tiling window manager")
- [ ] Keywords in meta description
- [ ] Keywords in page title and headers
- [ ] Natural keyword density (not stuffed)

**Accessibility Audit:**
- [ ] Color contrast meets WCAG AA (4.5:1 minimum)
- [ ] All interactive elements keyboard accessible
- [ ] Focus indicators visible and clear
- [ ] Screen reader announces game state appropriately
- [ ] No flashing content that could trigger seizures
- [ ] Text remains readable when zoomed to 200%
- [ ] About section content accessible to screen readers

**Structured Data:**
- [ ] Schema.org markup present and valid
- [ ] VideoGame schema includes all required properties
- [ ] HowTo or Article schema for About section
- [ ] JSON-LD format valid (test with Google Rich Results)

### Donation System Testing

**Support Button & Modal:**
- [ ] Support button displays in splash screen
- [ ] Button styled with CRT aesthetic (green glow, pulse)
- [ ] Clicking button opens donation modal
- [ ] Modal displays all form fields correctly
- [ ] Amount buttons ($3, $5, $10, Custom) work
- [ ] Custom amount validates (min $1, max $500)
- [ ] Email validation works (format checking)
- [ ] Note textarea enforces 200 character limit
- [ ] Character counter updates in real-time
- [ ] Display note checkbox toggles correctly
- [ ] Updates checkbox toggles correctly
- [ ] Privacy statement visible and readable
- [ ] ESC key closes modal
- [ ] Click outside modal closes modal

**Payment Flow:**
- [ ] Form submission creates Stripe Checkout session
- [ ] Redirect to Stripe Checkout works
- [ ] Can complete test payment successfully
- [ ] Payment completion redirects back to game
- [ ] Thank you message displays after payment
- [ ] Webhook receives Stripe checkout.session.completed events
- [ ] Webhook signature verification works
- [ ] Donation data stored in Supabase correctly
- [ ] Thank you email sent successfully
- [ ] Email added to donor_emails table
- [ ] Email list updated if opted in

**Sticky Notes Display:**
- [ ] Approved notes load from database
- [ ] Notes display on left and right sides
- [ ] Notes have random rotation (-5° to +5°)
- [ ] Notes have varied sizes (150-200px)
- [ ] No significant overlap between notes
- [ ] Pin/tack graphic displays at top
- [ ] Handwriting font renders correctly
- [ ] Drop shadow provides depth
- [ ] Notes fade in sequentially on page load
- [ ] Hover effect (scale 1.05x, shadow increase) works
- [ ] Notes cycle/refresh every 5 minutes
- [ ] Mobile responsive (fewer notes, adjusted size/position)
- [ ] Only moderation_status='approved' notes display
- [ ] Display respects display_priority ordering

**AI Moderation:**
- [ ] Moderation script runs without errors
- [ ] Pending notes fetched from database
- [ ] Gemini API connection works
- [ ] Moderation prompt generates valid responses
- [ ] JSON response parsed correctly
- [ ] Notes table updated with moderation results
- [ ] Approved notes have status='approved'
- [ ] Rejected notes have status='rejected'
- [ ] AI score and reason stored
- [ ] Display priority calculated correctly
- [ ] High-value donation rejections flagged
- [ ] Spam/abuse detected and rejected
- [ ] Genuine appreciation approved

**Email System:**
- [ ] Thank you email template renders correctly
- [ ] Email sent immediately after donation
- [ ] Unsubscribe link works
- [ ] Unsubscribe updates database
- [ ] Unsubscribe confirmation page displays
- [ ] Project update emails send to opted-in users only
- [ ] Email list respects subscribe_updates flag

### PWA Testing

- [ ] manifest.json valid
- [ ] Icons display correctly
- [ ] "Install app" prompt appears
- [ ] Installs on desktop (Chrome/Edge)
- [ ] Installs on iOS (Add to Home Screen)
- [ ] Installs on Android
- [ ] Launches in standalone mode
- [ ] Works offline after initial load
- [ ] Updates check in background

### Performance Benchmarks

**Lighthouse Audit:**
- Performance: >95
- Accessibility: >95 (must validate alt text, color contrast)
- Best Practices: >95
- SEO: >95 (must validate meta tags, image names, structured data)
- PWA: Pass all checks

**Core Web Vitals:**
- LCP (Largest Contentful Paint): <2.5s
- FID (First Input Delay): <100ms
- CLS (Cumulative Layout Shift): <0.1

**Asset Optimization Validation:**
- [ ] All images under 100KB (full-screen) or 20KB (sprites)
- [ ] WebP format used with fallbacks
- [ ] Images include width/height to prevent layout shift
- [ ] Lazy loading on below-fold images
- [ ] Critical images use preload hints

---

## Success Metrics

### Technical Metrics

**Load Performance:**
- First Contentful Paint: <500ms (target: <300ms)
- Time to Interactive (splash): <1s
- Game start (cached): <100ms
- Asset load complete: <10s

**Reliability:**
- Uptime: >99.9%
- Error rate: <0.1%
- Service worker activation: >95%

**Engagement:**
- Average session duration: >5 minutes
- Stage 1 completion rate: >60%
- Return visitor rate: >30%
- Offline play sessions: >20%

### User Metrics

**Adoption:**
- Week 1: 100+ unique players
- Month 1: 500+ unique players  
- PWA installs: >10% of users

**Engagement:**
- Play Now button clicks: Track how many fall for the trap (expect >50%)
- Super+Enter after button trap: Measure if users learn the lesson
- Average session duration: >5 minutes
- Stage 1 completion rate: >60%
- Return visitor rate: >30%
- Offline play sessions: >20%

**Skill Development:**
- Average time to Stage 1 complete: <10 minutes
- Hotkey accuracy (Stage 1): >80% by completion
- Mouse contamination rate during gameplay: <2 touches per session (excluding initial button trap)

**Virality:**
- Social shares: >10% of players
- QR code scans: Tracked via referral parameter
- Reddit/Discord mentions: Monitor manually

**Donations & Community:**
- Donation conversion rate: >1% of players (5+ donations per 500 players)
- Average donation amount: $5-10
- Note submission rate: >50% of donors leave notes
- Note approval rate: >80% of submitted notes approved by AI
- Note display quality: AI score average >0.75
- Email opt-in rate: >70% of donors
- Unsubscribe rate: <5% of email list
- Sticky note engagement: Track hover interactions

---

## Initial Setup Deliverables

Before beginning full development, the senior developer must create these foundational files for Chad to review and configure:

### 1. .env.example File

Create a comprehensive .env.example template with:
- All required API keys listed with empty values
- Detailed comments explaining what each key is for
- Direct URLs to where credentials can be obtained
- Notes about which keys are needed immediately vs Phase 2
- Permission/scope requirements for each service

Chad will copy this to .env and fill in actual credentials before development continues.

### 2. config.json File

Create a config.json with well-researched defaults:
- Test and select the best ElevenLabs voice for the military commander
- Provide 2-3 voice options with descriptions for Chad to audition
- Include all game configuration with sensible defaults
- Cloudflare settings (project names, bucket names)
- Asset path configurations for development vs production
- All timing thresholds and difficulty settings

This file should be production-ready with good defaults. Chad can modify as needed.

### 3. Asset Naming Manifest

Create a document or spreadsheet listing:
- All required image assets with SEO-friendly filenames (including "xswarm" prefix)
- Suggested alt text for each image (mentioning xSwarm brand where appropriate)
- Required dimensions for each image
- Social sharing image specifications
- Icon requirements for PWA
- Application window screenshots needed (Terminal, Browser, Email, Calendar)
- 9-slice cutting specifications for each window type

**Important:** Every image filename must include the "xswarm" prefix for consistent branding and SEO optimization. For example: `xswarm-gnome-riding-mouse-sprite-64x64.png` not just `gnome-riding-mouse-sprite-64x64.png`.

This ensures all assets follow SEO best practices and promote the xSwarm brand from the start.

### 4. About Section Content Framework

Create an HTML structure for the About section with:
- Semantic HTML tags (h2, h3, p, ul, li)
- Placeholder content for the 5 sections (Problem, Solution, Skills, Audience, About xSwarm)
- SEO-optimized header structure
- Schema.org markup (HowTo or Article type)
- Space for target keywords

Chad will provide final marketing copy to fill in the placeholders, but the structure should be SEO-ready with proper semantic HTML.

### 5. Development Utilities

**Screenshot Scraper Script:**
Create `scripts/scrape-screenshots.js` that:
- Scrapes Omarchy documentation for application screenshots
- Downloads and organizes images by application
- Reports missing applications
- Provides fallback suggestions for manual screenshot

**Asset Management Utility:**
Create `scripts/asset-manager/` with:

**Image Assets (index.html):**
- Simple Express server (server.js)
- HTML frontend for browsing all image assets
- Integration with Google Gemini 2.0 Flash API for image analysis
- Chat interface for each asset to request improvements
- Upload/replace functionality
- Asset validation and comparison features

**Audio Assets (audio.html):**
- Browser for all 200+ voice lines organized by category
- Audio playback controls with waveform visualization
- Display of script text and generation parameters
- Gemini chat for analyzing voice performance
- One-click regeneration via ElevenLabs API
- Parameter adjustment controls (stability, similarity, style, speed)
- A/B comparison between versions
- Batch operations for categories
- Status tracking (generated/needs_review/approved)
- Export and R2 upload functionality

**Server Integration (server.js):**
- Express server with both Gemini and ElevenLabs API integration
- Routes for image and audio asset management
- File system operations for local development
- API proxying to avoid CORS issues
- Manifest generation and updates

The asset manager helps Chad review and validate all game assets using AI capabilities. Image assets use Gemini vision for validation, audio assets use both Gemini for analysis and ElevenLabs for regeneration. Essential for Mac development without Omarchy installed.

**Demo Script System:**
Create `scripts/demo-editor/` with:
- Visual timeline editor for creating demo scripts
- Record mode to capture gameplay actions with timestamps
- Edit/adjust event timing on timeline
- Preview playback functionality
- Export to JSON script format
- Pre-written demo templates (perfect-run, rookie-mistakes, mouse-addict, speedrun)
- Command-line interface: `npm run demo <script.json>`

The demo system enables:
1. **Promotional videos** - Create funny, scripted gameplay for marketing
2. **Mac testing** - Simulate Super key presses for development on Mac
3. **Consistent demos** - Replay exact sequences as assets improve
4. **Automated testing** - QA validation through scripted playback

**Review Process:** Chad will review these files, fill in .env with actual credentials (including GEMINI_API_KEY and ELEVENLABS_API_KEY), approve config.json defaults, run screenshot scraper, use asset manager to validate all visual assets, generate and review all audio assets, test demo script system, create initial promotional demo scripts, provide About section marketing copy, and coordinate any missing application screenshots before full development begins.

---

## Open Questions & Decisions Needed

1. **ElevenLabs Voice Selection:**
   - Senior developer will research and test voice options
   - Provide top 3 recommendations with sample audio in config.json
   - Chad will test each voice option using audio asset manager
   - Select final voice by generating sample lines and reviewing in audio manager
   - Voice can be changed per-file if needed for variety

2. **Audio Generation and Review Workflow:**
   - Senior developer creates batch generation script
   - Script generates all 200+ voice lines from script manifest
   - Chad uses audio asset manager to review each voice line
   - For unsatisfactory audio:
     * Chat with Gemini about issues
     * Adjust parameters (stability, speed, tags)
     * Regenerate with one click
     * A/B compare versions
   - Mark approved audio for export
   - Batch regenerate entire categories if needed
   - Export approved assets to R2

2. **Background Music Style:**
   - Recommendation: 8-bit chiptune for retro aesthetic consistency
   - Chad to confirm or request alternative style

3. **PWA Icon Design:**
   - Recommendation: Custom icon featuring keyboard and/or gnome-on-mouse theme
   - Senior developer to provide icon design or Chad can commission separately

4. **Cloudflare R2 Public URL Format:**
   - Need to confirm exact public URL structure for R2 bucket
   - Format should be: https://r2.xswarm.ai/omarchy-defender-assets/ (or custom domain)
   - Chad to provide final URL for config.json

5. **Social Media Preview Images:**
   - Who will create the social sharing images (1200x630 for OG, 800x418 for Twitter)?
   - Senior developer can create with game screenshots, or Chad can provide custom graphics

6. **Analytics Tracking:**
   - Confirm use of Cloudflare Web Analytics (privacy-friendly, no cookies)
   - Chad to provide tracking token if using this feature

7. **Application Screenshots Workflow:**
   - Senior developer creates screenshot scraper script
   - Script attempts to download screenshots from Omarchy docs (learn.omacom.io)
   - Chad runs scraper to collect available screenshots
   - Chad uses asset manager utility to review all assets with Gemini AI
   - For missing screenshots, Chad coordinates:
     * Option A: Chad takes screenshots on an Omarchy system (if available)
     * Option B: Senior developer installs Omarchy to capture screenshots
     * Option C: Use placeholders and refine later
   - Asset manager validates all screenshots before 9-slice cutting
   - Gemini AI helps identify issues and suggest improvements

8. **About Section Marketing Copy:**
   - Senior developer provides HTML structure and SEO framework
   - Chad will write final marketing copy targeting frustrated Hyprland learners
   - Copy should naturally integrate target keywords without stuffing

9. **Gemini API Key:**
   - Chad to obtain Google Gemini API key from https://aistudio.google.com/app/apikey
   - Add to .env for asset manager development utility
   - Used only for local development, not deployed to production

10. **Stripe Payment Setup:**
   - Chad to create/configure Stripe account at https://dashboard.stripe.com
   - Obtain publishable key, secret key, and webhook secret
   - Add to .env for donation processing
   - Create product in Stripe: "Support Omarchy Defender"
   - Configure webhook endpoint for checkout.session.completed events
   - Test with Stripe test mode before production

11. **Donation Feature Rollout:**
   - Phase 1 (MVP): Basic Stripe integration with email capture
   - Phase 2: Add note submission and sticky note display
   - Phase 3: Implement AI moderation and email system
   - Chad to decide rollout timeline

## Appendices

### A. Complete Hotkey Reference

**Stage 1 Hotkeys:**

- Super+Enter: Spawn terminal in focused cell
- Super+Q: Close focused window
- Super+H: Focus left
- Super+J: Focus down
- Super+K: Focus up
- Super+L: Focus right
- Super+Shift+H: Move window left
- Super+Shift+J: Move window down
- Super+Shift+K: Move window up
- Super+Shift+L: Move window right
- Super+Shift+Arrow: Swap windows (alternative method)
- Super+F: Fullscreen toggle
- Super+Space: Float/tile toggle

**Stage 2 Hotkeys (Future):**

- Super+1 through Super+9: Switch to workspace 1-9
- Super+Shift+1 through Super+Shift+9: Move window to workspace 1-9
- Super+Comma: Previous monitor
- Super+Period: Next monitor

**Stage 3 Hotkeys (Future):**

- Super+Return: Terminal (already learned in Stage 1)
- Super+Shift+B: Browser
- Super+Shift+Alt+B: Browser (private/incognito)
- Super+Shift+F: File manager
- Super+Shift+T: Activity monitor (btop)
- Super+Shift+M: Music (Spotify)
- Super+Shift+/: Password manager (1Password)
- Super+Shift+N: Neovim editor
- Super+Shift+E: Email (HEY)
- Super+Shift+C: Calendar (HEY)
- Super+Shift+A: AI (ChatGPT)
- Super+Shift+X: X (formerly Twitter)
- Super+Shift+O: Obsidian
- Super+Shift+G: Messenger (Signal)
- Super+Shift+Ctrl+G: Messenger (WhatsApp)
- Super+Shift+Alt+G: Messenger (Google)
- Super+Shift+D: Docker (LazyDocker)
- Super+Space: App launcher (Walker)
- Super+Alt+Space: Omarchy menu
- Ctrl+Super+S: Share menu (LocalSend)

### B. File Naming Conventions

**Audio Files:**

Use the format: category underscore action underscore variant dot mp3

Examples include:
- cmd_spawn_terminal.mp3
- hint_super_enter.mp3
- urgent_super_q.mp3
- angry_super_enter.mp3
- success_excellent.mp3
- mouse_detected_1.mp3
- joke_sluggish_mouse.mp3

**Image Files:**

Use the format: xswarm-entity-variant-size dot extension

All image files must include the "xswarm" prefix for branding and SEO.

Examples include:
- xswarm-omarchy-defender-logo-600w.webp and xswarm-omarchy-defender-logo-600w.png
- xswarm-defender-rubber-stamp-400w.webp
- xswarm-gnome-cavalry-riding-mouse-64x64.png
- xswarm-terminal-window-icon-128x128.png
- xswarm-keyboard-purity-badge-256w.png
- xswarm-workspace-grid-overlay.png

### C. Git Configuration

**`.gitignore` Contents:**

The following should be excluded from git:

```
# Build output
build/

# Environment secrets
.env

# Assets (too large for git, stored on R2)
assets/audio/
assets/images/

# OS files
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/

# Logs
*.log
npm-debug.log*

# Temporary files
*.tmp
*.temp
```

**Files that SHOULD be committed:**
- All files in `src/` folder (index.html, CSS, JS)
- Config files in root (.env.example, config.json, manifest.json)
- Build scripts in `scripts/` folder
- Documentation (README.md)
- SEO files (robots.txt, sitemap.xml)

**Files that should NOT be committed:**
- `build/` folder (generated during build process)
- `.env` file (contains secrets)
- `assets/` folder (stored on R2, too large for git)

### Git Workflow

The project exists as a subfolder within the xswarm-boss parent repository:
- Path: `~/Dropbox/Public/JS/Projects/xswarm-boss/omarchy-defender/`
- Can be tracked in parent repo or initialized as separate git repository
- If separate repo, create at: https://github.com/chadananda/omarchy-defender

### D. Git Commit Conventions

Follow standard conventional commit format with prefixes:
- feat: for new features
- fix: for bug fixes
- perf: for performance improvements
- docs: for documentation
- style: for styling changes
- refactor: for code restructuring
- test: for adding tests
- chore: for build/tooling updates

Examples: "feat: Add Stage 1 grid system" or "fix: Mouse detection triggering on trackpad"

---

**END OF PRD**

**Document Owner:** Chad Jones (chadananda@gmail.com)  
**Last Updated:** December 4, 2024  
**Version:** 1.0.0  
**Status:** Ready for Implementation
