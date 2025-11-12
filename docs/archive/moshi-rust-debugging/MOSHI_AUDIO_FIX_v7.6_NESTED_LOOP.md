# MOSHI Audio Fix v7.6 - Nested Loop Implementation

**Version:** 0.1.0-2025.11.7.6
**Date:** 2025-11-08
**Status:** ⏳ **TESTING** (Build in progress)

## The Root Cause

Deep code comparison with the official MOSHI CLI revealed a **critical structural difference**: We were missing a nested loop!

### Official CLI Pattern (gen.rs:100-119)

```rust
for start_index in 0..(in_pcm_len / 1920).min(max_steps) {
    let in_pcm = in_pcm.i((.., .., start_index * 1920..(start_index + 1) * 1920))?;
    let codes = mimi.encode_step(&in_pcm.into(), &().into())?;

    if let Some(codes) = codes.as_option() {
        let (_b, _codebooks, steps) = codes.dims3()?;  // ← Get number of steps!

        for step in 0..steps {  // ← NESTED LOOP: Process each step!
            let codes = codes.i((.., .., step..step + 1))?;
            let codes = codes.i((0, .., 0))?.to_vec1::<u32>()?;

            prev_text_token = state.step_(...)?;

            if let Some(audio_tokens) = state.last_audio_tokens() {
                // decode audio tokens
            }
        }
    }
}
```

### Our Previous Pattern (v7.0-v7.5)

```rust
for frame_idx in 0..num_frames {
    // ... create pcm_tensor ...

    let codes_tensor = moshi_state.mimi_model.encode_step(...)?;

    // ❌ NO NESTED LOOP - assumed exactly one step per frame!
    let codes = codes_tensor.i((0, 0..input_codebooks, 0))?.to_vec1::<u32>()?;

    // ❌ LM step runs ONCE per frame instead of ONCE per step
    let text_token = lm_generator.step_(...)?;

    // ❌ Decode runs ONCE per frame instead of at correct frequency
    if let Some(audio_tokens) = lm_generator.last_audio_tokens() {
        // decode
    }
}
```

## The Problem

1. **`encode_step` returns (batch, codebooks, steps)** - Not just one step!
2. **We only processed step 0** - Our indexing `.i((0, 0..input_codebooks, 0))` only extracted the first step
3. **LM/decoder timing was wrong** - Called once per frame instead of once per step
4. **Temporal alignment broken** - Missing steps caused audio corruption

## The Fix (v7.6)

```rust
for frame_idx in 0..num_frames {
    // ... create pcm_tensor ...

    let codes_stream = moshi_state.mimi_model.encode_step(&pcm_tensor.into(), &().into())?;

    if let Some(codes_tensor) = codes_stream.as_option() {
        // ✅ NEW: Get dimensions to find number of steps
        let (_batch, _codebooks, num_steps) = codes_tensor.dims3()?;

        // ✅ NEW: Nested loop through each step
        for step in 0..num_steps {
            // ✅ NEW: Extract codes for THIS specific step
            let step_codes = codes_tensor.i((.., .., step..step + 1))?;
            let codes = step_codes.i((0, 0..input_codebooks, 0))?.to_vec1::<u32>()?;

            // ✅ LM step now called once per STEP (correct frequency)
            let text_token = lm_generator.step_(...)?;

            // ✅ Decode happens at correct frequency
            if let Some(audio_tokens) = lm_generator.last_audio_tokens() {
                let audio_tensor = Tensor::new(audio_tokens_slice, &mimi_device)?
                    .reshape((1, 1, ()))?
                    .t()?;

                let decoded = mimi_decoder.decode_step(&audio_tensor.into(), &().into())?;
                // ... collect PCM samples ...
            }
        }
    }
}
```

## What Changed

**Modified:** `packages/core/src/voice.rs` (lines 1140-1247)

### Key Changes:

1. **Line 1145-1148:** Added `dims3()` call to get `num_steps` from encoded tensor
2. **Line 1159-1237:** Wrapped LM/decode logic in `for step in 0..num_steps` loop
3. **Line 1161-1164:** Extract codes for specific step using `.i((.., .., step..step + 1))`
4. **Line 1166-1168:** Added step logging for first frame to verify multiple steps are processed
5. **Line 1185, 1204, etc.:** Updated error messages to include step number for debugging

### Debug Logging Added:

- Line 1150-1152: Log number of steps on first frame
- Line 1166-1168: Log code extraction for first few steps
- Line 1195-1197: Log audio tokens with step number
- Line 1207-1210: Log tensor properties with step number
- Line 1220-1226: Log PCM stats with step number

## Why Previous Fixes Failed

All v7.x versions produced **IDENTICAL** output (MD5: 398fe04c3836ce2ce5fa217cd9b7792c) because:

- **v7.3 (reset_state):** Didn't fix temporal misalignment
- **v7.4 (tensor transpose):** Didn't fix missing loop
- **v7.5 (debug logging):** Never logged the `steps` dimension!

**The bug was structural, not a matter of values or memory layout.**

## Expected Behavior

With the nested loop, we expect:

1. ✅ **First frame logs:** "First frame has N steps from encode_step" (N > 1 likely)
2. ✅ **More LM steps:** LM called N times per frame instead of once
3. ✅ **More decode steps:** MIMI decoder called N times per frame
4. ✅ **More PCM samples:** Total samples should increase by factor of N
5. ✅ **Proper synchronization:** Audio timing should match input timing
6. ✅ **Clear audio:** Human-intelligible speech output
7. ✅ **Different MD5:** Output should differ from v7.5

## Test Plan

1. Build v7.6
2. Clean previous test output: `rm -f ./tmp/moshi-response.wav`
3. Run test: `xswarm --moshi-test`
4. Check logs for: "First frame has X steps"
5. Verify more PCM samples generated (compare total to v7.5)
6. Calculate MD5 and confirm it differs from v7.5
7. Listen to audio with `afplay`
8. If still garbled, transcribe with Whisper and compare

## Files Modified

- `packages/core/src/voice.rs` (lines 1140-1247) - Added nested loop
- `packages/core/Cargo.toml` (line 3) - Version bump to 0.1.0-2025.11.7.6
- `docs/debugging/CRITICAL_FINDING_NESTED_LOOP.md` (created) - Root cause analysis
- `docs/debugging/MOSHI_AUDIO_FIX_v7.6_NESTED_LOOP.md` (this file) - Implementation details

## Confidence Level

**HIGH** - This fix addresses a fundamental structural difference between our code and the official CLI that:

1. Was found through systematic code comparison
2. Explains ALL symptoms (temporal misalignment)
3. Explains why previous fixes had zero effect
4. Matches the official implementation pattern exactly

This is the most promising fix attempt yet.

---

**Next:** Test and verify audio quality
**Fallback:** If still garbled, we know the issue is NOT in the encode/decode loop structure
