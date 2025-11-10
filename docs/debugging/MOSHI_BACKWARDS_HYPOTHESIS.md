# MOSHI "Backwards" Audio Hypothesis - Test Ready

**Date:** 2025-11-08
**Status:** 🔬 HYPOTHESIS TEST READY

---

## The Critical Clue

User reported: **"entirely garbled. almost sounds backwards"**

This is a HUGE clue that could reveal the root cause!

---

## Test Setup

I've created a reversed version of the garbled audio to test if the samples are in the wrong order:

### Files to Test

1. **Original Garbled Audio:**
   `./tmp/moshi-v8.2-output.wav`
   - This is the byte-identical garbled output from v8.2
   - MD5: `4d49440e24fa4cf984df84d280e47413`
   - Duration: 2.48 seconds
   - Whisper transcribes as: "and I'll see you in the next video. Take care."

2. **REVERSED Audio (NEWLY CREATED):**
   `./tmp/moshi-v8.2-REVERSED.wav`
   - Created using: `ffmpeg -af areverse`
   - Same duration: 2.48 seconds
   - **IF THIS SOUNDS LIKE A GREETING → BUG FOUND!**

---

## How to Test

```bash
# Listen to original garbled version
afplay ./tmp/moshi-v8.2-output.wav

# Listen to REVERSED version
afplay ./tmp/moshi-v8.2-REVERSED.wav
```

---

## Expected Results

### Scenario A: Reversed Audio is Intelligible ✅
**If reversed audio sounds like "Hello!" or a greeting:**
- ✅ BUG IDENTIFIED: Audio samples are being reversed/backwards
- Root cause: Sample ordering issue in decode or buffer handling
- Fix: Find where samples are being reversed and correct it

### Scenario B: Reversed Audio is Still Garbled ❌
**If reversed audio also sounds garbled (different garbling):**
- ❌ Not a simple reversal issue
- Root cause is more complex than sample ordering
- Need to investigate:
  - Codebook ordering (8 codebooks, maybe wrong order?)
  - Tensor dimensions (batch, codebooks, steps permutation?)
  - Decode step processing order

### Scenario C: Reversed Audio Sounds Identical ⚠️
**If reversed and original sound THE SAME:**
- ⚠️ Very weird - would suggest symmetric corruption
- OR audio is so garbled that reversal doesn't change perception
- Still doesn't prove/disprove backwards hypothesis

---

## Why This Matters

The v8.2 fix (shared encoder/decoder state) had **ZERO effect** - output was byte-identical to previous versions.

This proves:
1. The state sharing hypothesis was WRONG
2. We need a different approach
3. The "backwards" clue might reveal the actual bug

---

## Possible Root Causes If Backwards

If reversed audio becomes intelligible, the bug could be in:

### 1. WAV File Writing (audio_output.rs)
```rust
// Are we writing samples in reverse order?
// Check: hound::WavWriter::write_sample() calls
```

### 2. Decode Buffer Collection
```rust
// Are decoded frames being collected backwards?
for step in 0..NUM_STEPS {
    // Maybe should be: for step in (0..NUM_STEPS).rev() ?
}
```

### 3. MIMI Codec Internal Bug
- MIMI might decode frames in reverse chronological order
- Or codebooks might be processed backwards
- Would need to check against official MIMI implementation

### 4. Tensor Reshape/Transpose
```rust
// Are we transposing when we shouldn't?
decoded_tensor.t()? // Transpose might reverse something
```

---

## Next Steps

### If Backwards Confirmed:
1. Search code for all `.reverse()`, `.rev()`, loop order
2. Check all tensor operations that could flip order
3. Compare our tensor shapes with official MOSHI CLI
4. Add debug logging to show sample order at each stage

### If NOT Backwards:
1. Test codebook ordering permutations (8! = 40,320 possibilities - too many)
2. Compare tensor dimensions with official implementation
3. Check if codebook indices are being scrambled
4. Investigate if MIMI expects specific byte order on Metal

---

## Files Created

- `./scripts/reverse_audio.py` - Python script (has numpy arch issues)
- `./tmp/moshi-v8.2-REVERSED.wav` - Reversed audio test file (✅ CREATED)
- This document

---

## Commands Used

```bash
# Create reversed audio
ffmpeg -i ./tmp/moshi-v8.2-output.wav -af areverse ./tmp/moshi-v8.2-REVERSED.wav -y

# Verify creation
ls -lh ./tmp/moshi-v8.2-*.wav

# Test listening
afplay ./tmp/moshi-v8.2-REVERSED.wav
```

---

## CRITICAL: Human Verification Required

**USER MUST:**
1. Listen to `./tmp/moshi-v8.2-REVERSED.wav`
2. Report if it sounds like a greeting or still garbled
3. Describe what you hear (even if still garbled)

This test will immediately narrow down the root cause!

---

## Context: Why State Sharing Fix Failed

The v8.2 fix changed from:
```rust
// BEFORE v8.2 (used clone)
let decoded = mimi_decoder.decode_step(&audio_tensor.into(), &().into())

// AFTER v8.2 (shared instance)
let decoded = moshi_state.mimi_model.decode_step(&audio_tensor.into(), &().into())
```

**Result:** Byte-identical output (MD5 unchanged)

**Conclusion:** Shared state wasn't the issue - something else is wrong.

The "backwards" clue might be the actual root cause we've been missing!

---

**READY FOR TESTING** 🎧
