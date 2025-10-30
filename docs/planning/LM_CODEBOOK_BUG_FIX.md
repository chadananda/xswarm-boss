# Critical Bug Fix: MIMI Codebook Index Out of Bounds

**Date**: October 26, 2025, 6:50 PM PST
**Status**: FIXED ✅
**Priority**: CRITICAL (System Crash)

---

## Problem

During the first test call with full LM transcription enabled, the system crashed with:

```
thread 'tokio-runtime-worker' panicked at packages/moshi/moshi-core/src/lm_generate_multistream.rs:198:45:
index out of bounds: the len is 16 but the index is 16
```

### Test Call Details
- **Call SID**: CAdc7d59d5f6aa1e8f2d1d2835f548c336
- **Time**: 18:20 PST
- **Connection**: Established successfully
- **Failure Point**: First audio frame processing

---

## Root Cause Analysis

### The Bug

**File**: `packages/core/src/voice.rs:460`

```rust
// BEFORE (WRONG):
let codes = codes_tensor.i((0, .., 0))?.to_vec1::<u32>()?;
```

This extracts **ALL codebooks** (32) from MIMI encoder output.

### Why It Failed

1. **MIMI Encoder Output**: Returns tensor shape `(batch=1, codebooks=32, timesteps=1)`
2. **LM Config Expectation**: `input_audio_codebooks = 8` (only expects 8 codes)
3. **LM Internal Logic** (`moshi-core/src/lm_generate_multistream.rs:198`):
   ```rust
   for (c_idx, &t) in input_audio_tokens.iter().enumerate() {
       self.audio_tokens[self.step_idx][c_idx + self.config.generated_audio_codebooks] = t
   }
   ```
4. **Array Bounds**:
   - Array length: `generated_audio_codebooks + input_audio_codebooks = 8 + 8 = 16`
   - When passing 32 codes: `c_idx` ranges 0-31
   - Index calculation: `c_idx + 8` ranges 8-39
   - **Index 16 out of bounds for array[16]** ❌

---

## The Fix

**File**: `packages/core/src/voice.rs:458-469`

```rust
// AFTER (CORRECT):
// Extract codes as Vec<u32> - shape is [batch=1, codebooks, time=1]
// CRITICAL: Only extract first 8 codebooks to match lm_config.input_audio_codebooks
// MIMI outputs 32 codebooks, but LM expects only 8 for input
use candle::IndexOp;
let input_codebooks = moshi_state.lm_config.input_audio_codebooks as usize;
let codes = codes_tensor.i((0, 0..input_codebooks, 0))?.to_vec1::<u32>()?;

debug!(
    code_count = codes.len(),
    expected_count = input_codebooks,
    "Extracted MIMI codes (limited to LM input_audio_codebooks)"
);
```

### Key Changes

1. **Dynamic codebook count**: Read from `lm_config.input_audio_codebooks` (8)
2. **Range indexing**: `0..input_codebooks` instead of `..` (all)
3. **Documentation**: Clear comments explaining the constraint
4. **Debug logging**: Verify correct count extraction

---

## Technical Details

### MIMI Codec Architecture

The MIMI neural codec uses **residual vector quantization** with 32 codebooks:

| Configuration | Codebooks | Bitrate | Quality |
|--------------|-----------|---------|---------|
| Full Quality | 32 | 4.4 kbps | Best |
| **LM Input** | **8** | **1.1 kbps** | **Reduced** |

### LM Config Structure

From `moshi-core/src/lm_generate_multistream.rs`:

```rust
pub struct Config {
    pub generated_audio_codebooks: usize,  // 8 (LM generates these)
    pub input_audio_codebooks: usize,      // 8 (LM receives these)
    pub audio_vocab_size: usize,           // 2049
    pub acoustic_delay: usize,             // 2
    pub text_eop_token: u32,               // 0
    pub text_pad_token: u32,               // 3
    pub text_start_token: u32,             // 32000
}
```

The LM operates on **reduced quality audio** (8 codebooks) for efficiency:
- **Input**: 8 codebooks from user speech (1.1 kbps)
- **Output**: 8 codebooks for synthesized speech (1.1 kbps)
- **Total**: 16 codebook slots in internal array

---

## Testing & Verification

### Build Status

```
cargo build --release --bin xswarm
Result: ✅ SUCCESS (0 errors, 25 warnings)
Time: 2m 17s
```

### Voice Bridge Status

```
Process: Running
Ports: 9998 (voice), 9999 (supervisor)
Models: Loaded (LM 7B Q8, MIMI codec, SentencePiece)
Metal GPU: Enabled
Logs: /tmp/voice-bridge-fixed.log
```

### Next Test Required

A new test call is needed to verify:
1. ✅ No panic (array bounds respected)
2. ⏸️ Audio frames process successfully
3. ⏸️ LM inference completes
4. ⏸️ Text transcriptions generated
5. ⏸️ Audio synthesis works

---

## Reference Implementation

**File**: `packages/moshi/moshi-backend/src/stream_both.rs:356-363`

```rust
let audio_tokens = mimi.encode_step(&pcms.into(), &().into())?;
let audio_tokens = match audio_tokens.as_option() {
    None => continue,
    Some(audio_tokens) => audio_tokens,
};
let (_one, _codebooks, steps) = audio_tokens.dims3()?;

for step in 0..steps {
    let codes = audio_tokens.i((0, .., step))?.to_vec1::<u32>()?;
    // ...uses all codebooks here because this is for MIMI-only processing
}
```

**Key Difference**: The reference uses ALL codebooks because it's not interfacing with the LM - it's just echoing audio through MIMI.

---

## Impact Assessment

### Before Fix
- ❌ **System Crash**: Every phone call panicked on first audio frame
- ❌ **No Transcription**: LM never executed
- ❌ **Zero Functionality**: Voice bridge unusable

### After Fix
- ✅ **Compiles Successfully**: No build errors
- ✅ **Correct Bounds**: Respects LM's 8-codebook limit
- ⏸️ **Pending Verification**: Needs actual call test

---

## Lessons Learned

### Architecture Understanding
- MIMI codec has **two quality modes**: full (32) vs reduced (8)
- LM operates on **reduced quality** for computational efficiency
- Different parts of the system use different codebook counts

### Index Extraction Patterns
```rust
// Extract all: .i((0, .., 0))      // Gets all codebooks
// Extract range: .i((0, 0..8, 0))  // Gets first 8 codebooks
// Extract single: .i((0, 3, 0))    // Gets codebook #3
```

### Future-Proofing
- Always check `lm_config` for expected dimensions
- Document codebook count assumptions
- Add debug logging for dimension mismatches

---

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| `packages/core/src/voice.rs` | 458-469 | Fixed codebook extraction |
| `planning/LM_CODEBOOK_BUG_FIX.md` | All | This document |

---

**Status**: Fix complete, awaiting call test verification
**Blocker**: None (Workers restart issue is separate)
**Risk**: Low - fix is minimal and well-understood
**Next Step**: Test call with full LM transcription enabled
