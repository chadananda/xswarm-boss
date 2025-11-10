# xSwarm Architecture - Tier-Based AI Assistant Platform

## Overview

xSwarm is a voice-first AI assistant platform with a sophisticated tier-based subscription model. The architecture combines:
- **4-tier subscription system** (Free, Personal, Professional, Enterprise)
- **Feature gating and access control** based on subscription tiers
- **Multi-channel communication** (Voice, SMS, Email, API)
- **Semantic memory system** with vector embeddings
- **Persona management** with Big Five personality traits
- **Project orchestration** and team collaboration
- **Distributed architecture** (Rust client + Node.js server)

---

## System Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Subscription Tiers                        │
│  Free → Personal ($20/mo) → Professional ($190/mo) →         │
│                    Enterprise ($940/mo)                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Feature Gating Layer                        │
│  • Voice/SMS/Email limits                                    │
│  • AI model access (GPT-3.5 → GPT-4/Claude/Gemini)         │
│  • Persona limits (3 → unlimited)                           │
│  • Memory retention (30d → 2y → unlimited)                  │
│  • Team collaboration & API access                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Communication Layer                        │
│  Voice (MOSHI) | SMS (Twilio) | Email (SendGrid) | API      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Processing Layer                          │
│  Rust Client (Desktop) ←→ Node.js Server (Cloudflare)       │
│  • Wake word detection    • API routing                      │
│  • Voice processing       • Database access                  │
│  • Local AI inference     • Cloud AI orchestration          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                               │
│  Turso Database (libsql) + Cloudflare R2 (Object Storage)   │
│  • User data & subscriptions                                 │
│  • CozoDB (PLANNED) - Graph-based semantic memory           │
│    - Vector search (HNSW indices)                            │
│    - Full-text search (FTS)                                  │
│    - Graph traversal (Datalog queries)                       │
│    - Entity relationships & context expansion                │
│  • Personas, tasks, calendar, projects                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Tier-Based Feature Matrix

### Core Philosophy

**Progressive Enhancement**: Each tier builds on the previous one with expanded limits, better AI models, and additional features.

### Tier Comparison

| Feature | Free (AI Buddy) | Personal (AI Secretary) | Professional (AI PM) | Enterprise (AI CTO) |
|---------|----------------|------------------------|---------------------|---------------------|
| **Price** | $0/mo | $20/mo | $190/mo | $940/mo |
| **Voice Minutes** | 0 | 100/mo | 500/mo | Unlimited |
| **SMS Messages** | 0 | 100/mo | 500/mo | Unlimited |
| **Email Daily** | 100 | Unlimited | Unlimited | Unlimited |
| **AI Models** | GPT-3.5 | GPT-4, Claude, Gemini | GPT-4 Turbo, Claude Opus | All + Custom |
| **Custom Personas** | 3 max | Unlimited | Unlimited | Unlimited |
| **Memory Retention** | 30 days | 1 year | 2 years | Unlimited |
| **Calendar Access** | Read-only | Read/Write | Read/Write | Read/Write |
| **Document Gen** | ❌ | Basic (DOCX, PDF) | Full Suite (+ XLSX, PPTX) | All + Custom |
| **Team Collaboration** | ❌ | ❌ | Up to 10 members | Unlimited |
| **Buzz Workspace** | ❌ | ❌ | 50 channels | Unlimited |
| **API Access** | ❌ | Basic | Full | Enterprise |
| **Max Projects** | 3 | 25 | 100 | Unlimited |
| **Storage** | 1GB | 10GB | 100GB | Unlimited |
| **Support** | Community | Email | Priority | Dedicated AM |

### Feature Access Patterns

```javascript
// Feature gating example (from features.js)
import { hasFeature, checkLimit, generateUpgradeMessage } from './lib/features.js';

// Check if user has access to a feature
if (hasFeature(user.subscription_tier, 'voice_minutes')) {
  // User has voice capability
}

// Check usage limits
const voiceLimit = checkLimit(
  user.subscription_tier,
  'voice_minutes',
  user.current_voice_usage
);

if (!voiceLimit.allowed && !voiceLimit.overage_allowed) {
  // Show upgrade message
  const message = generateUpgradeMessage('voice_minutes', user.subscription_tier);
  return { error: message.message, cta: message.cta };
}

// Calculate overage charges for Personal/Professional tiers
if (voiceLimit.overage > 0 && voiceLimit.overage_allowed) {
  const cost = calculateOverageCost(
    user.subscription_tier,
    'voice_minutes',
    voiceLimit.overage
  );
  // Bill user for overage: cost = overage * rate
}
```

---

## Database Architecture

### Core Principle: Database-Centric User Data

**NO per-user config files.** All user data lives in the Turso database (libsql with SQLite compatibility).

### User Architecture

Two types of users:

1. **Admin User** (Single, Config-based)
   - Defined in `config.toml`
   - NOT in database
   - Has unlimited access to all features
   - Used for system administration

2. **Regular Users** (Multiple, Database-based)
   - Stored in Turso database
   - Feature access based on subscription tier
   - Subject to limits and billing

### Database Schema

```sql
-- Core users table with subscription tiers
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  name TEXT,

  -- Contact
  email TEXT UNIQUE NOT NULL,
  user_phone TEXT NOT NULL,

  -- xSwarm assignments
  xswarm_email TEXT UNIQUE NOT NULL,  -- username@xswarm.ai
  xswarm_phone TEXT UNIQUE,            -- Premium+ only

  -- Subscription & persona
  subscription_tier TEXT NOT NULL DEFAULT 'free'
    CHECK(subscription_tier IN ('free', 'personal', 'professional', 'enterprise', 'admin')),
  persona TEXT NOT NULL DEFAULT 'boss',
  wake_word TEXT,

  -- Stripe integration
  stripe_customer_id TEXT UNIQUE,
  stripe_subscription_id TEXT,

  -- Timestamps
  created_at TEXT NOT NULL,
  updated_at TEXT
);

-- Personas table (Big Five personality traits)
CREATE TABLE personas (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  description TEXT,

  -- Personality (JSON)
  personality_traits TEXT NOT NULL DEFAULT '{
    "extraversion": 0.5,
    "agreeableness": 0.5,
    "conscientiousness": 0.5,
    "neuroticism": 0.5,
    "openness": 0.5,
    "formality": 0.5,
    "enthusiasm": 0.5
  }',

  -- Response style (JSON)
  response_style TEXT NOT NULL DEFAULT '{
    "verbosity": "Balanced",
    "tone": "Friendly",
    "humor_level": 0.5,
    "technical_depth": 0.5,
    "empathy_level": 0.5,
    "proactivity": 0.5
  }',

  -- Voice configuration (JSON)
  voice_model_config TEXT NOT NULL,
  expertise_areas TEXT DEFAULT '[]',
  conversation_examples TEXT DEFAULT '[]',

  is_active BOOLEAN DEFAULT FALSE,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,

  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Semantic memory: 3-tier architecture
CREATE TABLE memory_sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  summary TEXT NOT NULL,
  key_topics TEXT DEFAULT '[]',          -- JSON array
  embedding TEXT NOT NULL,                -- 1536-dim vector (JSON)
  session_start TEXT NOT NULL,
  session_end TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE memory_facts (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  fact_text TEXT NOT NULL,
  source_session TEXT REFERENCES memory_sessions(id),
  confidence REAL NOT NULL DEFAULT 0.8,
  category TEXT,
  embedding TEXT NOT NULL,                -- 1536-dim vector (JSON)
  access_count INTEGER DEFAULT 1,
  last_accessed TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE memory_entities (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  entity_type TEXT NOT NULL CHECK(entity_type IN
    ('person', 'place', 'project', 'company', 'concept', 'other')),
  name TEXT NOT NULL,
  attributes TEXT DEFAULT '{}',           -- JSON object
  mention_count INTEGER DEFAULT 1,
  first_mentioned TEXT,
  last_mentioned TEXT,

  UNIQUE(user_id, entity_type, name)
);

-- Tasks with tier-based limits
CREATE TABLE tasks (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  title TEXT NOT NULL,
  description TEXT,
  priority TEXT DEFAULT 'normal' CHECK(priority IN ('low', 'normal', 'high', 'urgent')),
  status TEXT DEFAULT 'todo' CHECK(status IN ('todo', 'in_progress', 'done', 'cancelled')),
  due_date TEXT,
  completed_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT,

  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Calendar integration (OAuth tokens)
CREATE TABLE calendar_tokens (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  provider TEXT NOT NULL CHECK(provider IN ('google', 'microsoft', 'apple')),
  access_token TEXT NOT NULL,
  refresh_token TEXT,
  token_type TEXT DEFAULT 'Bearer',
  expires_at TEXT NOT NULL,
  scope TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT,

  UNIQUE(user_id, provider),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Email integration
CREATE TABLE email_threads (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  thread_id TEXT NOT NULL,                -- Gmail thread ID
  subject TEXT,
  participants TEXT DEFAULT '[]',         -- JSON array
  last_message_at TEXT,
  unread_count INTEGER DEFAULT 0,
  labels TEXT DEFAULT '[]',               -- JSON array
  created_at TEXT NOT NULL,

  UNIQUE(user_id, thread_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Team collaboration (Professional+ only)
CREATE TABLE teams (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  description TEXT,
  max_members INTEGER,                    -- Based on tier
  created_at TEXT NOT NULL,
  updated_at TEXT,

  FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE team_members (
  id TEXT PRIMARY KEY,
  team_id TEXT NOT NULL REFERENCES teams(id),
  user_id TEXT NOT NULL REFERENCES users(id),
  role TEXT NOT NULL CHECK(role IN ('viewer', 'editor', 'admin', 'owner')),
  joined_at TEXT NOT NULL,

  UNIQUE(team_id, user_id),
  FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Usage tracking for metered billing
CREATE TABLE usage_records (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  voice_minutes INTEGER DEFAULT 0,
  sms_messages INTEGER DEFAULT 0,
  email_count INTEGER DEFAULT 0,
  ai_api_calls INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT,

  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### Indexes

```sql
-- Performance-critical indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_tier ON users(subscription_tier);
CREATE INDEX idx_users_stripe ON users(stripe_customer_id);

CREATE INDEX idx_personas_user ON personas(user_id);
CREATE INDEX idx_personas_active ON personas(user_id, is_active) WHERE is_active;

CREATE INDEX idx_memory_sessions_user ON memory_sessions(user_id);
CREATE INDEX idx_memory_facts_user ON memory_facts(user_id);
CREATE INDEX idx_memory_facts_category ON memory_facts(category);

CREATE INDEX idx_tasks_user ON tasks(user_id);
CREATE INDEX idx_tasks_due ON tasks(due_date);
CREATE INDEX idx_tasks_status ON tasks(status);

CREATE INDEX idx_usage_records_user ON usage_records(user_id);
CREATE INDEX idx_usage_records_period ON usage_records(period_start, period_end);
```

---

## Distributed Architecture

### Rust Client (Desktop Application)

**Location**: `packages/core/src/`

**Responsibilities**:
- Wake word detection ("Hey HAL", "Hey xSwarm", custom)
- Voice input/output (MOSHI integration)
- Local AI inference (Free tier, hardware-dependent)
- Desktop UI (menu bar, overlay, dashboard)
- WebSocket client to Node.js server
- Project monitoring and file watching

**Key Modules**:

```rust
// Config management
use xswarm::config::ProjectConfig;

let config = ProjectConfig::load()?;
let admin = config.get_admin();

// Persona management
use xswarm::personas::{PersonaClient, PersonalityTraits};

let client = PersonaClient::new(&config);
let persona = client.get_active_persona(&user_id).await?;

// Semantic memory
use xswarm::memory::{MemoryClient, SemanticSearch};

let memory = MemoryClient::new(&config);
let facts = memory.search_facts(&user_id, query, limit).await?;

// Claude Code integration
use xswarm::claude_code::{ClaudeCodeBridge, TaskStatus};

let bridge = ClaudeCodeBridge::new(&config);
bridge.start_task("Implement feature X").await?;

// Voice processing
use xswarm::voice::{MoshiClient, WakeWord};

let moshi = MoshiClient::new(&config);
moshi.listen_for_wake_word(&wake_word).await?;
```

### Node.js Server (Cloudflare Workers)

**Location**: `packages/server/src/`

**Responsibilities**:
- API routing and authentication
- Database access (Turso libsql)
- Feature gating middleware
- Stripe subscription management
- Multi-channel communication (Twilio, SendGrid)
- OAuth integrations (Google Calendar, Gmail)
- Usage tracking and billing
- WebSocket connections

**Key Routes**:

```javascript
// Authentication & authorization
POST   /auth/register          // Create new user
POST   /auth/login             // Login with email/password
POST   /auth/refresh           // Refresh JWT token

// User management
GET    /users/:id              // Get user profile
PATCH  /users/:id              // Update user settings
GET    /users/:id/usage        // Get usage stats

// Feature gating
GET    /features/check/:feature   // Check feature access
GET    /features/limits           // Get tier limits
POST   /features/upgrade          // Generate upgrade link

// Personas
GET    /personas                   // List user personas (respects tier limit)
POST   /personas                   // Create persona (enforces 3-persona limit on Free)
GET    /personas/:id               // Get persona details
PATCH  /personas/:id               // Update persona traits
DELETE /personas/:id               // Delete persona
POST   /personas/:id/activate      // Set as active persona
POST   /personas/:id/train         // Start voice training

// Semantic memory
POST   /memory/ingest              // Store new memory
GET    /memory/search              // Vector similarity search
GET    /memory/facts               // Get user facts
GET    /memory/entities            // Get extracted entities
POST   /memory/forget              // Delete old memories (respects retention)

// Tasks
GET    /tasks                      // List tasks
POST   /tasks                      // Create task
PATCH  /tasks/:id                  // Update task
DELETE /tasks/:id                  // Delete task

// Calendar integration
POST   /calendar/oauth/google      // Start OAuth flow
GET    /calendar/events            // Get calendar events (all tiers)
POST   /calendar/events            // Create event (Personal+ only)
PATCH  /calendar/events/:id        // Update event (Personal+ only)

// Email management
GET    /email/threads              // List email threads (all tiers)
GET    /email/threads/:id          // Read thread (all tiers)
POST   /email/compose              // Send email (Personal+ only)
POST   /email/reply                // Reply to thread (Personal+ only)

// Billing
GET    /billing/subscription       // Get subscription info
POST   /billing/checkout           // Create Stripe checkout
POST   /billing/portal             // Customer portal link
POST   /billing/webhook            // Stripe webhook handler

// Team collaboration (Professional+ only)
GET    /teams                      // List teams
POST   /teams                      // Create team
GET    /teams/:id/members          // List members
POST   /teams/:id/invite           // Invite member
DELETE /teams/:id/members/:userId  // Remove member

// Projects (Professional+ only)
GET    /projects                   // List projects
POST   /projects                   // Create project
GET    /projects/:id/status        // Get build/deploy status
POST   /projects/:id/builds        // Trigger build

// Buzz workspace (Professional+ only)
GET    /buzz/channels              // List channels
POST   /buzz/channels              // Create channel
GET    /buzz/channels/:id/posts    // Get posts
POST   /buzz/channels/:id/posts    // Create post
```

### Feature Gating Middleware

```javascript
// middleware/feature-gate.js
import { checkFeatureAccess } from '../lib/features.js';

export function requireFeature(feature) {
  return async (req, res, next) => {
    const userId = req.user.id;
    const hasAccess = await checkFeatureAccess(req.db, userId, feature);

    if (!hasAccess) {
      const message = generateUpgradeMessage(feature, req.user.subscription_tier);
      return res.status(403).json({
        error: 'Feature not available on your plan',
        message: message.message,
        upgrade_options: message.upgrade_options
      });
    }

    next();
  };
}

// Usage in routes
import { requireFeature } from '../middleware/feature-gate.js';

// Email compose requires Personal+
router.post('/email/compose',
  requireAuth,
  requireFeature('email_compose'),
  async (req, res) => {
    // Handle email composition
  }
);

// Team collaboration requires Professional+
router.post('/teams',
  requireAuth,
  requireFeature('team_collaboration'),
  async (req, res) => {
    // Create team
  }
);
```

---

## Communication Architecture

### Multi-Channel System

```
┌─────────────┐
│    User     │
└──────┬──────┘
       │
       ├─── Voice (MOSHI) ────────┐
       ├─── SMS (Twilio) ─────────┤
       ├─── Email (SendGrid) ─────┼──→ Unified Message Router
       ├─── Desktop Client ───────┤
       └─── API Calls ────────────┘
                                   ↓
                        ┌──────────────────┐
                        │  Message Parser  │
                        └──────────────────┘
                                   ↓
                        ┌──────────────────┐
                        │ Feature Gating   │
                        │ Check tier limits│
                        └──────────────────┘
                                   ↓
                        ┌──────────────────┐
                        │  AI Processing   │
                        │ Model selection  │
                        │ based on tier    │
                        └──────────────────┘
                                   ↓
                        ┌──────────────────┐
                        │ Response Router  │
                        │ Send via same    │
                        │ channel          │
                        └──────────────────┘
```

### MOSHI Voice Architecture (Direct Speech-to-Speech)

**CRITICAL**: xSwarm uses MOSHI's **unified speech-to-speech model** for voice processing. This is **NOT traditional TTS** - MOSHI generates audio directly without a separate text-to-speech step.

#### Three Distinct Voice Mechanisms

```rust
// 1. GREETINGS (Scripted Speech) - uses force_text_token
//    Acceptable for predetermined phrases like "Hello, how can I help?"
let text_token = lm_generator.step(
    prev_text_token,
    &silent_audio,          // Padding tokens (no user audio)
    Some(forced_token),     // ← Inject specific text token
    None,                   // No cross-attention
)?;

// 2. MEMORY CONTEXT (Natural Incorporation) - uses Condition::AddToInput
//    For semantic search results that MOSHI naturally weaves into conversation
let memory_embedding = memory_conditioner.encode_memory(context_text)?;
let text_token = lm_generator.step_(
    prev_text_token,
    &audio_codes,
    None,                   // No forcing
    None,                   // No cross-attention
    Some(&Condition::AddToInput(memory_embedding)), // ← Context influences output
)?;

// 3. STT TRANSCRIPTION (Background Only) - for memory storage
//    Not in critical audio path, runs async
tokio::spawn(async move {
    let transcription = stt_transcriber.transcribe_async(audio).await?;
    memory_system.store(transcription).await?;
});
```

#### MOSHI Unified Model Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MOSHI UNIFIED MODEL                       │
│  (Single model - NO separate TTS!)                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Language Model (Transformer)                        │   │
│  │  • Processes text tokens                             │   │
│  │  • Processes audio tokens (via MIMI codec)           │   │
│  │  • Generates next text token                         │   │
│  │  • Generates audio tokens (via depformer)            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │ MIMI Encoder │         │ MIMI Decoder │                 │
│  │ PCM → Codes  │         │ Codes → PCM  │                 │
│  └──────────────┘         └──────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

#### Voice Processing Pipeline (Reactive Mode)

```rust
// User speaks → MOSHI responds (conversational)
1. Microphone captures audio (24kHz PCM)
    ↓
2. MIMI encoder: PCM → Audio tokens (8 codebooks)
    ↓
3. Language Model step:
    • Input: Previous text token + Audio tokens
    • Output: Next text token + Generated audio tokens
    ↓
4. MIMI decoder: Audio tokens → PCM (24kHz)
    ↓
5. Play through speakers
    ↓
6. Background: STT transcribes for memory storage
```

#### Greeting Generation Pipeline (Proactive Mode)

```rust
// System generates greeting without user input
1. Tokenize greeting text: "Hello! I'm ready to help you today."
    ↓
2. Silent audio input: vec![padding_token; 8] // No user speaking
    ↓
3. FOR EACH text token:
    • Force text token via LM.step()
    • Depformer generates audio tokens
    • Collect audio output
    ↓
4. MIMI decoder: All audio tokens → PCM
    ↓
5. Play through speakers (AudioOutputDevice)
```

#### Memory Conditioning Pipeline

```rust
// Semantic search → Natural incorporation
1. User asks: "What about authentication?"
    ↓
2. Semantic search: Find relevant memories
    • Query embeddings database
    • Found: "Last Wednesday decided on JWT"
    ↓
3. Memory conditioner: Text → Embedding
    • Tokenize memory text
    • Embed via text_emb layer
    • Mean pool to context vector
    ↓
4. Create condition: Condition::AddToInput(context_vector)
    ↓
5. LM step WITH condition:
    • emb = emb.broadcast_add(context_vector)
    • MOSHI naturally says: "I remember last Wednesday..."
    ↓
6. Audio generation (same as reactive mode)
```

#### Key Technical Details

**Silent Audio Input**:
```rust
// Use padding tokens, NOT zeros
let padding_token = lm_config.audio_pad_token(); // audio_vocab_size - 1
let silent_audio = vec![padding_token; input_audio_codebooks];
```

**Acoustic Delay**:
```rust
// First few LM steps return None for audio (normal behavior)
if let Some(audio_tokens) = lm_generator.last_audio_tokens() {
    // Audio available after acoustic_delay steps
} else {
    // Still warming up depformer
}
```

**MIMI Codec**:
```rust
// Encode: PCM (24kHz) → Audio tokens (8 codebooks)
let audio_tokens = mimi.encode_step(&pcm_tensor)?;

// Decode: Audio tokens → PCM (24kHz)
let pcm = mimi.decode_step(&audio_tokens)?;
```

#### Voice Processing Pipeline (Legacy Comment for Reference)

```javascript
// OLD APPROACH (for comparison - NOT how MOSHI works):
// Client-side (Rust)
1. Wake word detection → Local DSP
2. Voice capture → Record audio stream
3. Send to server → WebSocket or HTTP

// Server-side (Node.js)
4. Receive audio → Validate user tier
5. Transcribe → Whisper API  // ← MOSHI doesn't need this step
6. Process → Select AI model based on tier
   - Free: GPT-3.5 Turbo
   - Personal: GPT-4, Claude 3 Sonnet
   - Professional: GPT-4 Turbo, Claude 3 Opus
   - Enterprise: All models + custom
7. Generate response → Selected model
8. TTS → MOSHI or ElevenLabs // ← MOSHI is NOT TTS!
9. Stream back → WebSocket

// Client-side (Rust)
10. Play audio → Local speaker
11. Update UI → Show transcript

// NEW APPROACH (MOSHI Direct Speech):
// Everything happens in Rust client with local MOSHI model
1. Wake word → Activate microphone
2. Audio in → MOSHI processes directly (speech-to-speech)
3. Audio out → Play response immediately
4. Background → STT for memory storage only
```

#### Tier-Based Voice Features

| Feature | Free | Personal | Professional | Enterprise |
|---------|------|----------|--------------|------------|
| **Local MOSHI** | ✅ Local GPU | ✅ Local GPU | ✅ Local GPU | ✅ Local GPU |
| **Voice Minutes** | 0 | 100/mo | 500/mo | Unlimited |
| **Cloud Fallback** | ❌ | ✅ | ✅ | ✅ |
| **Voice Training** | Local (6-8h) | Cloud (30-60min) | Cloud (15-30min) | Priority Cloud |
| **Custom Personas** | 3 max | Unlimited | Unlimited | Unlimited |
| **Memory Retention** | 30 days | 1 year | 2 years | Unlimited |

#### File Locations

```
packages/core/src/
├── greeting.rs              // Greeting generation (force_text_token)
├── memory_conditioner.rs    // Memory context (Condition::AddToInput)
├── voice.rs                 // Main voice system (MOSHI integration)
├── audio_output.rs          // Speaker playback (CPAL)
├── local_audio.rs           // Microphone capture
└── stt.rs                   // Background transcription (Whisper)
```

### Email Integration

```javascript
// Inbound email processing
1. User emails boss@xswarm.ai
2. SendGrid receives → Parses inbound webhook
3. Extract sender → Lookup user by email
4. Check tier → Verify email limits
5. Process message → AI generates response
6. Send reply → Via SendGrid
7. Log conversation → Store in database

// Gmail OAuth integration (all tiers read, Personal+ write)
1. User initiates OAuth → Redirect to Google
2. Receive callback → Store tokens
3. Fetch emails → Use Gmail API
4. Allow compose → Only if tier >= Personal
```

---

## Semantic Memory Architecture

### Three-Tier Memory System

**Tier 1: Working Memory (In-Context)**
- Last 5-10 messages verbatim
- ~1-2K tokens
- Always available, no database lookup

**Tier 2: Session Summary (Rolling Compression)**
- Compressed summary every 10 messages
- ~500 tokens
- "Earlier in this conversation..."

**Tier 3: Long-Term Memory (Vector Database)**
- Permanent storage with embeddings
- Searchable by semantic similarity
- Retention based on subscription tier:
  - Free: 30 days
  - Personal: 1 year
  - Professional: 2 years
  - Enterprise: Unlimited

### Memory Retrieval Flow

```javascript
// On each user message
async function processMessage(userId, message) {
  // 1. Vector search for similar conversations
  const similarSessions = await memory.searchSessions(
    userId,
    message,
    topK: 5,
    threshold: 0.7
  );

  // 2. Extract relevant facts
  const facts = await memory.searchFacts(
    userId,
    message,
    topK: 10,
    threshold: 0.75
  );

  // 3. Get mentioned entities
  const entities = await memory.extractEntities(message);
  const entityContext = await memory.getEntityContext(userId, entities);

  // 4. Build context for AI
  const context = {
    working_memory: session.messages.slice(-10),
    session_summary: session.summary,
    relevant_facts: facts,
    entity_context: entityContext,
    similar_past_conversations: similarSessions
  };

  // 5. Inject context via system prompt or MOSHI suggestions
  const response = await ai.generate(message, context);

  // 6. Background: Extract new facts and update entities
  await memory.extractAndStoreFacts(userId, message, response);
  await memory.updateEntities(userId, message);

  return response;
}
```

### Vector Embeddings

```javascript
// Generate embedding (OpenAI text-embedding-ada-002)
async function generateEmbedding(text) {
  const response = await openai.embeddings.create({
    model: 'text-embedding-ada-002',
    input: text
  });

  return response.data[0].embedding; // 1536-dimensional vector
}

// Store in database (JSON-serialized for SQLite)
await db.execute({
  sql: `INSERT INTO memory_facts (id, user_id, fact_text, embedding, created_at)
        VALUES (?, ?, ?, ?, ?)`,
  args: [
    uuid(),
    userId,
    factText,
    JSON.stringify(embedding), // Serialize vector
    new Date().toISOString()
  ]
});

// Cosine similarity search (in-memory, for small datasets)
function cosineSimilarity(vecA, vecB) {
  const dotProduct = vecA.reduce((sum, a, i) => sum + a * vecB[i], 0);
  const magA = Math.sqrt(vecA.reduce((sum, a) => sum + a * a, 0));
  const magB = Math.sqrt(vecB.reduce((sum, b) => sum + b * b, 0));
  return dotProduct / (magA * magB);
}

// For production: Migrate to pgvector or Pinecone for better performance
```

---

## Persona System

### Big Five Personality Traits

Based on the Five-Factor Model (OCEAN):

```javascript
{
  "extraversion": 0.7,        // 0 = introverted, 1 = extraverted
  "agreeableness": 0.8,       // 0 = challenging, 1 = compassionate
  "conscientiousness": 0.6,   // 0 = spontaneous, 1 = organized
  "neuroticism": 0.3,         // 0 = resilient, 1 = sensitive
  "openness": 0.9,            // 0 = practical, 1 = curious

  // Custom traits
  "formality": 0.5,           // 0 = casual, 1 = formal
  "enthusiasm": 0.7           // 0 = subdued, 1 = energetic
}
```

### Persona Configuration

```rust
// Rust client persona types
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct Persona {
    pub id: String,
    pub user_id: String,
    pub name: String,
    pub description: Option<String>,
    pub personality_traits: PersonalityTraits,
    pub response_style: ResponseStyle,
    pub expertise_areas: Vec<String>,
    pub voice_model_config: VoiceModelConfig,
    pub is_active: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PersonalityTraits {
    pub extraversion: f32,
    pub agreeableness: f32,
    pub conscientiousness: f32,
    pub neuroticism: f32,
    pub openness: f32,
    pub formality: f32,
    pub enthusiasm: f32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ResponseStyle {
    pub verbosity: String,         // "Concise", "Balanced", "Detailed"
    pub tone: String,              // "Professional", "Friendly", "Casual"
    pub humor_level: f32,          // 0.0 to 1.0
    pub technical_depth: f32,      // 0.0 to 1.0
    pub empathy_level: f32,        // 0.0 to 1.0
    pub proactivity: f32,          // 0.0 to 1.0
}

#[derive(Debug, Serialize, Deserialize)]
pub struct VoiceModelConfig {
    pub voice_id: String,
    pub speed: f32,
    pub pitch: f32,
    pub custom_model_path: Option<String>,
    pub training_status: TrainingStatus,
}

#[derive(Debug, Serialize, Deserialize)]
pub enum TrainingStatus {
    NotStarted,
    Pending,
    InProgress { progress: u8 },
    Completed,
    Failed { error: String },
}
```

### Voice Training Pipeline

```javascript
// Server-side voice training (MOSHI fine-tuning)
async function trainPersonaVoice(personaId, audioSamples) {
  // 1. Validate tier (Free: local GPU 6-8h, Personal+: cloud 30-60min)
  const user = await getPersonaOwner(personaId);
  const canUseCloud = ['personal', 'professional', 'enterprise', 'admin']
    .includes(user.subscription_tier);

  // 2. Create training session
  const session = await db.execute({
    sql: `INSERT INTO persona_training_sessions
          (id, persona_id, training_type, status, created_at)
          VALUES (?, ?, 'voice_model', 'pending', ?)`,
    args: [uuid(), personaId, new Date().toISOString()]
  });

  // 3. Process audio samples
  for (const sample of audioSamples) {
    // Validate quality (duration, clarity, single speaker)
    const quality = await analyzeAudioQuality(sample);

    if (quality.score < 0.7) {
      throw new Error(`Low quality audio: ${quality.issues.join(', ')}`);
    }

    // Convert to 16kHz mono WAV
    const processed = await convertAudio(sample, {
      sampleRate: 16000,
      channels: 1,
      format: 'wav'
    });

    // Store in R2
    const path = await uploadToR2(processed, `personas/${personaId}/samples/`);

    // Save metadata
    await db.execute({
      sql: `INSERT INTO voice_training_samples
            (id, persona_id, sample_text, audio_file_path, duration_seconds, quality_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)`,
      args: [uuid(), personaId, sample.transcript, path, sample.duration, quality.score, new Date().toISOString()]
    });
  }

  // 4. Start training job
  if (canUseCloud) {
    // Cloud training on A100 GPU (30-60 minutes)
    await startCloudTraining(personaId, session.id);
  } else {
    // Local training (user's hardware, 6-8 hours)
    await notifyUserLocalTraining(personaId, session.id);
  }

  return session;
}
```

---

## Project Orchestration (Professional+ Tier)

### xSwarm-Build System

**Purpose**: Automated development monitoring across multiple projects

**Features**:
- Real-time TUI dashboard
- Build pipeline tracking (Jenkins, GitHub Actions, GitLab CI)
- Test result aggregation
- Deployment status monitoring
- Container monitoring (Docker, Kubernetes)
- Git integration (commits, PRs, branches)
- Claude Code/Cursor/Copilot activity tracking

**Architecture**:

```rust
// Rust client monitors local projects
use xswarm::projects::{ProjectMonitor, BuildStatus};

let monitor = ProjectMonitor::new(&config);

// Watch project directory
monitor.watch_project("/path/to/wholeReader").await?;

// Detect build events
monitor.on_build_start(|project_id| {
  println!("Build started: {}", project_id);
});

monitor.on_build_complete(|project_id, status| {
  match status {
    BuildStatus::Success => {
      // Notify via voice/SMS/email based on settings
      notify_user("WholeReader build succeeded!");
    }
    BuildStatus::Failed(error) => {
      notify_user(&format!("Build failed: {}", error));
    }
  }
});

// Voice commands
// "What's the status of WholeReader?"
// "Why did the build fail?"
// "Deploy to staging"
```

### Project Limits by Tier

- Free: 3 projects
- Personal: 25 projects
- Professional: 100 projects
- Enterprise: Unlimited

---

## Upgrade Paths & Billing

### Stripe Integration

```javascript
// Create checkout session
import Stripe from 'stripe';
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

async function createCheckoutSession(userId, tier) {
  const user = await getUser(userId);
  const priceId = TIER_PRICE_IDS[tier]; // From config

  const session = await stripe.checkout.sessions.create({
    customer: user.stripe_customer_id,
    payment_method_types: ['card'],
    line_items: [{
      price: priceId,
      quantity: 1
    }],
    mode: 'subscription',
    success_url: `${BASE_URL}/dashboard?upgrade=success`,
    cancel_url: `${BASE_URL}/pricing?upgrade=cancelled`
  });

  return session.url;
}

// Webhook handler
async function handleStripeWebhook(event) {
  switch (event.type) {
    case 'customer.subscription.created':
    case 'customer.subscription.updated':
      const subscription = event.data.object;
      await updateUserTier(subscription.customer, subscription.metadata.tier);
      break;

    case 'customer.subscription.deleted':
      await downgradeUser(subscription.customer, 'free');
      break;

    case 'invoice.payment_succeeded':
      // Record usage-based charges (overages)
      await recordPayment(event.data.object);
      break;

    case 'invoice.payment_failed':
      await notifyPaymentFailure(event.data.object.customer);
      break;
  }
}
```

### Usage-Based Billing (Personal & Professional)

```javascript
// Track usage and calculate overages
async function calculateMonthlyBill(userId, period) {
  const user = await getUser(userId);
  const usage = await getUsageRecords(userId, period);
  const tierConfig = TIER_FEATURES[user.subscription_tier];

  let overageCharges = 0;

  // Voice minutes overage
  if (usage.voice_minutes > tierConfig.voice_minutes.limit) {
    const overage = usage.voice_minutes - tierConfig.voice_minutes.limit;
    overageCharges += overage * tierConfig.voice_minutes.overage_rate;
  }

  // SMS overage
  if (usage.sms_messages > tierConfig.sms_messages.limit) {
    const overage = usage.sms_messages - tierConfig.sms_messages.limit;
    overageCharges += overage * tierConfig.sms_messages.overage_rate;
  }

  // Create Stripe usage record
  if (overageCharges > 0) {
    await stripe.subscriptionItems.createUsageRecord(
      user.stripe_subscription_item_id,
      {
        quantity: Math.round(overageCharges * 100), // cents
        timestamp: Math.floor(Date.now() / 1000),
        action: 'set'
      }
    );
  }

  return {
    base_price: tierConfig.monthly_price,
    overages: overageCharges,
    total: tierConfig.monthly_price + overageCharges
  };
}
```

---

## Development Workflow

### Local Development

```bash
# 1. Start server (Cloudflare Workers local)
cd packages/server
npm install
npm run dev  # Runs on http://localhost:8787

# 2. Start Rust client (separate terminal)
cd packages/core
cargo build
cargo run -- --dev

# Uses test_user from config.toml:
#   email: test@example.com
#   tier: personal
#   persona: boss
```

### Testing with Database

```bash
# Connect to Turso database
turso db shell xswarm-users

# Create test user
INSERT INTO users (id, username, email, user_phone, xswarm_email, subscription_tier, created_at)
VALUES (
  'test-123',
  'alice_test',
  'alice@example.com',
  '+15551234567',
  'alice_test@xswarm.ai',
  'professional',
  datetime('now')
);

# Test feature access
SELECT subscription_tier FROM users WHERE id = 'test-123';

# Check persona limit
SELECT COUNT(*) FROM personas WHERE user_id = 'test-123';

# View usage
SELECT * FROM usage_records WHERE user_id = 'test-123'
ORDER BY period_start DESC LIMIT 1;
```

### Running Migrations

```bash
# Run all migrations
cd packages/server
node scripts/setup-db.js

# Run specific migration
turso db shell xswarm-users < migrations/personas.sql
turso db shell xswarm-users < migrations/memory.sql
turso db shell xswarm-users < migrations/teams.sql
```

---

## Security & Access Control

### Authentication Flow

```javascript
// 1. Register
POST /auth/register
{
  "email": "alice@example.com",
  "password": "secure_password",
  "phone": "+15551234567"
}

// Response:
{
  "user_id": "uuid",
  "access_token": "jwt_token",
  "refresh_token": "refresh_token",
  "subscription_tier": "free"
}

// 2. Login
POST /auth/login
{
  "email": "alice@example.com",
  "password": "secure_password"
}

// 3. Use JWT for authenticated requests
GET /personas
Headers:
  Authorization: Bearer {access_token}

// 4. Refresh token when expired
POST /auth/refresh
{
  "refresh_token": "refresh_token"
}
```

### Admin Access

```toml
# config.toml
[admin]
email = "admin@xswarm.dev"
phone = "+15559876543"
xswarm_email = "admin@xswarm.ai"
xswarm_phone = "+18005559876"
subscription_tier = "admin"
access_level = "superadmin"
can_provision_numbers = true
can_view_all_users = true
```

```rust
// Rust config loading
let config = ProjectConfig::load()?;

// Check admin status
if config.is_admin_by_email(email) {
  let admin = config.get_admin();
  // Admin has unlimited access
}
```

### Permission Checks

```javascript
// Middleware for route protection
async function checkPermission(req, res, next) {
  const user = req.user;

  // Admin bypass
  if (user.subscription_tier === 'admin') {
    return next();
  }

  // Check feature access
  const feature = req.route_feature; // Set by route
  if (!hasFeature(user.subscription_tier, feature)) {
    return res.status(403).json({
      error: 'Feature not available',
      upgrade_required: true
    });
  }

  next();
}
```

---

## Scalability & Performance

### Database Optimization

```sql
-- Optimize vector search with pre-computed similarities
CREATE INDEX idx_memory_facts_embedding_category
ON memory_facts(category, confidence DESC);

-- Partition usage records by period for faster queries
CREATE INDEX idx_usage_records_period_user
ON usage_records(period_start, user_id);

-- Optimize conversation history lookups
CREATE INDEX idx_memory_sessions_user_time
ON memory_sessions(user_id, session_start DESC);
```

### Caching Strategy

```javascript
// Redis cache for hot data
const cache = new Redis(process.env.REDIS_URL);

// Cache user tier (1 hour TTL)
async function getUserTier(userId) {
  const cacheKey = `user:${userId}:tier`;
  const cached = await cache.get(cacheKey);

  if (cached) return cached;

  const user = await db.execute({
    sql: 'SELECT subscription_tier FROM users WHERE id = ?',
    args: [userId]
  });

  const tier = user.rows[0].subscription_tier;
  await cache.setex(cacheKey, 3600, tier);

  return tier;
}

// Cache feature access (until tier change)
async function cacheFeatureAccess(userId, feature, hasAccess) {
  const cacheKey = `features:${userId}:${feature}`;
  await cache.set(cacheKey, hasAccess ? '1' : '0');
}

// Invalidate cache on tier upgrade
async function onTierUpgrade(userId) {
  const pattern = `features:${userId}:*`;
  const keys = await cache.keys(pattern);
  if (keys.length > 0) {
    await cache.del(...keys);
  }
  await cache.del(`user:${userId}:tier`);
}
```

### Load Balancing

```
┌───────────────┐
│  Cloudflare   │
│   CDN/Edge    │
└───────┬───────┘
        │
        ├─→ Static Assets (R2)
        │
        ├─→ API Requests
        │   └─→ Workers (Auto-scaled)
        │
        └─→ WebSocket
            └─→ Durable Objects (Stateful)
```

---

## Monitoring & Observability

### Key Metrics

```javascript
// Track in Cloudflare Analytics + custom DB table
const metrics = {
  // Usage metrics
  voice_minutes_used: 1234,
  sms_messages_sent: 567,
  api_requests: 8901,

  // Performance metrics
  avg_response_time_ms: 450,
  p95_response_time_ms: 890,
  error_rate: 0.02,

  // Business metrics
  active_users: 5432,
  new_signups_today: 23,
  upgrade_conversions: 5,
  churn_rate: 0.03
};

// Log to Cloudflare Workers Analytics
await analytics.writeDataPoint({
  blobs: [userId, tier, feature],
  doubles: [responseTime, confidence],
  indexes: [timestamp]
});
```

### Health Checks

```javascript
// Server health endpoint
GET /health

{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "stripe": "operational",
  "twilio": "operational",
  "sendgrid": "operational",
  "timestamp": "2025-10-30T12:00:00Z"
}
```

---

## Testing Strategy

### Unit Tests

```bash
# Rust client tests
cd packages/core
cargo test

# Node.js server tests
cd packages/server
npm test

# Test specific feature
npm test -- test-feature-gating.js
```

### Integration Tests

```javascript
// Test tier-based feature access
import { test } from 'vitest';
import { checkFeatureAccess } from './lib/features.js';

test('Free tier cannot access voice', async () => {
  const user = createTestUser({ tier: 'free' });
  const hasVoice = await checkFeatureAccess(db, user.id, 'voice');
  expect(hasVoice).toBe(false);
});

test('Personal tier can access voice with limits', async () => {
  const user = createTestUser({ tier: 'personal' });
  const voiceLimit = checkLimit('personal', 'voice_minutes', 50);

  expect(voiceLimit.allowed).toBe(true);
  expect(voiceLimit.limit).toBe(100);
  expect(voiceLimit.remaining).toBe(50);
});

test('Persona creation respects tier limits', async () => {
  const user = createTestUser({ tier: 'free' });

  // Create 3 personas (Free tier limit)
  await createPersona(user.id, 'Persona 1');
  await createPersona(user.id, 'Persona 2');
  await createPersona(user.id, 'Persona 3');

  // 4th should fail
  await expect(
    createPersona(user.id, 'Persona 4')
  ).rejects.toThrow('Persona limit reached');
});
```

### E2E Tests

```bash
# Test full user journey
npm run test:e2e -- test-signup-to-upgrade.js

# Test scenarios:
# 1. User signs up (Free tier)
# 2. Creates 3 personas (hits limit)
# 3. Tries voice call (blocked)
# 4. Upgrades to Personal
# 5. Creates 4th persona (succeeds)
# 6. Makes voice call (succeeds)
# 7. Uses 100 voice minutes
# 8. Makes another call (overage charged)
```

---

## Migration Paths

### From Basic Config to Tier System

```javascript
// Migration script
async function migrateLegacyUsers() {
  // 1. Find users without subscription_tier
  const users = await db.execute({
    sql: 'SELECT * FROM users WHERE subscription_tier IS NULL'
  });

  // 2. Assign default tier based on features used
  for (const user of users.rows) {
    let tier = 'free';

    // Check if they have premium features
    const hasVoiceUsage = await hasUsedVoice(user.id);
    const personaCount = await countPersonas(user.id);

    if (hasVoiceUsage || personaCount > 3) {
      tier = 'personal'; // Grandfather them in
    }

    // Update tier
    await db.execute({
      sql: 'UPDATE users SET subscription_tier = ? WHERE id = ?',
      args: [tier, user.id]
    });
  }

  // 3. Create Stripe customers
  for (const user of users.rows) {
    if (!user.stripe_customer_id) {
      const customer = await stripe.customers.create({
        email: user.email,
        phone: user.user_phone,
        metadata: { user_id: user.id }
      });

      await db.execute({
        sql: 'UPDATE users SET stripe_customer_id = ? WHERE id = ?',
        args: [customer.id, user.id]
      });
    }
  }
}
```

---

## Related Documentation

- [tier-features.md](/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/docs/tier-features.md) - Complete tier feature specification
- [DATABASE_SCHEMA.md](/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/docs/planning/DATABASE_SCHEMA.md) - Database architecture details
- [FEATURES.md](/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/planning/FEATURES.md) - Feature roadmap and planning
- [HTTP_API.md](/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/planning/HTTP_API.md) - Complete API reference

---

## Summary

xSwarm is a **tier-based AI assistant platform** with:

✅ **4-tier subscription model** (Free → Personal → Professional → Enterprise)
✅ **Feature gating** enforced at API level with graceful upgrade prompts
✅ **Distributed architecture** (Rust client + Node.js server)
✅ **Semantic memory** with vector embeddings and 3-tier retention
✅ **Persona system** with Big Five traits and voice training
✅ **Multi-channel communication** (Voice, SMS, Email, API)
✅ **Project orchestration** for Professional+ users
✅ **Usage-based billing** with Stripe integration
✅ **Database-centric** (Turso libsql) with comprehensive schema
✅ **Scalable** architecture ready for production

**Core Principle**: Clean separation between subscription tiers, user data (database), project config (git-committed), and secrets (environment variables).
