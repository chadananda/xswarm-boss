# xSwarm Cross-Platform Build Status

**Date**: 2025-10-24
**Current Status**: Foundation Complete, Platform-Specific Implementation Needed

## Platform Support Matrix

| Platform | Architecture | MOSHI Status | Backend | Notes |
|----------|-------------|--------------|---------|-------|
| **macOS** | Apple Silicon (M1/M2/M3/M4) | ✅ Ready | MLX | Fully supported, tested on M4 |
| **macOS** | Intel (x86_64) | ⚠️ Limited | PyTorch | Not primary target |
| **Linux** | x86_64 + NVIDIA GPU | 🚧 Planned | PyTorch | Coming soon |
| **Linux** | AMD64 (CPU only) | 🚧 Planned | PyTorch | Lower priority |
| **Windows** | x86_64 + NVIDIA GPU | 🚧 Planned | PyTorch | Coming soon |
| **Windows** | AMD64 (CPU only) | 🚧 Planned | PyTorch | Lower priority |

## Current Implementation

### ✅ macOS (Apple Silicon) - MLX Backend

**Status**: Fully implemented and tested
**Model**: `kyutai/moshika-mlx-q4` (4-bit quantized)
**Requirements**:
- macOS 14+ (Sonoma or later)
- Apple Silicon (M1 or newer)
- Python 3.10+
- ~8GB RAM

**Installation**:
```bash
cd packages/voice
python3 -m pip install -e .
```

**Performance**:
- Latency: ~200ms (meeting target)
- Memory: ~4GB for model
- Neural Engine: Automatic acceleration

**Known Issues**:
- ⚠️ CFFI architecture mismatch if Python installed via Rosetta
- Solution: Reinstall Python native ARM64 or use Homebrew Python

### 🚧 Linux/Windows - PyTorch Backend

**Status**: Not yet implemented
**Planned Model**: `kyutai/moshika-pytorch-bf16` or `kyutai/moshika-pytorch-int8`

**Requirements** (when implemented):
- Python 3.10+
- PyTorch 2.0+
- CUDA 11.8+ (for GPU)
- ~16GB RAM (bf16) or ~8GB (int8)

**Installation** (planned):
```bash
# Install PyTorch backend
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install MOSHI PyTorch
pip install moshi  # PyTorch version

# Install xSwarm voice bridge
cd packages/voice
pip install -e .
```

## Architecture Decision

### Why MLX for macOS?

1. **Native Apple Silicon Support**: Optimized for M-series chips
2. **Unified Memory**: Efficient memory usage on macOS
3. **Neural Engine**: Automatic hardware acceleration
4. **Lower Latency**: ~200ms vs ~300ms+ with PyTorch
5. **Smaller Models**: 4GB (q4) vs 16GB (bf16)

### Why PyTorch for Linux/Windows?

1. **Cross-Platform**: Works on any GPU (NVIDIA, AMD via ROCm)
2. **Mature Ecosystem**: Better tooling and support
3. **CUDA Support**: Native NVIDIA GPU acceleration
4. **Wider Compatibility**: CPU-only fallback available

## Implementation Plan

### Phase 1: macOS MLX (Current) ✅

- [x] Python voice bridge structure
- [x] Platform detection
- [x] MLX-specific model loading
- [ ] Fix CFFI architecture issue
- [ ] Complete model inference integration
- [ ] Audio I/O implementation

### Phase 2: Linux/Windows PyTorch Support 🚧

**Priority Order**:
1. Linux x86_64 + NVIDIA GPU (servers, workstations)
2. Windows x86_64 + NVIDIA GPU (gaming PCs)
3. CPU-only fallback (both platforms)

**Implementation Tasks**:
- [ ] Add PyTorch backend to voice bridge
- [ ] Model loading for PyTorch variant
- [ ] CUDA device detection and setup
- [ ] Cross-platform audio I/O (Windows: WASAPI, Linux: ALSA/PulseAudio)
- [ ] Fallback to CPU inference
- [ ] Performance optimization

### Phase 3: Alternative Backends

**Rust/Candle** (Experimental):
- Fully cross-platform
- Single binary distribution
- Models: `kyutai/moshika-candle-q8`
- Pros: No Python dependency, smaller binaries
- Cons: Less mature, harder to integrate initially

## Build Configuration

### Current Structure

```
packages/voice/
├── pyproject.toml          # Python package config
├── src/xswarm_voice/
│   ├── bridge.py           # Platform-specific model loading
│   ├── server.py           # WebSocket server (cross-platform)
│   └── backends/           # (TODO) Backend implementations
│       ├── mlx.py          # macOS Apple Silicon
│       ├── pytorch.py      # Linux/Windows
│       └── candle.py       # (Future) Rust backend
└── test_moshi.py           # Platform detection test
```

### Proposed Backend Interface

```python
class VoiceBackend(ABC):
    @abstractmethod
    async def initialize(self, model_repo: str):
        """Load model"""
        pass

    @abstractmethod
    async def process_audio(self, audio: np.ndarray) -> np.ndarray:
        """Inference"""
        pass

    @abstractmethod
    def cleanup(self):
        """Release resources"""
        pass
```

## Testing Strategy

### Per-Platform Tests

**macOS**:
- [x] Model loading (MLX)
- [ ] Audio inference
- [ ] WebSocket streaming
- [ ] Latency benchmark

**Linux** (when implemented):
- [ ] CUDA detection
- [ ] GPU inference
- [ ] CPU fallback
- [ ] Audio I/O

**Windows** (when implemented):
- [ ] CUDA detection
- [ ] Audio I/O (WASAPI)
- [ ] Performance parity

### CI/CD

**Planned GitHub Actions**:
- macOS ARM: Native tests on M-series runners
- Linux: CUDA tests (if GPU runners available)
- Windows: CPU-only tests
- Cross-platform: Integration tests

## Distribution

### macOS

**Option 1: Python Package** (current)
```bash
pip install xswarm-voice
```

**Option 2: Standalone App** (future)
- Bundle Python + MLX + Models
- dmg installer
- ~5GB download

### Linux/Windows

**Option 1: Python Package**
```bash
pip install xswarm-voice[pytorch]
```

**Option 2: Docker**
```bash
docker run -it --gpus all xswarm/voice:latest
```

**Option 3: Native Binary** (with Rust/Candle)
```bash
# Single executable, no Python needed
./xswarm-voice
```

## Known Limitations

### Current

1. **macOS Only**: MLX backend limits to Apple Silicon
2. **CFFI Issue**: Architecture mismatch in current Python installation
3. **No Audio I/O**: WebSocket protocol defined but audio capture not implemented
4. **Model Stubs**: Inference code is placeholder, needs real implementation

### Architectural

1. **Model Size**: 4-16GB models require good internet for download
2. **Memory Requirements**: 8-16GB RAM minimum
3. **GPU Dependency**: Best performance requires discrete GPU on Linux/Windows
4. **Latency Target**: 200ms difficult on CPU-only systems

## Next Steps

### Immediate (macOS)

1. **Fix Python Architecture**:
   ```bash
   # Reinstall Python for ARM64
   brew install python@3.11
   # Or use pyenv
   pyenv install 3.11.x
   ```

2. **Complete MLX Integration**:
   - Study `moshi_mlx/local.py` implementation
   - Implement proper model loading
   - Add streaming inference

3. **Test on Mac**:
   - Run `test_moshi.py`
   - Verify model downloads
   - Test audio processing

### Short-term (Cross-Platform)

1. **Add PyTorch Backend**:
   - Create `backends/pytorch.py`
   - Test on Linux VM with NVIDIA GPU
   - Document installation steps

2. **Implement Audio I/O**:
   - macOS: `sounddevice` with CoreAudio
   - Linux: `sounddevice` with PulseAudio/ALSA
   - Windows: `sounddevice` with WASAPI

3. **Cross-Platform Testing**:
   - Set up VMs for Linux/Windows
   - Test GPU and CPU paths
   - Benchmark performance

## Resources

- **MOSHI GitHub**: https://github.com/kyutai-labs/moshi
- **MLX**: https://ml-explore.github.io/mlx/
- **PyTorch**: https://pytorch.org/
- **Candle (Rust)**: https://github.com/huggingface/candle
- **Hugging Face Models**: https://huggingface.co/kyutai

---

**Last Updated**: 2025-10-24
**Status**: macOS foundation complete, cross-platform expansion planned
