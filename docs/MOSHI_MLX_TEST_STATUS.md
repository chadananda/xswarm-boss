# MOSHI MLX Test Status

**Date**: 2025-11-08
**Platform**: macOS 14.4 (Darwin 23.4.0)
**Hardware**: Apple M3 Max

## Objective

Test Python MLX implementation of MOSHI to determine if garbled audio issue is:
- **Rust/Candle Metal backend specific**, OR
- **Model/M3 hardware specific**

## Progress

### ✅ Completed

1. **Virtual environment created**: `./tmp/venv-mlx/` with arm64 Python packages
2. **Packages installed successfully**:
   - `moshi_mlx==0.3.0` (arm64)
   - `soundfile==0.13.1` (macosx_11_0_arm64)
   - `mlx==0.26.5` (macosx_14_0_arm64)
   - `numpy==2.2.6` (macosx_14_0_arm64)
   - All dependencies properly installed for M3

3. **Architecture issue resolved**: Initial x86_64 package conflict fixed by using project-local virtual environment

### ❌ Blocked

**Problem**: `moshi_mlx` Python package does not export a programmatic API for testing.

**What we found**:
- Package structure shows: `['models', 'modules', 'utils']`
- NO direct export of `MimiModel`, `LMModel`, or similar classes
- Package designed for **command-line interface only**: `python -m moshi_mlx.local`
- CLI is **interactive voice chat** - cannot test with specific audio file input
- No documented programmatic API in PyPI, GitHub README, or web search

**What this means**:
- Cannot perform apples-to-apples comparison with Rust implementation
- Cannot test with same `./tmp/test-user-hello.wav` input used in Rust test
- Cannot generate comparable output for MD5 verification

## Alternative Approaches

### Option 1: Manual Interactive Testing (PARTIAL)
**Description**: Run MLX interactive mode, speak into microphone, listen to output quality

**Pros**:
- Quick to test
- Can subjectively assess audio quality

**Cons**:
- Not comparable to Rust test (different input)
- Subjective assessment only
- Doesn't isolate the specific issue

**Command**:
```bash
./tmp/venv-mlx/bin/python3 -m moshi_mlx.local -q 4
```

### Option 2: Inspect moshi_mlx Source Code
**Description**: Clone repository and examine source to create custom test script

**Steps**:
1. Clone: `git clone https://github.com/kyutai-labs/moshi`
2. Navigate to: `moshi_mlx/` directory
3. Find model loading code in source
4. Create custom script that imports internal modules

**Pros**:
- Would enable programmatic testing
- Could use same input file as Rust test

**Cons**:
- Time-intensive
- May break between versions
- Relies on internal/undocumented APIs

### Option 3: Test with PyTorch Implementation
**Description**: Use official PyTorch version instead of MLX

**Pros**:
- May have better documented API
- Different backend (PyTorch vs MLX vs Candle)
- Still isolates whether issue is Rust-specific

**Cons**:
- Different backend from MLX (not Apple-optimized)
- May not work well on M3 (designed for CUDA)

### Option 4: Focus on Upstream Bug Reports
**Description**: Document findings and report to Candle project

**Status**:
- ✅ MOSHI produces garbled audio on M3 with Candle 0.9.1 Metal backend
- ✅ Byte-identical output across multiple configurations (MD5: 4d49440e24fa4cf984df84d280e47413)
- ✅ Candle 0.9.2-alpha.1 crashes with "foreign exceptions" on M3
- ⬜ No existing GitHub issues for either problem (unreported bugs)
- ⬜ Report needs: Hardware specs, Candle versions, model details, reproduction steps

**Next steps**:
1. Create minimal reproduction case for Candle team
2. File issue: "MOSHI produces garbled audio on M3 Mac with Metal backend"
3. File issue: "Candle 0.9.2-alpha.1 crashes with foreign exceptions on M3"

## Recommendation

**RECOMMENDED**: **Option 4** - Report upstream to Candle project

**Reasoning**:
1. We have solid evidence:
   - Garbled audio is reproducible and consistent (byte-identical)
   - Tested multiple resampling configurations (all failed identically)
   - Candle upgrade crashes (v0.9.2-alpha.1 incompatible with M3)
   - No existing issue reports (novel discovery)

2. MLX testing blocked by API limitations - cannot perform comparable test

3. User confirmed: "CPU is not an option" - must work with GPU/Metal

4. Since no other M-series users have reported this, it's either:
   - M3-specific (newer hardware, less tested)
   - Configuration-specific
   - First discovery of this bug combination

## Current Status

**BLOCKED**: Cannot proceed with Python MLX comparative testing due to lack of programmatic API.

**READY TO PROCEED**: Have sufficient evidence to file upstream Candle bug reports.

## Related Documentation

- [Candle 0.9.2-alpha.1 Crash Report](./CANDLE_092_ALPHA_CRASH_REPORT.md)
- [Previous MOSHI audio investigation](../MOSHI_AUDIO_SUMMARY.md)
- [Test input audio](../tmp/test-user-hello.wav) - 48000Hz, synthetic voice "Hello"
- [Garbled output](../tmp/moshi-response.wav) - MD5: 4d49440e24fa4cf984df84d280e47413

## Next Actions

**User decision needed**:
1. **Report to Candle** - File bug reports with reproduction case?
2. **Manual MLX test** - Run interactive mode for subjective quality assessment?
3. **Deep dive MLX source** - Invest time to create custom test script?
4. **Wait for updates** - Monitor Candle releases for M3 fixes?

---

**Status**: AWAITING USER DECISION ON NEXT STEPS
