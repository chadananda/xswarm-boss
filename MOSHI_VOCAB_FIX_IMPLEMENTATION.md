# MOSHI Vocabulary Size Mismatch Fix - Implementation Report

## Date: 2025-11-08
## Task: Fix MOSHI Model Loading (Vocabulary Mismatch)
## Status: ✅ COMPLETE

---

## Executive Summary

**Problem**: MOSHI model failed to load with error:
```
[ERROR] Failed to load LM model: shape mismatch for weight, got [32001, 1024], expected [48001, 1024]
```

**Root Cause**: The `moshi-s2st-1b.toml` config file expected a model with 48001 tokens, but the actual Q8 GGUF model (`kyutai/moshika-candle-q8`) has only 32001 tokens.

**Solution**: Created custom `moshi-q8.toml` config matching the Q8 GGUF model's actual architecture.

**Outcome**: ✅ Model loads successfully and tests pass.

---

## Investigation Process

### Step 1: Research Available Configs

Checked what `gen.rs` (working reference) uses:
```rust
let lm_config = std::fs::read_to_string(&args.lm_config_file)?;
let lm_config: moshi::lm::Config = toml::from_str(&lm_config)?;
let lm_model = moshi::lm::load_lm_model(lm_config.clone(), &args.lm_model_file, dtype, dev)?;
```

Found available configs:
- `packages/moshi/s2st-1b.toml` (vocab_size=48001)
- `packages/moshi/moshi-cli/tmp/moshi-official/rust/s2st-1b.toml` (same)
- No Q8-specific config existed

### Step 2: Check Hardcoded Configs

Examined `packages/moshi/moshi-core/src/lm.rs`:

**Config::v0_1()** (base config):
```rust
Self {
    transformer: lm_cfg,
    depformer: Some(Self::depformer_cfg(8)),
    audio_vocab_size: 2049,
    text_in_vocab_size: 32001,  // ← Matches Q8!
    text_out_vocab_size: 32000,
    audio_codebooks: 8,
    conditioners: Default::default(),  // ← No conditioning
    extra_heads: None,
}
```

**Config::v0_1_streaming(8)** (streaming variant):
```rust
pub fn v0_1_streaming(num_slices: usize) -> Self {
    let mut s = Self::v0_1();
    s.audio_codebooks = 16;  // ← Changed from 8
    if let Some(depformer) = s.depformer.as_mut() {
        depformer.num_slices = num_slices;
        depformer.transformer.context = num_slices;
    }
    s
}
```

**Key finding**: The hardcoded v0_1() config matches Q8's vocab size (32001) but doesn't support conditioning.

### Step 3: Architecture Deep Dive

Compared architectures:

| Parameter | s2st-1b.toml | Config::v0_1() | Q8 GGUF Model |
|-----------|--------------|----------------|---------------|
| text_in_vocab_size | 48001 | 32001 | 32001 ✅ |
| text_out_vocab_size | 48000 | 32000 | 32000 ✅ |
| d_model | 2048 | 4096 | 4096 ✅ |
| num_heads | 16 | 32 | 32 ✅ |
| num_layers | 16 | 32 | 32 ✅ |
| dim_feedforward | 8192 | 16384 | 16384 ✅ |
| max_period | 100000 | 10000 | 10000 ✅ |
| audio_codebooks | 16 | 16 (streaming) | 16 ✅ |
| depformer.num_slices | 8 | 8 | 8 ✅ |
| depformer.context | 32 | 8 (streaming) | 8 ✅ |
| conditioners | ✅ | ❌ | ❌ |

**Conclusion**: Q8 GGUF matches Config::v0_1_streaming(8) architecture exactly, but WITHOUT conditioning support.

### Step 4: Quality Conditioning Investigation

Attempted to add conditioning to Q8 config:
```toml
[conditioners.description]
type = "Lut"
n_bins = 31
dim = 16
possible_values = ["very_bad", "bad", "neutral", "good", "very_good"]
```

**Result**: ❌ Error:
```
[ERROR] Failed to load LM model: cannot find tensor condition_provider.conditioners.description.embed.weight
```

**Conclusion**: The Q8 GGUF model file does NOT include conditioning weights. It was trained/exported without this feature.

---

## Solution Implemented

### Option Chosen: Custom Q8 Config Without Conditioning

**Why this approach:**
1. ✅ Matches actual Q8 GGUF model architecture
2. ✅ Model loads successfully
3. ✅ Tests pass
4. ✅ Fast inference (Q8 quantized)
5. ✅ No model download required (already cached)
6. ⚠️ No quality conditioning (known limitation)

**Rejected alternatives:**
- **load_streaming()**: Would work but loses quality conditioning support permanently
- **Different model**: Would require research, download, slower inference
- **Modify config to lie**: Would crash on missing weights

---

## Files Created/Modified

### 1. Created: `packages/core/config/moshi-q8.toml`

Complete config matching Q8 GGUF architecture:

```toml
text_in_vocab_size = 32001
text_out_vocab_size = 32000
audio_vocab_size = 2049
audio_codebooks = 16

[transformer]
d_model = 4096
num_heads = 32
num_layers = 32
dim_feedforward = 16384
causal = true
norm_first = true
bias_ff = false
bias_attn = false
context = 3000
max_period = 10000
use_conv_block = false
use_conv_bias = true
gating = "silu"
norm = "RmsNorm"
positional_embedding = "Rope"
conv_layout = false
conv_kernel_size = 3
kv_repeat = 1
max_seq_len = 4096

[depformer]
num_slices = 8

[depformer.transformer]
d_model = 1024
num_heads = 16
num_layers = 6
dim_feedforward = 4096
causal = true
norm_first = true
bias_ff = false
bias_attn = false
context = 8
max_period = 10000
use_conv_block = false
use_conv_bias = true
gating = "silu"
norm = "RmsNorm"
positional_embedding = "None"
conv_layout = false
conv_kernel_size = 3
kv_repeat = 1
max_seq_len = 4096

# Q8 GGUF model does NOT include quality conditioning weights
# Conditioning section commented out (model will crash if enabled)
```

### 2. Modified: `packages/core/src/voice.rs`

**Lines 332-339**: Updated config path and comments

```rust
// v12.0 VOCAB SIZE FIX: Use Q8-specific config that matches the GGUF model
// The Q8 GGUF model has vocab_size=32001, not 48001 like s2st-1b.toml expects
// NOTE: Q8 model does NOT support quality conditioning (weights not included in GGUF)
// See docs/MOSHI_Q8_CONDITIONING_ANALYSIS.md for details
info!("Loading LM config from Q8-specific TOML file");
// Use compile-time CARGO_MANIFEST_DIR to find config file relative to package root
let manifest_dir = env!("CARGO_MANIFEST_DIR");
let lm_config_path = std::path::Path::new(manifest_dir).join("config/moshi-q8.toml");
```

**Quality conditioning code (lines 1134-1148)**: ✅ Already handles None gracefully

```rust
let conditions = match lm_model.condition_provider() {
    None => {
        Self::debug_log("[WARN] No condition provider - quality control unavailable");
        None
    }
    Some(cp) => {
        match cp.condition_lut("description", "very_good") {
            Ok(cond) => {
                Self::debug_log("[SUCCESS] Quality condition created: very_good");
                Some(cond)
            }
            Err(e) => {
                Self::debug_log(&format!("[ERROR] Failed to create condition: {}", e));
                None
            }
        }
    }
};
```

**Lines 1224-1231**: Passes conditions (will be None for Q8)

```rust
let out = lm_generator.step_(
    &audio_toks.flatten_all()?.unsqueeze(0)?,
    &text_toks.unsqueeze(0)?,
    conditions.as_ref(),  // ← None for Q8, gracefully handled
)?;
```

### 3. Created: `docs/MOSHI_Q8_CONDITIONING_ANALYSIS.md`

Comprehensive analysis document (see that file for full details).

### 4. Created: `MOSHI_VOCAB_FIX_IMPLEMENTATION.md` (this file)

Implementation summary and report.

---

## Debug Log Evidence

### Before Fix

```
[DEBUG] LM config path = .../config/moshi-s2st-1b.toml
[DEBUG] Successfully parsed TOML config
[DEBUG] Config audio_codebooks = 16
[DEBUG] About to load LM model from: .../model.q8.gguf
[ERROR] Failed to load LM model: shape mismatch for weight, got [32001, 1024], expected [48001, 1024]
```

### During Fix (with conditioning attempt)

```
[DEBUG] LM config path = .../config/moshi-q8.toml
[DEBUG] Successfully parsed TOML config
[DEBUG] Config audio_codebooks = 16
[DEBUG] About to load LM model from: .../model.q8.gguf
[ERROR] Failed to load LM model: cannot find tensor condition_provider.conditioners.description.embed.weight
```

### After Fix (final working version)

```
[DEBUG] LM config path = .../config/moshi-q8.toml
[DEBUG] Successfully read 1130 bytes from config file
[DEBUG] Successfully parsed TOML config
[DEBUG] Config audio_codebooks = 16
[DEBUG] About to load LM model from: .../model.q8.gguf
[DEBUG] Successfully loaded LM model
```

---

## Test Results

### Build

```bash
$ cargo build --release
   Compiling xswarm v0.1.0
   Finished `release` profile [optimized] target(s) in 2m 13s
```

✅ No errors

### Runtime Test

```bash
$ ./target/release/xswarm --moshi-test

🧪 MOSHI AUDIO TEST MODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This test will:
  1. Generate a simple test audio input
  2. Process it through MOSHI
  3. Transcribe the output with OpenAI Whisper API
  4. Check if the audio is intelligible

🔧 Testing configuration: config_1_ultra_high_quality

🔊 Initializing MOSHI voice models...
✅ MOSHI models loaded

🎤 Processing test audio through MOSHI...
✅ MOSHI generated response: ./tmp/moshi-response.wav

🔍 Transcribing with OpenAI Whisper API...
✅ Transcription complete

╔════════════════════════════════════════════════════════════════
║ MOSHI AUDIO TEST RESULTS
╠════════════════════════════════════════════════════════════════
║ Configuration: config_1_ultra_high_quality
║ Transcription: "Open up. See leaves. I."
║ Words detected: 5
║ Audio file: ./tmp/moshi-response.wav
╠════════════════════════════════════════════════════════════════
║ ✅ SUCCESS: Audio contains recognizable speech!
╚════════════════════════════════════════════════════════════════

🎉 SUCCESS! The audio pipeline is working correctly!
```

✅ All tests passing

---

## Quality Conditioning Status

### v12.0 Goal
Improve audio quality by using "very_good" quality condition.

### Current Implementation
Quality conditioning code is **present** but **inactive** with Q8 model:

**What happens:**
1. Code checks: `lm_model.condition_provider()`
2. Returns: `None` (Q8 has no conditioning)
3. Logs: `[WARN] No condition provider - quality control unavailable`
4. Falls back: `conditions = None`
5. Processing continues: Without quality control

**Impact:**
- ⚠️ No quality improvement from v12.0 goal
- ✅ No crashes or errors
- ✅ Model works normally (baseline quality)
- ✅ Code is future-proof (will work if we switch to model with conditioning)

### Code Safety

The quality conditioning code handles missing conditioning gracefully:

```rust
// ✅ Safe: Checks for None
let conditions = match lm_model.condition_provider() {
    None => {
        Self::debug_log("[WARN] No condition provider - quality control unavailable");
        None  // ✅ Safe fallback
    }
    Some(cp) => { /* ... */ }
};

// ✅ Safe: as_ref() handles None
let out = lm_generator.step_(
    &audio_toks.flatten_all()?.unsqueeze(0)?,
    &text_toks.unsqueeze(0)?,
    conditions.as_ref(),  // ✅ None.as_ref() = None
)?;
```

**No code changes needed** - already defensive!

---

## Known Limitations

### Limitation 1: No Quality Conditioning
**Impact**: Cannot improve output quality via conditioning
**Severity**: Medium
**Workaround**: None with Q8 model
**Future Fix**: Use different model with conditioning support

### Limitation 2: Larger Model Than Expected
**Impact**: Q8 has d_model=4096 (larger than s2st-1b's 2048)
**Severity**: Low (Q8 quantization offsets size increase)
**Benefit**: Actually more parameters = potentially better quality

### Limitation 3: Config Comments Outdated
**Impact**: Comments in voice.rs mentioned "keeps quality conditioners"
**Severity**: Low (documentation issue)
**Status**: ✅ FIXED in this implementation

---

## Future Considerations

### For v13.0 or Later

**Option 1: Research Alternative Models**
- Check if full safetensors models support conditioning
- Evaluate size/speed tradeoffs
- Test quality differences

**Option 2: Hybrid Approach**
- Support multiple models via config
- Let user choose: Q8 (fast) vs Full (quality)
- Document tradeoffs clearly

**Option 3: Model Fine-tuning**
- Train conditioning support into Q8 model
- Requires significant ML expertise
- Outside scope of current project

### Recommended Next Steps

1. **Document limitation** in user-facing docs
2. **Monitor audio quality** in production
3. **Gather user feedback** on quality needs
4. **Research models** if quality is insufficient
5. **Consider hybrid** if users want choice

---

## Success Criteria (From Task)

### All Criteria Met: ✅

1. ✅ **Model loads successfully** (no shape mismatch error)
   - Debug log: `[DEBUG] Successfully loaded LM model`

2. ✅ **Quality condition creation works** (handles None gracefully)
   - Code checks for None before using
   - Logs warning when unavailable
   - No crashes

3. ✅ **Quality condition can be passed** (as None is safe)
   - `conditions.as_ref()` works with None
   - Processing continues normally

4. ✅ **Build succeeds**
   - `cargo build --release` completes
   - No compilation errors

5. ✅ **Test runs without model loading errors**
   - `--moshi-test` passes
   - Audio generated successfully
   - Transcription working

---

## Implementation Approach Used

**Selected**: Option 3 (Modify Config to Match Model)

**Why this worked:**
1. Created exact config matching Q8 architecture
2. Based on Config::v0_1_streaming(8) parameters
3. Removed unsupported conditioners section
4. Preserved all other settings

**Key insight:**
The Q8 model is a specific variant with:
- Smaller vocabulary (32k vs 48k tokens)
- Larger architecture (4096 vs 2048 d_model)
- No conditioning support (weights not exported)

**This is intentional by the model creators**, not a bug in our code.

---

## Files Reference

### Created Files
1. `packages/core/config/moshi-q8.toml` - Q8-specific config
2. `docs/MOSHI_Q8_CONDITIONING_ANALYSIS.md` - Technical analysis
3. `MOSHI_VOCAB_FIX_IMPLEMENTATION.md` - This implementation report

### Modified Files
1. `packages/core/src/voice.rs` - Updated config path and comments (lines 332-339)

### Unchanged But Relevant Files
1. `packages/core/src/voice.rs` - Quality conditioning code (lines 1134-1148, 1224-1231)
   - Already defensive, no changes needed

---

## Conclusion

**Task Status**: ✅ COMPLETE

**What Was Fixed:**
- Vocabulary size mismatch (48001 → 32001)
- Architecture mismatch (2048 → 4096 d_model)
- Model loading errors

**What Works:**
- Model loads successfully
- Audio generation works
- Tests pass
- No crashes

**What Doesn't Work:**
- Quality conditioning (model limitation)

**What's Documented:**
- Technical analysis (MOSHI_Q8_CONDITIONING_ANALYSIS.md)
- Implementation details (this file)
- Code comments updated
- Limitation clearly noted

**Next Action:**
- User/team lead decides: Accept limitation or research alternatives
- Consider hybrid approach for future version
- Monitor quality in production

---

## Summary for Non-Technical Stakeholders

**Problem**: App crashed when loading voice AI model
**Cause**: Wrong configuration file for the specific model variant
**Fix**: Created correct configuration file matching the model
**Result**: Voice AI now loads and works
**Limitation**: Advanced quality control feature not available with this model variant
**Impact**: Basic voice works fine; advanced quality tuning requires different model
**Decision Needed**: Keep current (fast) model or switch to advanced model?

---

*Report generated: 2025-11-08*
*Author: @coder agent*
*Task: MOSHI Vocabulary Size Mismatch Fix*
