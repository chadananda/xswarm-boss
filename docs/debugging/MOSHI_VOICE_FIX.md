# MOSHI Voice Output Fix

## Issue
MOSHI would generate greeting tones (3 beeps) but no voice output. User could hear only silence after the beeps.

## Root Cause
**Codebook Mismatch**: MIMI codec was initialized with 32 codebooks, but MOSHI LM generates only 8 codebooks.

### Error in logs:
```
ERROR: MOSHI processing failed: mismatch between the number of layers 31 and the code shape [7, 1, 1]
```

### The Problem:
1. We loaded MIMI model with `num_codebooks=32`
2. MOSHI LM generated `generated_audio_codebooks=8`
3. We created tensor with shape `[1, 8, 1]` (correct for LM output)
4. MIMI decoder expected 32 codebooks, received 8
5. ResidualVectorQuantization.decode() rejected the tensor

## Investigation Process

1. **Checked logs** at `~/.cache/xswarm/xswarm.log`
   - Found consistent error every time MOSHI tried to generate audio
   - Logs showed: "Calling MIMI decoder - tensor_shape=[1, 8, 1]"
   - Error immediately followed: "code shape [7, 1, 1]"

2. **Traced tensor flow**:
   - `voice.rs:1057-1061` - Create tensor `[1, 8, 1]` ✓
   - `mimi.rs:214-216` - Pass to `decode_step()` ✓
   - `quantization.rs:234-243` - Validation fails ✗

3. **Checked working examples**:
   - moshi-backend config: `"mimi_num_codebooks": 8`
   - LM Config.v0_1(): `generated_audio_codebooks: 8`
   - All working examples use 8 codebooks consistently

## The Fix

**File**: `packages/core/src/voice.rs`

**Line 85**:
```rust
// BEFORE:
const MIMI_NUM_CODEBOOKS: usize = 32;   // WRONG - mismatch with LM

// AFTER:
const MIMI_NUM_CODEBOOKS: usize = 8;    // CORRECT - matches LM generated_audio_codebooks
```

## Testing

**Version**: 0.1.0-2025.11.3.3

**Test Steps**:
1. Build with fix: `cargo build --release --bin xswarm`
2. Install: `cp target/release/xswarm ~/.local/bin/xswarm`
3. Clear log: `rm -f ~/.cache/xswarm/xswarm.log`
4. Run: `xswarm --dev`
5. Speak into microphone
6. Verify MOSHI voice output plays (not just beeps)

**Expected Result**:
- ✅ Greeting tones play (3 beeps at 600Hz, 800Hz, 1000Hz)
- ✅ MOSHI voice output plays after transcription
- ✅ No decoder errors in log file
- ✅ Log shows: "Audio generation SUCCESS - output_samples=1920"

## Related Files

- `packages/core/src/voice.rs:85` - MIMI_NUM_CODEBOOKS constant
- `packages/core/src/voice.rs:1020-1070` - Audio token decoding logic
- `packages/moshi/moshi-core/src/mimi.rs:214-222` - MIMI decode_step
- `packages/moshi/moshi-core/src/quantization.rs:234-251` - Validation error location
- `packages/moshi/moshi-core/src/lm_generate_multistream.rs:14-29` - LM config

## Key Learnings

1. **Always match codebook counts** between MIMI encoder/decoder and LM
2. **Check working examples** for correct configuration values
3. **8 codebooks is standard** for MOSHI v0.1 configuration
4. **32 codebooks** was a wrong assumption (likely from old documentation)

## Git Commit

```bash
git add packages/core/src/voice.rs packages/core/Cargo.toml
git commit -m "fix: correct MIMI codebook count from 32 to 8

- MIMI codec now loads with 8 codebooks (matches LM)
- Fixes decoder mismatch error that prevented voice output
- Version bump to 0.1.0-2025.11.3.3

Resolves: MOSHI voice output only played greeting beeps"
```

## Status

✅ **FIXED** - Ready for testing with v0.1.0-2025.11.3.3
