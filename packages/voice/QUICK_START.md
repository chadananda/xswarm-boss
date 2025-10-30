# xSwarm Voice - Quick Start Guide

## Interactive Testing (Fast Iteration)

### 1. Test Audio I/O (Working Now)
```bash
.venv/bin/python packages/voice/test_voice_interactive.py
```
**Status**: ✓ Ready (audio loopback test)
- Records 3s audio from microphone
- Shows audio stats (RMS, peak)
- Plays back audio
- Perfect for testing audio setup

### 2. MOSHI Inference Architecture (Discovered)

**From `moshi_mlx/run_inference.py` analysis:**

```python
# Components needed:
1. models.Lm(config)                    # Language Model
2. models.LmGen(model, samplers)        # Generator
3. rustymimi.Tokenizer(weights)         # Audio codec (Mimi)
4. sentencepiece.SentencePieceProcessor # Text tokenizer

# Processing loop (per 80ms chunk):
pcm_audio[1920 samples]
   ↓ rustymimi.encode_step()
audio_tokens
   ↓ model.step()
text_token + output_audio_tokens
   ↓ rustymimi.decode_step()
pcm_output[1920 samples]
```

**Key discoveries:**
- Audio processed in 1920-sample chunks (80ms at 24kHz)
- Streaming capable (step-by-step processing)
- Uses `rustymimi` for ultra-fast audio codec
- Full-duplex: input audio + output audio simultaneously

### 3. Files Created

```
packages/voice/
├── src/xswarm_voice/
│   ├── audio.py               ✓ Twilio conversion (tested)
│   ├── bridge.py              ⏸ Need to complete model loading
│   └── server.py              ⏸ WebSocket server
├── test_core.py               ✓ MOSHI imports (tested)
├── test_audio_resampling.py   ✓ Audio conversion (tested)
├── test_voice_interactive.py  ✓ Audio I/O test (ready)
└── QUICK_START.md             ← You are here
```

### 4. Next Implementation Steps

**Priority 1: Complete MOSHI model loading in bridge.py**

```python
# packages/voice/src/xswarm_voice/bridge.py

class VoiceBridge:
    async def initialize(self):
        # Download from Hugging Face
        from huggingface_hub import hf_hub_download

        hf_repo = "kyutai/moshika-mlx-q4"

        # 1. Load config
        config_path = hf_hub_download(hf_repo, "config.json")
        with open(config_path) as f:
            lm_config = json.load(f)

        # 2. Load model weights
        moshi_weights = hf_hub_download(hf_repo, "model.q4.safetensors")
        model = models.Lm(models.LmConfig.from_config_dict(lm_config))
        model.set_dtype(mx.bfloat16)
        nn.quantize(model, bits=4, group_size=32)
        model.load_weights(moshi_weights, strict=True)

        # 3. Load audio codec
        mimi_weights = hf_hub_download(hf_repo, lm_config["mimi_name"])
        audio_tokenizer = rustymimi.Tokenizer(mimi_weights, num_codebooks=16)

        # 4. Load text tokenizer
        tokenizer_path = hf_hub_download(hf_repo, lm_config["tokenizer_name"])
        text_tokenizer = sentencepiece.SentencePieceProcessor(tokenizer_path)

        # 5. Create generator
        self.gen = models.LmGen(
            model=model,
            max_steps=10000,  # Max conversation length
            text_sampler=utils.Sampler(top_k=25, temp=0.8),
            audio_sampler=utils.Sampler(top_k=250, temp=0.8),
        )

        self.audio_tokenizer = audio_tokenizer
        self.text_tokenizer = text_tokenizer

    async def process_audio_chunk(self, pcm_audio: np.ndarray) -> np.ndarray:
        """Process one 80ms chunk (1920 samples at 24kHz)"""
        # Encode input audio
        audio_tokens = self.audio_tokenizer.encode_step(pcm_audio[None, 0:1])
        audio_tokens = mx.array(audio_tokens).transpose(0, 2, 1)[:, :, :8]

        # Generate response
        text_token = self.gen.step(audio_tokens[0])
        output_tokens = self.gen.last_audio_tokens()

        # Decode output audio
        if output_tokens is not None:
            output_tokens = np.array(output_tokens[:, :, None]).astype(np.uint32)
            pcm_output = self.audio_tokenizer.decode_step(output_tokens)
            return pcm_output

        return np.zeros(1920, dtype=np.float32)
```

**Priority 2: Update interactive test to use MOSHI**

Replace echo with actual model inference.

**Priority 3: Add personality prompts**

Use condition tensor for persona:
```python
ct = model.condition_provider.condition_tensor("description", persona_text)
gen.step(audio_tokens, ct)
```

### 5. Testing Checklist

- [x] Audio resampling (Twilio 8kHz ↔ MOSHI 24kHz)
- [x] MOSHI imports and config
- [x] Audio I/O (microphone + speakers)
- [ ] Model loading from Hugging Face
- [ ] Streaming inference (80ms chunks)
- [ ] Text output (transcription)
- [ ] Personality conditioning
- [ ] WebSocket server
- [ ] Rust client integration

### 6. Run Current Tests

```bash
# Test 1: Audio conversion (Twilio compatibility)
.venv/bin/python packages/voice/test_audio_resampling.py
# Expected: ✓ ALL TESTS PASSED

# Test 2: MOSHI core (imports, config)
.venv/bin/python packages/voice/test_core.py
# Expected: ✓ ALL TESTS PASSED

# Test 3: Interactive audio I/O
.venv/bin/python packages/voice/test_voice_interactive.py
# Expected: Records and plays back audio
# Press Ctrl+C to stop
```

### 7. Model Downloads

**First run will download ~4GB:**
- Model weights: `model.q4.safetensors` (~3.5GB, quantized)
- Mimi codec: `mimi.safetensors` (~100MB)
- Text tokenizer: `text_tokenizer.model` (~500KB)
- Config: `config.json` (<1KB)

**Location**: `~/.cache/huggingface/hub/`

### 8. Mac-Specific: Menu Bar Interface (Future)

**For rapid iteration, start without menu bar:**
1. Run in terminal (foreground)
2. Test voice interaction
3. Iterate on personality
4. Add menu bar once stable

**Menu bar options:**
- Option A: Swift (most native, smoothest)
- Option B: Tauri (Rust + web UI)
- Option C: tray-icon crate (lightweight)

**Recommendation**: Defer menu bar until voice works.

### 9. Performance Expectations

**Mac M4 (your setup):**
- Model loading: ~10-30s (first run only)
- Inference: <160ms per 80ms chunk (2x realtime)
- Total latency: ~200ms (excellent for conversation)

**Memory:**
- Model: ~2GB RAM
- MLX Metal: ~1GB VRAM
- Python overhead: ~200MB
- **Total: ~3.5GB**

### 10. Quick Commands

```bash
# Install/update dependencies
.venv/bin/pip install -e packages/voice

# Run all tests
.venv/bin/python packages/voice/test_core.py && \
.venv/bin/python packages/voice/test_audio_resampling.py

# Interactive testing
.venv/bin/python packages/voice/test_voice_interactive.py

# Build Rust CLI (when ready)
cargo build --release
./target/release/xswarm config show
```

---

**Current Status**: Audio I/O working, MOSHI API understood, ready to implement model loading.

**Time estimate to working voice**: 2-4 hours of implementation + testing.
