# MOSHI Codebook Extraction Bug Analysis

**Date**: 2025-11-08
**Status**: Bug identified, fix needs testing
**Issue**: Garbled audio output (warmup crash was separate issue, already fixed)

## The Bug

Found by comparing `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/moshi/moshi-cli/src/gen.rs` (WORKING) with `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/voice.rs` (GARBLED).

### Working Implementation (gen.rs:108)

```rust
let codes = codes.i((0, .., 0))?.to_vec1::<u32>()?;
```

**Extracts ALL codebooks** from MIMI encoder output using `..`

### Broken Implementation (voice.rs:1172)

```rust
let codes = step_codes.i((0, 0..input_codebooks, 0))?.to_vec1::<u32>()
```

**Extracts ONLY first N codebooks** (0..8) from MIMI encoder output

## Why This Matters

Both implementations load MIMI identically:
- **gen.rs:38**: `moshi::mimi::load(&args.mimi_model_file, Some(8), dev)?`
- **voice.rs:350**: `moshi::mimi::load(&config.mimi_model_file, Some(MIMI_NUM_CODEBOOKS), mimi_device)` where `MIMI_NUM_CODEBOOKS = 8`

However, **passing `Some(8)` to MIMI might not actually limit the encoder output to 8 codebooks**. The MIMI encoder may still produce ALL codebooks (potentially 16 or 32), and we need to extract them all to pass to the LM.

## The Complete Flow Comparison

### gen.rs (WORKING):
1. Encode audio → `codes` tensor with shape `(batch, codebooks, steps)`
2. Extract codes: `codes.i((0, .., 0))` → Takes ALL codebooks
3. Pass ALL codebooks to LM: `state.step_(Some(prev_text_token), &codes, ...)`
4. Get audio_tokens from LM
5. Slice for decode: `&audio_tokens[..generated_audio_codebooks]` → Take first 8
6. Decode with MIMI

### voice.rs (GARBLED):
1. Encode audio → `codes_tensor` with shape `(batch, codebooks, steps)`
2. Extract codes: `step_codes.i((0, 0..input_codebooks, 0))` → Takes ONLY first 8 codebooks
3. Pass 8 codebooks to LM: `lm_generator.step_(..., &codes, ...)`
4. Get audio_tokens from LM
5. Slice for decode: `&audio_tokens[..generated_codebooks]` → Take first 8
6. Decode with MIMI

## Root Cause Hypothesis

The LM model expects to receive ALL codebooks from the MIMI encoder, even though it only GENERATES 8 codebooks. By slicing the input to only 8 codebooks, we're potentially:
- **Losing important codec information** from the higher codebook indices
- **Breaking the LM's assumptions** about input tensor structure
- **Causing the LM to generate incorrect audio tokens**

## The Fix

Change `voice.rs:1172` from:
```rust
let codes = step_codes.i((0, 0..input_codebooks, 0))?.to_vec1::<u32>()
```

To match gen.rs:
```rust
let codes = step_codes.i((0, .., 0))?.to_vec1::<u32>()
```

This will pass ALL codebooks to the LM, exactly as gen.rs does.

## Testing Plan

1. Apply the fix to voice.rs:1172
2. Rebuild: `cargo build --release`
3. Run test: `./target/release/xswarm --moshi-test`
4. Verify audio is clear (play with `afplay ./tmp/moshi-response.wav`)
5. Do NOT trust Whisper API transcription - must listen to audio

## Files to Modify

- `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/voice.rs`:1172

## Related Issues

- Warmup crash was SEPARATE issue (already fixed by warming up actual model instances)
- This codebook extraction bug is why audio is garbled despite crash being fixed
