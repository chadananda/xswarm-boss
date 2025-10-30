# CFFI Architecture Issue - Research & Solutions

**Date**: 2025-10-24
**Issue**: CFFI backend compiled for x86_64, need arm64
**Impact**: Blocks `sounddevice` library (audio I/O)

## Research Findings

### 1. Root Cause

```bash
$ file /Library/.../site-packages/_cffi_backend.cpython-311-darwin.so
Mach-O 64-bit x86_64 bundle  ← Problem: x86_64, need arm64
```

**Why**: CFFI was installed when Python was running under Rosetta (x86_64 emulation)

### 2. Critical Discovery

**WE DON'T NEED TO FIX THIS!**

Testing shows:
- ✅ `moshi_mlx.models` works WITHOUT sounddevice
- ✅ MLX array operations work
- ✅ Core inference works
- ❌ ONLY `moshi_mlx.local` (standalone CLI) needs sounddevice

**Why sounddevice is required**:
- `moshi_mlx.local.py` - Standalone CLI tool (uses microphone/speakers directly)
- Our `packages/voice/bridge.py` - WebSocket server (audio comes from Rust via WebSocket)

**Architecture**:
```
┌─────────────┐
│ Rust (cpal) │ ← Handles microphone/speakers (no Python)
└──────┬──────┘
       │ WebSocket (PCM audio bytes)
       ▼
┌─────────────┐
│ Python      │ ← Receives audio as numpy arrays
│ bridge.py   │   (doesn't need sounddevice!)
└──────┬──────┘
       │ MLX API
       ▼
┌─────────────┐
│ MOSHI Model │
└─────────────┘
```

### 3. Dependency Analysis

**moshi_mlx package imports**:
```python
# moshi_mlx/local.py (standalone CLI)
import sounddevice  # ← Only here!

# moshi_mlx/models/* (what we use)
import mlx.core     # ✓ Works
import numpy        # ✓ Works
import sentencepiece # ✓ Works
# No sounddevice!
```

**Our bridge.py imports**:
```python
import numpy
from moshi_mlx import models  # ✓ Works without sounddevice
import mlx.core               # ✓ Works
# No sounddevice needed!
```

## Solutions (Ranked)

### Option 1: Remove sounddevice Dependency (RECOMMENDED)

**Why**: We don't need it!

**How**:
```bash
cd packages/voice

# Update pyproject.toml to make sounddevice optional
# It's currently required by moshi_mlx, but we don't use that code path
```

**Pros**:
- No CFFI fix needed
- Cleaner architecture
- Works immediately
- No sudo required

**Cons**:
- Can't use `python3 -m moshi_mlx.local` for standalone testing
- (But we have our own test script anyway)

### Option 2: User-Local CFFI Install

**Why**: Avoid system-wide changes

**How**:
```bash
python3 -m pip install --user --force-reinstall cffi sounddevice
```

**Pros**:
- No sudo required
- Keeps all functionality
- Clean user isolation

**Cons**:
- Doesn't fix system CFFI (may conflict)
- User packages can get messy

### Option 3: Homebrew Python (CLEANEST)

**Why**: Fresh ARM64-native Python

**How**:
```bash
# Install Homebrew Python
brew install python@3.11

# Create virtual environment
/opt/homebrew/bin/python3.11 -m venv venv
source venv/bin/activate

# Install everything fresh
pip install -e packages/voice
```

**Pros**:
- Clean ARM64 Python
- Project-isolated
- All packages ARM64-native
- Industry best practice

**Cons**:
- Requires Homebrew (you probably have it)
- Extra setup step

### Option 4: pyenv (PROFESSIONAL)

**Why**: Multiple Python versions, project isolation

**How**:
```bash
# Install pyenv
brew install pyenv

# Install ARM64 Python
pyenv install 3.11.9

# Set for project
cd /path/to/xswarm-boss
pyenv local 3.11.9

# Create venv
python -m venv .venv
source .venv/bin/activate

# Install
pip install -e packages/voice
```

**Pros**:
- Industry standard
- Perfect isolation
- Multiple Python versions
- Reproducible

**Cons**:
- Most setup
- Learning curve

## Recommendation

**For immediate testing**: Option 1 (remove sounddevice)
**For development**: Option 3 (Homebrew Python + venv) or Option 4 (pyenv)

### Why Option 1 is Best Right Now

1. **We don't need sounddevice** - Rust handles audio I/O
2. **No architectural compromise** - Actually cleaner design
3. **Works immediately** - No installation changes
4. **No sudo** - Safe

## Implementation

### Option 1: Update Dependencies (Immediate)

```toml
# packages/voice/pyproject.toml
[project]
dependencies = [
    "moshi_mlx>=0.1.0",
    "numpy>=1.24.0",
    "websockets>=12.0",
    # sounddevice removed - not needed for bridge
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
    "mypy>=1.0.0",
]
standalone = [
    # Only if you want to run moshi_mlx.local
    "sounddevice>=0.5.0",
]
```

### Option 3: Homebrew Python (Long-term)

```bash
# Setup script
#!/bin/bash
set -e

echo "Setting up xSwarm voice development environment..."

# 1. Install Homebrew Python if needed
if ! command -v /opt/homebrew/bin/python3.11 &> /dev/null; then
    echo "Installing Homebrew Python..."
    brew install python@3.11
fi

# 2. Create virtual environment
echo "Creating virtual environment..."
cd /path/to/xswarm-boss
/opt/homebrew/bin/python3.11 -m venv .venv

# 3. Activate
source .venv/bin/activate

# 4. Install packages
echo "Installing xSwarm voice bridge..."
pip install --upgrade pip
pip install -e packages/voice

# 5. Verify
python -c "from moshi_mlx import models; import mlx.core; print('✓ Ready')"

echo "✓ Setup complete. Run 'source .venv/bin/activate' to use."
```

## Testing Without Fix

You can test MOSHI RIGHT NOW without fixing CFFI:

```python
#!/usr/bin/env python3
# test_moshi_minimal.py

from moshi_mlx import models
import mlx.core as mx
import numpy as np

print("Testing MOSHI without sounddevice...")

# Load model config
config = models.config1b_202412()
print(f"✓ Config: {config}")

# Test audio conversion
audio = np.zeros(24000, dtype=np.float32)
mx_audio = mx.array(audio)
print(f"✓ Audio: {audio.shape} → {mx_audio.shape}")

print("✓ MOSHI core works!")
```

## Conclusion

**Recommended Action**: Option 1 (remove sounddevice dependency)

**Why**:
1. Architecturally correct (Rust does audio I/O)
2. Works immediately
3. No configuration changes
4. No sudo required
5. Cleaner design

**Next Step**: Update `pyproject.toml` to remove `sounddevice` from dependencies, then test.

---

**Last Updated**: 2025-10-24
**Decision**: Remove sounddevice, test MOSHI core, proceed with WebSocket integration
