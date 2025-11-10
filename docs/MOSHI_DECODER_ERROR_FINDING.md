# MOSHI Decoder Error - Critical Finding

**Date**: 2025-11-08
**Test Result**: MIMI encoder config change did NOT fix the issue

## Error Message

```
❌ Startup error: MIMI decode failed for frame 2 step 0
```

## Critical Discovery

**The error occurs during DECODE, not ENCODE:**
- **ENCODE**: Audio → Tokens (working correctly)
- **DECODE**: Tokens → Audio (**FAILING at frame 2, step 0**)

## What We Tested

Changed MIMI loading from:
```rust
// Before
let mimi_model = moshi::mimi::load(
    &config.mimi_model_file,
    Some(8),  // Explicit 8 codebooks
    mimi_device,
)
```

To:
```rust
// After (matching MLX)
let mimi_model = moshi::mimi::load(
    &config.mimi_model_file,
    None,  // Use default 16 codebooks, slice to 8 after encoding
    mimi_device,
)
```

**Result**: Same error - "MIMI decode failed for frame 2 step 0"

## Implications

1. **Encoder config is likely correct** - The problem isn't in how we load MIMI or slice codebooks during encoding
2. **Decoder has the bug** - Something is wrong when we decode the LM-generated tokens back to audio
3. **Frame 2, Step 0 specific** - Fails consistently at same location (not random)

## Next Steps

Need to compare:
1. **MLX decoder configuration** - How does MLX configure MIMI decoder?
2. **Decoder invocation** - Are we calling the decoder correctly?
3. **Token format** - Are the tokens we're passing to decoder in correct format?
4. **Codebook count for decoder** - Do we need to pad tokens to 16 codebooks before decoding?

## Hypothesis

MLX might be:
- Using 16 codebooks for both encode AND decode
- Only slicing to 8 for LM input/output
- Padding LM output back to 16 before passing to MIMI decoder

If this is true, we need to:
1. Keep encoder at 16 codebooks (done ✅)
2. Slice to 8 for LM (already done ✅)
3. **Pad LM output back to 16 before decoding** (NOT DONE ❌)

## Code Location

Decoder usage is likely in `packages/core/src/voice.rs` where we process LM output and convert back to audio.

