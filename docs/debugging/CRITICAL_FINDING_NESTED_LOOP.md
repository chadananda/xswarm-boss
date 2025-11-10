# CRITICAL FINDING: Missing Nested Loop in MOSHI Audio Pipeline

**Date:** 2025-11-08
**Discovery:** Deep code comparison with official moshi-cli gen.rs

## The Issue

Our MOSHI audio test implementation is missing a **critical nested loop** structure that the official CLI uses.

### Official Pattern (gen.rs lines 100-119)

```rust
for start_index in 0..(in_pcm_len / 1920).min(max_steps) {
    let in_pcm = in_pcm.i((.., .., start_index * 1920..(start_index + 1) * 1920))?;
    let codes = mimi.encode_step(&in_pcm.into(), &().into())?;

    if let Some(codes) = codes.as_option() {
        let (_b, _codebooks, steps) = codes.dims3()?;  // ← CRITICAL: Get number of steps!

        for step in 0..steps {  // ← NESTED LOOP: Process each step individually
            let codes = codes.i((.., .., step..step + 1))?;
            let codes = codes.i((0, .., 0))?.to_vec1::<u32>()?;

            prev_text_token = state.step_(Some(prev_text_token), &codes, None, None, conditions.as_ref())?;

            if let Some(audio_tokens) = state.last_audio_tokens() {
                let audio_tokens = Tensor::new(&audio_tokens[..generated_audio_codebooks], dev)?
                    .reshape((1, 1, ()))?
                    .t()?;
                let out_pcm = mimi.decode_step(&audio_tokens.into(), &().into())?;
                if let Some(out_pcm) = out_pcm.as_option() {
                    out_pcms.push(out_pcm.clone());
                }
            }
        }
    }
}
```

### Our Current Pattern (voice.rs:1123-1220)

```rust
for frame_idx in 0..num_frames {
    // Create PCM tensor
    let pcm_tensor = Tensor::from_vec(frame_audio.clone(), (1, 1, frame_length), &mimi_device)?;

    let codes_stream = moshi_state.mimi_model.encode_step(&pcm_tensor.into(), &().into())?;

    let codes_tensor = match codes_stream.as_option() {
        Some(tensor) => tensor,
        None => { continue; }
    };

    // ❌ WRONG: Directly extract codes without checking steps dimension
    let codes = codes_tensor.i((0, 0..input_codebooks, 0))?.to_vec1::<u32>()?;

    // ❌ WRONG: Only one LM step per encode_step call
    let text_token = lm_generator.step_(
        Some(prev_text_token),
        &codes,
        force_text_token,
        None,
        None,
    )?;

    // ❌ WRONG: Only one decode per encode_step call
    if let Some(audio_tokens) = lm_generator.last_audio_tokens() {
        // ... decode once per frame
    }
}
```

## Why This Causes Garbled Audio

1. **`encode_step` may return multiple steps** - The codec dimension is `(batch, codebooks, steps)`
2. **We're only processing step 0** - Our `.i((0, 0..input_codebooks, 0))` extracts only the first step
3. **LM/decoder run out of sync** - We call LM once per frame instead of once per step
4. **Temporal alignment breaks** - Missing steps cause timing mismatches

## The Fix

We need to add the nested loop structure from the official CLI:

```rust
for frame_idx in 0..num_frames {
    // ... create pcm_tensor ...

    let codes_stream = moshi_state.mimi_model.encode_step(&pcm_tensor.into(), &().into())?;

    if let Some(codes_tensor) = codes_stream.as_option() {
        // ✅ NEW: Get dimensions to find number of steps
        let (_batch, _codebooks, num_steps) = codes_tensor.dims3()?;

        // ✅ NEW: Nested loop through each step
        for step in 0..num_steps {
            // ✅ NEW: Extract codes for THIS step only
            let step_codes = codes_tensor.i((.., .., step..step + 1))?;
            let codes = step_codes.i((0, 0..input_codebooks, 0))?.to_vec1::<u32>()?;

            // ✅ Now LM step is called once per STEP, not once per FRAME
            let text_token = lm_generator.step_(...)?;

            // ✅ Decode happens at correct frequency
            if let Some(audio_tokens) = lm_generator.last_audio_tokens() {
                // decode
            }
        }
    }
}
```

## Why Previous Fixes Failed

All v7.x fixes (reset_state, tensor transpose, debug logging) had **ZERO effect** because they were fixing the wrong part of the pipeline!

- v7.3: reset_state() → Doesn't fix temporal misalignment
- v7.4: Tensor transpose → Doesn't fix missing loop
- v7.5: Debug logging → Showed values looked correct because we never checked `steps` dimension

**The real issue was structural, not a matter of values or memory layout.**

## Expected Impact

Adding this nested loop should:
- ✅ Process ALL steps from encode_step, not just the first one
- ✅ Synchronize LM and decoder timing correctly
- ✅ Maintain proper temporal alignment
- ✅ Produce clear, intelligible audio

## Implementation Priority

**CRITICAL** - This is likely the root cause of ALL garbled audio issues.

Should implement immediately as v7.6.

---

**Status:** Found
**Next:** Implement nested loop fix in voice.rs
**Version:** Will be v0.1.0-2025.11.7.6
