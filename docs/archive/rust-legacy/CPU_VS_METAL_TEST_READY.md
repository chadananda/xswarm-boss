# CPU vs Metal Backend Test - READY TO RUN

**Date**: 2025-11-09
**Status**: ✅ Implementation complete, ready for testing
**Purpose**: Diagnose if garbled audio is caused by Candle Metal backend on M3 Max

---

## Summary

The garbled "backwards" sounding audio may be caused by a Candle Metal backend bug on M3 Max. We've added a CPU mode option to test this hypothesis.

---

## How to Test

### Test 1: Metal Backend (Current - Garbled)

```bash
# Clear old results
rm -rf ./tmp/experiments/ && rm -f ./tmp/moshi-response.wav

# Run with Metal (GPU)
MOSHI_TEST_MODE=1 ~/.local/bin/xswarm --dev

# Listen to audio
afplay ./tmp/moshi-response.wav

# Analyze waveform
python3 scripts/analyze-waveform.py ./tmp/moshi-response.wav

# Save for comparison
cp ./tmp/moshi-response.wav ./tmp/moshi-metal.wav
```

**Expected Result**: Garbled/choppy audio (score: ~50/100)

---

### Test 2: CPU Backend (Diagnostic)

```bash
# Clear old results
rm -rf ./tmp/experiments/ && rm -f ./tmp/moshi-response.wav

# Run with CPU (forced)
MOSHI_USE_CPU=1 MOSHI_TEST_MODE=1 ~/.local/bin/xswarm --dev

# Listen to audio
afplay ./tmp/moshi-response.wav

# Analyze waveform
python3 scripts/analyze-waveform.py ./tmp/moshi-response.wav

# Save for comparison
cp ./tmp/moshi-response.wav ./tmp/moshi-cpu.wav
```

**Expected Result**: Either clear audio (Metal bug) OR still garbled (code/model bug)

---

## Interpreting Results

### Scenario A: CPU Works, Metal Broken ✅

```
Metal Audio: Garbled (score: 50/100)
CPU Audio:   Clear (score: 80+/100)
```

**Conclusion**: Candle Metal backend bug on M3 Max

**Next Steps**:
1. File Candle GitHub issue with reproduction
2. Use CPU for development (slower but works)
3. Deploy to Linux with CUDA for production
4. Monitor Candle releases for Metal fixes
5. Document workaround for M3 users

**Production Impact**:
- ✅ Linux/CUDA unaffected (production OK)
- ⚠️ Mac M3 requires CPU mode (slower)
- 📋 Report to Candle team

---

### Scenario B: Both Broken ❌

```
Metal Audio: Garbled (score: 50/100)
CPU Audio:   Garbled (score: 50/100)
```

**Conclusion**: Code logic bug OR Q8 model issue (not backend)

**Next Steps**:
1. Deep comparison with gen.rs line-by-line
2. Test with bf16 safetensors model instead of Q8 GGUF
3. Check if Q8 GGUF export is corrupt
4. Consider Python MLX for reference comparison
5. Investigate MIMI codec state management

**Areas to investigate**:
- MIMI encoder/decoder state persistence
- Codebook extraction order
- Tensor dimension handling
- Sample rate conversions
- Q8 quantization artifacts

---

## Notes

**Performance Warning**: CPU mode will be SLOWER than Metal GPU:
- Metal: ~160-200ms latency
- CPU: ~500ms-1s latency (estimated)

**This is OK for diagnostics** - we need to isolate the bug source.

**User Constraint**: "CPU is not an option" for production, but testing CPU helps us decide:
- Should we report to Candle team? (if Metal broken)
- Should we debug our code? (if both broken)
- Should we try different model? (if Q8 issue)

---

## Current Status

**Implemented**:
- ✅ Added `MOSHI_USE_CPU` environment variable
- ✅ Modified main.rs to check env var in test mode
- ✅ Waveform analysis script ready
- ✅ Test procedure documented

**Ready to test**:
```bash
# Test Metal (current)
MOSHI_TEST_MODE=1 ~/.local/bin/xswarm --dev

# Test CPU (diagnostic)
MOSHI_USE_CPU=1 MOSHI_TEST_MODE=1 ~/.local/bin/xswarm --dev
```

**Compare audio**:
```bash
# Listen to both
afplay ./tmp/moshi-metal.wav
afplay ./tmp/moshi-cpu.wav

# Analyze both
python3 scripts/analyze-waveform.py ./tmp/moshi-metal.wav
python3 scripts/analyze-waveform.py ./tmp/moshi-cpu.wav
```

---

## What We've Tried So Far

All produced garbled audio on Metal:
- ✅ v12.0: Fixed config loading (vocab size)
- ✅ v13.0: Removed forced text tokens
- ✅ v10.0: Matched gen.rs tensor concatenation
- ✅ v8.2: Shared MIMI encoder/decoder state
- ✅ v7.6: Nested loop for codebook steps

**None of these fixed the garbling on Metal.**

**CPU test will tell us**: Is it the backend (Metal) or our code?

---

## Ready to Test

**Your next command**:
```bash
# Test with CPU backend
MOSHI_USE_CPU=1 MOSHI_TEST_MODE=1 ~/.local/bin/xswarm --dev
```

Then listen to `./tmp/moshi-response.wav` and tell us:
- Is it clear and intelligible?
- Or still garbled like Metal?

This one test will determine our next direction! 🎯
