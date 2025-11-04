// Speech-to-Text (STT) Transcription Module
//
// This module implements real-time speech-to-text transcription using Whisper
// to convert user voice input into text that can be:
// 1. Stored in the semantic memory system
// 2. Processed by Claude Code for Admin users
// 3. Used to provide context to MOSHI
//
// Flow:
// 1. Audio input from voice bridge (μ-law 8kHz from Twilio)
// 2. Resample to Whisper's required format (16kHz PCM)
// 3. Run Whisper transcription (async in background)
// 4. Send transcription to supervisor for:
//    - Memory storage (via MemorySystem)
//    - Claude Code routing (if Admin user)
//    - Context injection (via suggestion_queue)

use anyhow::{Context, Result};
use std::sync::Arc;
use tokio::sync::{mpsc, Mutex};
use tracing::{info, debug, warn, error};
use std::collections::HashMap;
use std::path::PathBuf;
use once_cell::sync::Lazy;

use crate::audio::AudioResampler;

// Whisper model imports (TODO: will be used when implementing actual Whisper API)
// use candle::Device;
// use candle_nn;
// use candle_transformers::models::whisper::{self as m, audio, Config};

/// STT engine configuration
#[derive(Debug, Clone)]
pub struct SttConfig {
    /// Whisper model size ("tiny", "base", "small", "medium", "large")
    pub model_size: String,

    /// Language hint (None = auto-detect)
    pub language: Option<String>,

    /// Enable background transcription
    pub background_transcription: bool,

    /// Minimum audio duration for transcription (ms)
    pub min_audio_duration_ms: u64,

    /// Whisper model path (if using local model)
    pub model_path: Option<String>,
}

impl Default for SttConfig {
    fn default() -> Self {
        Self {
            model_size: "base".to_string(), // Good balance of speed vs accuracy
            language: Some("en".to_string()), // English by default
            background_transcription: true,
            min_audio_duration_ms: 500, // Ignore very short audio
            model_path: None, // Will download from HuggingFace if needed
        }
    }
}

/// STT engine for real-time speech-to-text transcription
pub struct SttEngine {
    config: SttConfig,

    /// Audio resampler for 8kHz → 16kHz conversion (thread-safe)
    upsampler: Arc<Mutex<AudioResampler>>,

    /// Background transcription worker (if enabled)
    worker: Option<TranscriptionWorker>,
}

/// Background worker for async transcription
struct TranscriptionWorker {
    /// Channel to send audio chunks for transcription
    audio_tx: mpsc::UnboundedSender<AudioChunk>,

    /// Channel to receive transcription results
    transcription_rx: Arc<Mutex<mpsc::UnboundedReceiver<TranscriptionResult>>>,

    /// Worker task handle
    task_handle: tokio::task::JoinHandle<()>,
}

/// Audio chunk to be transcribed
#[derive(Debug, Clone)]
pub struct AudioChunk {
    /// PCM audio samples (16kHz, mono)
    pub samples: Vec<f32>,

    /// User ID for this audio
    pub user_id: String,

    /// Session ID (for grouping multiple chunks)
    pub session_id: String,

    /// Timestamp when audio was captured
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

/// Transcription result from Whisper
#[derive(Debug, Clone)]
pub struct TranscriptionResult {
    /// Transcribed text
    pub text: String,

    /// User ID
    pub user_id: String,

    /// Session ID
    pub session_id: String,

    /// Confidence score (0.0-1.0)
    pub confidence: f32,

    /// Language detected
    pub language: Option<String>,

    /// Processing time (ms)
    pub processing_time_ms: u64,

    /// Timestamp of original audio
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

// TODO: Whisper model cache structure - needs candle-transformers 0.9.1 API research
// The exact Model type and loading API differs from documentation.
// This is a placeholder structure that compiles.
type WhisperModelPlaceholder = String;

static WHISPER_MODELS: Lazy<std::sync::RwLock<HashMap<String, Arc<WhisperModelPlaceholder>>>> =
    Lazy::new(|| std::sync::RwLock::new(HashMap::new()));

/// Load Whisper model from cache or download if needed
///
/// TODO: This is a placeholder implementation. The actual candle-transformers 0.9.1
/// Whisper API needs to be researched. The Model type and loading functions differ
/// from the original implementation plan.
async fn load_whisper_model(model_size: &str) -> Result<Arc<WhisperModelPlaceholder>> {
    // 1. Check cache first
    {
        let cache = WHISPER_MODELS.read().unwrap();
        if let Some(model) = cache.get(model_size) {
            info!(model_size, "Whisper model loaded from cache");
            return Ok(model.clone());
        }
    }

    info!(model_size, "Loading Whisper model (not in cache)...");

    // 2. Download model files from HuggingFace if needed
    let _model_dir = download_whisper_model(model_size).await?;

    // TODO: Implement actual model loading once candle-transformers Whisper API is researched
    // Steps needed:
    // 1. Load Config from config.json
    // 2. Load model weights using correct VarBuilder API
    // 3. Create Whisper model instance
    // 4. Return and cache the model

    let placeholder_model = Arc::new(format!("whisper-{}", model_size));

    info!(model_size, "Whisper model placeholder created (needs real implementation)");

    // 5. Cache the placeholder model
    {
        let mut cache = WHISPER_MODELS.write().unwrap();
        cache.insert(model_size.to_string(), placeholder_model.clone());
    }

    Ok(placeholder_model)
}

/// Download Whisper model from HuggingFace Hub
async fn download_whisper_model(model_size: &str) -> Result<PathBuf> {
    info!(model_size, "Downloading Whisper model from HuggingFace...");

    // Use tokio::task::spawn_blocking since hf_hub API is sync
    let model_size_str = model_size.to_string();

    let model_dir = tokio::task::spawn_blocking(move || -> Result<PathBuf> {
        use hf_hub::api::sync::Api;

        let api = Api::new()?;
        let repo = api.model(format!("openai/whisper-{}", model_size_str));

        // Download required model files
        let config_path = repo.get("config.json")?;
        let weights_path = repo.get("model.safetensors")?;

        // Get the directory containing the model files
        let model_dir = config_path.parent()
            .context("Failed to get model directory")?
            .to_path_buf();

        info!(
            model_size = %model_size_str,
            ?model_dir,
            "Whisper model downloaded from HuggingFace"
        );

        // Verify both files exist
        if !weights_path.exists() {
            anyhow::bail!("Model weights not found after download");
        }

        Ok(model_dir)
    })
    .await
    .context("Model download task failed")??;

    Ok(model_dir)
}

impl SttEngine {
    /// Create a new STT engine with default configuration
    pub fn new() -> Result<Self> {
        Self::with_config(SttConfig::default())
    }

    /// Create a new STT engine with custom configuration
    pub fn with_config(config: SttConfig) -> Result<Self> {
        info!(
            model_size = %config.model_size,
            language = ?config.language,
            background = config.background_transcription,
            "Initializing STT engine"
        );

        // Create upsampler for converting Twilio 8kHz to Whisper 16kHz
        let upsampler = AudioResampler::new(8000, 16000, 960) // 960 samples = 120ms at 8kHz
            .context("Failed to create STT upsampler")?;

        // Wrap in Arc<Mutex<>> for thread-safe sharing
        let upsampler = Arc::new(Mutex::new(upsampler));

        // Create background worker if enabled
        let worker = if config.background_transcription {
            Some(Self::create_worker(config.clone())?)
        } else {
            None
        };

        Ok(Self {
            config,
            upsampler,
            worker,
        })
    }

    /// Create background transcription worker
    fn create_worker(config: SttConfig) -> Result<TranscriptionWorker> {
        let (audio_tx, mut audio_rx) = mpsc::unbounded_channel::<AudioChunk>();
        let (transcription_tx, transcription_rx) = mpsc::unbounded_channel::<TranscriptionResult>();

        // Spawn background task for transcription
        let task_handle = tokio::spawn(async move {
            info!("STT background worker started");

            while let Some(chunk) = audio_rx.recv().await {
                debug!(
                    user_id = %chunk.user_id,
                    session_id = %chunk.session_id,
                    samples = chunk.samples.len(),
                    "Transcribing audio chunk"
                );

                let start_time = std::time::Instant::now();

                // TODO: Implement actual Whisper transcription
                // For now, return placeholder
                match Self::transcribe_with_whisper(&chunk, &config).await {
                    Ok(text) => {
                        let processing_time_ms = start_time.elapsed().as_millis() as u64;

                        let result = TranscriptionResult {
                            text,
                            user_id: chunk.user_id,
                            session_id: chunk.session_id,
                            confidence: 0.95, // Placeholder
                            language: config.language.clone(),
                            processing_time_ms,
                            timestamp: chunk.timestamp,
                        };

                        if transcription_tx.send(result).is_err() {
                            warn!("Failed to send transcription result - receiver dropped");
                            break;
                        }
                    }
                    Err(e) => {
                        error!(error = ?e, "Transcription failed");
                    }
                }
            }

            info!("STT background worker stopped");
        });

        Ok(TranscriptionWorker {
            audio_tx,
            transcription_rx: Arc::new(Mutex::new(transcription_rx)),
            task_handle,
        })
    }

    /// Transcribe audio chunk using Whisper (async)
    ///
    /// This is called from the background worker task.
    ///
    /// TODO: This is a placeholder implementation. The actual Whisper inference
    /// needs to be implemented once the candle-transformers 0.9.1 API is researched.
    async fn transcribe_with_whisper(
        chunk: &AudioChunk,
        config: &SttConfig,
    ) -> Result<String> {
        info!(
            model = %config.model_size,
            samples = chunk.samples.len(),
            user_id = %chunk.user_id,
            session_id = %chunk.session_id,
            "Starting Whisper transcription"
        );

        // 1. Load Whisper model (with caching)
        let _model = load_whisper_model(&config.model_size).await?;

        info!(
            model = %config.model_size,
            "Whisper model loaded successfully"
        );

        // TODO: Implement actual Whisper inference once API is researched
        // Steps needed:
        // 2. Prepare audio tensor from chunk.samples (16kHz, mono, f32)
        //    - Convert Vec<f32> to candle Tensor
        //    - Normalize audio if needed
        //    - Pad or chunk to Whisper's expected length (30s = 480,000 samples @ 16kHz)
        //
        // 3. Convert audio to mel spectrogram
        //    - Use Whisper's mel filter bank
        //    - Apply FFT and mel filtering
        //
        // 4. Run Whisper encoder
        //    - Pass mel spectrogram through encoder
        //    - Get encoder output features
        //
        // 5. Run Whisper decoder
        //    - Initialize decoder with language token
        //    - Decode tokens autoregressively
        //    - Apply beam search or greedy decoding
        //
        // 6. Convert tokens to text
        //    - Use Whisper's tokenizer to decode token IDs
        //    - Return transcribed text

        // Placeholder transcription for testing
        let placeholder_text = format!(
            "[PLACEHOLDER TRANSCRIPTION - {} samples from user {} in session {}]",
            chunk.samples.len(),
            chunk.user_id,
            chunk.session_id
        );

        info!(
            text_len = placeholder_text.len(),
            "Whisper transcription complete (placeholder)"
        );

        Ok(placeholder_text)
    }

    /// Submit audio for background transcription
    ///
    /// Audio is queued for transcription and processed asynchronously.
    /// Results can be retrieved via `get_transcription()`.
    pub async fn submit_audio(
        &self,
        audio: &[u8], // μ-law audio from Twilio (8kHz)
        user_id: String,
        session_id: String,
    ) -> Result<()> {
        if let Some(worker) = &self.worker {
            // Convert μ-law to PCM
            let pcm_8khz = Self::mulaw_to_pcm(audio)?;

            // Upsample to 16kHz for Whisper (using locked upsampler)
            let pcm_16khz = {
                let mut upsampler = self.upsampler.lock().await;
                let mut output = Vec::new();

                for chunk in pcm_8khz.chunks(960) {
                    let resampled = upsampler.resample(chunk)?;
                    output.extend_from_slice(&resampled);
                }

                output
            }; // Lock dropped here

            // Create audio chunk
            let chunk = AudioChunk {
                samples: pcm_16khz,
                user_id,
                session_id,
                timestamp: chrono::Utc::now(),
            };

            // Submit to worker
            worker.audio_tx.send(chunk)
                .context("Failed to submit audio to STT worker")?;

            Ok(())
        } else {
            anyhow::bail!("Background transcription not enabled")
        }
    }

    /// Try to get a transcription result (non-blocking)
    ///
    /// Returns None if no transcription is ready yet.
    pub async fn get_transcription(&self) -> Result<Option<TranscriptionResult>> {
        if let Some(worker) = &self.worker {
            let mut rx = worker.transcription_rx.lock().await;
            Ok(rx.try_recv().ok())
        } else {
            anyhow::bail!("Background transcription not enabled")
        }
    }

    /// Transcribe audio synchronously (blocking)
    ///
    /// This is useful for one-off transcriptions without background processing.
    pub async fn transcribe_sync(
        &self,
        audio: &[u8], // μ-law audio from Twilio (8kHz)
    ) -> Result<String> {
        // Convert μ-law to PCM
        let pcm_8khz = Self::mulaw_to_pcm(audio)?;

        // Upsample to 16kHz for Whisper (using locked upsampler)
        let pcm_16khz = {
            let mut upsampler = self.upsampler.lock().await;
            let mut output = Vec::new();

            for chunk in pcm_8khz.chunks(960) {
                let resampled = upsampler.resample(chunk)?;
                output.extend_from_slice(&resampled);
            }

            output
        }; // Lock dropped here

        // Create temporary chunk
        let chunk = AudioChunk {
            samples: pcm_16khz,
            user_id: "sync".to_string(),
            session_id: "sync".to_string(),
            timestamp: chrono::Utc::now(),
        };

        // Run Whisper transcription
        Self::transcribe_with_whisper(&chunk, &self.config).await
    }

    /// Convert μ-law audio to PCM f32
    fn mulaw_to_pcm(mulaw: &[u8]) -> Result<Vec<f32>> {
        // Use audio module's mulaw_to_pcm which returns Vec<i16>
        let pcm_i16 = crate::audio::mulaw_to_pcm(mulaw);

        // Convert i16 to f32 (normalize to -1.0 to 1.0)
        let pcm_f32 = pcm_i16.iter()
            .map(|&sample| sample as f32 / 32768.0)
            .collect();

        Ok(pcm_f32)
    }
}

impl Drop for SttEngine {
    fn drop(&mut self) {
        if let Some(worker) = &self.worker {
            info!("Shutting down STT background worker");
            worker.task_handle.abort();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_stt_engine_creation() {
        let engine = SttEngine::new();
        assert!(engine.is_ok());
    }

    #[test]
    fn test_stt_config_default() {
        let config = SttConfig::default();
        assert_eq!(config.model_size, "base");
        assert_eq!(config.language, Some("en".to_string()));
        assert!(config.background_transcription);
        assert_eq!(config.min_audio_duration_ms, 500);
    }

    #[test]
    fn test_mulaw_to_pcm() {
        let mulaw = vec![0xFF, 0x00, 0x7F];
        let pcm = SttEngine::mulaw_to_pcm(&mulaw);
        assert!(pcm.is_ok());
        assert_eq!(pcm.unwrap().len(), 3);
    }
}
