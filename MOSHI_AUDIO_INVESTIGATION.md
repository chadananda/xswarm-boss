# MOSHI Audio Generation Investigation Report

## Executive Summary

MOSHI reports as "started" successfully but generates NO audio output and NO greeting. This investigation reveals the root causes and provides a clear path to implementation.

---

## Problem Statement

**Observed Behavior:**
- Dashboard shows "MOSHI voice system and microphone started"
- Voice bridge WebSocket server starts on port 9998
- Supervisor WebSocket server starts on port 9999
- NO audio is generated when system starts
- NO greeting message ("hello, how can I help?") is played
- System appears ready but is completely silent

**Expected Behavior:**
- MOSHI should generate a greeting when initialized
- Audio should be audible/playable through output devices
- User should hear "hello, how can I help?" or similar greeting

---

## Investigation Findings

### 1. MODEL LOADING STATUS ✅ WORKING

**Location:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/voice.rs:215-243`

**Analysis:**
The MOSHI models ARE loading correctly:

```rust
// Lines 215-243: Model loading implementation
pub fn new(config: VoiceConfig) -> Result<Self> {
    info!("Initializing MOSHI voice models...");

    // Load language model
    let lm_model = moshi::lm::load_streaming(&config.lm_model_file, dtype, &device)
        .context("Failed to load language model")?;

    // Load MIMI codec
    let mimi_model = moshi::mimi::load(&config.mimi_model_file, Some(MIMI_NUM_CODEBOOKS), mimi_device)
        .context("Failed to load MIMI codec")?;

    // Load text tokenizer
    let text_tokenizer = sentencepiece::SentencePieceProcessor::open(&config.text_tokenizer_file)
        .context("Failed to load text tokenizer")?;

    // Warm up models
    Self::warmup(&mut lm_model.clone(), &mut mimi_model.clone(), &device, mimi_device)?;

    info!("MOSHI models initialized successfully");
}
```

**Status:** ✅ Models load successfully, warmup completes, no errors reported

---

### 2. AUDIO GENERATION CAPABILITY ⚠️ PARTIALLY IMPLEMENTED

**Location:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/voice.rs:601-764`

**Analysis:**
MOSHI CAN generate audio in response to incoming voice input:

```rust
// Lines 601-764: Audio generation during conversation
async fn process_with_lm(&self, conn_state: &mut ConnectionState, audio: Vec<f32>) -> Result<Vec<f32>> {
    // Step 1: Encode incoming audio to MIMI codes
    let codes = moshi_state.mimi_model.encode_step(&pcm_tensor.into(), &().into())?;

    // Step 2: Run LM inference
    let text_token = conn_state.lm_generator.step(prev_text_token, &codes, force_text_token, None)?;

    // Step 3: Get audio tokens from LM and decode to audio
    if let Some(audio_tokens) = conn_state.lm_generator.last_audio_tokens() {
        let audio_tensor = Tensor::from_slice(audio_tokens_slice, (1, cb, 1), mimi_device)?;
        let decoded = moshi_state.mimi_model.decode_step(&audio_tensor.into(), &().into())?;
        let audio_vec = audio_tensor.flatten_all()?.to_vec1::<f32>()?;

        // Broadcast amplitude for visualizer
        moshi_state.broadcast_amplitude(&audio_vec).await;

        return Ok(audio_vec);
    }
}
```

**Status:** ⚠️ Audio generation works during conversation but is REACTIVE ONLY (requires incoming audio input)

---

### 3. TEXT-TO-SPEECH (TTS) ❌ NOT IMPLEMENTED

**Location:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/tts.rs:38-64`

**Critical Finding:**
The TTS system that would enable greeting audio is STUBBED OUT:

```rust
// Lines 49-64: TTS text_to_tokens method
pub async fn text_to_tokens(
    &mut self,
    text: &str,
    moshi_state: &mut tokio::sync::RwLockWriteGuard<'_, MoshiState>,
) -> Result<Vec<Vec<u32>>> {
    info!(text = %text, "Synthesizing text to audio tokens");

    // Step 1: Tokenize text using SentencePiece
    let text_tokens = Self::tokenize_text(text, &moshi_state.text_tokenizer)?;
    debug!(token_count = text_tokens.len(), "Text tokenized");

    // Step 2: Use TTS streaming to generate audio tokens
    // Note: This requires MOSHI TTS model which is separate from the main LM
    // For now, we'll return an error indicating TTS model is not loaded
    // TODO: Load and integrate MOSHI TTS model
    anyhow::bail!("TTS model not yet integrated - requires separate MOSHI TTS model")
}
```

**Root Cause:** The TTS model is NOT loaded, and the synthesis function immediately returns an error!

---

### 4. MOSHI TTS MODULE EXISTS ✅ AVAILABLE

**Location:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/moshi/moshi-core/src/tts.rs`

**Analysis:**
Kyutai provides a full TTS implementation in the MOSHI core library:

```rust
// MOSHI TTS Model structure
pub struct Model {
    t5: t5::T5EncoderModel,           // T5 text encoder
    pub lm: crate::lm::LmModel,        // Language model
    speaker_cond: Option<(crate::mimi::Mimi, Linear)>,  // Speaker conditioning
    t5_proj: Linear,
    pub sample_rate: f64,
    frame_rate: f64,
    audio_vocab_size: u32,
    audio_codebooks: usize,
    pub max_duration_s: f64,
    max_speakers: usize,
    end_of_gen: Option<usize>,
}

// Sample method generates audio tokens from text conditions
pub fn sample(&mut self, conditions: &Tensor, cfg_alpha: f64) -> Result<Vec<Vec<u32>>> {
    // Generates audio tokens that can be decoded by MIMI to PCM audio
}
```

**Status:** ✅ TTS module exists and is fully functional in moshi-core

---

### 5. GREETING IMPLEMENTATION ❌ NOT IMPLEMENTED

**Analysis:**
There is NO code that:
- Generates a greeting when MOSHI starts
- Plays audio through speakers/output devices
- Triggers TTS synthesis on initialization

The voice system only:
1. Loads models ✅
2. Starts WebSocket servers ✅
3. Waits for incoming Twilio connections ✅
4. Processes incoming audio reactively ✅

It does NOT:
1. Generate proactive audio ❌
2. Play greeting messages ❌
3. Output to local audio devices ❌

---

### 6. AUDIO OUTPUT PIPELINE ⚠️ INCOMPLETE

**Current Audio Flow:**

```
Twilio → WebSocket → MOSHI → Process → MOSHI generates audio → Back to Twilio
```

**Missing Audio Flow:**

```
Text Input → TTS Model → Audio Tokens → MIMI Decoder → PCM Audio → Audio Output Device
```

**Location:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/supervisor.rs:772-821`

The supervisor has a `synthesize_text` method but:

```rust
// Line 811-813: Critical TODO
// TODO: Send mulaw_audio to active Twilio stream via voice bridge
// For now, just log success
warn!("TTS audio generated but not yet sent to Twilio - voice bridge integration pending");
```

The audio is generated but NOT sent anywhere!

---

### 7. AUDIO AMPLITUDE BROADCASTING ✅ WORKING

**Location:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/voice.rs:258-282`

**Analysis:**
The amplitude broadcasting for visualizers IS implemented:

```rust
pub async fn set_amplitude_channel(&self, tx: mpsc::UnboundedSender<f32>) {
    let mut amplitude_tx = self.audio_amplitude_tx.write().await;
    *amplitude_tx = Some(tx);
    info!("Audio amplitude channel connected for visualizer");
}

async fn broadcast_amplitude(&self, audio_samples: &[f32]) {
    // Calculate RMS amplitude
    let rms = if audio_samples.is_empty() {
        0.0
    } else {
        let sum: f32 = audio_samples.iter().map(|&s| s * s).sum();
        (sum / audio_samples.len() as f32).sqrt()
    };

    // Send to amplitude channel if connected
    let amplitude_tx = self.audio_amplitude_tx.read().await;
    if let Some(tx) = amplitude_tx.as_ref() {
        let _ = tx.send(rms);
    }
}
```

**Status:** ✅ Amplitude data is broadcast BUT only when MOSHI generates audio in response to input

---

## Root Causes Summary

### PRIMARY ISSUES:

1. **NO TTS MODEL LOADED**
   - Location: `packages/core/src/tts.rs:64`
   - The TTS synthesis immediately errors with "TTS model not yet integrated"
   - Separate TTS model files need to be loaded from Hugging Face

2. **NO GREETING TRIGGER**
   - Location: `packages/core/src/dashboard.rs:714-722`
   - Voice system starts but never calls any greeting generation function
   - No initialization audio playback implemented

3. **NO AUDIO OUTPUT DEVICE INTEGRATION**
   - Location: `packages/core/src/voice.rs` (missing)
   - MOSHI generates audio for Twilio but not for local speakers
   - No CPAL or similar audio output implementation

4. **TTS AUDIO NOT ROUTED TO OUTPUT**
   - Location: `packages/core/src/supervisor.rs:811-813`
   - Even if TTS worked, audio is not sent anywhere
   - Missing connection between TTS output and audio playback

---

## What Needs to Be Implemented

### CRITICAL PATH TO GREETING AUDIO:

#### Step 1: Load MOSHI TTS Model
```rust
// In packages/core/src/voice.rs or new tts.rs module
pub struct TtsState {
    tts_model: moshi::tts::Model,  // Load from HuggingFace
    t5_tokenizer: /* T5 tokenizer */,
}

impl TtsState {
    pub fn new() -> Result<Self> {
        // Download TTS model from HuggingFace
        // kyutai/moshika-tts-v0.2 or similar
        // Load T5 encoder, LM, and speaker conditioning
    }
}
```

#### Step 2: Implement Greeting Generation
```rust
// In packages/core/src/voice.rs
impl VoiceBridge {
    pub async fn generate_greeting(&self) -> Result<Vec<f32>> {
        let greeting_text = "Hello, how can I help you?";

        // Use TTS to convert text to audio tokens
        let audio_tokens = self.tts_state.text_to_tokens(greeting_text).await?;

        // Decode tokens to PCM audio using MIMI
        let pcm_audio = self.decode_audio_tokens(&audio_tokens).await?;

        Ok(pcm_audio)
    }
}
```

#### Step 3: Implement Audio Output Device
```rust
// In packages/core/src/audio_output.rs (new file)
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};

pub struct AudioOutput {
    stream: cpal::Stream,
    sample_rate: u32,
}

impl AudioOutput {
    pub fn new() -> Result<Self> {
        // Initialize CPAL output device
        // Create audio stream at 24kHz (MOSHI native)
    }

    pub fn play(&self, pcm_samples: &[f32]) -> Result<()> {
        // Send PCM samples to output device
        // Play through speakers
    }
}
```

#### Step 4: Trigger Greeting on Startup
```rust
// In packages/core/src/dashboard.rs after line 722
match self.start_voice_system().await {
    Ok(()) => {
        info!("Voice system started successfully - MOSHI and microphone active");

        // NEW: Generate and play greeting
        if let Some(voice_bridge) = &self.voice_bridge {
            match voice_bridge.generate_greeting().await {
                Ok(greeting_audio) => {
                    // Play greeting through speakers
                    audio_output.play(&greeting_audio)?;
                    info!("Greeting audio played successfully");
                }
                Err(e) => {
                    warn!("Failed to generate greeting: {}", e);
                }
            }
        }

        let mut state = self.state.write().await;
        state.add_event(ActivityEvent::SystemEvent {
            message: "MOSHI voice system and microphone started".to_string(),
            time: Local::now(),
        });
    }
}
```

---

## Recommended Implementation Plan

### PHASE 1: TTS Model Integration (CRITICAL)
1. Add TTS model download to `VoiceBridge::download_models_if_needed()`
2. Load TTS model in `MoshiState::new()`
3. Implement `text_to_audio_tokens()` using loaded TTS model
4. Test text → audio token conversion

### PHASE 2: Audio Output Device (CRITICAL)
1. Add `cpal` dependency to `Cargo.toml`
2. Create `AudioOutput` struct with CPAL integration
3. Implement `play()` method for PCM audio
4. Test audio playback with simple tones

### PHASE 3: Greeting Implementation
1. Add `generate_greeting()` method to `VoiceBridge`
2. Call greeting generation after voice system starts
3. Route greeting audio to `AudioOutput`
4. Test complete greeting flow

### PHASE 4: Supervisor TTS Integration
1. Connect supervisor `synthesize_text()` to `AudioOutput`
2. Implement audio routing from TTS to speakers
3. Test bidirectional conversation with audio output

---

## Testing Checklist

- [ ] Verify TTS model loads without errors
- [ ] Verify text tokenization produces valid tokens
- [ ] Verify TTS generates audio tokens from text
- [ ] Verify MIMI decodes tokens to PCM audio
- [ ] Verify audio output device initializes
- [ ] Verify PCM audio plays through speakers
- [ ] Verify greeting generates on startup
- [ ] Verify greeting is audible
- [ ] Verify amplitude visualization shows greeting activity
- [ ] Verify supervisor TTS routes to speakers

---

## Files Requiring Changes

1. `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/Cargo.toml`
   - Add `cpal` dependency for audio output

2. `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/voice.rs`
   - Load TTS model in `MoshiState::new()`
   - Add `generate_greeting()` method
   - Update `download_models_if_needed()` for TTS models

3. `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/tts.rs`
   - Remove error stub in `text_to_tokens()`
   - Implement actual TTS generation using moshi::tts module

4. `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/audio_output.rs` (NEW)
   - Create audio output device integration
   - Implement PCM playback

5. `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/dashboard.rs`
   - Call greeting generation after voice system starts
   - Add audio output initialization

6. `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/supervisor.rs`
   - Route synthesized audio to output device
   - Remove TODO comment after implementation

---

## Dependencies to Add

```toml
[dependencies]
cpal = "0.15"  # Audio output device
```

---

## Expected Logs After Fix

```
INFO Initializing MOSHI voice models...
INFO Loading language model
INFO Loading MIMI codec
INFO Loading text tokenizer
INFO Loading TTS model from HuggingFace
INFO Models warmed up and ready
INFO MOSHI models initialized successfully
INFO Voice system started successfully
INFO Generating greeting audio...
INFO Text tokenized: 6 tokens
INFO TTS generated 45 audio frames
INFO MIMI decoded 108000 PCM samples
INFO Playing greeting through audio output...
INFO Greeting audio played successfully
INFO MOSHI voice system and microphone started
```

---

## Conclusion

**MOSHI DOES NOT GENERATE GREETING AUDIO BECAUSE:**

1. ❌ TTS model is not loaded (separate from conversational LM)
2. ❌ TTS synthesis is stubbed out and returns an error
3. ❌ No greeting generation is triggered on startup
4. ❌ No audio output device integration exists
5. ❌ Audio is only generated reactively in response to input

**TO FIX:**
- Load MOSHI TTS model from HuggingFace
- Implement text-to-audio synthesis
- Add CPAL audio output device
- Call greeting generation on voice system startup

All the pieces exist in the codebase, they just need to be wired together!
