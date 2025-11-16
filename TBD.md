# TO BE DONE - Current Development Status

**Last Updated:** 2025-01-16 (Terminal Session 2)
**Current Version:** v0.1.8
**Status:** Memory system fixed, Moshi voice integration testing phase

---

## ✅ COMPLETED: Memory System Integration (v0.1.8)

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

**Committed:**
```
4670ae1 fix(memory): add missing get_conversation_history() method to MemoryManager
```

**Test Results:**
- ✅ TUI starts without errors
- ✅ Memory system initializes (`✅ Memory system initialized`)
- ✅ No more AttributeError on greeting generation
- ⏳ Need to test full voice conversation flow

---

## Previous Progress (v0.1.7)

### ✅ Fixed - Import Error
**Problem:** `ModuleNotFoundError: No module named 'moshi'` on TUI startup
**Root Cause:** `assistant/voice/__init__.py` was importing from `moshi_pytorch` instead of `moshi_mlx`
**Solution:** Changed import to use `moshi_mlx` bridge (Apple Silicon optimized)

**Committed:**
```
a56b514 fix(voice): use moshi_mlx bridge instead of moshi_pytorch
```

**Test Results:**
- ✅ TUI starts without ImportError
- ✅ Moshi models load successfully (q8 quality, ~30-60s on M1/M2/M3)
- ✅ Dashboard renders with progress animation

---

## 🚧 CURRENT PHASE: Moshi Voice Integration Testing

### Priority Tasks (In Order)

1. **Test Greeting Generation** (NEXT)
   - Start TUI and wait for Moshi models to load (~30-60s)
   - Verify greeting generates without errors
   - Check audio playback of greeting
   - **Status:** Ready to test (Memory system now fixed)

2. **Verify Voice Conversation Flow**
   - Test microphone input capture
   - Test Moshi speech-to-text
   - Test LLM response generation
   - Test Moshi text-to-speech output
   - Test full conversation loop

3. **Test Wake Word Detection**
   - Verify "Hey HAL" (or current persona) wake word works
   - Test wake word sensitivity
   - Test false positive handling

4. **Test Persona Voice Switching**
   - Switch between personas (HAL, JARVIS, GLaDOS, etc.)
   - Verify voice profile changes correctly
   - Test persona-specific responses

5. **Add Error Handling & Logging**
   - Add try/catch for Memory system calls
   - Add logging for greeting generation process
   - Add logging for audio I/O pipeline
   - Handle Moshi model loading failures gracefully

6. **Run Audio Pipeline Tests**
   - Execute `tests/test_audio_pipeline.py`
   - Fix any failing tests
   - Create Moshi integration tests if needed

---

## 🔜 NEXT PHASE: Intelligence Layer (NOT Starting Yet)

See `docs/INTELLEGENCE_LAYER.md` for full specification.

**Overview:** Dynamic intelligence engine selection (local LLM or API) based on hardware detection.

**Key Capabilities:**
- Automatic VRAM detection (Windows/Linux/Mac)
- Intelligence level assignment (0-6 based on available VRAM)
- Model download and management (Qwen2.5 family)
- llama.cpp/Ollama integration
- API routing for low-resource systems
- Context memory management

**Intelligence Levels:**
- **Level 0**: <8GB VRAM - API routing (Claude Sonnet 4, Gemini Flash) - ~97% quality
- **Level 1**: 12-16GB VRAM - Qwen2.5-7B Q5_K_M - ~89% quality
- **Level 2**: 20-24GB VRAM - Qwen2.5-14B Q6_K - ~93% quality
- **Level 3**: 28-32GB VRAM - Qwen3-30B-A3B Q4_K_M - ~96% quality
- **Level 4**: 40-48GB VRAM - Qwen2.5-72B IQ4_XS - ~98% quality
- **Level 5**: 60-80GB VRAM - Qwen2.5-72B Q6_K/Q8_0 - ~99% quality
- **Level 6**: 12GB+ VRAM - Hybrid (best local + API fallback) - ~97% quality

**WAITING** for Moshi voice to be fully functional first.

---

## Technical Debt

### Code Quality
- [ ] Add error handling for Memory system calls
- [ ] Add logging for greeting generation process
- [ ] Add unit tests for Memory API integration
- [ ] Add integration tests for Moshi voice pipeline

### Documentation
- [x] Create TBD.md status document
- [x] Add Intelligence Layer roadmap (docs/INTELLEGENCE_LAYER.md)
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
M README.md
M packages/assistant/voice_assistant.egg-info/PKG-INFO
?? docs/INTELLEGENCE_LAYER.md
```

**Recent Commits:**
```
4670ae1 fix(memory): add missing get_conversation_history() method to MemoryManager
a56b514 fix(voice): use moshi_mlx bridge instead of moshi_pytorch
2a4188b feat(tui): improve startup UX with loading progress animation
90359f8 fix(voice): fix TUI exit crash and Moshi greeting generation
901adf2 fix(tui): use quality parameter in initialize_moshi()
```

---

## Workflow Reminders

**After Terminal Restart:**
1. ✅ Read TBD.md for context
2. ✅ Review git status
3. **START HERE:** Test greeting generation and Moshi voice integration
4. Work through priority tasks listed above
5. Commit changes incrementally

**Testing Commands:**
```bash
# Start TUI and test voice
cd packages/assistant
python -m assistant.dashboard.app

# Run audio pipeline tests
pytest tests/test_audio_pipeline.py -v

# Check Moshi model status
ls -lh ~/.cache/moshi/
```

**Known Issues:**
- None currently blocking - Memory system fix resolved the AttributeError
- Terminal corruption issue (requires restart to continue)

---

## Next Steps Summary

1. **IMMEDIATE:** Test greeting generation now that Memory system is fixed
2. **SHORT-TERM:** Complete full Moshi voice integration testing
3. **MEDIUM-TERM:** Add error handling and logging improvements
4. **LONG-TERM:** Begin Intelligence Layer implementation (Phase 5)

---

## Questions Resolved

1. ~~When was the Memory system API last changed?~~ - Found the issue and fixed it
2. ~~Is there a migration guide for the new Memory API?~~ - Not needed, fixed the missing method
3. ~~Should `.get_conversation_history()` be replaced with a different method?~~ - Method is correct, just was missing from client.py
4. ~~Are there other places using the old Memory API that need updating?~~ - No, the fix is complete

---

**End of Status Document**
