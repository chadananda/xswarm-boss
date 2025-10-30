// Text-to-Speech Integration Module
//
// This module implements text-to-speech synthesis using MOSHI's TTS model
// to enable Claude to speak responses back to the caller through Twilio.
//
// Flow:
// 1. Claude sends text response via WebSocket to supervisor
// 2. Supervisor forwards to TTS engine
// 3. TTS tokenizes text and generates audio tokens
// 4. MIMI decoder converts tokens to PCM audio
// 5. Audio is resampled and sent back through voice bridge to Twilio

use anyhow::{Context, Result};
use candle::Tensor;
use tracing::{info, debug, error};

use crate::audio::{self, AudioResampler};
use crate::voice::MoshiState;

/// TTS engine state for streaming text-to-speech synthesis
pub struct TtsEngine {
    /// MIMI audio resampler for 24kHz → 8kHz conversion
    downsampler: AudioResampler,
}

impl TtsEngine {
    /// Create a new TTS engine
    pub fn new() -> Result<Self> {
        // Create downsampler for converting MOSHI 24kHz output to Twilio 8kHz
        let downsampler = AudioResampler::new(24000, 8000, 1920)
            .context("Failed to create TTS downsampler")?;

        Ok(Self {
            downsampler,
        })
    }

    /// Synthesize text to audio tokens using MOSHI TTS model
    ///
    /// This uses MOSHI's TTS streaming capabilities to convert text into
    /// audio tokens that can be decoded to PCM.
    ///
    /// # Arguments
    /// * `text` - The text to synthesize
    /// * `moshi_state` - Shared MOSHI state with models
    ///
    /// # Returns
    /// Audio tokens ready for MIMI decoding
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

    /// Tokenize text using SentencePiece tokenizer
    fn tokenize_text(
        text: &str,
        tokenizer: &sentencepiece::SentencePieceProcessor,
    ) -> Result<Vec<u32>> {
        let tokens = tokenizer
            .encode(text)
            .context("Failed to tokenize text")?
            .into_iter()
            .map(|id| id.id as u32)
            .collect();

        Ok(tokens)
    }

    /// Synthesize text directly to μ-law audio for Twilio
    ///
    /// This is the complete pipeline: text → tokens → audio → μ-law
    ///
    /// # Arguments
    /// * `text` - The text to synthesize
    /// * `moshi_state` - Shared MOSHI state with models
    ///
    /// # Returns
    /// μ-law encoded audio at 8kHz ready for Twilio
    pub async fn synthesize_to_mulaw(
        &mut self,
        text: &str,
        moshi_state: &mut tokio::sync::RwLockWriteGuard<'_, MoshiState>,
    ) -> Result<Vec<u8>> {
        // Get audio tokens from TTS
        let audio_tokens = self.text_to_tokens(text, moshi_state).await?;

        // Decode audio tokens to PCM using MIMI
        let pcm_24khz = Self::decode_audio_tokens(&audio_tokens, moshi_state)?;

        // Convert to Twilio format (downsample and encode to μ-law)
        let mulaw_8khz = audio::moshi_to_twilio(&pcm_24khz, &mut self.downsampler)?;

        Ok(mulaw_8khz)
    }

    /// Decode audio tokens to PCM using MIMI codec
    fn decode_audio_tokens(
        audio_tokens: &[Vec<u32>],
        moshi_state: &mut MoshiState,
    ) -> Result<Vec<f32>> {
        debug!(frame_count = audio_tokens.len(), "Decoding audio tokens to PCM");

        let mut pcm_samples = Vec::new();
        let mimi_device = if moshi_state.config.use_cpu_for_mimi {
            &candle::Device::Cpu
        } else {
            &moshi_state.device
        };

        // Decode each frame of audio tokens
        for (frame_idx, frame_tokens) in audio_tokens.iter().enumerate() {
            // Skip frames that are all padding
            // Note: quantizer_bins represents the valid token range (2048 for MIMI)
            let max_valid_token = moshi_state.mimi_model.config().quantizer_bins as u32;
            if frame_tokens.iter().all(|&t| t >= max_valid_token) {
                debug!(frame_idx, "Skipping padding frame");
                continue;
            }

            // Create tensor from audio tokens: [batch=1, codebooks, time=1]
            let tokens_tensor = Tensor::from_vec(
                frame_tokens.clone(),
                (1, frame_tokens.len(), 1),
                mimi_device,
            )?;

            // Decode to PCM
            let decoded = moshi_state.mimi_model.decode_step(&tokens_tensor.into(), &().into())?;

            let audio_tensor = decoded.as_option()
                .ok_or_else(|| anyhow::anyhow!("MIMI decoder returned None for frame {}", frame_idx))?;

            // Extract PCM samples
            let frame_samples = audio_tensor.flatten_all()?.to_vec1::<f32>()?;
            pcm_samples.extend_from_slice(&frame_samples);
        }

        info!(sample_count = pcm_samples.len(), "Audio decoding complete");
        Ok(pcm_samples)
    }
}

/// WebSocket message types for TTS requests from Claude/supervisor
#[derive(Debug, serde::Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum TtsRequest {
    /// Synthesize text to speech
    Synthesize {
        text: String,
        #[serde(default)]
        stream_sid: Option<String>,
    },
}

/// WebSocket response types for TTS
#[derive(Debug, serde::Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum TtsResponse {
    /// Synthesis started
    SynthesisStarted {
        text: String,
    },
    /// Synthesis completed
    SynthesisComplete {
        text: String,
        duration_ms: u64,
    },
    /// Synthesis failed
    SynthesisError {
        error: String,
    },
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tts_engine_creation() {
        let engine = TtsEngine::new();
        assert!(engine.is_ok());
    }
}
