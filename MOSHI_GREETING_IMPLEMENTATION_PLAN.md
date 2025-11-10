# MOSHI Greeting Audio Implementation Plan

## Overview

This document provides step-by-step instructions to implement greeting audio generation for the MOSHI voice system.

---

## Prerequisites

### Required Models
- **MOSHI Conversational LM**: ✅ Already loaded (`kyutai/moshika-candle-q8`)
- **MIMI Codec**: ✅ Already loaded (bundled with LM)
- **MOSHI TTS Model**: ❌ NOT loaded - needs to be added
- **T5 Text Encoder**: ❌ NOT loaded - required for TTS

### Model Information
- TTS Repository: `kyutai/moshika-tts-v0.2` or `kyutai/moshi-tts`
- Required Files:
  - T5 encoder weights
  - TTS LM weights
  - Speaker conditioning model (optional)

---

## Implementation Steps

### STEP 1: Add Audio Output Dependencies

**File:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/Cargo.toml`

**Action:** Add CPAL for audio output

```toml
[dependencies]
# Existing dependencies...
cpal = "0.15"  # Cross-platform audio output
```

**Verification:**
```bash
cd /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core
cargo check
```

---

### STEP 2: Create Audio Output Module

**File:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/audio_output.rs` (NEW)

**Implementation:**

```rust
// Audio Output Module - Local Speaker Playback
//
// This module handles playing PCM audio through the system's audio output device
// using CPAL for cross-platform compatibility.

use anyhow::{Context, Result};
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use std::sync::{Arc, Mutex};
use tracing::{info, warn, error};

/// Audio output device for playing MOSHI-generated audio
pub struct AudioOutput {
    device: cpal::Device,
    config: cpal::StreamConfig,
    sample_rate: u32,
}

impl AudioOutput {
    /// Create a new audio output device
    pub fn new(sample_rate: u32) -> Result<Self> {
        info!(sample_rate, "Initializing audio output device");

        // Get default audio host
        let host = cpal::default_host();
        info!(host_id = ?host.id(), "Using audio host");

        // Get default output device
        let device = host
            .default_output_device()
            .context("No audio output device available")?;

        info!(device_name = ?device.name(), "Selected output device");

        // Configure audio stream
        let supported_config = device
            .default_output_config()
            .context("Failed to get default output config")?;

        let config = cpal::StreamConfig {
            channels: 1,  // Mono audio
            sample_rate: cpal::SampleRate(sample_rate),
            buffer_size: cpal::BufferSize::Default,
        };

        info!(?config, "Audio output configured");

        Ok(Self {
            device,
            config,
            sample_rate,
        })
    }

    /// Play PCM audio samples through the output device
    ///
    /// This creates a temporary stream, plays the audio, and waits for completion.
    /// For streaming audio, use `play_stream()` instead.
    pub fn play(&self, samples: &[f32]) -> Result<()> {
        if samples.is_empty() {
            warn!("Attempted to play empty audio buffer");
            return Ok(());
        }

        info!(sample_count = samples.len(), duration_s = samples.len() as f32 / self.sample_rate as f32, "Playing audio");

        // Create shared buffer for audio samples
        let buffer = Arc::new(Mutex::new(samples.to_vec()));
        let buffer_clone = buffer.clone();
        let mut position = 0usize;

        // Build output stream
        let stream = self.device.build_output_stream(
            &self.config,
            move |data: &mut [f32], _: &cpal::OutputCallbackInfo| {
                let mut buf = buffer_clone.lock().unwrap();
                for sample in data.iter_mut() {
                    if position < buf.len() {
                        *sample = buf[position];
                        position += 1;
                    } else {
                        *sample = 0.0;  // Silence after buffer ends
                    }
                }
            },
            |err| {
                error!(error = ?err, "Audio stream error");
            },
            None,
        )
        .context("Failed to build output stream")?;

        // Play the stream
        stream.play().context("Failed to play audio stream")?;

        // Wait for audio to complete
        let duration_ms = (samples.len() as f32 / self.sample_rate as f32 * 1000.0) as u64;
        std::thread::sleep(std::time::Duration::from_millis(duration_ms + 100));

        // Stream will be automatically dropped and stopped
        info!("Audio playback completed");

        Ok(())
    }

    /// Get the configured sample rate
    pub fn sample_rate(&self) -> u32 {
        self.sample_rate
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_audio_output_creation() {
        // This test may fail in CI environments without audio devices
        match AudioOutput::new(24000) {
            Ok(output) => {
                assert_eq!(output.sample_rate(), 24000);
            }
            Err(e) => {
                eprintln!("Audio output test skipped (no device): {}", e);
            }
        }
    }

    #[test]
    fn test_empty_audio() {
        if let Ok(output) = AudioOutput::new(24000) {
            // Should not panic with empty buffer
            assert!(output.play(&[]).is_ok());
        }
    }

    #[test]
    fn test_simple_tone() {
        if let Ok(output) = AudioOutput::new(24000) {
            // Generate a 440Hz tone for 0.5 seconds
            let duration = 0.5;
            let sample_count = (24000.0 * duration) as usize;
            let frequency = 440.0;
            let mut samples = Vec::with_capacity(sample_count);

            for i in 0..sample_count {
                let t = i as f32 / 24000.0;
                let sample = (2.0 * std::f32::consts::PI * frequency * t).sin() * 0.3;
                samples.push(sample);
            }

            // Should play without error
            assert!(output.play(&samples).is_ok());
        }
    }
}
```

**Verification:**
```bash
cargo test --package xswarm-core --lib audio_output
```

---

### STEP 3: Update TTS Module to Use MOSHI TTS

**File:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/tts.rs`

**Changes Required:**

1. Add TTS model loading to `TtsEngine`
2. Implement actual text-to-audio synthesis
3. Remove error stub

**Updated Implementation:**

```rust
// Add TTS state to TtsEngine
pub struct TtsEngine {
    /// MIMI audio resampler for 24kHz → 8kHz conversion
    downsampler: AudioResampler,
    /// TTS model for text-to-audio synthesis (if loaded)
    tts_model: Option<moshi::tts::Model>,
}

impl TtsEngine {
    /// Create a new TTS engine with optional TTS model
    pub fn new_with_tts(tts_model: Option<moshi::tts::Model>) -> Result<Self> {
        let downsampler = AudioResampler::new(24000, 8000, 1920)
            .context("Failed to create TTS downsampler")?;

        Ok(Self {
            downsampler,
            tts_model,
        })
    }

    /// Synthesize text to audio tokens using MOSHI TTS model
    pub async fn text_to_tokens(
        &mut self,
        text: &str,
        moshi_state: &mut tokio::sync::RwLockWriteGuard<'_, MoshiState>,
    ) -> Result<Vec<Vec<u32>>> {
        info!(text = %text, "Synthesizing text to audio tokens");

        // Check if TTS model is loaded
        let tts_model = self.tts_model.as_mut()
            .ok_or_else(|| anyhow::anyhow!("TTS model not loaded"))?;

        // Step 1: Tokenize text using T5 tokenizer
        // Note: This requires T5 tokenizer which is part of TTS model
        let text_tokens = Self::tokenize_text_for_tts(text, &moshi_state.text_tokenizer)?;
        debug!(token_count = text_tokens.len(), "Text tokenized for TTS");

        // Step 2: Create T5 conditions from text tokens
        let device = &moshi_state.device;
        let text_tensor = candle::Tensor::from_vec(
            text_tokens,
            (1, text_tokens.len()),
            device,
        )?;

        // Step 3: Generate audio tokens using TTS model
        let conditions = tts_model.conditions(&text_tensor, None)?;
        let audio_tokens = tts_model.sample(&conditions, 0.0)?;

        info!(frame_count = audio_tokens.len(), "TTS generated audio tokens");

        Ok(audio_tokens)
    }

    /// Tokenize text for TTS (different from conversational tokenization)
    fn tokenize_text_for_tts(
        text: &str,
        tokenizer: &sentencepiece::SentencePieceProcessor,
    ) -> Result<Vec<u32>> {
        let tokens = tokenizer
            .encode(text)
            .context("Failed to tokenize text for TTS")?
            .into_iter()
            .map(|id| id.id as u32)
            .collect();

        Ok(tokens)
    }
}
```

**Note:** This step requires loading the TTS model, which is addressed in Step 4.

---

### STEP 4: Add TTS Model Loading to Voice Bridge

**File:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/voice.rs`

**Changes Required:**

1. Update `VoiceConfig` to include TTS model paths
2. Update `download_models_if_needed()` to download TTS models
3. Add TTS model to `MoshiState`
4. Load TTS model in `MoshiState::new()`

**Implementation:**

```rust
// Update VoiceConfig
#[derive(Debug, Clone)]
pub struct VoiceConfig {
    // ... existing fields ...

    /// Path to TTS model file (optional, for greeting/synthesis)
    pub tts_model_file: Option<String>,
    /// Path to T5 encoder for TTS (optional)
    pub t5_encoder_file: Option<String>,
}

impl Default for VoiceConfig {
    fn default() -> Self {
        let home = std::env::var("HOME").unwrap_or_else(|_| "/Users/chad".to_string());
        let lm_snapshot_path = format!(
            "{}/.cache/huggingface/hub/models--kyutai--moshika-candle-q8/snapshots/4b4a873fc1d3b92ce32b3ae91ff8e95bbb62193f",
            home
        );

        // TTS models (optional)
        let tts_snapshot_path = format!(
            "{}/.cache/huggingface/hub/models--kyutai--moshika-tts-v0.2/snapshots/latest",
            home
        );

        Self {
            // ... existing fields ...
            tts_model_file: Some(format!("{}/tts_model.safetensors", tts_snapshot_path)),
            t5_encoder_file: Some(format!("{}/t5_encoder.safetensors", tts_snapshot_path)),
        }
    }
}

// Update MoshiState
pub struct MoshiState {
    // ... existing fields ...

    /// TTS model for text-to-audio synthesis (optional)
    pub tts_model: Option<moshi::tts::Model>,
}

// Update download_models_if_needed
pub async fn download_models_if_needed(mut config: VoiceConfig) -> Result<VoiceConfig> {
    // ... existing model downloads ...

    // Download TTS models if specified
    if config.tts_model_file.is_some() && config.t5_encoder_file.is_some() {
        info!("Checking TTS models...");

        let tts_files_exist = [
            config.tts_model_file.as_ref().unwrap(),
            config.t5_encoder_file.as_ref().unwrap(),
        ]
        .iter()
        .all(|f| Path::new(f).exists());

        if !tts_files_exist {
            info!("Downloading TTS models from Hugging Face");
            // TODO: Implement TTS model download
            warn!("TTS model download not yet implemented - continuing without TTS");
            config.tts_model_file = None;
            config.t5_encoder_file = None;
        }
    }

    Ok(config)
}
```

---

### STEP 5: Add Greeting Generation Method

**File:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/voice.rs`

**Add to VoiceBridge implementation:**

```rust
impl VoiceBridge {
    /// Generate greeting audio when voice system starts
    pub async fn generate_greeting(&self) -> Result<Vec<f32>> {
        info!("Generating greeting audio");

        let greeting_text = "Hello, how can I help you?";

        // Get MOSHI state
        let mut moshi_state = self.state.write().await;

        // Check if TTS is available
        if moshi_state.tts_model.is_none() {
            anyhow::bail!("TTS model not loaded - cannot generate greeting");
        }

        // Create TTS engine with TTS model
        let mut tts_engine = crate::tts::TtsEngine::new_with_tts(
            moshi_state.tts_model.clone()
        )?;

        // Generate audio tokens from text
        let audio_tokens = tts_engine.text_to_tokens(greeting_text, &mut moshi_state).await?;

        // Decode audio tokens to PCM
        let pcm_audio = Self::decode_tts_audio_tokens(&audio_tokens, &mut moshi_state)?;

        info!(
            sample_count = pcm_audio.len(),
            duration_s = pcm_audio.len() as f32 / 24000.0,
            "Greeting audio generated"
        );

        Ok(pcm_audio)
    }

    /// Decode TTS audio tokens to PCM using MIMI
    fn decode_tts_audio_tokens(
        audio_tokens: &[Vec<u32>],
        moshi_state: &mut MoshiState,
    ) -> Result<Vec<f32>> {
        debug!(frame_count = audio_tokens.len(), "Decoding TTS audio tokens");

        let mut pcm_samples = Vec::new();
        let mimi_device = if moshi_state.config.use_cpu_for_mimi {
            &candle::Device::Cpu
        } else {
            &moshi_state.device
        };

        // Decode each frame
        for (frame_idx, frame_tokens) in audio_tokens.iter().enumerate() {
            // Skip padding frames
            let max_valid_token = moshi_state.mimi_model.config().quantizer_bins as u32;
            if frame_tokens.iter().all(|&t| t >= max_valid_token) {
                debug!(frame_idx, "Skipping padding frame");
                continue;
            }

            // Create tensor: [batch=1, codebooks, time=1]
            let tokens_tensor = candle::Tensor::from_vec(
                frame_tokens.clone(),
                (1, frame_tokens.len(), 1),
                mimi_device,
            )?;

            // Decode to PCM
            let decoded = moshi_state.mimi_model.decode_step(&tokens_tensor.into(), &().into())?;
            let audio_tensor = decoded.as_option()
                .ok_or_else(|| anyhow::anyhow!("MIMI decoder returned None for frame {}", frame_idx))?;

            // Extract samples
            let frame_samples = audio_tensor.flatten_all()?.to_vec1::<f32>()?;
            pcm_samples.extend_from_slice(&frame_samples);
        }

        info!(sample_count = pcm_samples.len(), "TTS audio decoding complete");
        Ok(pcm_samples)
    }
}
```

---

### STEP 6: Integrate Greeting Playback in Dashboard

**File:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/dashboard.rs`

**Add audio output field to DashboardApp:**

```rust
pub struct DashboardApp {
    // ... existing fields ...

    /// Audio output device for greeting and TTS playback
    audio_output: Option<Arc<crate::audio_output::AudioOutput>>,
}
```

**Update initialization (around line 690):**

```rust
// Initialize audio output device
let audio_output = match crate::audio_output::AudioOutput::new(24000) {
    Ok(output) => {
        info!("Audio output device initialized");
        Some(Arc::new(output))
    }
    Err(e) => {
        warn!("Failed to initialize audio output: {}", e);
        None
    }
};
```

**Update voice system startup (around line 714):**

```rust
// Auto-start MOSHI voice system for real audio data in visualizers
info!("Auto-starting MOSHI voice system for dashboard audio visualization");
match self.start_voice_system().await {
    Ok(()) => {
        info!("Voice system started successfully - MOSHI and microphone active");

        // NEW: Generate and play greeting
        if let Some(voice_bridge) = self.voice_bridge.read().await.as_ref() {
            info!("Generating greeting audio...");
            match voice_bridge.generate_greeting().await {
                Ok(greeting_pcm) => {
                    if let Some(audio_out) = &self.audio_output {
                        info!("Playing greeting through speakers...");
                        match audio_out.play(&greeting_pcm) {
                            Ok(()) => {
                                info!("✅ Greeting audio played successfully!");
                                let mut state = self.state.write().await;
                                state.add_event(ActivityEvent::SystemEvent {
                                    message: "Greeting audio played: 'Hello, how can I help you?'".to_string(),
                                    time: Local::now(),
                                });
                            }
                            Err(e) => {
                                warn!("Failed to play greeting audio: {}", e);
                            }
                        }
                    } else {
                        warn!("Audio output not available - cannot play greeting");
                    }
                }
                Err(e) => {
                    warn!("Failed to generate greeting: {}", e);
                    info!("Continuing without greeting - TTS may not be available");
                }
            }
        }

        let mut state = self.state.write().await;
        state.add_event(ActivityEvent::SystemEvent {
            message: "MOSHI voice system and microphone started".to_string(),
            time: Local::now(),
        });
    }
    Err(e) => {
        // ... existing error handling ...
    }
}
```

---

### STEP 7: Add Audio Output Module to lib.rs

**File:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/lib.rs`

**Add module declaration:**

```rust
pub mod audio_output;
```

---

## Testing Plan

### Unit Tests

```bash
# Test audio output module
cargo test --package xswarm-core --lib audio_output

# Test TTS engine
cargo test --package xswarm-core --lib tts

# Test voice module
cargo test --package xswarm-core --lib voice
```

### Integration Test

```bash
# Run the full dashboard
cargo run --package xswarm-core

# Expected output:
# INFO Initializing audio output device
# INFO Audio output device initialized
# INFO Auto-starting MOSHI voice system
# INFO Generating greeting audio...
# INFO TTS generated audio tokens: 45 frames
# INFO TTS audio decoding complete: 108000 samples
# INFO Playing greeting through speakers...
# ✅ Greeting audio played successfully!
```

### Manual Verification

1. Start dashboard: `cargo run`
2. Listen for audible greeting: "Hello, how can I help you?"
3. Check dashboard activity log shows greeting played
4. Verify no errors in console output

---

## Fallback Strategy (If TTS Models Not Available)

If TTS models cannot be loaded initially, implement a simpler greeting:

```rust
// Generate simple tone greeting as placeholder
pub async fn generate_simple_greeting(&self) -> Result<Vec<f32>> {
    info!("Generating simple tone greeting (TTS not available)");

    // Generate a pleasant two-tone notification sound
    let sample_rate = 24000;
    let duration = 0.5; // 0.5 seconds
    let sample_count = (sample_rate as f32 * duration) as usize;

    let mut samples = Vec::with_capacity(sample_count);

    // First tone: 800 Hz
    for i in 0..sample_count / 2 {
        let t = i as f32 / sample_rate as f32;
        let sample = (2.0 * std::f32::consts::PI * 800.0 * t).sin() * 0.3;
        samples.push(sample);
    }

    // Second tone: 1000 Hz
    for i in 0..sample_count / 2 {
        let t = i as f32 / sample_rate as f32;
        let sample = (2.0 * std::f32::consts::PI * 1000.0 * t).sin() * 0.3;
        samples.push(sample);
    }

    Ok(samples)
}
```

---

## Known Limitations

1. **TTS Model Size**: TTS models are large (several GB) - ensure sufficient disk space
2. **Download Time**: First run will download models - may take several minutes
3. **Audio Device**: Requires audio output device - will fail in headless environments
4. **CPAL Support**: May have platform-specific issues on some systems

---

## Troubleshooting

### No Audio Device Found
```
Error: No audio output device available
```
**Solution:** Ensure speakers/headphones are connected and system audio is enabled

### TTS Model Not Found
```
Error: TTS model not loaded - cannot generate greeting
```
**Solution:** TTS feature is optional - system will skip greeting if not available

### Audio Playback Failed
```
Error: Failed to play audio stream
```
**Solution:** Check audio device permissions and ensure no other app is using exclusive mode

---

## Success Criteria

- [ ] Dashboard starts without errors
- [ ] Audio output device initializes
- [ ] MOSHI voice system starts
- [ ] Greeting audio is generated
- [ ] Greeting is audible through speakers
- [ ] Dashboard shows "Greeting audio played" event
- [ ] No errors in console output
- [ ] Amplitude visualizer shows activity during greeting

---

## Next Steps After Implementation

1. Add configurable greeting text
2. Support multiple greeting voices
3. Add greeting audio to Twilio connections
4. Implement full supervisor TTS integration
5. Add audio output for all system notifications

---

## References

- MOSHI TTS Documentation: https://github.com/kyutai-labs/moshi
- CPAL Documentation: https://docs.rs/cpal/
- Candle Audio Processing: https://github.com/huggingface/candle
