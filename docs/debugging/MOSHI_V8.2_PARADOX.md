# MOSHI v8.2 Paradox - Fix Applied But Output Unchanged

**Date:** 2025-11-08
**Version:** v0.1.0-2025.11.8.2
**Status:** 🔴 CRITICAL INVESTIGATION NEEDED

---

## The Paradox

Applied v8.2 fix (encoder/decoder state sharing) but output audio is **byte-identical** to previous garbled versions.

## Evidence

### MD5 Checksums
```
moshi-response.wav:      4d49440e24fa4cf984df84d280e47413
moshi-v8.2-output.wav:   4d49440e24fa4cf984df84d280e47413
```

**Both files are IDENTICAL** (same MD5, both 116KB, same timestamp Nov 8 08:40)

### Audio Metrics (v8.2)
```
Mean volume: -21.4 dB (same as v8.0, v8.1)
Dynamic range: 92.2 dB (same as v8.0, v8.1)
```

**Metrics are identical to previous garbled versions!**

### Whisper Transcription (v8.2)
```
"and I'll see you in the next video. Take care."
```

**This is NOT a greeting!** Expected something like "Hello!" or "Hi there!"

---

## v8.2 Fix Verification

**Fix IS in source code (voice.rs:1219-1221):**
```rust
// v8.2 CRITICAL FIX: Use the SAME model instance for decode (not a clone!)
// Encoder and decoder MUST share state for streaming codec
let decoded = moshi_state.mimi_model.decode_step(&audio_tensor.into(), &().into())
```

**Binary was built at:** Nov 8 08:40
**Audio was generated at:** Nov 8 08:40 (confirms test used v8.2 binary)

**Fix locations:**
- Line 1221: Main decode loop (test path) - ✅ FIXED
- Line 1286: Flush loop (test path) - ✅ FIXED
- Line 1621: Production streaming (ConnectionState) - ❌ STILL USES CLONE

---

## Code Analysis

### Test Path (--moshi-test) - v8.2 Fixed

**Encoding** (line 1147):
```rust
let codes_stream = moshi_state.mimi_model.encode_step(&pcm_tensor.into(), &().into())
```

**Decoding** (line 1221 - FIXED in v8.2):
```rust
let decoded = moshi_state.mimi_model.decode_step(&audio_tensor.into(), &().into())
```

**Both use the SAME instance:** `moshi_state.mimi_model` ✅

### Production Path (ConnectionState) - Still Broken

**Encoding** (line 1437):
```rust
let codes_stream = moshi_state.mimi_model.encode_step(&pcm_tensor.into(), &().into())?;
```

**Decoding** (line 1621 - STILL USES CLONE):
```rust
let decoded = conn_state.mimi_decoder.decode_step(&audio_tensor.into(), &().into())?;
```

**Uses DIFFERENT instances:**
- Encoder: `moshi_state.mimi_model` (global shared)
- Decoder: `conn_state.mimi_decoder` (cloned at line 562)

**This is the SAME BUG!** ❌

---

## The Paradox: Why Is Output Identical?

**Expected:** Fixing state sharing should produce DIFFERENT audio output
**Actual:** v8.2 output is byte-identical to previous garbled versions

**Possible explanations:**

1. **Deterministic seeding overrides state?**
   - Seed 299792458 used for audio/text logits
   - Maybe this forces identical output despite state fix?
   - But then why would official CLI work?

2. **Fix didn't actually compile?**
   - ❌ RULED OUT - Comments and code confirm it's there
   - Binary timestamp matches audio timestamp

3. **Misunderstood MIMI architecture?**
   - Maybe encoder/decoder aren't supposed to share state?
   - ❌ RULED OUT - Official CLI doesn't clone (gen.rs:113-122)

4. **There's another bug preventing the fix from working?**
   - Reset_state() call somewhere?
   - State not being maintained between steps?
   - Something in LM generator breaking continuity?

5. **Cached output being reused?**
   - ❌ RULED OUT - Deleted experiments directory before test
   - File has fresh timestamp matching build time

---

## What This Means

1. **v8.2 fix is correctly applied to test path**
2. **But output is unchanged from garbled versions**
3. **This suggests either:**
   - The fix is correct but something else is wrong
   - OR our understanding of the root cause is incorrect
   - OR there's a deeper issue preventing the fix from working

---

## Next Steps

Need to investigate:

1. **Check if state is actually being shared**
   - Add debug logging to verify mimi_model instance ID
   - Confirm encode/decode are using same memory address

2. **Compare with official CLI**
   - Run official moshi-cli gen with same input
   - Compare audio output MD5
   - If official also produces garbled audio → not our bug!
   - If official produces clear audio → we're missing something

3. **Test without deterministic seeding**
   - Try random seed instead of fixed 299792458
   - See if output changes between runs
   - This would confirm whether seeding is the issue

4. **Check for hidden reset_state() calls**
   - Search for any other places that might reset state
   - Verify state continuity is maintained

5. **Examine LM generator state**
   - Maybe the issue is in how LM processes codes?
   - Not in MIMI encode/decode?

---

## Files Changed in v8.2

**packages/core/src/voice.rs:**
- Lines 1059-1072: Removed clone, added fix comments
- Lines 1219-1222: Changed decode to use shared model
- Lines 1285-1286: Fixed second occurrence in flush loop

**packages/core/Cargo.toml:**
- Version: 0.1.0-2025.11.8.2

---

## Conclusion

**The v8.2 fix is real and compiled, but the output is unchanged.**

This is a critical paradox that suggests either:
- We fixed the wrong thing
- OR there's something preventing the fix from working
- OR deterministic testing is masking the fix

**Human verification still needed:** Listen to `moshi-v8.2-output.wav` to confirm it's actually garbled.

If it's still garbled despite the fix, we need deeper investigation into:
1. Why shared state isn't changing the output
2. Whether the official CLI also produces garbled output
3. What else might be corrupting the audio stream

