# Dev Mode - Local Development & Server Bypass

Dev mode (`--debug` flag) enables local development by bypassing the server and using local AI models, embeddings, and configuration.

## 🎯 Purpose

**Dev Mode** allows developers to:

1. **Develop offline** without server connectivity
2. **Use local models** (Ollama, sentence-transformers) - FREE
3. **Test locally** with .env configuration
4. **Bypass payment** requirements during development
5. **Iterate quickly** without API rate limits

**Production Mode** (default):

1. **Always online** - requires server connection
2. **Server-managed** models and thinking
3. **Pay-as-you-go** for AI services ($5 minimum)
4. **Rate limited** and usage tracked
5. **No .env** for end users

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Dev Mode                            │
│  (--debug flag, admin only, .env configured)                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐         ┌────────────────┐              │
│  │ Embedder     │────────▶│ Local Models   │              │
│  │              │         │ - sentence-    │              │
│  │ debug=True   │         │   transformers │              │
│  └──────────────┘         └────────────────┘              │
│                                                             │
│  ┌──────────────┐         ┌────────────────┐              │
│  │ Memory Client│────────▶│ Local APIs     │              │
│  │              │         │ - Ollama       │              │
│  │ debug=True   │         │ - Anthropic    │              │
│  │              │         │ - OpenAI       │              │
│  └──────────────┘         └────────────────┘              │
│                           (API keys in .env)                │
│                                                             │
│  ┌──────────────┐         ┌────────────────┐              │
│  │ Config       │────────▶│ .env file      │              │
│  │              │         │ (gitignored)   │              │
│  └──────────────┘         └────────────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     Production Mode                         │
│  (default, end users, no .env)                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐         ┌────────────────┐              │
│  │ Embedder     │────────▶│ Server API     │              │
│  │              │         │ /api/embed     │              │
│  │ debug=False  │         │ (OpenAI)       │              │
│  └──────────────┘         └────────────────┘              │
│                                                             │
│  ┌──────────────┐         ┌────────────────┐              │
│  │ Memory Client│────────▶│ Server API     │              │
│  │              │         │ /api/thinking  │              │
│  │ debug=False  │         │ (cost-based)   │              │
│  └──────────────┘         └────────────────┘              │
│                                                             │
│  ┌──────────────┐         ┌────────────────┐              │
│  │ Config       │────────▶│ No .env        │              │
│  │              │         │ (API keys on   │              │
│  │              │         │  server only)  │              │
│  └──────────────┘         └────────────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Usage

### Launch Dev Mode

```bash
# With debug flag
python -m assistant.dashboard.app --debug

# Or set environment variable
export DEBUG_MODE=1
python -m assistant.dashboard.app
```

### Launch Production Mode

```bash
# Default (no flag)
python -m assistant.dashboard.app

# Explicitly disable debug
python -m assistant.dashboard.app --no-debug
```

## ⚙️ Configuration

### .env File (Dev Mode Only)

```env
# ============================================================
# Thinking Service (dev mode only)
# ============================================================

# Light tier - fast and cheap
THINKING_ENGINE_LIGHT="ANTHROPIC:claude-haiku-4-5"

# Normal tier - balanced
THINKING_ENGINE_NORMAL="ANTHROPIC:claude-sonnet-4"

# Deep tier - maximum quality
THINKING_ENGINE_DEEP="ANTHROPIC:sonnet-4-5"

# ============================================================
# AI Provider API Keys (dev mode only)
# ============================================================

ANTHROPIC_API_KEY="sk-ant-..."
OPENAI_API_KEY="sk-..."

# ============================================================
# Embeddings (dev mode uses local, prod uses OpenAI)
# ============================================================

# OpenAI embeddings (for production fallback)
OPENAI_EMBEDDING_MODEL="text-embedding-3-small"

# Local embeddings (dev mode, free)
LOCAL_EMBEDDING_MODEL="all-MiniLM-L6-v2"

# ============================================================
# Ollama (optional, for FREE local inference)
# ============================================================

OLLAMA_BASE_URL="http://localhost:11434"

# Override thinking models to use Ollama
# THINKING_ENGINE_LIGHT="OLLAMA:llama3:8b"
# THINKING_ENGINE_NORMAL="OLLAMA:mixtral:8x7b"
# THINKING_ENGINE_DEEP="OLLAMA:llama3:70b"

# ============================================================
# Server (for production mode)
# ============================================================

SERVER_URL="http://localhost:3000"
```

### Dual-Mode Code Pattern

```python
from assistant.config import Config
from assistant.memory.memory_orchestrator import MemoryOrchestrator

# Initialize based on debug flag
config = Config(debug_mode=args.debug)

# Orchestrator automatically adapts to mode
orchestrator = MemoryOrchestrator(
    config,
    debug_mode=config.debug_mode
)

# In dev mode:
#   - Uses local embeddings (sentence-transformers)
#   - Uses local thinking (Ollama/Anthropic/OpenAI from .env)
#   - No server connection required

# In production mode:
#   - Uses server /api/embed
#   - Uses server /api/thinking
#   - Requires server connection
```

## 🎛️ Feature Flags

### Embeddings

| Mode       | Implementation              | Cost  | Speed |
|------------|-----------------------------|-------|-------|
| Dev        | sentence-transformers       | FREE  | Fast  |
| Production | OpenAI text-embedding-3-small | $0.02/M | Fast  |

### Thinking Service

| Mode       | Implementation              | Cost  | Provider Selection |
|------------|-----------------------------|-------|--------------------|
| Dev        | Local API (from .env)       | Varies | Hard-coded in .env |
| Production | Server API                  | $0.15-$30/M | Cheapest at runtime |

### Memory Storage

| Mode       | Implementation              | Persistence |
|------------|-----------------------------| ------------|
| Dev        | In-memory (stubbed)         | Session only |
| Production | Server LibSQL/Turso         | Permanent |

## 🛠️ Installation

### Dev Mode Dependencies

```bash
# Install Python packages
pip install sentence-transformers anthropic openai

# Install Ollama (optional, for local inference)
brew install ollama

# Pull models
ollama pull llama3:8b
ollama pull mixtral:8x7b
```

### Production Mode Dependencies

```bash
# Only need base packages
pip install anthropic  # For production AI client
pip install openai     # For production embeddings (server-side)

# No local models needed
```

## 🧪 Testing Dev Mode

### 1. Test Embeddings

```python
from assistant.memory.embedder import Embedder, EmbeddingConfig

# Dev mode (local)
config = EmbeddingConfig()
embedder = Embedder(config, debug_mode=True)

embedding = await embedder.embed("Hello world")
print(f"Dimension: {len(embedding)}")  # 384 (local model)

# Production mode (OpenAI)
config = EmbeddingConfig(openai_api_key="sk-...")
embedder = Embedder(config, debug_mode=False)

embedding = await embedder.embed("Hello world")
print(f"Dimension: {len(embedding)}")  # 1536 (OpenAI)
```

### 2. Test Thinking

```python
from assistant.memory.memory_client import MemoryClient
from assistant.config import Config

# Dev mode
config = Config(debug_mode=True)
client = MemoryClient(config)

# Uses local API from .env
memories = await client.filter_memories(
    level="light",
    context="User asking about colors",
    candidates=[...]
)
```

### 3. Test Full Pipeline

```bash
# Launch app in dev mode
python -m assistant.dashboard.app --debug

# Check debug indicator in TUI
# Should show: [DEBUG MODE] in header
```

## 🔍 Debugging

### Enable Verbose Logging

```python
import logging

# Set log level
logging.basicConfig(level=logging.DEBUG)

# Or specific modules
logging.getLogger('assistant.memory').setLevel(logging.DEBUG)
```

### Check Mode at Runtime

```python
from assistant.config import Config

config = Config()
print(f"Debug mode: {config.debug_mode}")
print(f"Server URL: {config.server_url}")
print(f"Embedder: {'local' if config.debug_mode else 'OpenAI'}")
```

### Common Issues

**Issue**: `sentence-transformers not installed`

```bash
# Solution
pip install sentence-transformers
```

**Issue**: `ANTHROPIC_API_KEY not set`

```bash
# Solution: Add to .env
echo 'ANTHROPIC_API_KEY="sk-ant-..."' >> .env
```

**Issue**: `Ollama connection refused`

```bash
# Solution: Start Ollama
ollama serve

# Or check if running
curl http://localhost:11434/api/tags
```

## 🔒 Security

### .env File Protection

```gitignore
# .gitignore
.env
.env.local
.env.development
```

### API Key Exposure

- **Dev mode**: API keys in .env (local only, never committed)
- **Production**: API keys on server only (never client-side)

### Debug Flag Validation

```python
# Only allow debug mode for admin users
if args.debug and not is_admin_user():
    raise PermissionError(
        "Debug mode requires admin privileges. "
        "Contact admin@xswarm.ai for access."
    )
```

## 📊 Mode Comparison

| Feature | Dev Mode | Production Mode |
|---------|----------|-----------------|
| **Server connection** | Optional | Required |
| **API keys** | Local (.env) | Server-side |
| **Embeddings** | Local (FREE) | OpenAI ($$$) |
| **Thinking** | Local/API | Server API |
| **Memory storage** | In-memory | LibSQL/Turso |
| **Cost tracking** | None | Full tracking |
| **Rate limiting** | None | Enforced |
| **Model selection** | Hard-coded | Dynamic (cheapest) |
| **Offline capable** | Yes | No |
| **End-user ready** | No | Yes |

## 🎯 When to Use Each Mode

### Use Dev Mode When:

✅ Developing new features locally
✅ Testing without server connection
✅ Iterating quickly (no rate limits)
✅ Using local Ollama models (free)
✅ Admin/developer with API keys

### Use Production Mode When:

✅ End-user deployment
✅ Production environment
✅ Cost tracking required
✅ Server-managed models
✅ Rate limiting needed
✅ No local API keys available

## 📚 Related Documentation

- [THINKING_SERVICE.md](./THINKING_SERVICE.md) - Thinking service architecture
- [MOSHI_MEMORY.md](./MOSHI_MEMORY.md) - Memory strategy
- [CONFIGURATION.md](./CONFIGURATION.md) - Complete config reference

## 🚦 Status

**Phase 2 (Thinking Service)**: ✅ Core Complete

Dev mode is fully implemented for:
- [x] Embedder (local sentence-transformers)
- [x] Memory client (local Ollama/Anthropic/OpenAI)
- [x] Memory orchestrator (dual-mode)
- [x] Configuration (.env parsing)
- [x] Conversation loop (automatic mode detection)

Production mode is ready for:
- [x] Server-based embeddings
- [x] Server-based thinking
- [x] Cost tracking and optimization
- [ ] Full integration testing (Phase 2.9)
