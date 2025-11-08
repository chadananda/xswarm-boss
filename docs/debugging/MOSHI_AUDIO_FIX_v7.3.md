# MOSHI Audio Fix - Version 0.1.0-2025.11.7.3

## Root Cause IDENTIFIED

**Problem:** Completely garbled audio that sounds like "crowd of people talking at once"

**Root Cause:** Missing `reset_state()` call after cloning MIMI decoder

## How We Found It

After two failed attempts (per-connection cloning, batch_size initialization), I researched the official MOSHI server implementation:

**File:** `packages/moshi/moshi-server/src/lm.rs` **Line 126:**
```rust
let mut audio_tokenizer = self.audio_tokenizer.clone();
audio_tokenizer.reset_state(); // ← THIS WAS MISSING!
```

## The Fix

Added `reset_state()` calls in TWO locations:

### 1. Real-time conversation mode (voice.rs:562-563)
```rust
let mut mimi_decoder = moshi_state.mimi_model.clone();
mimi_decoder.reset_state(); // Reset state for fresh connection (CRITICAL - fixes garbled audio)
```

### 2. Test mode (voice.rs:1051-1052)
```rust
let mut mimi_decoder = moshi_state.mimi_model.clone();
mimi_decoder.reset_state(); // Reset state for fresh test (CRITICAL - fixes garbled audio)
```

## Why This Fixes It

When you `clone()` a MIMI model:
- ✅ Creates a new instance per connection (correct)
- ❌ **Copies the internal transformer state** (problem!)

Without `reset_state()`:
- Each new connection inherits stale state from wherever the original model was last used
- Decoder has "memory" of previous audio frames
- Causes temporal corruption → "crowd talking" effect

With `reset_state()`:
- Clears encoder/decoder transformer states
- Resets upsample/downsample buffers
- Each connection starts with clean slate
- Should produce clear, intelligible audio

## What reset_state() Does

From `moshi-core/src/mimi.rs:224-232`:
```rust
pub fn reset_state(&mut self) {
    self.encoder.reset_state();
    self.encoder_transformer.reset_state();
    self.decoder.reset_state();
    self.decoder_transformer.reset_state();
    self.upsample.reset_state();
    self.downsample.reset_state();
}
```

## Expected Results

If this fix works:
- ✅ Clear, intelligible speech in real-time playback
- ✅ Test WAV files sound clear when played directly
- ✅ "Crowd talking" effect disappears
- ✅ Temporal continuity restored
- ✅ MOSHI finally works as intended!

## Testing

```bash
# Build
cargo build --release

# Test
export OPENAI_API_KEY="your_key"
./target/release/xswarm --moshi-test

# Listen to generated WAV
play moshi-test.wav
```

## Version History

- **v0.1.0-2025.11.7.0**: Initial version (garbled audio)
- **v0.1.0-2025.11.7.1**: Per-connection decoder cloning (NO CHANGE - still garbled)
- **v0.1.0-2025.11.7.2**: Reverted batch_size changes (caused mask error)
- **v0.1.0-2025.11.7.3**: Added reset_state() calls (SHOULD FIX GARBLED AUDIO)

## Research Credit

Fixed by studying official MOSHI server source code at:
- `packages/moshi/moshi-server/src/lm.rs`
- `packages/moshi/moshi-server/src/mimi.rs`

The official implementation uses `clone()` + `reset_state()` pattern, which we were missing.

---

**Status:** Fix implemented, build in progress
**Next:** Generate test WAV and verify audio quality
**Date:** 2025-11-07
