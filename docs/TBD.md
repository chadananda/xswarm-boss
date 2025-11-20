# Current Status (TBD)

Quick reference for AI agents resuming work on this project.

**Version:** v0.3.90
**Last Updated:** 2025-11-19

---

## Active Development

### Current Focus: Documentation Reorganization

Restructuring docs/ for clarity:
- `docs/README.md` - Main architecture (done)
- `docs/TBD.md` - This file
- `docs/{assistant,server,voice}/README.md` - Subsystem architecture

### Recent Commits

```
ec9ccb0 docs: update README and moshi_research_report with current architecture
06c9858 feat(thinking): add Sonnet 4.5 summarization for terse context injection v0.3.90
b2f3d73 feat(thinking): add ThinkingEngine for tool/memory decisions v0.3.89
936e40f feat(voice): add transcript monitoring for thinking system v0.3.88
27102d8 fix(voice): faster is_server_running check with LINGER=0 v0.3.87
```

---

## Architecture State

### Three Subsystems

| Component | Status | Location |
|-----------|--------|----------|
| Assistant (Python TUI) | Active | `packages/assistant/` |
| Server (Cloudflare Workers) | Active | `packages/server/` |
| Voice (MOSHI MLX) | Active | `packages/voice/` |

### Key Integrations Working

- Authentication (JWT + email verification)
- Stripe billing (4 tiers + metered)
- Memory system (3-tier + embeddings)
- MOSHI voice (WebSocket bridge)
- Wake word detection
- Persona system (Big Five traits)
- ThinkingEngine (tool/memory decisions)

---

## Near-Term Tasks

### High Priority

1. **Complete docs reorganization** - READMEs for each subsystem
2. **Voice ↔ Assistant integration** - Full WebSocket flow testing
3. **Memory conditioning** - Semantic search → MOSHI context injection

### Medium Priority

4. **Phone integration** - Twilio → MOSHI bridge
5. **Calendar sync** - Google OAuth read/write
6. **Email management** - SendGrid inbound parsing

### Technical Debt

- Test coverage gaps (see tests/)
- Unused code cleanup (git status shows deletions staged)
- Config consolidation (config.toml vs .env)

---

## Known Issues

### Voice

- Model download requires good internet (use hf-transfer with `HF_XET_HIGH_PERFORMANCE=1`)
- First inference slow (model loading ~6-8s)
- 24kHz sample rate required (no resampling)
- MLX operations must run on main thread (not audio callback)

### Server

- Cloudflare Workers: no Node.js natives (use @noble/hashes, not crypto)
- Turso connection pooling needed for high traffic

### Assistant

- Terminal cleanup on TUI exit (Textual issue)
- Theme switching state persistence
- Background processes need proper shutdown

---

## File Locations

### Configuration

- `config.toml` - Main app config
- `wake-word.toml` - Wake word definitions
- `packages/server/.env` - Server secrets
- `packages/assistant/pyproject.toml` - Python dependencies

### Entry Points

- `packages/assistant/assistant/main.py` - TUI entry
- `packages/server/src/index.js` - Server routes
- `packages/voice/voice_server.py` - MOSHI bridge

### Key Modules

- `packages/assistant/assistant/thinking_engine.py` - Tool/memory decisions
- `packages/assistant/assistant/memory.py` - Embeddings + retrieval
- `packages/assistant/assistant/voice.py` - Audio I/O
- `packages/server/src/lib/features.js` - Tier gating

---

## Resume Commands

```bash
# Assistant
cd packages/assistant && pip install -e . && python -m assistant

# Server
cd packages/server && pnpm install && pnpm run dev

# Voice
cd packages/voice && pip install -e . && python voice_server.py

# Tests
cd tests && pytest assistant/

# Kill hanging processes
pkill -9 -f "python -m assistant"
```

---

## Context for AI Agents

### What This Project Is

Voice-first AI assistant with:
- TUI dashboard (Textual)
- MOSHI speech-to-speech (not TTS)
- 4-tier SaaS billing (Stripe)
- Semantic memory (embeddings)
- Personas (Big Five personality)

### What It's NOT

- Not the original Rust/Linux multi-machine architecture (see PRD in archive)
- Not using traditional STT→LLM→TTS pipeline
- Not a CLI replacement

### Key Design Decisions

1. **MOSHI direct speech**: Generates audio tokens, not text→TTS
2. **Python over Rust**: Easier iteration, Textual for TUI
3. **Cloudflare Workers**: Edge compute, but limits libraries
4. **Apple Silicon focus**: MLX for MOSHI inference

### Where to Find Things

- Historical planning: `docs/archive/`
- Personas: `personas/` (moved from packages)
- Tests: `tests/{assistant,server,voice}/`
- Scripts: `scripts/` (utilities, migrations)
- Implementation lessons: `docs/{assistant,server,voice}/` subfiles

---

## Development Notes

### Voice Pipeline (Fixed in v0.3.17)

```
Mic → audio_callback (queue only) → _moshi_input_queue
     → moshi_processing_loop (main thread) → step_frame()
     → _moshi_output_queue → moshi_playback_loop → Speakers
```

MLX GPU operations must run on main thread to avoid segfault.

### Thinking Engine (v0.3.89+)

ThinkingEngine decides when to use tools vs memory:
- Monitors conversation transcript
- Uses Sonnet 4.5 for terse context summarization
- Injects relevant context into MOSHI responses

### Debug Logs

```bash
tail -f /tmp/xswarm_debug.log     # Main debug
tail -f /tmp/moshi_timing.log     # Load timing
tail -f /tmp/moshi_text.log       # Transcriptions
```

---

## Version History

- **v0.3.90** - Sonnet 4.5 summarization for context injection
- **v0.3.89** - ThinkingEngine for tool/memory decisions
- **v0.3.88** - Transcript monitoring for thinking system
- **v0.3.87** - Faster voice server checks
- **v0.3.17** - Fixed MLX segfault (moved off audio callback)
- **v0.3.16** - Full-duplex MOSHI streaming

---

## Questions to Answer When Testing

1. Does MOSHI respond to voice input?
2. Does the visualizer update when speaking?
3. Is text transcription working? (check `/tmp/moshi_text.log`)
4. Is audio latency acceptable? (<500ms ideal)
5. Does the full conversation loop work?

---

**End of Status Document**
