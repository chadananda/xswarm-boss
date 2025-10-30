# xSwarm Voice Bridge

Python bridge for MOSHI voice model integration with xSwarm Rust core.

## Overview

This package provides a WebSocket server that interfaces between:
- **MOSHI MLX** (Apple Silicon optimized voice model)
- **xSwarm Rust core** (orchestrator and TUI)

## Architecture

```
┌─────────────────┐   WebSocket    ┌──────────────────┐
│  xSwarm Rust    │◄──────────────►│  Voice Bridge    │
│  (main binary)  │   Audio I/O    │  (Python/MLX)    │
└─────────────────┘                └──────────────────┘
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │  MOSHI MLX   │
                                    │  (Voice AI)  │
                                    └──────────────┘
```

## MOSHI Specifications

- **Model**: Kyutai MOSHI (7B parameter speech-text foundation model)
- **Codec**: Mimi (24kHz audio → 12.5Hz neural codec)
- **Latency**: 160ms theoretical, 200ms practical
- **Features**: Full-duplex, voice cloning, inner monologue
- **Quantization**: 4-bit (moshika-mlx-q4) for optimal performance/memory

## Installation

```bash
# Install the package
cd packages/voice
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

## Usage

### Standalone Mode
```bash
python -m xswarm_voice.server --host localhost --port 8765
```

### Integration with xSwarm
The voice bridge is automatically launched by the xSwarm Rust binary when voice is enabled.

## Configuration

Voice settings are managed through xSwarm's config.toml:

```toml
[voice]
default_persona = "hal-9000"
sample_rate = 24000  # MOSHI requirement
include_personality = true
```

## Development

```bash
# Run tests
pytest tests/

# Format code
black src/

# Type checking
mypy src/
```

## Requirements

- Python 3.10+
- macOS with Apple Silicon (M1/M2/M3/M4)
- MLX framework (auto-installed with moshi_mlx)
- ~4GB RAM for model (q4 quantization)

## License

MIT (same as xSwarm)
