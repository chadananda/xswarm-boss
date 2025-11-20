# xSwarm Boss Architecture

Voice-first AI assistant platform with personality-driven personas, semantic memory, and multi-channel communication.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    xSwarm Boss Platform                      │
├─────────────────┬──────────────────┬────────────────────────┤
│   Assistant     │     Server       │        Voice           │
│   (Python TUI)  │ (Cloudflare JS)  │    (Python MLX)        │
├─────────────────┼──────────────────┼────────────────────────┤
│ • Dashboard     │ • Auth/JWT       │ • MOSHI Speech-to-     │
│ • Chat panels   │ • Stripe billing │   Speech (24kHz)       │
│ • Wake word     │ • Email/SendGrid │ • Apple Silicon        │
│ • Voice I/O     │ • Calendar OAuth │   optimized (MLX)      │
│ • Thinking      │ • Feature gating │ • WebSocket bridge     │
│   engine        │ • Turso database │ • 200ms latency        │
└─────────────────┴──────────────────┴────────────────────────┘
```

## Architecture

### Three Autonomous Subsystems

| Component | Location | Tech Stack | Purpose |
|-----------|----------|------------|---------|
| **Assistant** | `packages/assistant/` | Python + Textual | Voice-interactive TUI dashboard |
| **Server** | `packages/server/` | JS + Cloudflare Workers | Auth, billing, APIs, email |
| **Voice** | `packages/voice/` | Python + MLX | MOSHI speech-to-speech bridge |

### Communication Flow

```
User ←→ Assistant TUI ←→ Voice Server (WebSocket)
              ↓
        Server API (HTTP)
              ↓
      Turso DB / Stripe / SendGrid
```

## Technology Stack

### Assistant (Python TUI)

- **Framework**: Textual (modern terminal UI)
- **Voice I/O**: CPAL audio, WebSocket to MOSHI
- **Memory**: Embeddings + vector similarity (OpenAI ada-002)
- **Tools**: Email, phone (Twilio), calendar, personas

### Server (Cloudflare Workers)

- **Runtime**: Cloudflare Workers (edge compute)
- **Database**: Turso (libsql/SQLite, distributed)
- **Auth**: JWT + PBKDF2 (100k iterations, OWASP)
- **Payments**: Stripe (4-tier subscriptions + metered billing)
- **Email**: SendGrid (transactional + inbound parsing)
- **Calendar**: Google OAuth for read/write access

### Voice (MOSHI MLX)

- **Model**: Kyutai MOSHI 7B (speech-to-speech, NOT TTS)
- **Codec**: Mimi (24kHz → 12.5Hz tokens, 8 codebooks)
- **Hardware**: Apple Silicon (M1/M2/M3), 4-bit quantization
- **Latency**: ~200ms end-to-end
- **Interface**: WebSocket server for assistant connection

## Subscription Tiers

| Feature | Free | Personal ($20/mo) | Professional ($190/mo) | Enterprise ($940/mo) |
|---------|------|-------------------|------------------------|----------------------|
| Voice Minutes | 0 | 100/mo | 500/mo | Unlimited |
| SMS Messages | 0 | 100/mo | 500/mo | Unlimited |
| AI Models | GPT-3.5 | GPT-4, Claude | GPT-4 Turbo, Opus | All + Custom |
| Custom Personas | 3 | Unlimited | Unlimited | Unlimited |
| Memory Retention | 30 days | 1 year | 2 years | Unlimited |
| Calendar | Read-only | Read/Write | Read/Write | Read/Write |
| Teams | - | - | Up to 10 | Unlimited |
| API Access | - | Basic | Full | Enterprise |

### Feature Gating

```javascript
import { hasFeature, checkLimit } from './lib/features.js';

if (hasFeature(user.subscription_tier, 'voice_minutes')) {
  const limit = checkLimit(tier, 'voice_minutes', currentUsage);
  if (!limit.allowed && !limit.overage_allowed) {
    return generateUpgradeMessage('voice_minutes', tier);
  }
}
```

## Database Schema

### Core Tables

- **users** - Subscription tier, Stripe IDs, contact info
- **personas** - Big Five traits, voice config, response style
- **memory_sessions** - Conversation summaries + embeddings
- **memory_facts** - Extracted knowledge with confidence scores
- **memory_entities** - People, places, projects, relationships
- **tasks** - Todo items with priority and status
- **calendar_tokens** - OAuth tokens for Google/Microsoft
- **usage_records** - Metered billing (voice/SMS/API calls)

### Memory Architecture (3-Tier)

```
┌─────────────────────────────────────┐
│  Working Memory (In-Context)        │
│  Last 5-10 messages, ~1-2K tokens   │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Session Summary (Rolling)          │
│  Compressed every 10 messages       │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Long-Term Memory (Vector DB)       │
│  Embeddings, tier-based retention   │
└─────────────────────────────────────┘
```

### Memory Retrieval Scoring

```
Score = (Similarity × 0.6) + (Recency × 0.3) + (Frequency × 0.1)
```

## Voice Processing (MOSHI)

**Critical**: MOSHI is a unified speech-to-speech model, NOT traditional STT→LLM→TTS.

### Pipeline

```
User speaks → Mimi encoder → LM step → Mimi decoder → Audio out
     │                          │
     └── 8 codebooks ──────────→│
                                 └── Audio tokens generated directly
```

### Three Voice Mechanisms

1. **Greetings** (Scripted) - Force specific text tokens
2. **Memory Context** - Condition::AddToInput for semantic search results
3. **STT Background** - Async transcription for memory storage only

### Key Parameters

- Sample rate: 24kHz
- Audio codebooks: 8
- Model: kyutai/moshika-mlx-q4 (4-bit quantized)
- Latency: ~200ms on Apple Silicon

## Persona System

### Big Five Personality Traits

```json
{
  "extraversion": 0.7,
  "agreeableness": 0.8,
  "conscientiousness": 0.6,
  "neuroticism": 0.3,
  "openness": 0.9,
  "formality": 0.5,
  "enthusiasm": 0.7
}
```

### Response Style

```json
{
  "verbosity": "Balanced",
  "tone": "Friendly",
  "humor_level": 0.5,
  "technical_depth": 0.5,
  "empathy_level": 0.5,
  "proactivity": 0.5
}
```

### Available Personas

Located in `personas/` directory:
- **boss/** - Default professional assistant
- **jarvis/** - Formal British butler
- **glados/** - Sarcastic testing AI
- **hal-9000/** - Calm and ominous
- **c3po/** - Anxious protocol droid
- **tars/** - Adjustable humor
- And more...

## Security

### Authentication

- JWT tokens (7-day expiration)
- PBKDF2 hashing (100k iterations)
- Email verification (24-hour tokens)
- Password reset (1-hour tokens)
- Token version management for instant invalidation

### Feature Gating

All tier-restricted features enforced at API level:
- Middleware checks subscription tier
- Graceful upgrade prompts
- Usage tracking for metered billing

### Data Protection

- User data isolation enforced by database indexes
- GDPR-compliant deletion endpoints
- Automatic memory cleanup based on tier retention

## Development

### Local Setup

```bash
# Assistant (Python TUI)
cd packages/assistant
pip install -e .
python -m assistant

# Server (Cloudflare Workers)
cd packages/server
pnpm install
pnpm run dev  # http://localhost:8787

# Voice (MOSHI)
cd packages/voice
pip install -e .
python -m voice_server
```

### Environment Variables

```bash
# Server
JWT_SECRET=<openssl rand -base64 64>
TURSO_DATABASE_URL=libsql://...
TURSO_AUTH_TOKEN=...
STRIPE_SECRET_KEY=sk_...
SENDGRID_API_KEY=SG....

# Assistant
OPENAI_API_KEY=sk-...

# Voice
HF_XET_HIGH_PERFORMANCE=1  # Fast model downloads
```

### Database Migrations

```bash
cd packages/server
node scripts/migrate-db.js
```

## Directory Structure

```
xswarm-boss/
├── docs/
│   ├── README.md          # This file (architecture)
│   ├── TBD.md             # Current tasks, crash recovery
│   ├── assistant/         # TUI documentation
│   ├── server/            # Server documentation
│   ├── voice/             # Voice/MOSHI documentation
│   └── archive/           # Historical planning docs
├── packages/
│   ├── assistant/         # Python TUI app
│   ├── server/            # Cloudflare Workers server
│   └── voice/             # MOSHI voice bridge
├── personas/              # Shared persona configurations
├── tests/                 # Test suites
└── scripts/              # Utility scripts
```

## Key Implementation Details

### Challenging Technologies

Each subsystem has documented lessons learned:

- **Voice**: Model downloading on weak internet (chunk verification, hf-transfer)
- **Server**: Cloudflare Workers compatibility (no Node.js natives)
- **Assistant**: Textual TUI theming and responsive layouts

See individual README files in `docs/assistant/`, `docs/server/`, `docs/voice/` for detailed implementation guides.

## API Reference

### Authentication Endpoints

```
POST /auth/signup          - Register with email verification
POST /auth/verify-email    - Confirm email address
POST /auth/login           - Get JWT token
POST /auth/logout          - Invalidate token
POST /auth/forgot-password - Request reset
POST /auth/reset-password  - Set new password
GET  /auth/me              - Get current user
```

### Memory Endpoints

```
POST /api/memory/store     - Store conversation
POST /api/memory/retrieve  - Get relevant context
GET  /api/memory/stats     - Memory statistics
POST /api/memory/facts     - Store extracted fact
DELETE /api/memory/all     - GDPR deletion
```

### Core Endpoints

```
GET  /users/:id           - Get user profile
GET  /personas            - List user personas
POST /personas            - Create persona
GET  /calendar/events     - Get calendar events
GET  /billing/subscription - Get subscription info
POST /billing/checkout    - Create Stripe session
```

## Performance Targets

- Voice latency: <200ms (Apple Silicon)
- API response: <100ms
- Memory search: <50ms
- Dashboard: 60fps
- Startup: <2 seconds

## Deployment

### Server (Cloudflare Workers)

```bash
cd packages/server
wrangler deploy
wrangler secret put JWT_SECRET
wrangler secret put STRIPE_SECRET_KEY
```

### Voice Server

Local deployment on Apple Silicon machine with MOSHI model downloaded.

### Assistant

Distributed as Python package, runs on user's machine.

## References

- [MOSHI by Kyutai](https://kyutai.org/moshi/)
- [Textual TUI Framework](https://textual.textualize.io/)
- [Cloudflare Workers](https://workers.cloudflare.com/)
- [Turso Database](https://turso.tech/)
- [Stripe Billing](https://stripe.com/billing)
