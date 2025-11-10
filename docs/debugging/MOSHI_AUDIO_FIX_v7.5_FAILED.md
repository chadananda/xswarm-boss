# MOSHI Audio Fix v7.5 - FAILED ❌

## Status: Debug Logging Shows "Correct" Pipeline, Audio Still Garbled

**Version:** 0.1.0-2025.11.7.5
**Result:** ❌ **Audio still completely garbled**
**Critical Discovery:** v7.3, v7.4, and v7.5 produce **IDENTICAL** output

## What We Tried

Added comprehensive debug logging to track the entire audio pipeline:

### Debug Logging Added (voice.rs)

**Input Audio Stats (lines 1044-1052):**
```rust
if !user_audio.is_empty() {
    let min = user_audio.iter().fold(f32::INFINITY, |a, &b| a.min(b));
    let max = user_audio.iter().fold(f32::NEG_INFINITY, |a, &b| a.max(b));
    let mean = user_audio.iter().sum::<f32>() / user_audio.len() as f32;
    let first_10: Vec<f32> = user_audio.iter().take(10).copied().collect();
    info!("MOSHI_DEBUG: Input audio stats - samples={}, min={:.4}, max={:.4}, mean={:.6}, first_10={:?}",
          user_audio.len(), min, max, mean, first_10);
}
```

**Audio Token Logging (lines 1175-1178):**
```rust
if frame_idx < 5 {
    info!("MOSHI_DEBUG: Frame {}: Audio tokens: {:?}", frame_idx, audio_tokens_slice);
}
```

**Tensor Properties Logging (lines 1188-1192):**
```rust
if frame_idx < 3 {
    info!("MOSHI_DEBUG: Frame {}: Tensor shape: {:?}, stride: {:?}, dtype: {:?}",
          frame_idx, audio_tensor.shape(), audio_tensor.stride(), audio_tensor.dtype());
}
```

**PCM Output Stats (lines 1201-1209):**
```rust
if frame_idx < 5 && !frame_samples.is_empty() {
    let min = frame_samples.iter().fold(f32::INFINITY, |a, &b| a.min(b));
    let max = frame_samples.iter().fold(f32::NEG_INFINITY, |a, &b| a.max(b));
    let mean = frame_samples.iter().sum::<f32>() / frame_samples.len() as f32;
    let first_10: Vec<f32>  = frame_samples.iter().take(10).copied().collect();
    info!("MOSHI_DEBUG: Frame {}: PCM stats - samples={}, min={:.4}, max={:.4}, mean={:.6}, first_10={:?}",
          frame_idx, frame_samples.len(), min, max, mean, first_10);
}
```

## The Shocking Result

**MD5 Hash Comparison:**
```
MD5 (moshi-test-v7.3.wav) = 398fe04c3836ce2ce5fa217cd9b7792c
MD5 (moshi-test-v7.4.wav) = 398fe04c3836ce2ce5fa217cd9b7792c
MD5 (moshi-test-v7.5.wav) = 398fe04c3836ce2ce5fa217cd9b7792c
```

**All three versions produce byte-for-byte IDENTICAL output!**

## Debug Log Analysis

The logs show everything appears to be working correctly:

### ✅ Input Audio (Valid)
```
MOSHI_DEBUG: Input audio stats - samples=24000, min=-0.0010, max=0.0010, mean=0.000001
first_10=[-0.0005187988, 9.1552734e-5, -0.00091552734, ...]
```
- Test WAV file is valid
- Quiet but normal audio range
- 24000 samples = 1 second at 24kHz

### ✅ Audio Tokens (Normal)
```
Frame 2: Audio tokens: [1776, 1267, 628, 703, 1203, 1020, 162, 1940]
Frame 3: Audio tokens: [1340, 666, 151, 1921, 444, 276, 1707, 962]
Frame 4: Audio tokens: [1618, 1902, 341, 589, 1787, 917, 381, 1878]
```
- 8 tokens per frame (correct for 8 codebooks)
- Reasonable integer values (codebook indices)
- Values vary per frame (not stuck/frozen)

### ✅ Tensor Properties (Correct with Transpose!)
```
Frame 2: Tensor shape: [1, 8, 1], stride: [8, 1, 8], dtype: U32
```
- Shape is `[1, 8, 1]` (batch=1, codebooks=8, time=1) ✅
- **Stride is `[8, 1, 8]`** - This confirms the `.t()` transpose is applied! ✅
- Data type is U32 (unsigned 32-bit) ✅

### ✅ PCM Output (Normal Range)
```
Frame 2: PCM stats - samples=1920, min=-0.3252, max=0.3012, mean=-0.000070
Frame 3: PCM stats - samples=1920, min=-0.2870, max=0.3031, mean=-0.000562
Frame 4: PCM stats - samples=1920, min=-0.2366, max=0.2681, mean=0.002000
```
- All values in expected `[-1, 1]` range ✅
- 1920 samples per frame = 80ms at 24kHz ✅
- Values vary per frame (decoder is producing output) ✅

## The Mystery: Everything Looks Correct, But Audio Is Garbled

**What the debug logs tell us:**
- Input audio is valid
- LM generates sensible audio tokens
- Tensor has correct shape AND stride (transposed!)
- MIMI decoder produces PCM in normal range
- Frame assembly works (accumulates samples correctly)

**Yet the audio is still completely garbled!**

## What This Means

The problem is **NOT** in the areas we've been modifying:
- ❌ NOT missing reset_state() (v7.3 tried this)
- ❌ NOT tensor memory layout (v7.4 confirmed transpose works, v7.5 shows stride `[8, 1, 8]`)
- ❌ NOT invalid input data (debug logs show valid input)
- ❌ NOT wrong token values (tokens look reasonable)
- ❌ NOT PCM out of range (all values in `[-1, 1]`)

The problem **MIGHT BE**:
1. **Wrong codebook ordering** - Despite correct shape/stride, codebooks might be in wrong order
2. **MOSHI API misuse** - Something fundamental about how we're calling the API
3. **Model mismatch** - Wrong model variant or incompatible versions
4. **Frame timing issue** - Something about how frames are assembled or synchronized
5. **MIMI decoder internal state** - Something we can't observe with logging

## Whisper Transcription

Despite garbled audio to human ears, Whisper API successfully transcribed:
```
"I was trying to look cheep, but my windows were blocked. Yeah, I didn't verify it."
```
- 16 words detected
- This proves phonetic content IS present
- But temporal/structural integrity is broken
- Whisper is TOO GOOD at reconstructing garbled speech

## Version History

- **v0.1.0-2025.11.7.0**: Initial (garbled audio)
- **v0.1.0-2025.11.7.1**: Per-connection cloning (NO CHANGE)
- **v0.1.0-2025.11.7.2**: Batch size changes (ERROR - reverted)
- **v0.1.0-2025.11.7.3**: Added reset_state() (NO CHANGE)
- **v0.1.0-2025.11.7.4**: CLI tensor pattern with transpose (ZERO EFFECT - identical MD5)
- **v0.1.0-2025.11.7.5**: Debug logging ✅ **Logs look correct, audio still garbled**

## Test Files

- `moshi-test-v7.3.wav` - Garbled (116KB)
- `moshi-test-v7.4.wav` - Garbled (116KB, identical MD5)
- `moshi-test-v7.5.wav` - Garbled (116KB, identical MD5)

All three files are byte-for-byte identical despite different code changes.

## Debug Logs Location

Logs are in: `~/.cache/xswarm/xswarm.log`

To view MOSHI debug logs:
```bash
grep "MOSHI_DEBUG" ~/.cache/xswarm/xswarm.log | tail -50
```

## Next Steps (Recommendations)

Given that debug logging shows everything "looks correct" but audio is still garbled:

1. **Test Official MOSHI CLI** - Build and run official `moshi-cli gen` to get known-good output for comparison
2. **Test Real-Time Mode** - Try actual microphone input in conversation mode (maybe test mode is broken)
3. **Deep Code Comparison** - Line-by-line comparison with official MOSHI server/CLI implementation
4. **Contact MOSHI Developers** - File GitHub issue with findings and garbled audio sample
5. **Investigate Model Loading** - Check if we're using correct model variant/version

## Key Lesson

**Debug logging revealed a critical insight:**
- Just because intermediate values "look correct" doesn't mean the output is correct
- The problem may be in HOW we're using the API, not in the values we're passing
- Need to compare with known-working implementation (official CLI)

---

**Status:** ❌ Audio still garbled despite correct-looking pipeline
**Logs:** `~/.cache/xswarm/xswarm.log`
**Test File:** `moshi-test-v7.5.wav` (identical to v7.3 and v7.4)
**Date:** 2025-11-08
**Conclusion:** Problem is deeper than we can observe with current logging
**Next:** Test official MOSHI CLI or contact developers
