# Language Model Transcription Implementation Plan

## Overview

Implementing full bidirectional speech-to-text/text-to-speech requires integrating MOSHI's language model with the voice bridge. This document outlines the implementation strategy.

## Current Architecture (Fast Path)

```rust
// packages/core/src/voice.rs:395-419
// FAST PATH: Skip language model
let codes = state.mimi_model.encode_step(&pcm_tensor.into(), &().into())?;
let decoded = state.mimi_model.decode_step(&codes, &().into())?;
// Result: Audio echo only, no transcription
```

**Latency**: ~50-100ms per frame
**Capability**: Audio echo via MIMI codec
**Missing**: Speech-to-text transcription, text-to-speech synthesis

## Target Architecture (Full LM Path)

```rust
// Per-connection LM state
struct ConnectionState {
    lm_generator: moshi::lm_generate_multistream::State,
    lm_config: moshi::lm_generate_multistream::Config,
    prev_text_token: u32,
}

// For each audio frame:
1. Encode audio → MIMI codes
2. Call lm_generator.step(prev_text_token, &codes, ...)
3. Get text token → decode to transcription
4. Get audio tokens → decode to output audio
5. Broadcast transcription to supervisor
```

**Latency**: ~200-500ms per frame with Metal GPU
**Capability**: Full bidirectional text + audio

## Key Components

### 1. LM Generator Config

```rust
use moshi::lm_generate_multistream::{Config, State};

let lm_config = Config::v0_1(); // Default MOSHI config
// Contains:
// - text_start_token, text_pad_token, text_eop_token
// - audio_pad_token
// - delay_pattern for audio generation
```

### 2. LM Generator State (Per-Connection)

```rust
let lm_generator = State::new(
    lm_model,              // From MoshiState
    max_steps,             // Max inference steps
    audio_logits_processor, // Sampling strategy
    text_logits_processor,  // Text token sampling
    &lm_config,
)?;
```

**Critical**: Must be created per WebSocket connection, not shared globally.

### 3. Inference Loop

```rust
// Step 1: Encode audio to codes
let audio_codes = mimi.encode_step(&audio_tensor, &().into())?;
let codes = audio_codes.i((0, .., step))?.to_vec1::<u32>()?;

// Step 2: LM inference
let text_token = lm_generator.step(
    prev_text_token,
    &codes,
    None,  // force_text_token
    None,  // ca_src (cross-attention)
)?;

// Step 3: Decode text token to transcription
if text_token != lm_config.text_start_token &&
   text_token != lm_config.text_pad_token &&
   text_token != lm_config.text_eop_token {
    let text = text_tokenizer.decode_piece_ids(&[text_token])?;
    // Broadcast to supervisor
}

// Step 4: Get audio tokens for output
if let Some(audio_tokens) = lm_generator.last_audio_tokens() {
    let audio_tensor = Tensor::from_slice(
        &audio_tokens[..num_codebooks],
        (1, num_codebooks, 1),
        device
    )?;
    let output_audio = mimi.decode_step(&audio_tensor, &().into())?;
}

prev_text_token = text_token;
```

### 4. Text Decoding (Incremental)

MOSHI generates text tokens incrementally. We need to track previous tokens to decode properly:

```rust
fn decode_text_incremental(
    tokenizer: &SentencePieceProcessor,
    prev_token: u32,
    curr_token: u32,
    config: &Config,
) -> Option<String> {
    if curr_token == config.text_start_token ||
       curr_token == config.text_pad_token ||
       curr_token == config.text_eop_token {
        return None;
    }

    if prev_token == config.text_start_token {
        // First token after start
        tokenizer.decode_piece_ids(&[curr_token]).ok()
    } else {
        // Incremental decode: get diff from previous
        let prev_text = tokenizer.decode_piece_ids(&[prev_token]).ok()?;
        let curr_text = tokenizer.decode_piece_ids(&[prev_token, curr_token]).ok()?;

        if curr_text.len() > prev_text.len() {
            Some(curr_text[prev_text.len()..].to_string())
        } else {
            None
        }
    }
}
```

## Implementation Steps

### Step 1: Add LM Config to MoshiState

```rust
pub struct MoshiState {
    lm_model: moshi::lm::LmModel,
    mimi_model: moshi::mimi::Mimi,
    text_tokenizer: sentencepiece::SentencePieceProcessor,
    device: candle::Device,
    config: VoiceConfig,
    lm_config: moshi::lm_generate_multistream::Config,  // NEW
    suggestion_queue: Arc<Mutex<VecDeque<String>>>,
}
```

### Step 2: Add Connection State to VoiceBridge

```rust
struct CallState {
    lm_generator: moshi::lm_generate_multistream::State,
    prev_text_token: u32,
    // Buffers, resampler, etc.
}

impl VoiceBridge {
    async fn handle_connection(&self, stream: TcpStream) {
        // Create per-connection LM state
        let call_state = CallState::new(&self.moshi_state)?;

        // Use call_state for inference
    }
}
```

### Step 3: Replace Fast Path with Full LM Inference

File: `packages/core/src/voice.rs:395-419`

Replace the fast path block with full LM inference as shown above.

### Step 4: Broadcast Transcriptions to Supervisor

```rust
// In handle_connection loop
if let Some(transcription) = decode_text_incremental(...) {
    let event = SupervisorEvent::UserSpeech {
        text: transcription,
        duration_ms: 0,  // TODO: track duration
        timestamp: chrono::Utc::now().to_rfc3339(),
    };

    supervisor_server.broadcast(event).await?;
}
```

### Step 5: Inject Supervisor Suggestions

```rust
// Check suggestion queue
let force_text_token = {
    let mut queue = moshi_state.suggestion_queue.lock().await;
    if let Some(suggestion) = queue.pop_front() {
        // Encode suggestion to text tokens
        // Return first token to force
        Some(encode_text_to_token(&suggestion)?)
    } else {
        None
    }
};

let text_token = lm_generator.step(
    prev_text_token,
    &codes,
    force_text_token,  // Force this token if supervisor injected
    None,
)?;
```

## Performance Considerations

### With Metal GPU (M3/M4 Mac):
- **LM inference**: ~150-300ms per frame (7B model)
- **MIMI codec**: ~50-100ms per frame
- **Total latency**: ~200-400ms per frame
- **Real-time capable**: Yes, within phone latency tolerance

### CPU Fallback:
- **LM inference**: ~5-10s per frame
- **Not suitable for real-time**: Would need async processing

## Testing Strategy

1. **Unit test**: Text decoding with known tokens
2. **Integration test**: Single frame inference
3. **End-to-end test**: Phone call with transcription logging
4. **Supervisor test**: Inject text during call, verify synthesis

## Risks & Mitigations

### Risk 1: Latency Too High
**Mitigation**: Metal GPU acceleration (already enabled in Phase 1)

### Risk 2: State Management Complexity
**Mitigation**: Careful lifetime management, Arc<Mutex<>> for shared state

### Risk 3: Text Encoding for Injection
**Challenge**: Converting supervisor text to tokens
**Mitigation**: Use text_tokenizer.encode() or simple token lookup

## Next Steps

1. Implement MoshiState changes
2. Add ConnectionState/CallState struct
3. Replace fast path with full LM
4. Add text decoding
5. Test with phone call
6. Add supervisor broadcasting

## Estimated Timeline

- **Implementation**: 3-4 hours
- **Testing**: 1-2 hours
- **Debugging**: 1-2 hours
- **Total**: 5-8 hours

## Files to Modify

1. `packages/core/src/voice.rs` (Major changes)
2. `packages/core/src/supervisor.rs` (Add transcription events)
3. `packages/core/src/bin/supervisor-cli.rs` (Display transcriptions)

---

**Status**: Ready to implement
**Blocker**: None (Metal GPU enabled)
**Priority**: Critical for bidirectional communication
