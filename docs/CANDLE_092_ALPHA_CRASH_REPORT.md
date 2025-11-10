# Candle 0.9.2-alpha.1 Crash Report - M3 Mac

**Date**: 2025-11-08
**Platform**: macOS 14.4 (Darwin 23.4.0)
**Hardware**: Apple M3 Max
**Issue**: Fatal crash with "foreign exceptions" when initializing MOSHI models

## Summary

Tested upgrading from Candle 0.9.1 to 0.9.2-alpha.1 (Metal refactor) to investigate garbled audio issue. **Result: Immediate crash during model initialization.**

## Error Details

```
fatal runtime error: Rust cannot catch foreign exceptions
```

**Error Location**: During MOSHI voice model initialization
**Stack**: Metal backend / ONNX runtime foreign exception

## Test Procedure

1. ✅ Updated `Cargo.toml` workspace dependencies:
   ```toml
   candle = { version = "0.9.2-alpha.1", package = "candle-core", features = ["metal"] }
   candle-nn = { version = "0.9.2-alpha.1", features = ["metal"] }
   candle-transformers = { version = "0.9.2-alpha.1", features = ["metal"] }
   candle-flash-attn = "0.9.2-alpha.1"
   ```

2. ✅ Updated dependencies:
   ```
   Updating candle-core v0.9.1 -> v0.9.2-alpha.1
   Updating candle-metal-kernels v0.9.1 -> v0.9.2-alpha.1
   Removing metal v0.27.0  (new Metal backend)
   ```

3. ✅ Compilation successful - no errors, only warnings
4. ✅ Binary built successfully (release mode)
5. ❌ **Runtime crash** during MOSHI model initialization

## Crash Log

```
🧪 MOSHI AUDIO TEST MODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 Testing configuration: config_1_ultra_high_quality
   Ultra high quality: sinc_len=512, f_cutoff=0.99, Linear

🔊 Initializing MOSHI voice models...
   (This may take 30-60 seconds for first-time model download)

fatal runtime error: Rust cannot catch foreign exceptions
```

## Analysis

### Root Cause
The Candle 0.9.2-alpha.1 Metal refactor introduced breaking changes or bugs that cause foreign exceptions (likely from Metal framework or ONNX runtime) during model initialization on M3 hardware.

### Why No Prior Reports?
1. **Alpha version** - Not widely tested in production
2. **M3-specific** - Newer hardware with less adoption
3. **MOSHI + Candle combination** - Specific use case may not be extensively tested

### Comparison with v0.9.1
- **v0.9.1**: Models load successfully, generate audio (garbled but doesn't crash)
- **v0.9.2-alpha.1**: Immediate crash during initialization

## Implications

1. **Cannot use Metal refactor** - Must stay on v0.9.1 until fixed
2. **Garbled audio persists** - Still present in v0.9.1 (original issue)
3. **Needs upstream fix** - Bug report to Candle project required

## Rollback

Reverted to Candle 0.9.1 with documentation:
```toml
# NOTE: Tested v0.9.2-alpha.1 on M3 - CRASHES with "foreign exceptions"
# Rolling back to v0.9.1 until Metal refactor is stable
candle = { version = "0.9.1", package = "candle-core", features = ["metal"] }
```

## Next Steps

1. ✅ **Rollback complete** - Back to stable v0.9.1
2. ⬜ **Report to Candle** - File issue about M3 crash in 0.9.2-alpha.1
3. ⬜ **Report garbled audio** - File issue about M3 garbled MOSHI output in 0.9.1
4. ⬜ **Alternative investigation** - Try MLX implementation (Python-based, different backend)

## Related Issues

### Investigated
- **Candle Issue #85**: Different symptoms (ELU kernel, f32/bf16 precision)
- **Candle Issue #2818**: "IOGPUMetalCommandBuffer failed assertion" - related but different error
- **Candle Issue #2570**: argsort Metal kernel bug - different operation

### Not Found
- No reports of completely garbled/unintelligible MOSHI audio on M-series Macs
- No reports of "foreign exceptions" crash in 0.9.2-alpha.1 on M3

## Conclusion

**Candle 0.9.2-alpha.1 Metal refactor is incompatible with M3 Mac for MOSHI workloads.**

The crash prevents any testing of whether the Metal refactor would have fixed the garbled audio issue. Must wait for:
- Candle team to fix M3 compatibility in Metal refactor, OR
- Investigate alternative approaches (MLX, CPU mode, different model versions)

---

**Status**: BLOCKED on upstream Candle Metal refactor M3 compatibility
