# MOSHI Audio - ROOT CAUSE IDENTIFIED

**Date**: 2025-11-08
**Status**: ❌ ROOT CAUSE FOUND - Using WRONG model loading function
**Versions Tested**: v8.x, v9.0, v9.1, v10.0 - ALL FAILED

## Summary

ALL previous fixes (v8.x warmup, v9.0 buffer reversal, v9.1 per-frame reversal, v10.0 tensor concatenation) were treating symptoms, not the root cause.

**The real problem**: We use `load_streaming()` which loads a **hardcoded config**, while gen.rs (working code) uses `load_lm_model()` with the **official config from TOML file**.

## The Root Cause

### What We Do (WRONG):

**File**: `packages/core/src/voice.rs:322`
```rust
let mut lm_model = moshi::lm::load_streaming(&config.lm_model_file, dtype, &device)?;
```

**What `load_streaming` does** (moshi-core/src/lm.rs:1047-1054):
```rust
pub fn load_streaming<P: AsRef<std::path::Path>>(
    model_file: P,
    dtype: DType,
    dev: &Device,
) -> Result<LmModel> {
    let cfg = Config::v0_1_streaming(8);  // <-- HARDCODED CONFIG!
    load_lm_model(cfg, model_file, dtype, dev)
}
```

### What gen.rs Does (CORRECT):

**File**: `packages/moshi/moshi-cli/src/gen.rs:35-40`
```rust
// Load config from TOML file
let lm_config = std::fs::read_to_string(&args.lm_config_file)?;
let lm_config: moshi::lm::Config = toml::from_str(&lm_config)?;

// Use the proper config
let lm_model = moshi::lm::load_lm_model(lm_config.clone(), &args.lm_model_file, dtype, dev)?;
```

**Config File**: `packages/moshi/moshi-cli/tmp/moshi-official/rust/s2st-1b.toml`

## The Problem

The hardcoded config in `load_streaming` likely differs from the official config in critical ways:

**Official Config (s2st-1b.toml)**:
- `audio_vocab_size = 2049`
- `audio_codebooks = 16`
- `depformer.num_slices = 8`
- Complete transformer and depformer settings
- Conditioner settings
- Extensive configuration

**Hardcoded Config (`Config::v0_1_streaming(8)`)**:
- Unknown what this actually creates
- Likely missing or incorrectly configured settings
- May have wrong depformer configuration
- May be missing critical settings

This mismatch could cause:
- Wrong audio token generation
- Incorrect decoding parameters
- Misaligned model expectations
- **Garbled audio output**

## Why Previous Fixes Failed

All previous fixes attacked the PCM extraction/reversal:
- ✅ Warmup (v8.x) - Fixed crashes, not audio quality
- ❌ Codebook count correction (v8.x) - Irrelevant to config issue
- ❌ Full buffer reversal (v9.0) - Made things worse
- ❌ Per-frame reversal (v9.1) - Still garbled
- ❌ Tensor concatenation (v10.0) - Matches gen.rs extraction, still garbled

**None of these touched the MODEL CONFIGURATION**, which is where the issue actually is!

## The Fix (v11.0)

### Plan

1. Copy `s2st-1b.toml` to our project
2. Read the config from file (like gen.rs does)
3. Use `load_lm_model()` with the proper config (NOT `load_streaming()`)
4. Test audio generation
5. **DO NOT USE WHISPER FOR VALIDATION**

### Implementation

**Where to put config file**:
```
packages/core/config/moshi-s2st-1b.toml
```

**Changes needed in voice.rs**:

Replace:
```rust
let mut lm_model = moshi::lm::load_streaming(&config.lm_model_file, dtype, &device)?;
```

With:
```rust
// Load LM config from TOML file (like gen.rs does)
let lm_config_path = "packages/core/config/moshi-s2st-1b.toml";
let lm_config_str = std::fs::read_to_string(lm_config_path)
    .context("Failed to read LM config file")?;
let lm_config: moshi::lm::Config = toml::from_str(&lm_config_str)
    .context("Failed to parse LM config")?;

// Use load_lm_model with the proper config (NOT load_streaming!)
let mut lm_model = moshi::lm::load_lm_model(lm_config.clone(), &config.lm_model_file, dtype, &device)
    .context("Failed to load LM model with proper config")?;
```

## Why This Should Work

1. **gen.rs uses this exact approach** and produces working audio
2. **We match gen.rs in every other aspect**:
   - ✅ MIMI loading (line 38 gen.rs vs line 306 voice.rs)
   - ✅ Tensor creation for audio tokens (line 116 gen.rs vs line 1215 voice.rs)
   - ✅ Tensor concatenation (line 134 gen.rs vs line 1295 voice.rs)
   - ✅ Sample extraction (line 136 gen.rs vs line 1304 voice.rs)
3. **Only remaining difference**: Model configuration!

## Evidence

### Comparison

| Aspect | gen.rs (WORKING) | voice.rs (GARBLED) |
|--------|-----------------|-------------------|
| LM Config | From s2st-1b.toml | Hardcoded v0_1_streaming(8) |
| LM Load | `load_lm_model(config, ...)` | `load_streaming(...)` |
| MIMI Load | `moshi::mimi::load(..., Some(8), ...)` | `moshi::mimi::load(..., Some(8), ...)` ✅ |
| Tensor Creation | `Tensor::new(...).reshape((1,1,())).t()` | `Tensor::new(...).reshape((1,1,())).t()` ✅ |
| Tensor Concat | `Tensor::cat(&out_pcms, 2)` | `Tensor::cat(&out_pcm_tensors, 2)` ✅ |
| Sample Extract | `.i((0, 0))?.to_vec1::<f32>()` | `.i((0, 0))?.to_vec1::<f32>()` ✅ |

The ONLY difference is the model configuration!

## Expected Outcome

After using the proper config:
- ✅ Audio should be intelligible
- ✅ Should sound natural
- ✅ Should match gen.rs output quality

## Files to Modify

1. **Create**: `packages/core/config/moshi-s2st-1b.toml` (copy from official)
2. **Modify**: `packages/core/src/voice.rs:320-324` (change model loading)

## Next Steps

1. Implement v11.0 fix (use proper config)
2. Build and test
3. **User verification by listening** (NO WHISPER!)
4. If this works: Update all documentation
5. If this fails: Deep dive into Config::v0_1_streaming() to see what it creates

## Reference

- **Official Config**: `packages/moshi/moshi-cli/tmp/moshi-official/rust/s2st-1b.toml`
- **gen.rs**: `packages/moshi/moshi-cli/src/gen.rs:35-40`
- **load_streaming**: `packages/moshi/moshi-core/src/lm.rs:1047-1054`
- **load_lm_model**: `packages/moshi/moshi-core/src/lm.rs:1014-1036`
- **voice.rs**: `packages/core/src/voice.rs:322`
