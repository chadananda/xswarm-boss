# MOSHI Audio Investigation - Executive Summary

## Problem
MOSHI reports as "started" but generates **NO audio output** and **NO greeting**.

## Root Causes (4 Critical Issues)

### 1. TTS Model Not Loaded ❌
- **File:** `packages/core/src/tts.rs:64`
- **Issue:** TTS synthesis immediately returns error: `"TTS model not yet integrated"`
- **Impact:** Cannot convert text to audio (no greeting possible)

### 2. No Greeting Trigger ❌
- **File:** `packages/core/src/dashboard.rs:714-722`
- **Issue:** Voice system starts but never calls greeting generation
- **Impact:** Even if TTS worked, no code triggers it

### 3. No Audio Output Device ❌
- **File:** `packages/core/src/voice.rs` (missing)
- **Issue:** No CPAL or audio device integration
- **Impact:** Even if audio is generated, nowhere to play it

### 4. TTS Audio Not Routed ❌
- **File:** `packages/core/src/supervisor.rs:811-813`
- **Issue:** Generated audio not sent to output
- **Impact:** Audio dies in the pipeline

## What Works ✅

1. **MOSHI Conversational LM** - Loads successfully
2. **MIMI Codec** - Encodes/decodes audio correctly
3. **Reactive Audio Generation** - Works during conversations (Twilio input → MOSHI output)
4. **Amplitude Broadcasting** - Visualizers receive amplitude data
5. **Model Loading** - All conversational models warm up properly

## What's Missing ❌

1. **TTS Model** - Separate model for text-to-speech
2. **T5 Encoder** - Required for TTS text processing
3. **Audio Output Device** - CPAL integration for speakers
4. **Greeting Logic** - Code to generate greeting on startup
5. **Audio Routing** - Pipeline from TTS to speakers

## Quick Fix Checklist

```bash
# 1. Add CPAL dependency
echo 'cpal = "0.15"' >> packages/core/Cargo.toml

# 2. Create audio output module
touch packages/core/src/audio_output.rs

# 3. Update lib.rs
echo 'pub mod audio_output;' >> packages/core/src/lib.rs

# 4. Implement greeting generation in voice.rs

# 5. Trigger greeting in dashboard.rs startup

# 6. Test
cargo run --package xswarm-core
```

## Expected Result After Fix

```
INFO Initializing MOSHI voice models...
INFO MOSHI models initialized successfully
INFO Initializing audio output device
INFO Audio output device initialized
INFO Auto-starting MOSHI voice system
INFO Generating greeting audio...
INFO TTS generated 45 audio frames
INFO Playing greeting through speakers...
✅ Greeting audio played successfully!
INFO MOSHI voice system and microphone started
```

**User hears:** "Hello, how can I help you?" through speakers

## Implementation Priority

### Phase 1: Audio Output (CRITICAL)
- Add CPAL dependency ⏱️ 5 min
- Create `audio_output.rs` module ⏱️ 30 min
- Test audio playback ⏱️ 15 min

### Phase 2: Simple Greeting (HIGH)
- Generate tone-based greeting ⏱️ 15 min
- Trigger on startup ⏱️ 10 min
- Test end-to-end ⏱️ 10 min

### Phase 3: TTS Integration (MEDIUM)
- Load TTS model ⏱️ 1 hour
- Implement text-to-audio ⏱️ 2 hours
- Test full TTS pipeline ⏱️ 30 min

**Total estimated time:** 4-5 hours

## Files to Modify

1. `packages/core/Cargo.toml` - Add dependencies
2. `packages/core/src/audio_output.rs` - NEW - Audio device
3. `packages/core/src/lib.rs` - Add module
4. `packages/core/src/voice.rs` - Add greeting generation
5. `packages/core/src/dashboard.rs` - Trigger greeting
6. `packages/core/src/tts.rs` - Remove error stub

## Testing Command

```bash
# Run tests
cargo test --package xswarm-core

# Run dashboard with debug logs
RUST_LOG=debug cargo run --package xswarm-core

# Expected: Audible greeting + visual confirmation
```

## Troubleshooting

### "No audio output device available"
- Check speakers are connected
- Verify system audio enabled
- Test: `speaker-test -t wav -c 1` (Linux) or equivalent

### "TTS model not loaded"
- TTS is optional in Phase 1
- Use simple tone greeting as fallback
- Full TTS in Phase 3

### "Failed to play audio stream"
- Check audio permissions
- Close other apps using audio device
- Verify sample rate compatibility

## Documentation

- **Full Investigation:** `MOSHI_AUDIO_INVESTIGATION.md`
- **Implementation Plan:** `MOSHI_GREETING_IMPLEMENTATION_PLAN.md`
- **This Summary:** `MOSHI_AUDIO_SUMMARY.md`

## Key Insight

MOSHI **can** generate audio (it works reactively in conversations), but the **proactive audio pipeline** (TTS → Audio Output) is not implemented. All the pieces exist in separate modules - they just need to be connected!

---

**Status:** Ready for implementation
**Complexity:** Medium (mostly wiring existing components)
**Risk:** Low (core MOSHI functionality already works)
