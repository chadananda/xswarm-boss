# Viral Feature Architecture - xswarm Voice Assistant

## Vision: The Most Addictive, Customizable AI Assistant TUI

**Core Philosophy:**
- **Free & Viral**: Base features are powerful and free (FOSS libraries)
- **Endlessly Customizable**: "Ricing" culture meets AI assistance
- **Community-Driven**: Plugin marketplace, theme sharing, ecosystem growth
- **Privacy-First**: Local-first with optional cloud (BYOK)
- **Modern & High-Attitude**: Cyberpunk aesthetics, personality-rich

## Architecture Overview

```
xswarm/
├── Core Engine (Free, Open Source)
│   ├── Voice Assistant (Moshi + Personas)
│   ├── Plugin System (Dynamic loading, sandboxed)
│   ├── Theme Engine (Persona themes + Pywal)
│   └── Local AI (Whisper, ChromaDB, local models)
│
├── Built-in Plugins (Free Base Features)
│   ├── File Search (lightning-fast local search)
│   ├── Note Search (Whoosh full-text)
│   ├── Task Manager (Kanban board, SQLite)
│   ├── System Monitor (CPU, GPU, battery)
│   ├── Web Research (BeautifulSoup scraper)
│   └── Quick Actions (clipboard, screenshots)
│
├── Premium Plugins (BYOK or Paid)
│   ├── Email Suite (Gmail API, SMTP)
│   ├── Calendar Sync (Google Calendar API)
│   ├── Meeting Transcriber (Whisper + GPT summary)
│   ├── Workflow Automator (APScheduler, Celery)
│   └── Cloud Sync (E2E encrypted backups)
│
└── Community Features (Viral Growth)
    ├── Theme Gallery (share/download themes)
    ├── Plugin Marketplace (discover/install plugins)
    ├── Rice Showcase (screenshot sharing)
    └── Assistant Personalities (custom personas)
```

---

## Feature Prioritization for Viral Growth

### 🔥 Phase 1: Foundation (Week 1-2) - "Make it Shareable"

**1. Plugin System Architecture**
- Dynamic plugin loading from `~/.config/xswarm/plugins/`
- Plugin manifest with dependencies, permissions
- Hot-reload support for development
- Sandboxed execution (import restrictions)
- Plugin API for TUI integration

**Why Viral:** Enables community contributions, exponential feature growth

**Implementation:**
```python
# plugins/base.py
class PluginBase:
    name: str
    version: str
    author: str
    dependencies: List[str]
    permissions: List[str]  # ["filesystem", "network", "clipboard"]

    def on_load(self): pass
    def on_command(self, cmd: str): pass
    def get_widget(self) -> Optional[Widget]: pass
```

**2. Theme Gallery & Sharing**
- Built-in theme browser (Textual widget)
- One-click theme download from community repo
- Theme preview before applying
- "Share my rice" - upload screenshots + theme
- GitHub-backed theme repository

**Why Viral:** Ricing culture = sharing culture. Users will show off themes on r/unixporn

**Implementation:**
- `plugins/theme_gallery/` - Browse/download/upload
- GitHub repo: `xswarm-themes` with CI/CD for validation
- Theme rating/starring system

**3. File Search Plugin** (Quick Win)
- Lightning-fast local file search
- Preview in TUI (text files, code, images as ASCII)
- Fuzzy matching (fzf-style)
- Recent files, frecency algorithm

**Why Viral:** Immediately useful, replaces `find` + `grep`

**Implementation:**
- `whoosh` for indexing
- `textual` DataTable for results
- Hotkey: `Ctrl+P` (like VS Code)

---

### 🚀 Phase 2: Productivity Powerhouse (Week 3-4) - "Make it Indispensable"

**4. Task Management (Kanban Board)**
- Visual Kanban board widget
- SQLite backend
- Drag-and-drop (Textual DragDrop)
- Tags, priorities, due dates
- Smart inbox (voice-to-task)

**Why Viral:** Visually impressive, replaces Trello/Notion for CLI users

**Implementation:**
```python
# plugins/tasks/
├── kanban.py         # Kanban widget
├── storage.py        # SQLite CRUD
└── voice_parser.py   # "Add task: fix bug" -> task creation
```

**5. Note Search & Context Memory**
- Full-text search across notes/docs
- Semantic search (ChromaDB embeddings)
- Automatic context tagging
- "Remember this for later"

**Why Viral:** Second brain functionality, competes with Obsidian

**Implementation:**
- `whoosh` for full-text
- `chromadb` for semantic
- Markdown preview widget

**6. Pywal Theme Integration**
- Auto-detect Pywal colors from `~/.cache/wal/colors.json`
- Real-time theme sync on wallpaper change
- Generate persona theme from Pywal palette

**Why Viral:** Linux ricing community will LOVE this (r/unixporn goldmine)

**Implementation:**
```python
# assistant/dashboard/pywal.py
def load_pywal_colors() -> Optional[Dict[str, str]]:
    pywal_cache = Path.home() / ".cache" / "wal" / "colors.json"
    if pywal_cache.exists():
        with open(pywal_cache) as f:
            colors = json.load(f)
        return {
            "primary": colors["colors"]["color4"],    # Blue
            "secondary": colors["colors"]["color5"],  # Magenta
            "accent": colors["colors"]["color2"],     # Green
            "background": colors["special"]["background"],
            "text": colors["special"]["foreground"],
        }
```

---

### 💎 Phase 3: Premium Features (Week 5-6) - "Make it Revenue-Ready"

**7. Email Automation Suite** (Premium/BYOK)
- Unified inbox widget
- Draft assistant (voice dictation)
- Smart filters and auto-categorization
- Gmail API + SMTP fallback

**Why Premium:** Email is business-critical, worth paying for

**Implementation:**
- Free: SMTP send-only
- Premium: Full Gmail API integration with BYOK

**8. Calendar & Scheduling** (Premium/BYOK)
- Calendar widget (month/week/day views)
- Event creation via voice
- Google Calendar sync
- Smart rescheduling

**Why Premium:** Calendar sync is high-value business feature

**9. Meeting Transcriber** (Premium/BYOK)
- Record meetings (Whisper local transcription)
- AI summary generation
- Action item extraction
- Export to Markdown

**Why Premium:** Transcription + summary = premium workflow

---

### 🌟 Phase 4: Community & Ecosystem (Ongoing) - "Make it Unstoppable"

**10. Plugin Marketplace**
- Discover plugins in TUI
- One-click install
- Plugin ratings & reviews
- Developer monetization (premium plugins)

**Why Viral:** App store = ecosystem lock-in

**11. Rice Showcase**
- Share screenshots + theme + plugins
- Upvote/comment system
- "Setup of the Week" featured
- Direct theme installation from showcase

**Why Viral:** Instagram for TUIs - viral loop

**12. Workflow Automation**
- Visual workflow builder
- APScheduler + Celery backend
- Trigger: time, file change, voice command, API webhook
- Actions: run script, send email, create task, etc.

**Why Premium:** Automation = power users = willing to pay

---

## Technical Architecture

### Plugin System Design

```python
# assistant/plugins/manager.py

class PluginManager:
    """
    Manages plugin lifecycle and integration with TUI.
    """

    def __init__(self, plugin_dir: Path):
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, Plugin] = {}
        self.widgets: Dict[str, Widget] = {}

    def discover_plugins(self) -> List[str]:
        """Scan plugin directory for valid plugins"""
        # Look for:
        # ~/.config/xswarm/plugins/
        #   plugin-name/
        #     manifest.yaml
        #     plugin.py

    def load_plugin(self, name: str) -> bool:
        """Load plugin with sandboxing"""
        # 1. Parse manifest.yaml
        # 2. Check dependencies
        # 3. Verify permissions
        # 4. Import plugin.py (with restrictions)
        # 5. Call on_load()
        # 6. Register commands/widgets

    def get_plugin_widget(self, plugin_name: str) -> Optional[Widget]:
        """Get Textual widget from plugin"""

    def execute_command(self, plugin_name: str, cmd: str, args: dict):
        """Execute plugin command"""
```

### Plugin Manifest Format

```yaml
# manifest.yaml
name: "file-search"
version: "1.0.0"
author: "xswarm team"
description: "Lightning-fast file search with preview"
license: "MIT"

# Dependencies (pip packages)
dependencies:
  - whoosh>=2.7.4
  - rich>=13.0.0

# Permissions required
permissions:
  - filesystem.read     # Read any file
  - filesystem.write    # Write to plugin cache
  # - network           # (not needed for this plugin)
  # - clipboard         # (not needed)

# Entry point
entry: "plugin.py"
widget_class: "FileSearchWidget"

# Commands exposed to voice assistant
commands:
  - name: "search files"
    handler: "handle_search"
    description: "Search for files by name or content"

  - name: "recent files"
    handler: "handle_recent"
    description: "Show recently accessed files"

# Settings (user-configurable)
settings:
  index_paths:
    type: list
    default: ["~/Documents", "~/Projects"]
    description: "Directories to index for search"

  max_results:
    type: integer
    default: 50
    description: "Maximum search results to show"
```

### Theme Gallery Architecture

```python
# plugins/theme_gallery/gallery.py

class ThemeGallery:
    """
    Community theme browser and installer.
    """

    THEME_REPO = "https://raw.githubusercontent.com/xswarm/themes/main/index.json"

    def fetch_themes(self) -> List[ThemeMetadata]:
        """Fetch list of community themes"""

    def preview_theme(self, theme_id: str):
        """Show live preview of theme"""

    def install_theme(self, theme_id: str):
        """Download and install theme"""

    def upload_theme(self, theme_path: Path, screenshot: Path):
        """Share theme with community (via PR to GitHub)"""
```

---

## Viral Growth Loops

### Loop 1: Ricing Culture
1. User customizes xswarm with cool theme
2. User shares screenshot on r/unixporn / r/linux
3. Comments ask "What TUI is that?"
4. User shares theme file or link to gallery
5. New users install, customize, share → repeat

**Accelerators:**
- "Share my rice" button generates Reddit post template
- Theme gallery with direct links
- Weekly "Rice of the Week" contest

### Loop 2: Plugin Ecosystem
1. Developer builds useful plugin
2. Shares in marketplace
3. Users discover and install
4. Users become dependent on plugin
5. More users = more developers → repeat

**Accelerators:**
- Plugin revenue sharing (premium plugins)
- Featured plugins showcase
- Plugin starter templates

### Loop 3: Voice Persona Personality
1. User tries JARVIS/GLaDOS/NEON personas
2. Falls in love with personality
3. Shares funny/cool interactions
4. "Check out what GLaDOS said to me!"
5. Others want to try → repeat

**Accelerators:**
- Custom persona builder
- Persona marketplace
- "Best of" personality moments

---

## Base (Free) vs Premium Features

### ✅ Base Features (Free Forever)
- All voice assistant functionality
- All persona themes (JARVIS, GLaDOS, NEON, etc.)
- File search
- Note search (local)
- Task manager (local)
- System monitoring
- Web scraping/research
- Theme customization
- Plugin system
- Community theme gallery
- Pywal integration
- Local transcription (Whisper)

### 💎 Premium Features (BYOK or Paid)
- Gmail API integration (full inbox management)
- Google Calendar sync
- Cloud backup (E2E encrypted)
- Premium AI models (GPT-4, Claude)
- Priority support
- Commercial workflow automation
- Team features (shared plugins, themes)

**Philosophy:** "Give away the sizzle, sell the steak"
- Base version is so good users want to share it
- Premium features are nice-to-haves for power users and businesses

---

## Implementation Roadmap

### Sprint 1: Plugin Foundation (Week 1)
- [ ] Plugin system architecture
- [ ] Plugin manager implementation
- [ ] Manifest parser and loader
- [ ] Permission system (filesystem, network, clipboard)
- [ ] Hot-reload support
- [ ] Example plugin: "hello-world"

### Sprint 2: Viral Features (Week 2)
- [ ] Theme gallery plugin
- [ ] File search plugin
- [ ] Pywal integration
- [ ] "Share my rice" feature
- [ ] GitHub theme repository setup

### Sprint 3: Productivity (Week 3)
- [ ] Task manager plugin (Kanban board)
- [ ] Note search plugin
- [ ] Quick actions plugin (clipboard, screenshots)
- [ ] Voice-to-task parser

### Sprint 4: Polish & Launch (Week 4)
- [ ] Plugin marketplace UI
- [ ] Documentation for plugin developers
- [ ] Rice showcase website
- [ ] Reddit/HackerNews launch campaign
- [ ] Video demo (voice + TUI)

### Sprint 5-6: Premium Features
- [ ] Email plugin (BYOK Gmail API)
- [ ] Calendar plugin (BYOK Google Calendar)
- [ ] Meeting transcriber
- [ ] Workflow automation

---

## Success Metrics

### Viral Growth Indicators
- **GitHub Stars:** 1000+ in first month
- **Theme Gallery:** 50+ community themes
- **Plugin Count:** 20+ plugins in marketplace
- **Reddit Mentions:** 10+ posts on r/unixporn
- **Install Base:** 5000+ active users

### Engagement Metrics
- **Daily Active Users:** 60%+ retention
- **Plugin Installs:** Avg 3+ plugins per user
- **Theme Changes:** Avg 5+ themes tried per user
- **Voice Commands:** 10+ per day per user

### Revenue Metrics (Premium)
- **Conversion Rate:** 5-10% to premium
- **MRR Growth:** 20% month-over-month
- **Churn Rate:** <5% monthly

---

## Technical Debt Prevention

### Plugin System Safety
- **Sandboxing:** Restrict imports (no `os.system`, `subprocess` without permission)
- **Rate Limiting:** Prevent plugins from hogging resources
- **Crash Isolation:** Plugin crash shouldn't kill main app
- **Audit Logging:** Track plugin actions for security

### Performance
- **Lazy Loading:** Load plugins on demand
- **Background Indexing:** File/note search indexing in background
- **Cache Management:** Smart caching for theme previews, search results
- **Memory Limits:** Per-plugin memory caps

### Maintainability
- **Plugin API Versioning:** Semantic versioning, deprecation warnings
- **Automated Testing:** Plugin validation CI/CD
- **Documentation:** Auto-generated API docs from code
- **Community Governance:** Plugin review process

---

## Launch Strategy

### Pre-Launch (2 Weeks)
1. Build core plugin system
2. Create 3-5 essential plugins
3. Seed theme gallery with 10 themes
4. Create demo video
5. Write launch blog post

### Launch Day
1. Post to r/unixporn, r/commandline, r/python
2. Submit to HackerNews
3. Tweet with demo video
4. Product Hunt submission
5. Email existing xSwarm users

### Post-Launch (Ongoing)
1. Daily engagement on Reddit/HN comments
2. Weekly "Plugin of the Week" showcase
3. Monthly "Rice of the Month" contest
4. Quarterly feature releases
5. Annual conference/meetup

---

## Competitive Advantages

vs **Siri/Alexa/Google Assistant:**
- Privacy-first (local AI)
- Endlessly customizable
- Open source
- Terminal-native (for developers)

vs **Notion/Obsidian:**
- Voice-first interface
- Integrated with system
- Faster than web app
- Plugin ecosystem

vs **Textual Apps:**
- Built-in voice assistant
- Persona system (personality)
- Theme marketplace
- Community ecosystem

---

## Community Building

### Discord Server
- #general - General discussion
- #themes - Theme sharing
- #plugins - Plugin development
- #support - User help
- #showcase - Rice screenshots

### GitHub Organization
- `xswarm/assistant` - Main repo
- `xswarm/themes` - Community themes
- `xswarm/plugins` - Official plugins
- `xswarm/docs` - Documentation
- `xswarm/showcase` - Rice screenshots

### Documentation Site
- Getting Started
- Theme Customization Guide
- Plugin Development Tutorial
- API Reference
- Showcase Gallery

---

## Revenue Model (Optional)

### Free Tier (Forever)
- All base features
- Community support
- Unlimited plugins
- Unlimited themes

### Pro Tier ($9/month or $90/year)
- Cloud sync (E2E encrypted)
- Premium AI models
- Priority support
- Early access to features
- Commercial use license

### Enterprise Tier ($29/user/month)
- Team features
- Shared plugins/themes
- SSO integration
- Dedicated support
- Custom deployment

**Note:** Revenue is OPTIONAL. Can sustain on donations/sponsorships if we want to stay 100% free.

---

## Next Actions

**Immediate (This Sprint):**
1. ✅ Persona theming system (DONE)
2. ✅ Platform detection (DONE)
3. 🔄 Plugin system architecture (IN PROGRESS)
4. [ ] File search plugin (Quick win)
5. [ ] Pywal integration (Viral)

**This Month:**
- Complete plugin system
- Launch theme gallery
- Build 5 essential plugins
- Prep launch materials

**This Quarter:**
- Public launch
- 1000 GitHub stars
- 50 community themes
- 20 plugins in marketplace
