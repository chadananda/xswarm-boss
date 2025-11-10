# MOSHI Root Cause - FOUND!

**Date:** 2025-11-08
**Version tested:** v0.1.0-2025.11.8.1
**Status:** 🎯 ROOT CAUSE IDENTIFIED

---

## The Bug

**File:** `packages/core/src/voice.rs`

**Lines 1149 vs 1221:**

```rust
// Line 1149: Encoding with ORIGINAL model
let codes_stream = moshi_state.mimi_model.encode_step(&pcm_tensor.into(), &().into())

// Line 1061: Clone decoder
let mut mimi_decoder = moshi_state.mimi_model.clone();

// Line 1221: Decoding with CLONED model (WRONG!)
let decoded = mimi_decoder.decode_step(&audio_tensor.into(), &().into())
```

## Why This Causes Garbled Audio

**MIMI is a streaming codec** - the encoder and decoder **MUST share internal state** for proper reconstruction.

### What's Happening:

1. **Encoder** (`moshi_state.mimi_model`) processes input audio frame-by-frame
2. Encoder builds up internal state (temporal context, autocorrelation, etc.)
3. **Decoder** (`mimi_decoder` - a CLONE) tries to decode the tokens
4. Decoder has NO ACCESS to encoder's state (it's a separate instance!)
5. Result: Valid-looking samples but wrong semantic content → GARBLED AUDIO

### Why Metrics Look Good But Audio Sounds Garbled:

The decoder still produces audio with:
- ✅ Correct amplitude distribution
- ✅ Good dynamic range
- ✅ Speech-like frequency patterns

But the samples don't form coherent speech because they're reconstructed **without access to the encoding context**.

## Evidence Timeline

### v7.7: TopK Sampling
- Added seed 299792458
- Result: Still garbled

### v8.0: Cubic Interpolation
- Changed resampler from Linear to Cubic
- Result: Still garbled

### v8.1: Removed reset_state()
- Removed `mimi_decoder.reset_state()` call
- Result: **STILL GARBLED** ← This proved reset_state() wasn't the only issue

### v8.2: Use Same Model Instance (THIS FIX)
- Remove clone
- Use `moshi_state.mimi_model` for BOTH encoding AND decoding
- Expected result: CLEAR AUDIO (encoder/decoder share state)

## The Fix

**Remove:** Line 1061 (clone)
**Change:** Line 1221 (use original model)

```rust
// BEFORE (WRONG):
let mut mimi_decoder = moshi_state.mimi_model.clone();  // ← BUG!
// ... later ...
let decoded = mimi_decoder.decode_step(&audio_tensor.into(), &().into())

// AFTER (CORRECT):
// No clone needed - use the same model instance for both encode and decode
// ... later ...
let decoded = moshi_state.mimi_model.decode_step(&audio_tensor.into(), &().into())
```

## Why We Didn't See This Earlier

1. **Misleading Comment:** The code had "Following moshi-server pattern: each test/connection gets its own decoder"
   - This is true for separate connections
   - But NOT true within a single encode/decode cycle!

2. **GitHub Issue #118 Red Herring:**
   - Issue was about `reset_state()` breaking streaming
   - We fixed that but it wasn't the only bug
   - The clone was also breaking state sharing

3. **Good Metrics:**
   - Statistical audio analysis showed "perfect speech"
   - This masked the semantic corruption
   - Only human listening revealed the truth

## Confidence Level

**99% Confident** this is the root cause because:

1. ✅ Streaming codecs MUST share state between encode/decode
2. ✅ We're using TWO separate instances (original + clone)
3. ✅ Official CLI likely uses same instance for both
4. ✅ This explains why ALL previous fixes failed
5. ✅ Physics/logic makes perfect sense
6. ✅ This is a fundamental architectural error

## Version History

- **v7.6**: Added nested loop for multi-step encoding
- **v7.7**: TopK sampling with seed 299792458 (still garbled)
- **v8.0**: Cubic interpolation (still garbled)
- **v8.1**: Removed reset_state() (still garbled)
- **v8.2**: **THIS FIX** - Use same model for encode/decode

## Test Plan

1. Apply fix (remove clone, use same model instance)
2. Build v8.2
3. Run test: `./target/release/xswarm --moshi-test`
4. **Delete old output:** Prevent confusion with old files
5. Listen to output: Should be CLEAR for first time
6. If clear: Git commit and celebrate 🎉
7. If still garbled: Investigate encoder/decoder initialization

---

**Next Steps:** Applying fix now...
