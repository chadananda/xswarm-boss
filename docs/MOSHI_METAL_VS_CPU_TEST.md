# MOSHI Metal vs CPU Backend Testing

**Date**: 2025-11-09
**Status**: Proposed diagnostic test
**Hypothesis**: Garbled audio may be caused by Candle Metal backend bug on M3 Max

---

## Problem Statement

MOSHI generates garbled/choppy audio that sounds "backwards" despite:
- ✅ Correct config loading (v12.0)
- ✅ Correct tensor operations (v10.0)
- ✅ Natural text generation (v13.0 - no forced tokens)
- ✅ Code matches working gen.rs implementation

**Waveform Analysis**: 50/100 score (appears garbled)
**User Confirmation**: "Extremely choppy and garbled... like a room full of people talking backwards"

---

## Hypothesis

The Q8 GGUF model may not work correctly with **Candle Metal backend on M3 Max**.

**Evidence**:
1. User's investigation docs mention Candle 0.9.2-alpha.1 **crashes on M3** with "foreign exceptions"
2. M3 Max is newer hardware - may have untested Metal backend issues
3. No GitHub issues found for "M3 garbled audio" or "Candle Metal MOSHI"
4. Audio sounds "backwards" - suggests fundamental tensor/buffer ordering issue

---

## Proposed Test: CPU Backend

**Goal**: Isolate whether garbling is caused by Metal backend or code logic

**Method**: Force MOSHI to use CPU backend instead of Metal GPU

### Implementation

**Option 1: Environment Variable** (if supported)
```bash
# Force CPU mode
CANDLE_FORCE_CPU=1 MOSHI_TEST_MODE=1 ~/.local/bin/xswarm --dev

# Compare with Metal mode
MOSHI_TEST_MODE=1 ~/.local/bin/xswarm --dev
```

**Option 2: Code Flag** (modify voice.rs)
```rust
// In voice.rs, line 324:
let device = Device::Cpu;  // Force CPU instead of Metal
```

**Option 3: Compile-time Flag**
```bash
# Build without Metal support
cargo build --release --no-default-features
```

### Expected Outcomes

| Scenario | CPU Audio | Metal Audio | Conclusion |
|----------|-----------|-------------|------------|
| **A** | ✅ Clear | ❌ Garbled | Metal backend bug on M3 |
| **B** | ❌ Garbled | ❌ Garbled | Code logic bug (not Metal) |
| **C** | ✅ Clear | ✅ Clear | Bug fixed (shouldn't happen) |

---

## If Metal is the Problem (Scenario A)

### Workaround Options

1. **Use CPU for development** (slow but works)
   - Set environment variable or code flag
   - Accept slower performance
   - Wait for Candle Metal fix

2. **Try Candle 0.9.2+ ** (if stable release exists)
   - Check if newer Candle fixes Metal issues
   - Test carefully (0.9.2-alpha.1 crashed)

3. **Switch to MLX backend** (Python)
   - Native M3 optimization
   - Better Metal support for Apple Silicon
   - Requires Python rewrite

4. **Report to Candle project**
   - File GitHub issue with reproduction
   - Provide M3 Max specs
   - Include garbled audio sample

### Production Strategy

If Metal is broken on M3:
- **Development**: Use CPU mode (slow but correct)
- **Production**: Deploy to Linux with CUDA (works correctly)
- **Mac users**: Offer CPU mode with warning about performance

---

## If Code Logic is the Problem (Scenario B)

Then the issue is in our implementation, not Candle/Metal. Need to:

1. **Deeper gen.rs comparison**
   - Check every single line
   - Verify MIMI state management
   - Check codebook extraction

2. **Test with same input as gen.rs**
   - Use identical audio file
   - Use identical seed
   - Compare byte-for-byte output

3. **Check Q8 GGUF model itself**
   - Maybe the Q8 export is corrupt?
   - Try different Q8 model variant
   - Try bf16 safetensors instead

---

## Testing Procedure

### Step 1: Force CPU Mode

**Edit voice.rs line 324**:
```rust
// BEFORE:
let device = Self::select_device(config.use_cpu)?;

// AFTER (force CPU):
let device = Device::Cpu;  // v13.2 TEST: Force CPU to isolate Metal
info!("FORCING CPU MODE FOR DIAGNOSTIC TEST");
```

### Step 2: Rebuild and Test
```bash
cargo build --release
MOSHI_TEST_MODE=1 ~/.local/bin/xswarm --dev
```

### Step 3: Listen to Audio
```bash
afplay ./tmp/moshi-response.wav
```

### Step 4: Run Waveform Analysis
```bash
python3 scripts/analyze-waveform.py ./tmp/moshi-response.wav
```

### Step 5: Document Results

**If CPU works**:
```
✅ CPU Audio: Clear and intelligible (score: 80+/100)
❌ Metal Audio: Garbled (score: 50/100)
→ CONCLUSION: Candle Metal backend bug on M3 Max
```

**If CPU also garbled**:
```
❌ CPU Audio: Still garbled (score: 50/100)
❌ Metal Audio: Garbled (score: 50/100)
→ CONCLUSION: Code logic bug or Q8 model issue
```

---

## Next Steps Based on Results

### If Metal is the Problem
1. File Candle GitHub issue
2. Use CPU for development
3. Deploy to Linux/CUDA for production
4. Monitor Candle releases for Metal fixes

### If Code/Model is the Problem
1. Deep dive into gen.rs line-by-line
2. Test with bf16 safetensors model
3. Check if Q8 GGUF export is corrupt
4. Consider Python MLX for comparison

---

## User Constraint

**Important**: User said "CPU is not an option" for production use.

**However**: CPU testing is still valuable for **diagnosis**, even if not production-viable:
- Helps identify if Metal is the root cause
- Informs whether to report to Candle team
- Guides whether to invest time in code fixes vs backend fixes

---

## Implementation Status

- [ ] Add CPU force flag to voice.rs
- [ ] Test with CPU backend
- [ ] Document CPU audio quality
- [ ] Compare CPU vs Metal results
- [ ] Make recommendation based on findings

---

**Next Action**: Implement CPU mode test to isolate Metal backend as potential cause
