# CPU vs Metal Test Results

**Date**: 2025-11-09
**Test Result**: ❌ Both backends produce equally garbled audio

---

## Test Results

| Backend | Audio Quality | Waveform Score | User Description |
|---------|--------------|----------------|------------------|
| **Metal GPU** | ❌ Garbled | ~50/100 | "Extremely choppy and garbled" |
| **CPU** | ❌ Garbled | ~50/100 | "Equally garbled" |

---

## Conclusion

✅ **Ruled Out**: Candle Metal backend bug on M3 Max

❌ **Problem Confirmed**: Code logic bug OR Q8 GGUF model issue

The fact that both backends produce identical garbled output proves the issue is NOT in the Candle backend, but either:
1. Our implementation has a fundamental bug
2. The Q8 GGUF model itself is corrupt/broken

---

## What This Means

### Good News
- Not a platform-specific bug
- Will be same issue on Linux/CUDA
- Once fixed, will work everywhere

### Bad News
- Need deeper investigation
- Can't blame Candle/Metal
- Issue is in our code or the model

---

## Next Steps (Priority Order)

### 1. Test Official gen.rs (CRITICAL) ⭐

**Why**: Verify the Q8 model works with official implementation

**How**:
```bash
# Use official gen.rs with our test input
cd packages/moshi/moshi-cli

# Need to get gen.rs compiled and working
# Then run with same input file
```

**Expected Results**:
- **If gen.rs produces clear audio**: Our code has a bug
- **If gen.rs also produces garbled audio**: Q8 model is broken

### 2. Try bf16 Safetensors Model

**Why**: Q8 GGUF may have export issues

**Model**: `kyutai/moshika-candle-bf16` (3GB vs 1.5GB)

**Pros**:
- Full precision (no quantization artifacts)
- Likely has quality conditioning support
- Matches what PyTorch uses

**Cons**:
- Larger download (3GB)
- Slower inference (~2x)
- More VRAM

### 3. Deep Code Comparison

**If gen.rs works with Q8**, then we have a code bug. Compare:
- MIMI encoder/decoder state management
- Codebook extraction and ordering
- Tensor dimension handling
- Sample concatenation logic
- Any subtle differences in parameters

### 4. Test Python MLX as Reference

**Why**: Independent implementation to verify expected output

**How**:
```bash
# Install MLX version
pip install moshi-mlx

# Test with same input audio
# Compare output quality
```

---

## Most Likely Root Causes (Ranked)

### 1. Q8 GGUF Model Export Issue (High Probability)

**Evidence**:
- Q8 lacks quality conditioning weights
- Q8 uses different architecture config
- No existing bug reports (may be untested)

**Test**: Use bf16 safetensors instead

### 2. MIMI Codec State Management (Medium Probability)

**Evidence**:
- We share one MIMI instance for encode/decode
- Streaming codecs require careful state handling
- v8.2 tried to fix this

**Test**: Compare state handling with gen.rs

### 3. Codebook Ordering/Extraction (Medium Probability)

**Evidence**:
- v7.6 added nested loop for steps
- Codebook extraction is complex
- "Backwards" description suggests ordering issue

**Test**: Log codebook values and compare with gen.rs

### 4. LM Model Config Mismatch (Low Probability)

**Evidence**:
- v12.0 fixed vocab size
- moshi-q8.toml created custom config
- depformer settings may be wrong

**Test**: Use exact same config as gen.rs

---

## Recommended Action Plan

**Phase 1: Verify Model (1 hour)**
1. Get official gen.rs working
2. Test with same input file
3. If gen.rs produces clear audio → our code bug
4. If gen.rs also garbled → Q8 model issue

**Phase 2: Model Fix (If Q8 is broken)**
1. Download bf16 safetensors model
2. Update config to use bf16
3. Test audio generation
4. If works → document Q8 as broken

**Phase 3: Code Fix (If gen.rs works)**
1. Line-by-line comparison with gen.rs
2. Add extensive logging of tensors
3. Find exact point where output diverges
4. Fix the bug

---

## Technical Notes

### Why Both Backends Failed Identically

The garbling happens at a **higher level** than the backend:
- Tensor operations (wrong dimensions/order)
- Model configuration (wrong parameters)
- Data processing (codebook extraction)

The backend (Metal/CPU) just executes the operations we give it. If we give it wrong operations, both backends will produce wrong results.

### Why "Backwards" Description

The "talking backwards" sensation likely comes from:
- Temporal ordering issues (samples/frames in wrong order)
- Frequency domain artifacts (wrong codec parameters)
- Codebook misalignment (audio tokens don't match what MIMI expects)

---

## Files Created

- `docs/CPU_VS_METAL_TEST_READY.md` - Test preparation
- `docs/MOSHI_TESTING_METHODS.md` - Testing approaches
- `scripts/analyze-waveform.py` - Objective quality analysis
- `TEST_CPU_MODE.sh` - Automated test script

---

## Current Status

**What We Know**:
- ✅ Not a Metal backend bug
- ✅ Not a platform-specific issue
- ✅ Reproducible across CPU and GPU
- ✅ Consistent garbled output

**What We Don't Know**:
- ❓ Does official gen.rs work with Q8?
- ❓ Is Q8 GGUF model corrupt?
- ❓ Where exactly does our code diverge from gen.rs?

**Next Action**: Test official gen.rs implementation to isolate model vs code issue

---

**Priority**: Get gen.rs working and test it ASAP - this will tell us definitively if it's the model or our code.
