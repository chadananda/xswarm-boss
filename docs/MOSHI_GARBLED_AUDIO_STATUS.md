# MOSHI Garbled Audio - Investigation Status

**Date**: 2025-11-08
**Status**: ❌ UNRESOLVED - Audio still garbled
**Whisper API**: Cannot be trusted - hallucinates plausible text from garbled audio

## What Works

✅ **MLX (Python) implementation** - Produces clear, intelligible speech
✅ **moshi-cli gen.rs** - Produces clear, intelligible speech
✅ **Model loading** - No crashes, models load correctly
✅ **MIMI warmup fix** - Fixed decoder crash at frame 2 (separate issue)

## What Doesn't Work

❌ **Our voice.rs implementation** - Produces completely garbled audio
❌ **Audio quality** - Unintelligible despite Whisper API claiming otherwise

## Fixes Attempted

### 1. ✅ MIMI Warmup Fix (Resolved crash, NOT audio quality)
**File**: `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/voice.rs:361-363`

**Problem**: Warming up cloned model instances left actual instances uninitialized
**Fix**: Warm up actual `lm_model` and `mimi_model` instances
**Result**: Fixed crash at frame 2, but audio still garbled

### 2. ❌ Codebook Extraction Fix (Did NOT fix)
**File**: `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/voice.rs:1174`

**Problem**: Thought we were extracting wrong number of codebooks
**Fix**: Changed `step_codes.i((0, 0..input_codebooks, 0))` to `step_codes.i((0, .., 0))`
**Result**: Audio still garbled

## Configuration Comparison

### Both Load MIMI Identically
- **gen.rs:38**: `moshi::mimi::load(&args.mimi_model_file, Some(8), dev)?`
- **voice.rs:350**: `moshi::mimi::load(&config.mimi_model_file, Some(8), mimi_device)?`

### Both Use Same Codebook Count
- **gen.rs**: 8 codebooks
- **voice.rs**: 8 codebooks (`MIMI_NUM_CODEBOOKS`)

### Key Difference: LM Loading

**gen.rs:40 (WORKING - batch generation)**:
```rust
let lm_model = moshi::lm::load_lm_model(lm_config.clone(), &args.lm_model_file, dtype, dev)?;
```

**voice.rs:322 (GARBLED - streaming)**:
```rust
let mut lm_model = moshi::lm::load_streaming(&config.lm_model_file, dtype, &device)?;
```

**Analysis**:
- gen.rs uses `load_lm_model` for batch generation
- voice.rs uses `load_streaming` for real-time streaming
- This is CORRECT for our use case (streaming), but might explain configuration differences

## Test Outputs

### Latest Test with Codebook Fix
**File**: `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/moshi-codebook-fix-test.wav`
**Whisper API claimed**: "I don't think I've ever seen anything like this before."
**User verification**: Still completely garbled

### Previous Test with Warmup Fix
**File**: `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/moshi-verification-audio.wav`
**Whisper API claimed**: "I don't think I've ever seen anything like this before."
**User verification**: Completely garbled

### Pattern
- Whisper API consistently hallucinates the same transcription from garbled audio
- Cannot trust Whisper API for validation
- Must rely on human listening

## What We Know

1. **MLX uses SAME Rust MIMI backend** - So the codec itself works
2. **gen.rs produces clear audio** - So the Rust MOSHI code works
3. **Our streaming implementation is garbled** - Something specific to `load_streaming` or our loop structure
4. **Warmup was necessary but insufficient** - Fixed crash, not audio quality
5. **Codebook extraction matched gen.rs** - Still garbled

## Possible Remaining Issues

### 1. Streaming State Management
gen.rs is batch (all frames at once), we're streaming (frame by frame). Maybe:
- State isn't being maintained correctly between frames
- LM generator state is corrupted
- MIMI decoder state is out of sync

### 2. Text Token Forcing
We force specific text tokens during generation:
```rust
let text_token = lm_generator.step_(
    Some(prev_text_token),
    &codes,
    force_text_token,  // We force tokens, gen.rs doesn't
    None,
    None,
)
```

Maybe forcing text tokens breaks the audio generation?

### 3. Acoustic Delay
We process frames sequentially. Maybe acoustic delay isn't handled correctly?

### 4. Frame/Step Loop Structure
gen.rs has:
```rust
for start_index in 0..frames {
    encode_step()
    for step in 0..steps {
        lm.step_()
        decode_step()
    }
}
```

We have same structure, but maybe subtle difference in how we accumulate audio?

### 5. Generated vs Input Codebooks
- `input_audio_codebooks`: 8 (encoder output)
- `generated_audio_codebooks`: 8 (LM output)

Maybe these need to be different?

## Next Investigation Steps

1. **Compare LM generator creation** - How does gen.rs create the LM state vs our `load_streaming`?
2. **Add detailed audio token logging** - Log actual token values to see if they're reasonable
3. **Test without text forcing** - Let LM generate freely, see if audio improves
4. **Compare frame loop structure** - Ensure we're not missing any state updates
5. **Check if moshi-cli has a streaming example** - Look for official streaming code

## Files to Review

- `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/voice.rs:1120-1310` - Test mode generation loop
- `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/moshi/moshi-cli/src/gen.rs:100-125` - Working generation loop
- `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/moshi/moshi-core/src/lm.rs` - LM loading functions

## Current Hypothesis

The issue is likely in:
1. How we're managing LM generator state across frames
2. OR how we're forcing text tokens (maybe shouldn't force them?)
3. OR some subtle difference in how we call `step_()` vs gen.rs

It's NOT:
- ❌ MIMI configuration (same as gen.rs)
- ❌ Codebook count (verified to be 8 like gen.rs)
- ❌ Warmup (fixed, prevents crash but not audio quality)
- ❌ Candle vs MLX (MLX uses same Rust MIMI backend)

## Conclusion

We're close - the infrastructure is correct, models load, no crashes. The bug is subtle, likely in:
- LM state management across streaming frames
- Text token forcing interfering with audio generation
- Or some other subtle API usage difference from gen.rs

Needs deeper investigation into LM generator state and step_() call patterns.
