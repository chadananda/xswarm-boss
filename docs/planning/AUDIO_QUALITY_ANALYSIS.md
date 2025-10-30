# Audio Quality Analysis & Improvement Plan

**Created**: 2025-10-26
**Status**: Functional echo working, but quality poor

## Current Status

Voice echo is working through the MIMI codec, but audio quality is described as "awful" by the user. This document analyzes the root causes and proposes solutions.

## Root Cause Analysis

### 1. MIMI Codec Configuration

**Current Setup (Low Quality)**:
- **Codebooks**: 8 (MIMI_NUM_CODEBOOKS = 8 in voice.rs:30)
- **Bitrate**: 1.1 kbps (lowest quality setting)
- **Model**: moshika-candle-q8 (quantized to 8-bit)
- **Precision**: Q8 (8-bit quantized weights)

**Issue**: Using minimum quality codec settings

**Full MIMI Capabilities**:
- **Codebooks**: Up to 32 (standard configuration)
- **Bitrate**: 4.4 kbps with 32 codebooks (4x improvement)
- **Model**: kyutai/mimi (standalone, full-precision)
- **Precision**: F32 (32-bit floating point)

**Impact**: Currently using 25% of available codec quality (8/32 codebooks) with quantized weights.

### 2. Multiple Lossy Conversions

**Current Audio Pipeline**:
```
Phone (μ-law 8kHz)
  ↓ [Lossy: μ-law decoding]
  → PCM i16
  ↓ [Lossy: normalization]
  → f32 normalized
  ↓ [Lossy: resampling]
  → 24kHz f32
  ↓ [Lossy: MIMI encode/decode with 8 codebooks]
  → 24kHz f32
  ↓ [Lossy: resampling]
  → 8kHz f32
  ↓ [Lossy: denormalization]
  → PCM i16
  ↓ [Lossy: μ-law encoding]
  → μ-law 8kHz
```

**Issue**: 7 lossy conversion steps compound quality degradation

### 3. Resampling Quality

**Current Configuration** (audio.rs:171-177):
```rust
let params = SincInterpolationParameters {
    sinc_len: 256,              // Filter length
    f_cutoff: 0.95,             // Cutoff frequency (good)
    interpolation: SincInterpolationType::Linear,  // ⚠️ Basic interpolation
    oversampling_factor: 256,   // High (good)
    window: WindowFunction::BlackmanHarris2,  // Good window
};
```

**Issue**: Using `Linear` interpolation, which is the fastest but lowest quality option.

**Available Options**:
- `Linear` - Current (fast, lower quality)
- `Cubic` - Better quality, moderate speed
- `Quadratic` - Best quality, slower

## Improvement Plan

### Priority 1: Increase MIMI Codebooks (High Impact, Easy)

**Change**: Increase from 8 to 32 codebooks

**File**: `packages/core/src/voice.rs`

**Line**: 30
```rust
// Before:
const MIMI_NUM_CODEBOOKS: usize = 8;

// After:
const MIMI_NUM_CODEBOOKS: usize = 32;  // Full quality (4.4 kbps)
```

**Expected Impact**:
- 4x bitrate increase (1.1 kbps → 4.4 kbps)
- Significantly better audio quality
- Moderate performance impact (~2-4x slower encoding/decoding)

**Risk**: Moderate - May increase latency, but should still be real-time

### Priority 2: Upgrade Resampling Quality (Medium Impact, Easy)

**Change**: Switch from Linear to Cubic interpolation

**File**: `packages/core/src/audio.rs`

**Line**: 174
```rust
// Before:
interpolation: SincInterpolationType::Linear,

// After:
interpolation: SincInterpolationType::Cubic,  // Better quality
```

**Expected Impact**:
- Smoother interpolation between samples
- Better preservation of high frequencies
- Minimal performance impact

**Risk**: Low - Marginal CPU increase

### Priority 3: Consider Full-Precision MIMI Model (High Impact, Hard)

**Change**: Switch from quantized to full-precision MIMI

**Current**: `moshika-candle-q8` (8-bit quantized, bundled with Moshi)
**Alternative**: `kyutai/mimi` (F32 full-precision, standalone, 96.2M parameters)

**Expected Impact**:
- Much better audio quality
- Higher memory usage (~4x)
- Potentially slower inference

**Risk**: High - Requires significant code changes:
1. Load standalone MIMI model separately
2. Handle different model format
3. May not be compatible with current Candle integration
4. Increased memory footprint

**Recommendation**: Test priorities 1 & 2 first before considering this.

## Testing Strategy

1. **Baseline**: Record current quality metrics
   - Make test call, record audio quality assessment
   - Check latency (currently ~50-100ms per frame)

2. **Test Priority 1** (32 codebooks):
   - Update MIMI_NUM_CODEBOOKS to 32
   - Rebuild: `cargo build --release --bin xswarm`
   - Make test call
   - Assess quality vs latency tradeoff

3. **Test Priority 2** (Cubic interpolation):
   - Change resampling interpolation type
   - Rebuild
   - Make test call
   - Compare quality improvement

4. **Test Combined** (32 codebooks + Cubic):
   - Apply both changes together
   - Final quality assessment

## Implementation Order

### Step 1: Quick Wins (Est. 15 min)
- [ ] Change MIMI_NUM_CODEBOOKS from 8 to 32
- [ ] Change resampling interpolation to Cubic
- [ ] Rebuild in release mode
- [ ] Test with phone call

### Step 2: Fine-tuning (If needed)
- [ ] If latency too high with 32 codebooks, try 16 or 24
- [ ] Consider adjusting other resampling parameters
- [ ] Profile performance bottlenecks

### Step 3: Advanced (Future)
- [ ] Evaluate full-precision MIMI model
- [ ] Consider reducing conversion steps
- [ ] Investigate direct 8kHz processing (skip upsampling?)

## Performance Considerations

### Current Performance:
- **MIMI encode/decode**: ~50-100ms per 80ms frame
- **Total latency**: ~80-120ms (real-time capable)
- **CPU usage**: Moderate (running on CPU, not GPU)

### Expected After Changes:
- **32 codebooks**: 2-4x slower MIMI processing
- **Estimated latency**: 150-400ms per frame
- **Still acceptable**: Twilio can buffer 500ms+

### Fallback Options:
- If 32 codebooks too slow: Try 16 or 24
- If still slow: Enable GPU acceleration (Metal on M4)
- If still issues: Consider optimizing buffering

## Quality Metrics to Track

1. **Subjective Quality**:
   - User assessment (primary metric)
   - Speech intelligibility
   - Artifacts (crackling, distortion, etc.)

2. **Objective Metrics**:
   - Processing latency per frame
   - End-to-end latency
   - CPU usage
   - Memory usage

3. **Success Criteria**:
   - Audio quality acceptable for conversation
   - Latency < 500ms (Twilio buffer limit)
   - CPU usage sustainable
   - No dropped frames or disconnects

## Technical References

### MIMI Codec Specifications:
- **Sample Rate**: 24 kHz
- **Frame Rate**: 12.5 Hz (80ms frames)
- **Codebooks**: 8 (low) to 32 (high quality)
- **Bitrate**: 1.1 kbps (8 codebooks) to 4.4 kbps (32 codebooks)
- **Architecture**: RVQ (Residual Vector Quantization) with 32 levels
- **Training**: Uses WavLM distillation + adversarial loss

### Key Papers & Documentation:
- Moshi paper: https://kyutai.org/Moshi.pdf
- Moshi GitHub: https://github.com/kyutai-labs/moshi
- MIMI Hugging Face: https://huggingface.co/kyutai/mimi
- Codec explainer: https://kyutai.org/next/codec-explainer

## Notes

- MIMI uses RVQ dropout during training, allowing flexible codebook counts at inference
- The paper advertises 8 codebooks (1.1 kbps) but implementation defaults to 32 (4.4 kbps)
- For TTS applications, 8 codebooks is common, but full-duplex voice benefits from higher quality
- Twilio's μ-law is already lossy (8kHz, log compression), limiting the ceiling for quality improvements

## Conclusion

**Short Answer**: Yes, audio quality is solvable!

**Quick Fix**: Increase codebooks to 32 and upgrade resampling to Cubic interpolation. This should provide immediate quality improvements with acceptable latency.

**Long-term**: Consider GPU acceleration (Metal) and potentially the full-precision MIMI model for maximum quality.

**Next Step**: Implement Priority 1 & 2 changes and test.
