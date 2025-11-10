# MOSHI Audio Garbling - Diagnosis Status

**Date**: 2025-11-09
**Status**: In Progress - Testing official implementation

---

## What We've Established

### ✅ Confirmed Facts

1. **Audio is garbled on both CPU and Metal** (Scenario B)
   - Waveform score: ~50/100 on both backends
   - User description: "Extremely choppy and garbled, like people talking backwards"
   - Whisper API gives false positives (hallucinates text from garbled audio)

2. **Not a Candle backend bug**
   - Both Metal GPU and CPU produce identical garbled output
   - Rules out M3-specific Metal issues
   - Rules out platform-specific bugs

3. **Code matches gen.rs patterns**
   - Tensor concatenation: `Tensor::cat(&tensors, 2)` ✅
   - Sample extraction: `.i((0, 0))?.to_vec1::<f32>()` ✅
   - MIMI state: Shared encoder/decoder instance ✅
   - Nested loop: Processing each step ✅

4. **Config is correct**
   - v12.0 fixed vocab size mismatch (32001 vs 48001)
   - moshi-q8.toml matches Q8 architecture
   - depformer settings configured

5. **Not caused by forced text tokens**
   - v13.0 removed forced tokens
   - Still garbled with natural generation

---

## Current Hypothesis

**Two possible root causes remain:**

### Hypothesis A: Q8 GGUF Model is Broken ⚠️

**Evidence**:
- Q8 lacks quality conditioning weights (weights not in GGUF export)
- Q8 uses different architecture (4096 d_model vs 2048 in s2st-1b)
- No GitHub issues about Q8 audio quality (untested?)
- Both our implementation AND reference would fail

**Test**: Run official gen.rs with Q8 model
- **If official also garbled**: Q8 model is broken
- **If official works**: Our code has a bug

### Hypothesis B: Subtle Implementation Bug 🔍

**Possible areas**:
1. **MIMI codec state persistence** between encode/decode steps
2. **Codebook extraction order** or indexing
3. **Sample rate conversion** somewhere in the pipeline
4. **Tensor dimension handling** (subtle reshape/transpose issue)
5. **Config parameter** we haven't noticed yet

**Test**: Line-by-line comparison with working gen.rs

---

## Testing Strategy

### Phase 1: Isolate Model vs Code (IN PROGRESS)

**Action**: Test official MOSHI CLI with Q8 model

```bash
# Building official CLI now (background process)
cd packages/moshi/moshi-cli/tmp/moshi-official/rust
cargo build --release

# Then test with our input file
./target/release/moshi-cli gen \
  --lm-model-file ~/.cache/huggingface/.../model.q8.gguf \
  --lm-config-file ./s2st-1b.toml \
  --mimi-model-file ~/.cache/huggingface/.../mimi.safetensors \
  --audio-input-file /path/to/test-user-hello.wav \
  --text-tokenizer ~/.cache/huggingface/.../tokenizer.model \
  --audio-output-file ./tmp/official-output.wav
```

**Expected Results**:
- **Official works**: Our implementation bug (→ deep code comparison)
- **Official also garbled**: Q8 model is broken (→ try bf16 safetensors)

### Phase 2A: If Model is Broken

**Action**: Switch to bf16 safetensors model

**Model**: `kyutai/moshika-candle-bf16` or `kyutai/moshiko-candle-bf16`

**Changes needed**:
1. Update `hf_repo` in VoiceConfig
2. Use `s2st-1b.toml` config (48001 vocab)
3. Download ~3GB model
4. Test audio generation

**Expected**: Clear, intelligible audio

### Phase 2B: If Our Code is Buggy

**Action**: Deep comparison with gen.rs

**Method**:
1. Add extensive logging to voice.rs:
   - Log every tensor shape
   - Log codebook values
   - Log audio token arrays
   - Log PCM sample ranges

2. Run official gen.rs with same logging

3. Compare outputs line-by-line to find divergence point

4. Fix the bug

---

## Key Files

### Our Implementation
- `packages/core/src/voice.rs:1074-1400` - MOSHI test mode
- `packages/core/config/moshi-q8.toml` - Q8 config

### Official Reference
- `packages/moshi/moshi-cli/tmp/moshi-official/rust/` - Official repo
- `moshi-cli/src/gen.rs` - Reference implementation
- `s2st-1b.toml` - Official config

### Test Files
- `./tmp/test-user-hello.wav` - Input audio (24kHz)
- `./tmp/moshi-response.wav` - Our garbled output
- `./tmp/moshi-metal.wav` - Metal backend output (garbled)
- `./tmp/moshi-cpu.wav` - CPU backend output (garbled)

---

## Timeline

- **2025-11-06**: Initial garbled audio discovery
- **2025-11-07**: Multiple fix attempts (v8.x - v10.0)
- **2025-11-08**: Fixed config/vocab (v12.0)
- **2025-11-09**: Removed forced tokens (v13.0)
- **2025-11-09**: CPU vs Metal test - both garbled
- **2025-11-09**: Building official CLI for comparison

---

## Next Actions (Priority Order)

1. ⏳ **Wait for official CLI build** (in progress)
2. 🧪 **Test official gen.rs with Q8 model**
3. 🔍 **Analyze results**:
   - If official works → Deep code comparison
   - If official fails → Switch to bf16 model
4. 🔧 **Apply fix** based on findings
5. ✅ **Verify audio quality**

---

## Decision Tree

```
Test Official gen.rs with Q8
         │
         ├─→ Works?
         │   └─→ YES: Our code bug
         │       ├─ Deep comparison with gen.rs
         │       ├─ Add extensive logging
         │       ├─ Find divergence point
         │       └─ Fix bug
         │
         └─→ Also Garbled?
             └─→ YES: Q8 model broken
                 ├─ Download bf16 safetensors
                 ├─ Update config for bf16
                 ├─ Test with bf16
                 └─ Document Q8 as unusable
```

---

## Current Status

- 🔄 **Building**: Official MOSHI CLI
- ⏸️ **Waiting**: Build completion (few minutes)
- 🎯 **Next**: Run official gen.rs test
- 📋 **Outcome**: Will determine entire strategy

---

**This one test will tell us definitively**: Is it the model or our code? 🎯
