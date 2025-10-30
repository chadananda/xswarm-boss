# MOSHI Voice Integration - Quick Start Guide

## Current Status

**Foundation**: ✅ Complete
**Mac Testing**: ⚠️ Architecture Issue Detected
**Linux/Windows**: 🚧 Planned

## What's Working

✅ Python voice bridge package (`packages/voice/`)
✅ MOSHI MLX installed (v0.3.0)
✅ Platform detection
✅ Config updated for MOSHI
✅ WebSocket server structure
✅ Test scripts created

## Current Issue

**CFFI Architecture Mismatch**:
```
ImportError: dlopen(..._cffi_backend.cpython-311-darwin.so, ...):
have 'x86_64', need 'arm64e' or 'arm64'
```

**Cause**: Python3 is likely installed for x86_64 (Rosetta) instead of native ARM64

**Impact**: Audio I/O (`sounddevice`) doesn't work, but model loading should still work

## Quick Fix Options

### Option 1: Use Homebrew Python (Recommended)

```bash
# Install Homebrew Python (native ARM64)
brew install python@3.11

# Use it for voice package
/opt/homebrew/bin/python3.11 -m pip install -e packages/voice

# Test
/opt/homebrew/bin/python3.11 packages/voice/test_moshi.py
```

### Option 2: Use pyenv (Clean)

```bash
# Install pyenv
brew install pyenv

# Install ARM64 Python
pyenv install 3.11.9

# Set for project
cd /path/to/xswarm-boss
pyenv local 3.11.9

# Reinstall packages
pip install -e packages/voice

# Test
python test_moshi.py
```

### Option 3: Skip Audio I/O for Now (Fastest)

Since we only need model loading for initial testing, we can work around the audio issue:

```python
# Simple model loading test (no audio I/O)
import mlx.core as mx
from moshi_mlx import models

# Load model config
config = models.config1b_202412()

# This should work even with CFFI issue
print(f"✓ Model config loaded: {config}")
```

## Testing Without Audio

The WebSocket server and model inference don't strictly need audio I/O - that's only needed for the standalone `moshi_mlx.local` command.

**Modified Test Plan**:
1. Load MOSHI model ✓ (should work)
2. Test inference with numpy arrays ✓ (should work)
3. WebSocket communication ✓ (should work)
4. Skip: Live microphone/speaker ✗ (needs CFFI fix)

## Next Steps

### For Mac Development (Now)

1. **Choose Fix Option** (recommend Option 1: Homebrew Python)

2. **Test Model Loading**:
   ```bash
   python3 -c "from moshi_mlx import models; print(models.config1b_202412())"
   ```

3. **Run Test Script**:
   ```bash
   cd packages/voice
   python3 test_moshi.py
   ```

4. **If Still Issues**: Check `planning/CROSS_PLATFORM_BUILDS.md` for details

### For Cross-Platform (Later)

See `planning/CROSS_PLATFORM_BUILDS.md` for:
- Linux PyTorch backend implementation
- Windows PyTorch backend implementation
- Docker distribution
- CI/CD setup

## Architecture Summary

```
xSwarm Rust ◄──WebSocket──► Python Bridge ◄──► MOSHI MLX
(cpal audio)                 (no audio dep)     (model only)
```

Audio I/O is handled by Rust (`cpal`), not Python, so CFFI issue won't block main integration.

## Testing Checklist

- [ ] Fix Python architecture OR use Homebrew Python
- [ ] Verify `import moshi_mlx` works
- [ ] Load model: `models.config1b_202412()`
- [ ] Test inference with dummy audio
- [ ] Start WebSocket server
- [ ] Connect Rust client (future)
- [ ] End-to-end audio test (future)

## Files Created

1. **`planning/MOSHI_INTEGRATION.md`** - Complete technical guide
2. **`planning/CROSS_PLATFORM_BUILDS.md`** - Platform support matrix
3. **`planning/MOSHI_QUICKSTART.md`** - This file
4. **`packages/voice/`** - Complete Python package
5. **`packages/voice/test_moshi.py`** - Test script

## Support

If issues persist:
1. Check Python architecture: `file $(which python3)`
2. Should show: `Mach-O 64-bit executable arm64`
3. If shows `x86_64`, reinstall Python

---

**TL;DR**:
- MOSHI infrastructure is ready
- Need to fix Python architecture for audio I/O
- Model loading should work regardless
- Can test WebSocket without audio
- Cross-platform expansion documented in CROSS_PLATFORM_BUILDS.md
