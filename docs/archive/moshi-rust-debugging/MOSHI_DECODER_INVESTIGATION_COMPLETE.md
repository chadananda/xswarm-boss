# MOSHI Decoder Investigation - Complete Analysis

**Date:** 2025-11-08
**Platform:** M3 Mac (Apple Silicon Metal)
**Status:** 🔍 ROOT CAUSE IDENTIFIED

---

## Executive Summary

Comprehensive investigation into MOSHI garbled audio output. Through code analysis, GitHub issue research, and comparison with official implementation, we have identified **TWO CRITICAL BUGS** and documented Apple Silicon Metal considerations.

---

## Part A: MIMI Decoder Code Analysis

### Bug #1: INCORRECT STATE MANAGEMENT ⚠️ **CRITICAL**

**Location:** `packages/core/src/voice.rs:1062`

**Our Code (INCORRECT):**
```rust
let mut mimi_decoder = moshi_state.mimi_model.clone();
mimi_decoder.reset_state(); // ← BUG: This breaks streaming audio!
```

**Official Code (CORRECT - gen.rs:116-119):**
```rust
// NO reset_state() call - maintains continuous state across frames
let audio_tokens =
    Tensor::new(&audio_tokens[..generated_audio_codebooks], dev)?
        .reshape((1, 1, ()))?
        .t()?;
let out_pcm = mimi.decode_step(&audio_tokens.into(), &().into())?;
```

**Root Cause Analysis:**

From GitHub Issue #118, users reported "generated samples with streaming inference contain some noise" when decoding frames independently. The solution was to maintain streaming context:

```python
# Python fix that solved the issue:
with mimi.streaming(batch_size=1):
    # decoder maintains state across frames
```

In Rust, this translates to **NOT calling `reset_state()` between frames**. The MIMI decoder needs continuous state to properly reconstruct audio across frame boundaries.

**Why This Causes Garbled Audio:**

1. MIMI is a **streaming codec** - it expects continuous context
2. Resetting state between frames breaks temporal dependencies
3. Decoder loses the autocorrelation information needed for reconstruction
4. Results in valid-looking samples (good metrics) but wrong semantic content (garbled sound)

**Evidence:**

- ✅ GitHub Issue #118: Streaming decoder noise fixed by maintaining state
- ✅ Official gen.rs: No `reset_state()` calls in the decoding loop
- ✅ Our code comment says "CRITICAL - fixes garbled audio" but we HAVE garbled audio
- ✅ The comment is backwards - reset_state() CAUSES the problem, not fixes it!

### Tensor Creation Pattern (VERIFIED CORRECT)

**Our Code:**
```rust
let audio_tensor = Tensor::new(audio_tokens_slice, &mimi_device)?
    .reshape((1, 1, ()))?
    .t()  // ← Transpose is CORRECT
    .context(...)?;
```

**Official Code:**
```rust
let audio_tokens =
    Tensor::new(&audio_tokens[..generated_audio_codebooks], dev)?
        .reshape((1, 1, ()))?
        .t()?;  // ← They do the same thing
```

**Verdict:** Tensor creation is CORRECT and matches official implementation.

---

## Part B: Codebook Configuration Analysis

### Current Configuration (VERIFIED CORRECT)

**Location:** `packages/core/src/voice.rs:1162-1163`

```rust
let input_codebooks = moshi_state.lm_config.input_audio_codebooks as usize;
let generated_codebooks = moshi_state.lm_config.generated_audio_codebooks as usize;
```

**Verification from MIMI Fix (commit c7efafd):**

Previous commit message confirms correct codebook count:
```
fix: correct MIMI codebook count from 32 to 8
```

**Official MIMI Specification:**
- MIMI uses **8 codebooks** (not 32)
- Encoder produces 8-dimensional codes
- Decoder expects 8-dimensional input

**Evidence from code:**
```rust
// Line 1170: Extract 8 codes (input_codebooks = 8)
let codes = step_codes.i((0, 0..input_codebooks, 0))?.to_vec1::<u32>()?;

// Line 1199: Use 8 codes (generated_audio_codebooks = 8)
let audio_tokens_slice = &audio_tokens[..generated_codebooks.min(audio_tokens.len())];
```

**Verdict:** Codebook configuration is CORRECT. The value 8 matches MIMI specification.

---

## Part C: Debug Logging Analysis

### Existing Debug Logging (COMPREHENSIVE)

**Current implementation already has extensive logging:**

```rust
// Lines 1157-1159: First frame step count
if frame_idx == 0 {
    info!("MOSHI_TEST: First frame has {} steps from encode_step", num_steps);
}

// Lines 1173-1175: Code extraction
if frame_idx == 0 && step < 3 {
    info!("MOSHI_TEST: Frame {} Step {}: Extracted {} codes", frame_idx, step, codes.len());
}

// Lines 1202-1204: Audio token logging
if frame_idx < 3 && step == 0 {
    info!("MOSHI_DEBUG: Frame {} Step {}: Audio tokens: {:?}", frame_idx, step, audio_tokens_slice);
}

// Lines 1214-1217: Tensor properties
if frame_idx < 2 && step == 0 {
    info!("MOSHI_DEBUG: Frame {} Step {}: Tensor shape: {:?}, stride: {:?}",
          frame_idx, step, audio_tensor.shape(), audio_tensor.stride());
}

// Lines 1227-1233: PCM statistics
if frame_idx < 3 && step == 0 && !frame_samples.is_empty() {
    let min = frame_samples.iter().fold(f32::INFINITY, |a, &b| a.min(b));
    let max = frame_samples.iter().fold(f32::NEG_INFINITY, |a, &b| a.max(b));
    let mean = frame_samples.iter().sum::<f32>() / frame_samples.len() as f32;
    info!("MOSHI_DEBUG: Frame {} Step {}: PCM stats - samples={}, min={:.4}, max={:.4}, mean={:.6}",
          frame_idx, step, frame_samples.len(), min, max, mean);
}

// Lines 1238-1241: Progress updates
if frame_idx % 10 == 0 && step == 0 {
    info!("MOSHI_TEST: Frame {} Step {}/{}: Decoded {} PCM samples (total: {})",
          frame_idx, step + 1, num_steps, frame_len, all_audio_samples.len());
}
```

**Verdict:** Logging is already comprehensive. No additional logging needed - existing logs will help verify the fix.

---

## Apple Silicon Metal Considerations

### Research Findings

**From Web Search:**

1. **MOSHI is optimized for Apple Silicon**
   - Uses Metal for GPU acceleration
   - Rust implementation designed for on-device inference
   - MLX backend specifically targets M-series chips

2. **Metal-Specific Issues Found:**
   - No documented reports of Metal-specific garbling
   - Issue #118 affected PyTorch (not Metal-specific)
   - The bug pattern is implementation-agnostic

3. **Our Configuration:**
   ```rust
   let mimi_device = if self.config.use_cpu_for_mimi {
       candle::Device::Cpu
   } else {
       moshi_state.device.clone()  // Metal on M3 Mac
   };
   ```

**Verdict:** The bug is NOT Apple Silicon/Metal-specific. It's a state management bug that affects all platforms.

---

## Root Cause Summary

### Primary Bug: Decoder State Reset

**What's happening:**
1. We clone the MIMI decoder
2. We call `reset_state()` thinking it helps
3. This breaks streaming context
4. Each frame is decoded independently without temporal dependencies
5. Audio has correct statistical properties but wrong semantic content

**Why metrics look good but audio sounds garbled:**

The decoder still produces valid audio samples with:
- ✅ Correct amplitude distribution (-21.4 dB mean)
- ✅ Good dynamic range (92.2 dB)
- ✅ Speech-like zero crossing rate (0.092)
- ✅ Structured spectral content (flatness = 0.000)

But the samples don't form coherent speech because temporal dependencies are broken.

**Analogy:**
Imagine trying to reconstruct a movie by looking at each frame independently, without knowing what came before. Each frame might look like a valid image (good "metrics"), but the sequence won't make narrative sense (garbled "semantics").

---

## The Fix

### Change Required

**File:** `packages/core/src/voice.rs`
**Line:** 1062

**REMOVE:**
```rust
mimi_decoder.reset_state(); // Reset state for fresh test (CRITICAL - fixes garbled audio)
```

**REPLACE WITH:**
```rust
// DO NOT reset state - MIMI decoder needs continuous streaming context
// Resetting between frames breaks temporal dependencies and causes garbled audio
// See: GitHub Issue #118 - streaming decoder requires maintained state
```

**That's it.** One line removed.

---

## Testing Plan

### Verify the Fix

1. **Remove line 1062** (`mimi_decoder.reset_state()`)
2. **Rebuild:**
   ```bash
   touch packages/core/src/voice.rs
   cargo build --release -p xswarm
   ```

3. **Test:**
   ```bash
   rm -rf ./tmp/experiments ./tmp/moshi-response.wav
   ./target/release/xswarm --moshi-test
   ```

4. **Listen to output:**
   ```bash
   afplay ./tmp/moshi-response.wav
   ```

5. **Expected result:**
   - Audio should be clear and intelligible
   - Should say the expected greeting phrase
   - Whisper transcription should match actual audio content

### Validation Checklist

- [ ] Audio sounds clear when listening
- [ ] No garbling or noise
- [ ] Whisper transcription matches what you hear
- [ ] Audio metrics remain good (they should, they were already good)
- [ ] Determinism preserved (byte-for-byte identical with same seed)

---

## Additional Evidence

### GitHub Issue #118 Quote

> "generated samples with streaming inference contain some noise when I use a single frame for streaming inference"

**User's broken approach:** `mimi.decode(codes[:, :, idx:idx+1])` (independent frames)

**Working solution:**
```python
with mimi.streaming(batch_size=1):
    # decoding with maintained state
```

**User's confirmation:** "The samples are very good now :)"

### This Exactly Matches Our Bug

- ❌ Our code: Resetting state between frames (equivalent to independent frame decoding)
- ✅ Fix needed: Maintain continuous state (equivalent to streaming context)

---

## Confidence Level

**95% Confident** this is the root cause because:

1. ✅ Exact pattern match with documented GitHub issue
2. ✅ Official code doesn't call reset_state()
3. ✅ Our misleading comment suggests we added it to "fix" garbling
4. ✅ Symptoms match perfectly (good metrics, garbled output)
5. ✅ Apple Silicon is not the issue (affects all platforms)
6. ✅ Codebook config is correct
7. ✅ Tensor operations match official code
8. ✅ The physics makes sense (streaming codec needs continuous state)

---

## Files to Modify

1. `packages/core/src/voice.rs`
   - **Line 1062**: Remove `mimi_decoder.reset_state();`
   - **Line 1062**: Add explanatory comment

2. `packages/core/Cargo.toml`
   - **Line 3**: Update version to `0.1.0-2025.11.8.1`

---

## Version History

- v0.1.0-2025.11.6.2: Added forced text for testing
- v0.1.0-2025.11.7.7: Added TopK sampling, seed 299792458
- v0.1.0-2025.11.8.0: Changed to Cubic interpolation (didn't fix it)
- v0.1.0-2025.11.8.1: **THIS FIX** - Remove decoder state reset

---

## Next Steps

1. **IMMEDIATELY**: Remove the `reset_state()` call
2. **Build**: Compile v0.1.0-2025.11.8.1
3. **Test**: Run MOSHI test mode
4. **Listen**: Verify audio is clear
5. **Commit**: Git commit the fix
6. **Document**: Update architecture docs with streaming requirement
7. **Close**: Mark this issue as resolved

---

## Lessons Learned

1. **Trust the symptoms**: Good metrics + garbled audio = data corruption, not signal quality
2. **Compare with official code**: The official implementation is the ground truth
3. **Read the issues**: GitHub issues often document exact solutions
4. **Question the comments**: "CRITICAL - fixes garbled audio" was actually causing it
5. **Streaming codecs need state**: Never reset state mid-stream

---

**Investigation complete. Ready to apply fix.**
