# Phase 3: Speech-to-Text (STT) Implementation

## Overview

Implementing real-time speech-to-text transcription using Whisper for voice input processing.

## Progress

### ✅ Phase 3.1: Create STT Module (COMPLETE)

**Completed**: packages/core/src/stt.rs (350 lines)
**Commit**: ee8a340

**Implemented**:
- ✅ `SttEngine` struct with configuration
- ✅ `SttConfig` with model selection and language support
- ✅ Background `TranscriptionWorker` with async queue
- ✅ `AudioChunk` and `TranscriptionResult` types
- ✅ Audio format conversion (μ-law → PCM → 16kHz)
- ✅ `AudioResampler` integration (8kHz → 16kHz upsampling)
- ✅ Background worker architecture with channels
- ✅ `mulaw_to_pcm()` conversion helper
- ✅ Public API: `new()`, `submit_audio()`, `get_transcription()`

**Features**:
- Configurable Whisper model size ("tiny", "base", "small", "medium", "large")
- Language detection support
- Background transcription queue
- Minimum audio duration filtering (500ms default)
- Async/await compatible

---

### 🔄 Phase 3.2: Add Background STT Transcription with Whisper (IN PROGRESS)

**Status**: Implementation required

**Remaining Tasks**:

#### 1. Fix AudioResampler Ownership

**Issue**: `AudioResampler` requires mutable reference, but `SttEngine` is used across threads.

**Solution**:
```rust
pub struct SttEngine {
    config: SttConfig,
    upsampler: Arc<Mutex<AudioResampler>>,  // Changed from AudioResampler
    worker: Option<TranscriptionWorker>,
}
```

**Changes Required**:
- packages/core/src/stt.rs:61 - Wrap upsampler in Arc<Mutex<>>
- packages/core/src/stt.rs:136 - Create with Arc::new(Mutex::new(...))
- packages/core/src/stt.rs:248-255 - Update submit_audio() to lock upsampler
- packages/core/src/stt.rs:326-337 - Update upsample_audio() to take Arc<Mutex<>>

---

#### 2. Implement Whisper Transcription

**Current**: `transcribe_with_whisper()` returns error (line 233)

**Implementation Requirements**:

##### A. Model Loading & Caching
```rust
use candle_transformers::models::whisper;
use once_cell::sync::Lazy;
use std::sync::RwLock;

// Global model cache
static WHISPER_MODELS: Lazy<RwLock<HashMap<String, Arc<whisper::Model>>>> =
    Lazy::new(|| RwLock::new(HashMap::new()));

async fn load_whisper_model(model_size: &str) -> Result<Arc<whisper::Model>> {
    // 1. Check cache
    {
        let cache = WHISPER_MODELS.read().unwrap();
        if let Some(model) = cache.get(model_size) {
            return Ok(model.clone());
        }
    }

    // 2. Download from HuggingFace if needed
    let model_path = download_whisper_model(model_size).await?;

    // 3. Load model with candle
    let model = whisper::Model::new(&model_path)?;
    let model_arc = Arc::new(model);

    // 4. Cache it
    {
        let mut cache = WHISPER_MODELS.write().unwrap();
        cache.insert(model_size.to_string(), model_arc.clone());
    }

    Ok(model_arc)
}
```

##### B. Audio Tensor Preparation
```rust
use candle_core::{Tensor, Device};

fn prepare_audio_tensor(samples: &[f32]) -> Result<Tensor> {
    // 1. Convert to tensor
    let tensor = Tensor::from_vec(samples.to_vec(), samples.len(), &Device::Cpu)?;

    // 2. Normalize to [-1.0, 1.0] (already done in our case)

    // 3. Pad/truncate to Whisper's expected length (30 seconds @ 16kHz = 480,000 samples)
    let expected_length = 30 * 16000;
    let tensor = if samples.len() < expected_length {
        // Pad with zeros
        pad_tensor(tensor, expected_length)?
    } else {
        // Truncate or chunk
        tensor.narrow(0, 0, expected_length)?
    };

    // 4. Add batch dimension [1, samples]
    tensor.unsqueeze(0)
}
```

##### C. Whisper Inference
```rust
async fn transcribe_with_whisper(
    chunk: &AudioChunk,
    config: &SttConfig,
) -> Result<String> {
    // 1. Load model
    let model = load_whisper_model(&config.model_size).await?;

    // 2. Prepare audio tensor
    let audio_tensor = prepare_audio_tensor(&chunk.samples)?;

    // 3. Run Whisper encoder
    let mel_filters = whisper::mel_filters()?;
    let mel_spectrogram = whisper::pcm_to_mel(&audio_tensor, &mel_filters)?;
    let encoder_output = model.encode(&mel_spectrogram)?;

    // 4. Run Whisper decoder
    let mut decoder = whisper::Decoder::new(model.clone(), config.language.as_deref())?;
    let tokens = decoder.decode(&encoder_output)?;

    // 5. Convert tokens to text
    let tokenizer = whisper::Tokenizer::new()?;
    let text = tokenizer.decode(&tokens, true)?;

    info!(
        model = %config.model_size,
        text_len = text.len(),
        samples = chunk.samples.len(),
        "Whisper transcription complete"
    );

    Ok(text.trim().to_string())
}
```

##### D. Model Download Helper
```rust
use hf_hub::api::sync::Api;

async fn download_whisper_model(model_size: &str) -> Result<PathBuf> {
    // Use HuggingFace Hub API
    let api = Api::new()?;
    let repo = api.model(format!("openai/whisper-{}", model_size));

    // Download model files
    let model_path = repo.get("model.safetensors").await?;

    info!(
        model_size,
        path = ?model_path,
        "Downloaded Whisper model from HuggingFace"
    );

    Ok(model_path)
}
```

---

#### 3. Dependencies Required

Add to `packages/core/Cargo.toml`:

```toml
[dependencies]
# Existing...

# Whisper dependencies
candle-transformers = { version = "0.9", features = ["whisper"] }
hf-hub = "0.4"
once_cell = "1.21"
```

---

#### 4. Testing Plan

Create `packages/core/examples/test_stt_transcription.rs`:

```rust
/// Test STT Transcription
///
/// Usage:
/// ```bash
/// cargo run --example test_stt_transcription
/// ```

use anyhow::Result;
use xswarm::stt::{SttEngine, SttConfig};

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    println!("🎤 Testing STT Transcription 🎤\n");

    // Create STT engine
    let config = SttConfig {
        model_size: "base".to_string(),
        language: Some("en".to_string()),
        background_transcription: true,
        min_audio_duration_ms: 500,
        model_path: None,
    };

    let engine = SttEngine::with_config(config)?;
    println!("✓ STT engine created\n");

    // TODO: Test with sample audio
    // For now, just verify it compiles

    println!("✅ STT transcription test complete!");
    Ok(())
}
```

---

### 🔜 Phase 3.3: Connect STT to Memory System (PENDING)

**Goal**: Store transcriptions in semantic memory

**Tasks**:
1. Integrate `SttEngine` with `MemorySystem`
2. Store transcriptions as conversation messages
3. Add context retrieval for transcriptions
4. Test end-to-end: voice → transcription → memory → retrieval

---

## Architecture Diagram

```
Voice Input (μ-law 8kHz from Twilio)
    ↓
SttEngine::submit_audio()
    ↓
Convert μ-law → PCM f32
    ↓
AudioResampler: 8kHz → 16kHz
    ↓
Background Worker Queue (async)
    ↓
TranscriptionWorker::transcribe()
    ↓
Load Whisper Model (cached)
    ↓
Prepare Audio Tensor
    ↓
Whisper Inference (candle)
    ↓
Decode Tokens → Text
    ↓
TranscriptionResult
    ↓
SttEngine::get_transcription()
    ↓
Supervisor → Memory Storage
    ↓
Semantic Memory Database
```

---

## Implementation Status

**Phase 3.1**: ✅ COMPLETE (350 LOC, ee8a340)
**Phase 3.2**: 🔄 IN PROGRESS (Whisper implementation needed)
**Phase 3.3**: ⏳ PENDING (Memory integration)

**Next Step**: Implement Whisper transcription in `transcribe_with_whisper()`

---

## Notes

- Whisper model download may take time on first run (models are ~100MB-1.5GB)
- Model caching prevents re-downloads
- Consider using "tiny" or "base" models for faster inference
- "small", "medium", "large" models provide better accuracy but slower
- Whisper supports 99+ languages via `language` parameter
- Background transcription prevents blocking main thread

---

## References

- Whisper paper: https://arxiv.org/abs/2212.04356
- Candle transformers: https://github.com/huggingface/candle/tree/main/candle-transformers
- HuggingFace Hub: https://huggingface.co/openai/whisper-base
