# TO BE DONE - Current Development Status

**Last Updated:** 2025-01-16
**Current Version:** v0.1.7
**Status:** Moshi voice integration in progress, preparing for Intelligence Layer implementation

---

## Recent Progress (v0.1.7)

### ✅ Fixed - Import Error
**Problem:** `ModuleNotFoundError: No module named 'moshi'` on TUI startup
**Root Cause:** `assistant/voice/__init__.py` was importing from `moshi_pytorch` instead of `moshi_mlx`
**Solution:** Changed import to use `moshi_mlx` bridge (Apple Silicon optimized)
**Files Modified:**
- `packages/assistant/assistant/voice/__init__.py:5-6`
- `packages/assistant/pyproject.toml:3` (version 0.1.6 → 0.1.7)

**Test Results:**
- ✅ TUI starts without ImportError
- ✅ Moshi models load successfully (q8 quality, ~30-60s on M1/M2/M3)
- ✅ Dashboard renders with progress animation
- ✅ Version v0.1.7 displays correctly in status bar

---

## ✅ FIXED: Memory System Integration (v0.1.8)

**Issue:** `'MemoryManager' object has no attribute 'get_conversation_history'`

**Root Cause:**
There are TWO MemoryManager classes in the codebase:
1. `assistant/memory.py` - Has `get_conversation_history()` ✅
2. `assistant/memory/client.py` - Missing `get_conversation_history()` ❌

The `memory/__init__.py` exports `MemoryManager` from `client.py`, so all imports were using the incomplete version.

**Fix Applied:**
Added `get_conversation_history()` method to `MemoryManager` in `packages/assistant/assistant/memory/client.py:387-421`

The method:
- Calls `get_context()` to retrieve messages
- Formats them as conversation history string
- Returns formatted string for LLM context

**Files Modified:**
- `packages/assistant/assistant/memory/client.py` (added missing method)

**Test Results:**
- ✅ TUI starts without errors
- ✅ Memory system initializes (`✅ Memory system initialized`)
- ⏳ Moshi models loading (takes 30-60s on M1/M2/M3)
- ⏳ Need to wait for model load to test greeting generation

---

## Next Steps (Priority Order)

### 1. **Complete Moshi Voice Integration** (HIGH - In Progress)
- [x] ~~Fix Memory System Integration~~ ✅
- [ ] Wait for Moshi models to load (~30-60s)
- [ ] Test greeting generation works
- [ ] Verify Moshi audio playback works
- [ ] Verify microphone input works
- [ ] Test full voice conversation flow
- [ ] Verify audio I/O pipeline
- [ ] Test wake word detection
- [ ] Verify persona voice switching
- [ ] Performance optimization (if needed)

### 3. **Intelligence Layer Preparation** (NEXT PHASE)
See `docs/INTELLEGENCE_LAYER.md` for full specification.

**Overview:** Dynamic intelligence engine selection (local LLM or API) based on hardware detection.

**Key Capabilities:**
- Automatic VRAM detection (Windows/Linux/Mac)
- Intelligence level assignment (0-6 based on available VRAM)
- Model download and management (Qwen2.5 family)
- llama.cpp/Ollama integration
- API routing for low-resource systems
- Context memory management

**NOT implementing yet** - waiting for Moshi voice to be fully functional first.

---

## Technical Debt

### Code Quality
- [ ] Add error handling for Memory system calls
- [ ] Add logging for greeting generation process
- [ ] Add unit tests for Memory API integration
- [ ] Add integration tests for Moshi voice pipeline

### Documentation
- [x] Create TBD.md status document
- [ ] Document Memory system API changes
- [ ] Update architecture docs with Memory integration details
- [x] Integrate Intelligence Layer roadmap into README

### Testing
- [ ] Run audio pipeline tests (`tests/test_audio_pipeline.py`)
- [ ] Create Moshi integration tests
- [ ] Add CI/CD for automated testing

---

## Development Environment Notes

**Platform:** macOS (Darwin 23.4.0)
**Hardware:** Apple Silicon (M-series)
**Python:** 3.11+
**Git Branch:** main
**Working Directory:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss`

**Modified Files (Uncommitted):**
```
M .claude/settings.local.json
M docs/README.md
M packages/assistant/assistant/voice/moshi_mlx.py
M packages/assistant/pyproject.toml
?? docs/MOSHI_DOWNLOAD_STATUS.md
?? docs/moshi-model-download-lessons.md
?? packages/assistant/assistant/voice/parallel_download.py
?? packages/assistant/assistant/voice/robust_download.py
?? packages/assistant/assistant/voice/verified_fast_download.py
?? TBD.md
```

**Recent Commits:**
```
a56b514 fix(voice): use moshi_mlx bridge instead of moshi_pytorch
76686d7 fix: integration bugs for Memory and Persona initialization
fae6a5a feat(tools): add persona switching via AI function calling
ee7593f feat(memory): add thinking service with AI-filtered memory
af912fd feat(voice): integrate Moshi bridge with TUI dashboard
```

---

## Workflow Reminders

**Before Terminal Restart:**
1. ✅ Create TBD.md with current status
2. ✅ Update README.md with Intelligence Layer roadmap
3. Commit documentation changes
4. Note current issue: Memory system integration

**After Terminal Restart:**
1. Read TBD.md for context
2. Review git status
3. Continue with Memory system investigation
4. Fix greeting generation error
5. Test Moshi audio playback

---

## Questions for Next Session

1. When was the Memory system API last changed?
2. Is there a migration guide for the new Memory API?
3. Should `.get_conversation_history()` be replaced with a different method?
4. Are there other places using the old Memory API that need updating?

---

**End of Status Document**
