# Assistant Architecture

Python TUI application for voice-interactive AI assistance.

## Overview

The assistant is a Textual-based terminal UI that acts as your:
- **Personal Secretary** - Email management, calendar, scheduling
- **Research Assistant** - Online research, knowledge synthesis
- **Project Manager** - Watches development, handles permissions, escalates blockers
- **Second Brain** - Semantic search across all communications and documents

Design philosophy: **Offline-first** with cloud API fallback for incapable hardware.

## Runtime Model

```
┌─────────────────────────────────────────────────────────┐
│                    Assistant TUI                         │
│                  (Python singleton)                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Scheduler  │    │  Thinking   │    │   Tools     │  │
│  │   Loop      │───▶│   Engine    │───▶│   (MCP)     │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
│                            │                             │
│                            ▼                             │
│                    ┌─────────────┐                       │
│                    │  Escalation │                       │
│                    │   Router    │                       │
│                    └─────────────┘                       │
│                            │                             │
└────────────────────────────┼────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
   ┌─────────┐         ┌─────────┐         ┌─────────┐
   │  Voice  │         │  Phone  │         │  Email  │
   │ Server  │         │  /SMS   │         │         │
   │(singleton)        │(Twilio) │         │(SendGrid)
   └─────────┘         └─────────┘         └─────────┘
```

### Component Lifecycle

- **TUI**: Python singleton, user-facing interface
- **Voice Server**: Background singleton (slow to start, stays running)
- **Cloud Fallback**: Connect to remote voice server if local hardware is too slow

```python
# TUI startup
if not voice_server.is_running():
    voice_server.start()  # Local MLX, takes 6-8s
elif voice_server.is_slow():
    voice_server.connect_remote()  # Cloud fallback
```

## Scheduler

Fixed-interval monitoring with smart defaults (no user configuration needed).

### Default Intervals

```python
SCHEDULE = {
    'email_check': 5 * 60,       # 5 min - responsiveness
    'project_status': 1 * 60,    # 1 min - catch blockers fast
    'calendar_check': 15 * 60,   # 15 min - meetings don't change often
    'memory_consolidation': 60 * 60,   # 1 hour
    'document_indexing': 6 * 60 * 60,  # 6 hours
}
```

### Scheduler Loop

Each tick:
1. Gather context (what's due, what changed)
2. Call thinking engine with context
3. Engine decides what actions to take
4. Execute tools as needed
5. Route notifications based on urgency

## Tools (MCP Servers)

Each subsystem is a tool the thinking engine can invoke:

| Tool | Purpose |
|------|---------|
| `check_email` | Fetch inbox, summarize, draft responses |
| `check_calendar` | Upcoming meetings, conflicts, reminders |
| `check_projects` | Git status, CI/CD, blockers, permissions |
| `search_memory` | Semantic search all content |
| `send_notification` | Voice/SMS/Email/Phone/Desktop |
| `execute_action` | Permissions, approvals, shell commands |
| `research_web` | Online research tasks |
| `query_knowledge` | Plugin knowledge bases (survival, etc.) |

### Tool Invocation

```python
# Thinking engine decides and calls
result = await tools.check_email(
    action='summarize',
    filter='unread',
    draft_responses=True
)

if result.urgent:
    await tools.send_notification(
        channel='sms',
        message=result.summary
    )
```

## Escalation Router

Routes notifications based on urgency and context.

### Urgency Levels

| Level | Channels | Examples |
|-------|----------|----------|
| Critical | Phone + SMS + Voice + Desktop | Project blocked, needs you NOW |
| High | SMS + Desktop + Voice | Meeting in 10 min, urgent email |
| Medium | Email + Voice | Email needs response today |
| Low | Voice only | Daily briefing, status update |

### Channel Selection

```python
def route_notification(urgency, message, context):
    if urgency == 'critical':
        # All channels simultaneously
        send_phone_call(message)
        send_sms(message)
        speak_via_voice(message)
        send_desktop_notification(message)
    elif urgency == 'high':
        send_sms(message)
        send_desktop_notification(message)
        if tui_active:
            speak_via_voice(message)
    # ... etc
```

See `escalation-routing.md` for detailed channel logic and quiet hours.

## Core Modules

### Dashboard (`dashboard.py`, `dashboard_widgets.py`)

Terminal UI built with Textual framework:
- Responsive panel layout
- Chat history and input
- Voice visualizer
- Status indicators
- Persona-based theming

### Voice (`voice.py`, `audio.py`)

Audio I/O and MOSHI integration:
- 24kHz audio capture (sounddevice)
- WebSocket connection to voice server
- Wake word detection
- Output queue and playback

### Thinking Engine (`thinking_engine.py`, `thinking.py`)

AI decision making:
- Determines when to use tools vs memory
- Sonnet 4.5 summarization for context
- Tool routing and execution
- Response generation

See `thinking-service.md` for full architecture.

### Memory System (`memory.py`)

3-tier semantic memory with AI-filtered retrieval:

```
L1: Session Memory (current conversation, ~1-2K tokens)
    ↓ (rolling compression every 10 messages)
L2: Episodic Memory (recent interactions, tier-based: 30-365+ days)
    ↓ (extraction & consolidation)
L3: Semantic Memory (long-term facts & knowledge, permanent)
```

**Retrieval Algorithm**:
```
Score = (Similarity × 0.6) + (Recency × 0.3) + (Frequency × 0.1)
```

See `memory-service.md` for database schema and API.

### Persona System

Personality modeling with Big Five traits:

```
Big Five (0.0-1.0):
- Extraversion, Agreeableness, Conscientiousness, Neuroticism, Openness

Response Style:
- Verbosity: Concise | Balanced | Detailed | Elaborate
- Tone: Professional | Friendly | Casual | Authoritative
```

See `persona-builder.md` for trait configuration and voice training.

### Persona Generator (Wizard)

**Free tier feature** - Professional voice customization as marketing differentiator.

5-step AI-assisted wizard to create custom personas:

**Step 1: Name & Introduction**
- Custom assistant name, greeting, character inspiration

**Step 2: Voice Search & Preview (AI Web Search)**
- AI searches web for voice samples (YouTube, audio libraries, clips)
- User selects best clips from AI-curated results
- YouTube URL extraction (manual option)
- File upload (fallback)
- AI auto-segments, quality-scores, and recommends best clips
- Preview player with waveform visualization

**Step 3: Personality Builder (AI-Assisted)**
- AI analyzes voice tone and suggests Big Five traits
- Interactive trait sliders with live descriptions
- Response style presets (Professional, Friendly, Casual, etc.)

**Step 4: Theme Designer (AI Image Search)**
- AI searches web for character/interface images
- Extracts color palettes from user-selected images
- AI generates cohesive theme with live preview
- Manual color adjustment with sliders

**Step 5: Generate & Test**
- **Fine-tune Mimi decoder** on voice samples (15-30 min background task)
- Professional-quality voice matching
- Test interaction, export config

**Voice Fine-tuning** (Free Tier):
- Users with GPU: Local fine-tuning
- No GPU: Cloud fine-tuning (1 persona/month free, unlimited on paid tiers)
- Real voice adaptation, not approximations
- ~500MB personalized decoder per persona

**Marketing Strategy**:
- Quality results drive word-of-mouth
- "I built my own JARVIS!" is shareable
- Users invest time = platform attachment
- Differentiates from voice characteristic matching competitors

See `persona-generator.md` for wizard implementation and AI assistance.

### Project Management

Watches your CLI projects and acts as you:

**Monitoring**:
- Git status and commit activity
- CI/CD pipeline status
- Blocker detection
- Permission requests

**Actions**:
- Grant permissions on your behalf
- Answer project questions
- Escalate immediately if blocked

**Health Scoring**:
```
Score = Commits(30%) + Tasks(25%) + Activity(20%) + Blocked(15%) + Repo(10%)
```

See `project-management.md` for monitoring configuration.

### User Content Indexing

Semantic search across all your content:

**Sources**:
- Documents (PDF, DOCX, TXT, local and cloud)
- Email archives
- Calendar events
- Task descriptions
- Communication history
- Knowledge base plugins

**Pipeline**:
```
Document → Extract → Chunk → Embed → Store → Index
Query → Embed → Search → Rank → Return
```

See `user-content-indexing.md` for indexing strategies.

### Knowledge Base Plugins

Specialized knowledge collections:

```python
PLUGINS = {
    'survival': 'plugins/survival-knowledge/',
    'medical': 'plugins/first-aid/',
    'cooking': 'plugins/recipes/',
    # User-defined collections
}
```

Query via: `query_knowledge(plugin='survival', query='water purification')`

## Knowledge Base Plugins

Specialized knowledge collections available as separate products (not tier-gated).

### Plugin Marketplace

**Free Core Plugins**:
- Basic survival knowledge
- First aid reference
- Cooking recipes

**Premium Plugins** (separate products, $5-$15 each):
- **Bunker-Buddy** ($15) - Comprehensive survival guide (water storage, food preservation, shelter, first aid, defense)
- **Medical Reference** ($10) - Drug interactions, symptoms, emergency procedures
- **Legal Assistant** ($10) - Contract templates, legal concepts
- **Code Mentor** ($5) - Programming patterns, best practices

**Integration Connectors**:
- **Obsidian Connector** ($10) - Index and search your Obsidian vaults
- **Notion Connector** ($10) - Sync and query Notion databases
- **Google Drive Connector** ($10) - Index cloud documents

### Plugin Architecture

Plugins are vector databases with metadata:

```python
{
  "name": "bunker-buddy",
  "version": "1.2.0",
  "description": "Comprehensive survival knowledge base",
  "categories": ["survival", "emergency", "preparedness"],
  "documents": 1247,
  "size_mb": 45,
  "auto_update": true
}
```

**Query Interface**:
```python
result = query_knowledge(
    plugin='bunker-buddy',
    query='long-term water storage methods',
    limit=5
)
```

**Installation**:
```bash
assistant plugins install bunker-buddy
assistant plugins list
assistant plugins update bunker-buddy
```

See `knowledge-plugins.md` for plugin development and marketplace listing.

## Data Flow

### Scheduled Check → Action

```
1. Scheduler tick (e.g., email_check due)
2. → Gather context (inbox state, recent activity)
3. → Thinking engine evaluates
4. → Decides: summarize inbox, draft 2 responses
5. → Executes check_email tool
6. → Routes notification (medium urgency → voice)
7. → Updates memory with new facts
```

### Voice Input → Response

```
1. Microphone → audio.py (24kHz PCM)
2. → voice.py → WebSocket → Voice Server (MOSHI)
3. → thinking_engine.py (tool/memory decision)
4. → memory.py (context retrieval)
5. → MOSHI generates response
6. → audio.py → speakers
```

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point |
| `scheduler.py` | Interval-based task loop |
| `dashboard.py` | TUI app |
| `thinking_engine.py` | Tool/memory decisions |
| `tools.py` | MCP tool implementations |
| `escalation.py` | Notification routing |
| `memory.py` | Embeddings + retrieval |
| `voice.py` | Audio I/O |
| `hardware.py` | GPU detection |

## Configuration

### Main Config (`config.js`)

```javascript
voice: {
  defaultPersona: 'boss',
  sampleRate: 24000,
  wakeWord: { enabled: true, sensitivity: 0.5, keywords: ['hey_hal'] }
}

ai: {
  anthropic: { model: 'claude-sonnet-4-5-20250929' },
  defaultVoiceProvider: 'moshi',
  models: { moshi: 'kyutai/moshika-mlx-q4' }
}

// Scheduler uses smart defaults, no config needed
```

### Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
THINKING_ENGINE_LIGHT="ANTHROPIC:claude-haiku-4-5"
THINKING_ENGINE_NORMAL="ANTHROPIC:claude-sonnet-4"
THINKING_ENGINE_DEEP="ANTHROPIC:sonnet-4-5"
OPENAI_EMBEDDING_MODEL="text-embedding-3-small"
```

## Installation

```bash
cd packages/assistant
pip install -e .
python -m assistant
```

## Dependencies

- **textual** - TUI framework
- **sounddevice** - Audio I/O
- **websockets** - MOSHI connection
- **openai** - Embeddings
- **anthropic** - Thinking engine

## Detailed Documentation

- `intelligence-layer.md` - GPU detection and local LLM selection (7 levels)
- `thinking-service.md` - AI-powered memory filtering with cost optimization
- `memory-service.md` - 3-tier memory architecture and retrieval
- `persona-builder.md` - Big Five traits, themes, voice training
- `persona-generator.md` - Wizard UI, voice search, AI assistance, viral features
- `project-management.md` - Project monitoring and automation
- `user-content-indexing.md` - Document and cloud indexing
- `escalation-routing.md` - Notification channel selection
- `knowledge-plugins.md` - Plugin marketplace, development, connectors

## Known Issues

### Terminal Corruption

After TUI exit, terminal may have corrupt escape codes. Workaround: close and reopen terminal.

### Voice Server Startup

First launch takes 6-8 seconds for model loading. Server stays running to avoid repeated startup.

### MLX Thread Safety

MLX GPU operations must run on main thread. Voice pipeline queues audio in callbacks, processes on main.

## Debug Logging

```bash
tail -f /tmp/xswarm_debug.log     # Main debug
tail -f /tmp/moshi_timing.log     # Model timing
tail -f /tmp/moshi_text.log       # Transcriptions
```

## Testing

```bash
cd tests
pytest assistant/
```
