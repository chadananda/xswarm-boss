# MOSHI Audio Corruption - Investigation Status

**Date:** 2025-11-08
**Current Version:** v0.1.0-2025.11.8.2
**Status:** 🔴 BUG NOT FOUND - Multiple Hypotheses Ruled Out

---

## What We Know

### Audio Symptoms
- Garbled/unintelligible output
- Perfect statistical properties (mean: -21.4 dB, dynamic range: 92.2 dB)
- Whisper API hallucinates transcriptions (proves it's data corruption, not quality issue)
- User reports: "entirely garbled, almost sounds backwards"
- Duration: 2.48 seconds (expected for test)

### Test Results
- Test input: `./tmp/test-user-hello.wav` (user saying "hello")
- Expected output: MOSHI greeting
- Actual output: Garbled audio that Whisper transcribes as "and I'll see you in the next video. Take care."

---

## Hypotheses RULED OUT ❌

### 1. Encoder/Decoder State Sharing (v8.2)
**Hypothesis:** Encoder and decoder must share state for streaming codec
**Test:** Changed from cloned instance to shared `moshi_state.mimi_model`
**Result:** ❌ **FAILED** - Output was **byte-identical** to previous versions
**Evidence:**
- MD5 before: `4d49440e24fa4cf984df84d280e47413`
- MD5 after v8.2: `4d49440e24fa4cf984df84d280e47413` (SAME!)
- Proves this hypothesis was WRONG

**Files:**
- `docs/debugging/MOSHI_V8.2_PARADOX.md` - Full analysis
- voice.rs:1221, 1286 - Fix locations

### 2. Sample Reversal (Backwards Audio)
**Hypothesis:** Audio samples are being written in reverse order
**Test:** Reversed entire WAV file using `ffmpeg -af areverse`
**Result:** ❌ **FAILED** - Still totally garbled
**Evidence:**
- Original: `./tmp/moshi-v8.2-output.wav` (garbled)
- Reversed: `./tmp/moshi-v8.2-REVERSED.wav` (still garbled)
- MD5 of reversed: `feb936cf45c4718a61980f23d5934fef` (confirms reversal worked)
- User feedback: "nope, still totally garbled"

**Files:**
- `docs/debugging/MOSHI_BACKWARDS_HYPOTHESIS.md` - Test documentation
- `./scripts/reverse_audio.py` - Python reversal script (unused - numpy issues)
- Actual tool used: `ffmpeg -af areverse`

---

## Current Code Structure

### Tensor Shapes
```rust
// voice.rs:1281 - Audio token tensor creation
let audio_tensor = Tensor::from_slice(
    audio_tokens_slice,         // 8 codebook values from LM
    (1, generated_codebooks, 1), // Shape: (batch=1, codebooks=8, steps=1)
    &mimi_device,
)?;
```

### Encode Path (Test Mode)
```rust
// voice.rs:1147 - Encode user audio
let codes_stream = mimi_model.encode_step(&pcm_tensor.into(), &().into())?;

// voice.rs:1154 - Extract dimensions
let (_batch, _codebooks, num_steps) = codes_tensor.dims3()?;

// voice.rs:1168-1170 - Extract codes for each step
let step_codes = codes_tensor.i((.., .., step..step + 1))?;
let codes = step_codes.i((0, 0..input_codebooks, 0))?.to_vec1::<u32>()?;
```

### Decode Path (Test Mode - v8.2 Fixed)
```rust
// voice.rs:1286 - v8.2: Uses SAME model instance (not clone)
let decoded = moshi_state.mimi_model.decode_step(&audio_tensor.into(), &().into())?;

// voice.rs:1289 - Extract PCM samples
let frame_samples = pcm_tensor.flatten_all()?.to_vec1::<f32>()?;
all_audio_samples.extend(frame_samples);
```

---

## Remaining Hypotheses to Test

### 3. Codebook Ordering ⚠️ NOT TESTED
**Theory:** The 8 codebooks might be in the wrong order
**Evidence:**
- MIMI uses 8 codebooks (constant at voice.rs:85)
- Tensor shape is `(1, 8, 1)` - codebooks in middle dimension
- Maybe the order is wrong compared to official implementation

**How to test:**
1. Compare our codebook extraction with official MOSHI CLI
2. Try permuting codebook order (limited permutations to test)
3. Check if official MOSHI uses different indexing

**Likelihood:** Medium - codebook order mismatch could cause this

### 4. Tensor Dimension Permutation ⚠️ NOT TESTED
**Theory:** Maybe we're using `(batch, codebooks, steps)` but should use different order
**Evidence:**
- Encoder returns: `(batch, codebooks, steps)` per voice.rs:1151
- We create decode tensor as: `(1, codebooks, 1)`
- Maybe Metal/Candle expects different dimension order on Apple Silicon?

**How to test:**
1. Try `(codebooks, 1, 1)` instead of `(1, codebooks, 1)`
2. Try `(1, 1, codebooks)`
3. Check official MOSHI tensor shapes

**Likelihood:** Medium-High - dimension mismatch common cause of corruption

### 5. LM Audio Token Generation ⚠️ NOT TESTED
**Theory:** The language model is generating wrong/corrupt audio tokens
**Evidence:**
- Whisper transcribes something completely different from greeting
- "and I'll see you in the next video" sounds like training data leakage
- Maybe deterministic seed (299792458) is causing bad generation?

**How to test:**
1. Log the actual audio_tokens values from LM
2. Compare with official MOSHI CLI's audio tokens
3. Try different/random seed
4. Bypass LM entirely - decode known-good codes

**Likelihood:** Medium - LM could be generating wrong tokens

### 6. MIMI Metal/Apple Silicon Bug ⚠️ NOT TESTED
**Theory:** MIMI codec has bug specific to Metal/M-series chips
**Evidence:**
- Working on x86/CUDA but failing on Apple Silicon
- Candle Metal backend might have issues with MIMI operations
- Could be endianness, alignment, or precision issue

**How to test:**
1. Try CPU-only mode for MIMI (disable Metal)
2. Compare tensor values between encode/decode steps
3. Test official MOSHI CLI on same hardware
4. Check for Metal-specific tensor bugs in Candle

**Likelihood:** Low-Medium - platform-specific bugs are rare but possible

### 7. WAV Writing/Sample Format ⚠️ NOT TESTED
**Theory:** PCM samples are correct but WAV writing corrupts them
**Evidence:**
- Audio has perfect statistics but wrong content
- Maybe samples are being written with wrong format/encoding

**How to test:**
1. Export raw PCM data and load in audio editor
2. Compare WAV header with working audio
3. Try different bit depths (16-bit vs 32-bit float)
4. Test with different WAV libraries

**Likelihood:** Low - reversal test would have shown this

---

## Key Debug Locations

**Test mode entry:** voice.rs:1027-1028 (`--moshi-test` flag)
**MIMI encode:** voice.rs:1147
**Code extraction:** voice.rs:1168-1170
**LM generation:** voice.rs:1176-1204
**Audio token decode:** voice.rs:1279-1297
**WAV export:** voice.rs:1304-1327

---

## Files & Artifacts

### Test Audio Files
- Input: `./tmp/test-user-hello.wav` (user greeting)
- Output (garbled): `./tmp/moshi-v8.2-output.wav`
- Reversed (still garbled): `./tmp/moshi-v8.2-REVERSED.wav`

### Documentation
- `docs/debugging/MOSHI_V8.2_PARADOX.md` - State sharing failure
- `docs/debugging/MOSHI_BACKWARDS_HYPOTHESIS.md` - Reversal test
- `docs/debugging/MOSHI_ROOT_CAUSE_FOUND.md` - Original investigation
- This file: Investigation summary

### Test Logs
- `tmp/moshi-test-v8.2.log` - Latest test run showing "SUCCESS" (misleading!)

---

## Next Steps

**Priority 1:** Test codebook ordering
- Compare our implementation with official MOSHI CLI
- Try different codebook permutations

**Priority 2:** Test tensor dimension ordering
- Try different shapes for audio_tensor
- Verify against official implementation

**Priority 3:** Bypass LM to isolate issue
- Create test that encodes → immediately decodes
- Skip LM generation entirely
- Determines if bug is in MIMI or LM layer

**Priority 4:** Compare with official MOSHI CLI
- Build and run official CLI on same hardware
- Compare audio output quality
- If official also fails → upstream bug!

---

## Critical Questions

1. **Why did state sharing fix have ZERO effect?**
   → Suggests the bug isn't in MIMI state continuity

2. **Why does Whisper hallucinate coherent text from garbled audio?**
   → Proves it's data corruption, not just quality issues

3. **What does "almost sounds backwards" actually mean?**
   → Not literal reversal (tested), but maybe codebook order reversal?

4. **Why is the output byte-identical across different "fixes"?**
   → Deterministic seed (299792458) ensures reproducibility
   → Good for debugging but might mask some issues

---

**STATUS: Need new hypothesis. Codebook ordering is most promising next test.**
