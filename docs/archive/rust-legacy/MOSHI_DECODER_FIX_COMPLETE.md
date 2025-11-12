# MOSHI Decoder Fix - Complete Summary

**Date**: 2025-11-08
**Status**: ✅ RESOLVED
**Audio Quality**: Clear and intelligible speech

## The Problem

MOSHI was producing garbled audio that failed with the error:
```
❌ Startup error: MIMI decode failed for frame 2 step 0
```

## Root Cause Analysis

The bug was in `packages/core/src/voice.rs` line 362:

```rust
// WRONG - warms up clones that get immediately dropped
Self::warmup(&mut lm_model.clone(), &mut mimi_model.clone(), &device, mimi_device)?;
```

### Why This Failed

MIMI is a **streaming codec** with internal encoder/decoder state that must be initialized before use. The warmup function calls:
1. `encode_step()` - initializes encoder state
2. `decode_step()` - initializes decoder state

However, we were warming up **cloned instances** of the models that were immediately dropped after warmup completed. This left the actual MIMI model instances with **uninitialized decoder state**.

When the decoder tried to process frame 2, it failed because it had never been properly initialized.

## The Fix

### Changes Made to `packages/core/src/voice.rs`

**1. Made models mutable (lines 322, 348)**:
```rust
let mut lm_model = moshi::lm::load_streaming(&config.lm_model_file, dtype, &device)?;
let mut mimi_model = moshi::mimi::load(&config.mimi_model_file, Some(MIMI_NUM_CODEBOOKS), mimi_device)?;
```

**2. Fixed warmup to use actual instances (lines 361-363)**:
```rust
// Warm up models - CRITICAL: Must warmup the actual instances, not clones!
// MIMI is a streaming codec with internal state that needs initialization.
Self::warmup(&mut lm_model, &mut mimi_model, &device, mimi_device)?;
```

**3. Updated comment (line 1460)**:
```rust
// MIMI is configured with 8 codebooks (matching moshi-cli gen.rs)
```

## Test Results

### Before Fix
```
❌ Error: MIMI decode failed for frame 2 step 0
```

### After Fix
```
✅ SUCCESS: Audio contains recognizable speech!

Configuration: config_1_ultra_high_quality
Transcription: "I don't think I've ever seen anything like this before."
Words detected: 10
Audio file: ./moshi-verification-audio.wav
```

## Technical Details

### Why MLX Worked

The MLX (Python) implementation doesn't use the same warmup pattern and manages model state differently. It directly calls MIMI without pre-warming clones.

### Why This Was Hard to Find

1. **Error message was misleading**: "MIMI decode failed" suggested a decoder configuration issue, not an initialization problem
2. **Encoder worked fine**: The encode path succeeded, masking the decoder initialization issue
3. **Clone pattern seemed safe**: Cloning models for warmup seems like a reasonable pattern for stateless models
4. **Consistent failure**: Error always at frame 2, suggesting configuration rather than state issue

### Key Learning

**For streaming codecs with internal state**:
- Initialization (warmup) must happen on the actual model instances that will be used
- Cloning and warming up copies leaves the originals uninitialized
- This pattern only works for truly stateless models

## Verification

To verify the fix works:

```bash
# Run MOSHI test
./target/release/xswarm --moshi-test

# Play generated audio
afplay ./moshi-verification-audio.wav
```

The audio should be clear, intelligible speech.

## Files Modified

- `packages/core/src/voice.rs` (4 changes on lines 322, 348, 361-363, 1460)

## Related Documentation

- Previous investigation: `docs/MOSHI_DECODER_ERROR_FINDING.md`
- Config comparison: `docs/MOSHI_CONFIG_COMPARISON.md`
- MLX comparison: `docs/MOSHI_MLX_COMPARISON_RESULT.md`

## Commit Message

```
fix(moshi): initialize decoder state by warming up actual model instances

MIMI is a streaming codec that requires encoder/decoder state initialization.
Previously we were warming up cloned model instances that were immediately
dropped, leaving the actual models with uninitialized decoder state.

This caused "MIMI decode failed for frame 2 step 0" errors because the
decoder tried to process frames without being properly initialized.

Fix: Warm up the actual lm_model and mimi_model instances instead of clones.

Closes: MOSHI garbled audio issue
Test: ./target/release/xswarm --moshi-test now produces clear speech
```
