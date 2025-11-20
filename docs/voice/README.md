# Voice Architecture

MOSHI speech-to-speech model bridge for Apple Silicon and cloud deployment.

## Overview

Python WebSocket server bridging the assistant TUI to MOSHI MLX:
- Kyutai MOSHI 7B (speech-to-speech, NOT TTS)
- Apple Silicon optimized (MLX framework)
- 4-bit quantization for efficiency
- ~200ms latency end-to-end
- Memory and intelligence injection
- Cross-platform and cloud support

## Critical Concept

**MOSHI is NOT traditional TTS/STT**

```
Traditional: Speech → STT → Text → LLM → Text → TTS → Speech
MOSHI:       Speech → Audio Tokens → LM Step → Audio Tokens → Speech
```

MOSHI generates audio tokens directly from audio tokens. It understands speech semantically without intermediate text.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MOSHI Voice Server                    │
├───────────────┬───────────────┬─────────────────────────┤
│  Mimi Codec   │   MOSHI LM    │     WebSocket           │
│  (Encoder)    │   (7B MLX)    │     Server              │
├───────────────┼───────────────┼─────────────────────────┤
│ • 24kHz audio │ • Text tokens │ • Binary frames         │
│ • 8 codebooks │ • Audio gen   │ • Bidirectional         │
│ • 12.5Hz rate │ • q4 weights  │ • Low latency           │
└───────────────┴───────────────┴─────────────────────────┘
```

## Pipeline Flow

### Input Processing

```
1. Audio from assistant (24kHz PCM, ~80ms chunks)
2. → Mimi encoder → 8 codebooks × 12.5Hz
3. → MOSHI LM step (generates text + audio tokens)
4. → Mimi decoder → 24kHz PCM
5. → WebSocket → assistant → speakers
```

### Full-Duplex Streaming

```python
def step_frame(lm_gen, audio_chunk):
    codes = mimi_encoder.encode(audio_chunk)
    text_token, audio_codes = lm_gen.step(codes)
    audio_out = mimi_decoder.decode(audio_codes)
    return audio_out, text_token
```

## Memory Injection

AI-filtered semantic memory injection into MOSHI context.

### Protocol

```
User speaks → Transcribe → Embed query
                              ↓
                    Retrieve top-k memories (15)
                              ↓
                    Thinking engine filters
                              ↓
                    1-3 approved memories
                              ↓
                    Inject via Condition::AddToInput
                              ↓
                    MOSHI generates contextual response
```

### Injection Mechanism

MOSHI accepts context via `Condition::AddToInput`:

```python
# Inner monologue injection
context = "Remember: User prefers concise answers. Last meeting was Tuesday."
condition = Condition.AddToInput(context)
lm_gen.apply_condition(condition)
```

### Filtering Logic

Thinking engine scores each memory candidate:
- Relevance to current conversation (0-1)
- Importance for response (0-1)
- Only memories above threshold (0.7) are injected

See `moshi-interface.md` for detailed injection API.

## Intelligence Injection

Hardware-aware model selection from the intelligence layer.

### GPU Detection

```python
from hardware import detect_gpu_level

level = detect_gpu_level()  # Returns 0-6
# Level 0: <8GB VRAM → API only
# Level 1: 12-16GB → Qwen2.5-7B
# Level 2: 20-24GB → Qwen2.5-14B
# Level 3: 28-32GB → Qwen3-30B
# Level 4: 40-48GB → Qwen2.5-72B IQ4
# Level 5: 60-80GB → Qwen2.5-72B Q6
# Level 6: Hybrid → Local + API fallback
```

### Model Selection

Voice server queries intelligence layer for:
- Available local models
- API fallback configuration
- Context window limits
- Token budgets

### Integration

```python
# Voice server startup
gpu_level = detect_gpu_level()
if gpu_level == 0:
    # Use cloud MOSHI endpoint
    endpoint = config.cloud_moshi_url
else:
    # Use local MLX MOSHI
    load_local_model()
```

See `docs/assistant/intelligence-layer.md` for 7-level hierarchy.

## Platform Compatibility

Support for all platforms, not just Apple Silicon.

### Local Deployment (Apple Silicon)

- M1/M2/M3/M4 Macs
- MLX framework (native Metal)
- 7-10GB GPU memory required
- ~200ms latency

### Local Deployment (NVIDIA)

- Linux/Windows with CUDA
- PyTorch backend
- Requires CUDA 11.8+
- 8GB+ VRAM

```python
# CUDA configuration
[voice.moshi]
device = "cuda"
model = "kyutai/moshika-pytorch-q4"
```

### Local Deployment (CPU)

- Any platform
- Significantly slower (~2-5s latency)
- Fallback for testing

```python
[voice.moshi]
device = "cpu"
```

### Cloud Deployment

For users without capable hardware:

```
User Device → WebSocket → Cloud MOSHI Server → Response
```

**Cloud Architecture**:
- AWS/GCP with GPU instances
- Auto-scaling based on demand
- Geographic distribution for latency
- User authentication via JWT

**Configuration**:
```python
[voice]
provider = "moshi-cloud"
endpoint = "wss://moshi.xswarm.ai/v1/stream"
```

See `cloud-deployment.md` for infrastructure setup.

## Remote Access

WebSocket protocol for remote voice server access.

### Protocol

```
wss://voice.xswarm.ai/v1/stream
Authorization: Bearer <jwt>
```

### Binary Frames

```
Client → Server: 24kHz PCM int16 (1920 samples = 80ms)
Server → Client: 24kHz PCM int16 (variable length)
```

### Text Frames

```json
{"type": "status", "state": "listening"}
{"type": "transcript", "text": "How are you?"}
{"type": "memory", "injected": ["User prefers concise"]}
{"type": "error", "message": "Model failed to load"}
```

### Latency Optimization

- Edge servers in major regions
- Connection keep-alive
- Audio buffering strategies
- Predictive model warming

## Phone Integration (Twilio)

### Architecture

```
Phone → Twilio → WebSocket (Media Streams) → MediaStreamsServer
                                                    ↓
                                        TwilioVoiceBridge
                                                    ↓
                                        Audio Converter (mulaw ↔ PCM)
                                                    ↓
                                        MoshiBridge (MLX)
```

### Audio Format Conversion

- **Twilio**: mulaw 8kHz (base64)
- **MOSHI**: PCM 24kHz float32

Conversion: `mulaw_to_pcm24k()` and `pcm24k_to_mulaw()`

### Call Flow

1. Incoming call establishes WebSocket
2. mulaw chunks → PCM 24kHz → 80ms frames
3. MOSHI generates response
4. PCM → mulaw → Twilio → phone

## Model Details

### MOSHI 7B

- **Parameters**: 7 billion
- **Quantization**: 4-bit (q4)
- **Memory**: 7-10GB GPU RAM
- **Model ID**: `kyutai/moshika-mlx-q4`

### Mimi Codec

- **Input**: 24kHz PCM audio
- **Output**: 8 codebooks × 12.5Hz tokens
- **Compression**: 1920 samples → 150 tokens
- **Latency**: ~80ms per frame

## Configuration

```toml
[voice]
provider = "moshi"
sample_rate = 24000
model = "kyutai/moshika-mlx-q4"
max_steps = 1000

[voice.moshi]
device = "mlx"  # mlx, cuda, cpu, cloud
```

## Installation

### Prerequisites

- Apple Silicon Mac (M1/M2/M3) OR NVIDIA GPU OR cloud access
- Python 3.10+
- ~15GB disk for model

### Setup

```bash
cd packages/voice
pip install -e .

# Download model (14GB)
export HF_XET_HIGH_PERFORMANCE=1
python -c "from huggingface_hub import hf_hub_download; hf_hub_download('kyutai/moshika-mlx-q4', 'model.safetensors')"
```

## Critical Implementation Details

### Thread Safety (Segfault Fix)

MLX GPU operations are not thread-safe. Queue in callbacks, process on main thread.

```python
# CORRECT: Queue and process
def audio_callback(indata, outdata, frames, time, status):
    input_queue.put(indata)  # Just queue

async def processing_loop():
    while True:
        chunk = await input_queue.get()
        result = step_frame(lm_gen, chunk)  # MLX on main thread
```

### Model Download

Use `hf-transfer` with chunk verification:

```python
import os
os.environ["HF_XET_HIGH_PERFORMANCE"] = "1"

from huggingface_hub import hf_hub_download
model_file = hf_hub_download(
    "kyutai/moshika-mlx-q4",
    "model.safetensors",
    resume_download=True
)
```

### Three Voice Mechanisms

1. **Greetings** - Force specific text tokens for scripted phrases
2. **Memory Context** - Inject semantic search via `Condition::AddToInput`
3. **STT Background** - Async transcription for memory storage only

## Performance

- Model load: 6-8 seconds
- Inference latency: ~200ms
- GPU memory: 7-10GB
- CPU during load: ~67%

## Debug Logging

```bash
tail -f /tmp/moshi_timing.log     # Model load timing
tail -f /tmp/moshi_text.log       # Transcriptions
```

## Known Issues

### First Inference Slow

Model loading takes 6-8 seconds. Pre-warm on startup.

### Sample Rate Mismatch

MOSHI requires exactly 24kHz. No resampling supported.

### GPU Memory

4-bit model uses 7-10GB. Monitor with:
```bash
sudo powermetrics --samplers gpu_power
```

## Dependencies

- **mlx** - Apple ML framework
- **torch** - CUDA support
- **huggingface_hub** - Model download
- **hf-transfer** - Fast downloads
- **websockets** - Server
- **numpy** - Audio arrays
- **scipy** - Resampling

## Detailed Documentation

- `moshi-implementation-lessons.md` - Model download strategies, debugging
- `moshi-interface.md` - Memory injection API, LibSQL schema
- `cloud-deployment.md` - AWS/GCP infrastructure, scaling
- `platform-compatibility.md` - CUDA, CPU, remote access setup

## Testing

```bash
cd tests
pytest voice/
```

Manual testing:
```bash
cd packages/voice
python voice_server.py  # Start server
# Connect from assistant TUI
```
