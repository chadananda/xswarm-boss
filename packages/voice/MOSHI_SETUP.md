# MOSHI Voice Model - ARM64 Setup Guide

## Overview

MOSHI requires native ARM64 Python on Apple Silicon Macs because it uses the **MLX framework**, which is optimized for Apple's M1/M2/M3 chips and only compiles for ARM64 architecture.

## Architecture Requirements

- **Python**: 3.10 or later, ARM64 architecture
- **MLX Framework**: Apple Silicon only (no x86_64/Rosetta support)
- **Operating System**: macOS 11.0+ on Apple Silicon

## Problem: Mixed Architecture Environments

Many Mac setups have mixed x86_64 and ARM64 binaries:

```bash
# Check your architecture
uname -m                    # Should show: arm64
arch                        # Should show: arm64

# Check Python architecture
file $(which python3)       # Should include: arm64 or Mach-O universal
python3 --version          # Should be 3.10 or later

# Check if Python runs natively
arch -arm64 python3 -c "import platform; print(platform.machine())"
# Should output: arm64
```

### Common Issues

1. **Homebrew at `/usr/local`**: Runs in x86_64 mode (Rosetta)
   - Python from this Homebrew will be x86_64 only
   - Location: `/usr/local/Cellar/python@*`

2. **System Python 3.9**: Too old for MOSHI
   - macOS includes Python 3.9 at `/usr/bin/python3`
   - MOSHI requires Python 3.10+

3. **ARM64 Homebrew at `/opt/homebrew`**: Ideal but requires setup
   - Native ARM64 packages
   - Modern Python versions (3.11, 3.12)

## Setup Options

### Option 1: Automated Setup Script (Recommended)

Run the provided setup script with administrator privileges:

```bash
# From project root
sudo bash scripts/setup-moshi-python.sh
```

This script will:
1. Check current Python installations
2. Install ARM64 Homebrew at `/opt/homebrew` if needed
3. Install Python 3.11 or 3.12 (ARM64)
4. Create virtual environment at `packages/voice/.venv`
5. Install xswarm-voice package with dependencies
6. Verify MLX framework installation

### Option 2: Manual Setup with python.org

1. **Download Python 3.11 or 3.12** from https://www.python.org/downloads/
   - Get the "macOS 64-bit universal2 installer"
   - This includes both x86_64 and ARM64 binaries

2. **Install Python**:
   ```bash
   # Download and run the installer
   # It will install to /Library/Frameworks/Python.framework/
   ```

3. **Create ARM64 virtual environment**:
   ```bash
   cd packages/voice

   # Use the newly installed Python
   arch -arm64 /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m venv .venv

   # Activate
   source .venv/bin/activate

   # Verify ARM64
   python -c "import platform; print(f'Python {platform.python_version()} on {platform.machine()}')"
   # Should show: Python 3.11.x on arm64
   ```

4. **Install xswarm-voice**:
   ```bash
   pip install -e .
   ```

### Option 3: Manual Setup with ARM64 Homebrew

1. **Install ARM64 Homebrew** (if not already installed):
   ```bash
   sudo mkdir -p /opt/homebrew
   sudo chown -R $(whoami) /opt/homebrew

   # Install Homebrew at /opt/homebrew
   arch -arm64 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

   # Add to shell profile
   echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
   eval "$(/opt/homebrew/bin/brew shellenv)"
   ```

2. **Install Python 3.11**:
   ```bash
   /opt/homebrew/bin/brew install python@3.11
   ```

3. **Create virtual environment**:
   ```bash
   cd packages/voice

   # Create ARM64 venv
   arch -arm64 /opt/homebrew/bin/python3.11 -m venv .venv

   # Activate
   source .venv/bin/activate

   # Verify ARM64
   python -c "import platform; print(f'Python {platform.python_version()} on {platform.machine()}')"
   ```

4. **Install xswarm-voice**:
   ```bash
   pip install -e .
   ```

## Verification

After installation, verify everything is working:

```bash
cd packages/voice
source .venv/bin/activate

# 1. Check Python architecture
python -c "import platform; print(f'✓ Python {platform.python_version()} on {platform.machine()}')"
# Expected: Python 3.1x.x on arm64

# 2. Check MLX installation
python -c "import mlx.core as mx; print(f'✓ MLX version: {mx.__version__}')"
# Expected: ✓ MLX version: 0.x.x

# 3. Check rustymimi codec
python -c "import rustymimi; print('✓ rustymimi installed')"
# Expected: ✓ rustymimi installed

# 4. Check moshi_mlx
python -c "from moshi_mlx import models; print('✓ moshi_mlx installed')"
# Expected: ✓ moshi_mlx installed

# 5. Run MOSHI test
python test_moshi.py
# Expected: Model loads successfully (~4GB download on first run)
```

## Testing MOSHI

Once setup is complete, test the voice bridge:

```bash
cd packages/voice
source .venv/bin/activate

# Test MOSHI model loading
python test_moshi.py

# Expected output:
# Loading MOSHI model: kyutai/moshika-mlx-q4
# Persona: boss
# Platform: macOS ARM=True, Linux=False, Windows=False
# Using MLX backend (Apple Silicon)
# Downloading model from Hugging Face...
# ✓ Config loaded from kyutai/moshika-mlx-q4
# Downloading model weights (~3.5GB)...
# ✓ MOSHI model loaded
# ✓ Mimi codec loaded
# ✓ Text tokenizer loaded
# ✓ Persona conditioning applied: boss
# ✓ MOSHI ready for inference!
```

## Troubleshooting

### Error: "ImportError: dlopen(...): mach-o file, but is an incompatible architecture"

**Cause**: Package was installed for wrong architecture (x86_64 instead of ARM64)

**Fix**:
```bash
# Recreate venv with ARM64 Python
rm -rf .venv
arch -arm64 /path/to/python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Error: "No module named 'mlx'"

**Cause**: MLX requires ARM64 Python and won't install on x86_64

**Fix**: Verify Python architecture and recreate venv with ARM64 Python (see above)

### Error: "RuntimeError: Failed to load MOSHI model"

**Cause**: Network issues during model download from Hugging Face

**Fix**:
```bash
# Models are cached in ~/.cache/huggingface/hub/
# Delete cache and retry
rm -rf ~/.cache/huggingface/hub/models--kyutai--moshika-mlx-q4
python test_moshi.py
```

### Check Current Python Architecture

```bash
# Method 1: file command
file $(which python3)

# Method 2: platform module
python3 -c "import platform; print(platform.machine())"

# Method 3: arch command
arch -arm64 python3 -c "print('ARM64 works!')"
arch -x86_64 python3 -c "print('x86_64 works!')"
```

## Next Steps After Setup

Once MOSHI is working locally:

1. **Implement Twilio Media Streams WebSocket server**
   - Real-time audio streaming between Twilio and MOSHI
   - Audio format conversion (μ-law ↔ 24kHz PCM)

2. **Test phone call with MOSHI voice**
   - Boss can call you using MOSHI instead of Polly TTS
   - Bidirectional conversation support

3. **Integrate voice feedback loop**
   - Capture verbal feedback during call
   - Convert to text and implement as typed directions

## Resources

- **MLX Framework**: https://github.com/ml-explore/mlx
- **MOSHI Model**: https://github.com/kyutai-labs/moshi
- **moshi_mlx**: https://github.com/lucasnewman/moshi-mlx
- **Twilio Media Streams**: https://www.twilio.com/docs/voice/twiml/stream
