# Development Guide

Guide for developing xSwarm-boss on macOS (M1/M2/M3) and Linux.

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/chadananda/xswarm-boss.git
cd xswarm-boss

# 2. Install dependencies
just setup

# 3. Create .env file (optional - only if you need API keys)
cp .env.example .env
# Edit .env with your API keys (optional for initial development)

# 4. Build everything
just build

# 5. Run the CLI
cargo run -- theme list
```

## Development Environment Options

### Option 1: Native macOS (Recommended for Starting)

**Best for:**
- Core Rust development
- Theme system work
- Documentation
- CLI functionality

**Setup:**

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Node.js and pnpm
brew install node
npm install -g pnpm

# Install just task runner
brew install just

# Install cargo-watch (for auto-rebuild)
cargo install cargo-watch
```

**What works:**
- ✅ Rust compilation and testing
- ✅ CLI commands
- ✅ Theme system
- ✅ Documentation building
- ✅ Most core logic

**What doesn't work:**
- ❌ Linux-specific features (systemd)
- ❌ Package building (.deb, AUR)
- ❌ Final integration testing

### Option 2: Docker (Full Linux Environment)

**Best for:**
- Testing Linux-specific features
- Building packages
- Integration testing
- CI/CD simulation

**Setup:**

```bash
# Start all services
just dev

# Shell into development container
just docker-shell

# Inside container, you have full Arch Linux environment
cargo build
cargo test
```

**Services included:**
- Arch Linux dev container (Rust + Node.js)
- Meilisearch (port 7700)
- LibSQL (port 8080)

## Configuration vs Secrets

### Where Things Go

xSwarm-boss separates configuration from secrets:

**`.env` file (secrets only):**
- API keys (OpenAI, Anthropic, RunPod, etc.)
- Auth tokens (LibSQL, Meilisearch)
- Service credentials
- **Never committed to git**

**`~/.config/xswarm/config.toml` (configuration):**
- Theme selection (hal-9000, sauron, etc.)
- Voice settings (enabled, wake word, provider)
- Audio devices (input/output)
- GPU fallback chain
- Vassal/worker settings
- **Safe to share, backup, version control**

**Example `config.toml`:**
```toml
[overlord]
theme = "hal-9000"
voice_enabled = true
wake_word = "hey hal"

[voice]
provider = "openai_realtime"
model = "gpt-4o-realtime-preview"
include_personality = true

[audio]
input_device = "default"
output_device = "default"
sample_rate = 16000

[wake_word]
engine = "porcupine"
sensitivity = 0.5

[gpu]
use_local = false
fallback = ["runpod", "anthropic"]

[vassal]
# Vassal config set during 'xswarm setup --mode vassal'
# Not needed for overlord-only setups
name = "speedy"
host = "0.0.0.0"
port = 9000
```

## API Keys and Services

### What You Need When

**NO API KEYS NEEDED** for:
- ✅ Theme development
- ✅ CLI functionality
- ✅ Documentation work
- ✅ Core Rust architecture
- ✅ Configuration system
- ✅ Testing most features

**API KEYS NEEDED** for:
- ❌ Voice interface
- ❌ AI-powered responses
- ❌ Personality implementations
- ❌ LLM conversations

### Voice Interface Options

#### Option 1: OpenAI Realtime API (RECOMMENDED)

**What it is:**
Direct voice-to-voice conversation with GPT-4. Speaks in real-time with personality instructions.

**Setup:**

```bash
# In .env (secrets only)
OPENAI_API_KEY=sk-proj-your-key-here

# In ~/.config/xswarm/config.toml
[voice]
provider = "openai_realtime"
model = "gpt-4o-realtime-preview"
include_personality = true
```

**Cost:**
- Audio input: ~$0.06/minute
- Audio output: ~$0.24/minute
- Total: ~$0.30/minute (~$18/hour)

**Pros:**
- ✅ Direct voice-to-voice (fast, natural)
- ✅ Can inject personality instructions
- ✅ Low latency
- ✅ One API call

**Cons:**
- ❌ More expensive
- ❌ Voice won't sound exactly like HAL/Sauron/etc
- ❌ Less control over voice characteristics

**Best for:** Quick prototyping, natural conversations

#### Option 2: Traditional Pipeline (STT → LLM → TTS)

**What it is:**
Speech-to-Text → Claude/GPT (with personality) → Text-to-Speech

**Setup:**

```bash
# In .env (secrets only)
OPENAI_API_KEY=sk-your-whisper-key
ANTHROPIC_API_KEY=sk-ant-your-claude-key
ELEVENLABS_API_KEY=your-elevenlabs-key

# In ~/.config/xswarm/config.toml
[voice]
provider = "pipeline"

[voice.pipeline]
stt_provider = "openai_whisper"  # or deepgram
llm_provider = "anthropic"        # Claude for personality
tts_provider = "elevenlabs"       # or openai_tts
```

**Cost (per minute):**
- Whisper STT: ~$0.006
- Claude API: ~$0.01-0.05
- ElevenLabs TTS: ~$0.30
- Total: ~$0.35-0.40/minute

**Pros:**
- ✅ Better voice quality (ElevenLabs)
- ✅ Can use Claude for personality (better than GPT-4)
- ✅ More control over each step
- ✅ Can clone specific voices

**Cons:**
- ❌ Higher latency (3 API calls)
- ❌ More complex setup
- ❌ Slightly more expensive

**Best for:** Production, specific voice requirements

#### Option 3: Local Voice (Free, Private)

**What it is:**
Run everything locally with open source models.

**Requirements:**
- GPU with 8GB+ VRAM
- Or accept CPU-only (slower)

**Setup:**

```bash
# In ~/.config/xswarm/config.toml
[gpu]
use_local = true

[voice]
provider = "local"

[voice.local]
stt_model = "whisper.cpp"
llm_model = "llama3-70b"  # or smaller
tts_model = "coqui-tts"
model_path = "~/.local/share/xswarm/models/"

# Install dependencies
brew install llama.cpp whisper.cpp
```

**Cost:** $0 (just electricity)

**Pros:**
- ✅ Completely free
- ✅ Fully private
- ✅ Works offline
- ✅ No rate limits

**Cons:**
- ❌ Requires powerful hardware
- ❌ Slower than API
- ❌ More setup complexity
- ❌ Voice quality varies

**Best for:** Privacy-focused, long-term use, offline work

### Wake Word Detection (Local, No API)

Wake word detection runs **locally** using Porcupine (or similar):

```toml
# In ~/.config/xswarm/config.toml
[wake_word]
engine = "porcupine"
sensitivity = 0.5  # 0.0 to 1.0
```

**Supported engines:**
- **Porcupine** (Picovoice) - Best accuracy, free tier
- **Snowboy** - Older but works
- **Vosk** - Open source alternative

No API key needed for wake words! This runs on your Mac.

## Recommended Development Path

### Phase 1: No API Keys (Week 1)

Focus on core functionality:

```bash
# 1. Build and test CLI
cargo run -- theme list
cargo run -- theme switch marvin
cargo run -- config show

# 2. Develop new themes
# Add files to packages/themes/your-theme/

# 3. Work on docs
cd packages/docs
pnpm dev  # http://localhost:4321

# 4. Core Rust architecture
# Implement task tracking, project management, etc.
```

### Phase 2: Add Text API (Week 2)

Add just Claude for text-based testing:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-your-key

# Test AI responses (no voice)
cargo run -- ask "what's my project status?"
```

**Cost:** ~$0.10-0.50 per dev session

### Phase 3: Add Voice (Week 3+)

Start with OpenAI Realtime for quick testing:

```bash
# In .env (secrets)
OPENAI_API_KEY=sk-proj-your-key

# In config.toml
[voice]
provider = "openai_realtime"

# Test voice
cargo run -- daemon
# Say: "Hey HAL, hello!"
```

**Cost:** ~$5-10 per dev session

### Phase 4: Optimize (Later)

Switch to pipeline for better quality:

```bash
# In .env (add secrets)
ANTHROPIC_API_KEY=sk-ant-your-key
ELEVENLABS_API_KEY=your-elevenlabs-key
DEEPGRAM_API_KEY=your-deepgram-key

# In config.toml
[voice]
provider = "pipeline"

[voice.pipeline]
stt_provider = "deepgram"
llm_provider = "anthropic"
tts_provider = "elevenlabs"
```

## Common Development Tasks

### Build Commands

```bash
# Build everything
just build

# Build in release mode
just build-release

# Build only Rust
cargo build --workspace

# Build only docs
cd packages/docs && pnpm build

# Watch and rebuild on changes
cargo watch -x 'run -- theme list'
```

### Testing

```bash
# Run all tests
just test

# Run only Rust tests
cargo test --workspace

# Run tests in Docker
just docker-test

# Run with verbose logging
RUST_LOG=debug cargo test
```

### Documentation

```bash
# Start docs dev server
cd packages/docs
pnpm dev

# Build docs
pnpm build

# Check for broken links
pnpm check
```

### Packaging

```bash
# Build .deb package
just package-deb

# Build static binaries
just package-static

# Build all packages
just package-all
```

## IDE Setup

### VS Code

**Recommended Extensions:**
- **rust-analyzer** - Rust IDE support
- **Even Better TOML** - TOML/YAML editing
- **Astro** - Documentation site
- **CodeLLDB** - Debugging

**Settings** (`.vscode/settings.json`):

```json
{
  "rust-analyzer.cargo.features": "all",
  "rust-analyzer.checkOnSave.command": "clippy",
  "[rust]": {
    "editor.formatOnSave": true
  },
  "rust-analyzer.lens.references.adt.enable": true,
  "rust-analyzer.lens.references.trait.enable": true
}
```

### CLion / RustRover

Works great out of the box. Just open the project directory.

## Troubleshooting

### "Failed to compile"

```bash
# Update Rust
rustup update

# Clean build
cargo clean
just build
```

### "Docker compose not found"

```bash
# Install Docker Desktop for Mac
brew install --cask docker
```

### "pnpm command not found"

```bash
npm install -g pnpm
```

### "Can't access microphone"

macOS requires permission:
1. System Settings → Privacy & Security → Microphone
2. Enable Terminal (or your IDE)

### Voice not working

```bash
# Check .env has correct keys
cat .env | grep OPENAI

# Test with debug logging
RUST_LOG=debug cargo run -- daemon

# Check audio devices
cargo run -- config audio-test
```

## Project Structure

```
xswarm-boss/
├── packages/
│   ├── core/           # Main Rust binary
│   ├── mcp-server/     # Secret isolation server
│   ├── indexer/        # Semantic search
│   ├── themes/         # Personality themes
│   └── docs/           # Astro documentation
├── distribution/       # Package configs
│   ├── systemd/       # systemd services
│   ├── aur/           # Arch Linux
│   ├── debian/        # .deb packages
│   └── flatpak/       # Flatpak
├── planning/          # Design docs
├── .env.example       # Environment template
└── justfile           # Task runner
```

## Next Steps

1. **Start without API keys** - Build core functionality
2. **Add Anthropic key** - Test text-based AI
3. **Add OpenAI key** - Test voice interface
4. **Iterate on themes** - Perfect personality responses
5. **Add features** - Multi-machine, memory, etc.

## Getting Help

- **GitHub Discussions:** Ask questions
- **Issues:** Report bugs
- **Discord:** (Coming soon)

## Cost Summary

**Minimum to get started:** $0

**With text AI:** ~$5-10/month (Anthropic)

**With voice AI:** ~$20-50/month (OpenAI Realtime or pipeline)

**For serious development:** ~$50-100/month (all services)

Start free, add services as needed!
