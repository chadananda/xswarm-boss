# MOSHI Audio Garbling Fix - v14.0 (Tensor Handling)

**Date**: 2025-11-09
**Status**: ✅ Implemented, awaiting manual testing
**Version**: 0.1.0-2025.11.8.3

---

## The Root Cause

**Problem**: Garbled audio output from MOSHI on both Metal GPU and CPU

**Root Cause**: Creating new tensors for each audio frame instead of using tensor indexing

### Why This Breaks MOSHI

MIMI (the audio codec) is a **streaming codec** that maintains internal state between encode/decode steps. When we:

1. ❌ **Created new tensors** from Vec slices for each frame
2. ❌ Each new tensor had **inconsistent memory layout**
3. ❌ MIMI's streaming state became **corrupted**
4. ❌ Result: Garbled, backwards-sounding audio

**Correct Approach** (from gen.rs):
1. ✅ Create ONE tensor from entire audio upfront
2. ✅ Use tensor indexing (`.i()`) to extract frames
3. ✅ Preserves consistent memory layout
4. ✅ MIMI state remains valid across frames

---

## The Fix

### File: `packages/core/src/voice.rs`

### Change 1: Create Tensor Once (lines 1125-1139)

**BEFORE (BROKEN)**:
```rust
for frame_idx in 0..num_frames {
    let start_idx = frame_idx * frame_length;
    let end_idx = (start_idx + frame_length).min(user_audio.len());
    let mut frame_audio = user_audio[start_idx..end_idx].to_vec();  // ❌ Vec slice

    if frame_audio.len() < frame_length {
        frame_audio.resize(frame_length, 0.0);
    }

    let pcm_tensor = Tensor::from_vec(
        frame_audio.clone(),  // ❌ NEW tensor each iteration
        (1, 1, frame_length),
        &mimi_device,
    )?;
    // ... encode with this tensor
}
```

**AFTER (FIXED)**:
```rust
// v14.0 TENSOR FIX (CRITICAL): Create tensor ONCE like gen.rs, not per-frame
let frame_length = 1920;  // Hardcoded like gen.rs (24000 Hz / 12.5 fps)
let (in_pcm, in_pcm_len) = {
    let pcm_len = user_audio.len();
    let pcm = Tensor::from_vec(user_audio, (1, 1, pcm_len), &mimi_device)
        .context("Failed to create PCM tensor")?;
    (pcm, pcm_len)
};

let num_frames = (in_pcm_len / frame_length).min(2500);  // Like gen.rs max_steps
info!("MOSHI_TEST: Created PCM tensor with {} samples, processing {} frames ({}ms each)",
      in_pcm_len, num_frames, frame_length as f32 / 24.0);
```

### Change 2: Use Tensor Indexing (lines 1203-1210)

**BEFORE (BROKEN)**:
```rust
// Creates NEW tensor from Vec slice each iteration
let pcm_tensor = Tensor::from_vec(
    frame_audio.clone(),  // ❌ Inconsistent layout
    (1, 1, frame_length),
    &mimi_device,
)?;
```

**AFTER (FIXED)**:
```rust
// v14.0 TENSOR FIX: Use tensor indexing (.i()) instead of creating new tensors
for frame_idx in 0..num_frames {
    // Step 2a: Extract frame using tensor indexing (preserves memory layout)
    let pcm_tensor = in_pcm.i((.., .., frame_idx * frame_length..(frame_idx + 1) * frame_length))
        .context(format!("Failed to extract frame {} from tensor", frame_idx))?;

    let codes_stream = moshi_state.mimi_model.encode_step(&pcm_tensor.into(), &().into())
        .context("MIMI encode_step failed")?;
    // ...
}
```

---

## What Was Ruled Out

Through extensive debugging, we ruled out:

1. ✅ **Metal backend bug** - CPU produced identical garbled output
2. ✅ **Q8 GGUF model format** - It's the official Candle format
3. ✅ **Forced text tokens** (v13.0) - Removed, still garbled
4. ✅ **Config/vocab mismatch** (v12.0) - Fixed, still garbled
5. ✅ **Missing quality conditioning** (v12.0) - Added, still garbled

---

## The Diagnostic Journey

### Key Tests:
- **CPU vs Metal**: Both produced identical garbled audio → Not a backend bug
- **Official CLI**: Doesn't support Q8 GGUF format (safetensors only)
- **Python/MLX**: Uses Q4 safetensors and works (different implementation)
- **Line-by-line comparison**: Found tensor creation pattern difference

### The Discovery:

Comparing voice.rs with official gen.rs revealed:

**gen.rs pattern** (lines 100-126):
```rust
// Create tensor ONCE
let in_pcm = Tensor::from_vec(in_pcm, (1, 1, in_pcm.len()), &device)?;

// Use indexing to extract frames
for start_index in 0..(in_pcm_len / 1920).min(max_steps) {
    let in_pcm = in_pcm.i((.., .., start_index * 1920..(start_index + 1) * 1920))?;  // ✅
    let codes = mimi.encode_step(&in_pcm.into(), &().into())?;
    // ...
}
```

**Our pattern** (BEFORE fix):
```rust
// Create NEW tensor each iteration
for frame_idx in 0..num_frames {
    let frame_audio = user_audio[start_idx..end_idx].to_vec();  // ❌
    let pcm_tensor = Tensor::from_vec(frame_audio, ..., &mimi_device)?;  // ❌
    let codes = mimi.encode_step(&pcm_tensor.into(), &().into())?;
}
```

---

## Binary Location

**Installed at**: `~/.local/bin/xswarm`
**Version**: 0.1.0-2025.11.8.3
**Built**: 2025-11-09 18:08

---

## How to Test

### Simple Manual Test:

```bash
# Clean slate
rm -rf ./tmp/experiments/
rm -f ./tmp/moshi-response.wav

# Run in test mode
MOSHI_TEST_MODE=1 ~/.local/bin/xswarm --dev

# Should output: ./tmp/moshi-response.wav

# Listen to the audio
afplay ./tmp/moshi-response.wav

# Objective analysis (optional)
python3 scripts/analyze-waveform.py ./tmp/moshi-response.wav
```

### What to Listen For:

**If FIXED** ✅:
- Clear, intelligible male voice
- Natural speech cadence
- Responds to "hello" greeting

**If STILL BROKEN** ❌:
- Choppy, garbled audio
- "Backwards" sounding
- Room full of people talking simultaneously

---

## Expected Behavior

With the tensor fix, MOSHI should:
1. Load Q8 GGUF model successfully
2. Encode user audio (test-user-hello.wav) correctly
3. Generate natural speech response
4. Decode audio with proper temporal continuity
5. Write clear audio to ./tmp/moshi-response.wav

---

## If Still Garbled

If the audio is still garbled after this fix, we have ruled out:
- All Rust/Candle implementation issues we can find
- All configuration/model parameter mismatches
- All backend-specific bugs

**Fallback Option**: Switch to Python/MLX implementation
- User confirmed this is acceptable
- MLX works on Mac M3 with Q4 safetensors model
- Would eliminate Rust/Candle as variable

---

## Technical Details

### Frame Processing:
- **Frame length**: 1920 samples (hardcoded like gen.rs)
- **Sample rate**: 24000 Hz
- **Frame rate**: 12.5 fps (24000 / 1920)
- **Frame duration**: 80ms per frame

### Tensor Shape:
- **Input**: (1, 1, total_samples) - one big tensor
- **Frame slice**: (1, 1, 1920) - extracted via indexing
- **Memory layout**: Contiguous, preserved across frames

### MIMI Codec:
- **Encoder state**: Maintained across encode_step calls
- **Decoder state**: Maintained across decode_step calls
- **Codebooks**: 16 codebooks, 2049 vocab size per codebook
- **Frame rate**: 12.5 fps (consistent with 1920 samples @ 24kHz)

---

## References

### Files Modified:
- `packages/core/src/voice.rs:1125-1139` - Tensor creation
- `packages/core/src/voice.rs:1203-1210` - Tensor indexing

### Reference Implementation:
- `packages/moshi/moshi-cli/tmp/moshi-official/rust/moshi-cli/src/gen.rs:100-126`

### Previous Attempts:
- v8.x-v10.0: Various codec/config fixes
- v12.0: Config/vocab fixes
- v13.0: Removed forced text tokens
- v13.2: Added CPU testing
- v14.0: **Tensor handling fix** ⬅️ THIS ONE

---

## Status

✅ **Fix implemented**
✅ **Binary built and installed**
⏸️ **Awaiting manual testing**

Next: User runs manual test to verify audio quality
