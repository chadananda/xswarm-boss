// Voice Integration Module - MOSHI Real-Time Voice AI
//
// This module integrates Kyutai's MOSHI voice model for real-time
// phone conversations through Twilio Media Streams.
//
// Architecture:
// - Receives μ-law 8kHz audio from Twilio via WebSocket
// - Converts to PCM 24kHz for MOSHI processing
// - Generates voice responses using MOSHI
// - Converts back to μ-law 8kHz for Twilio
//
// The voice bridge runs locally and receives connections from
// Cloudflare Workers that proxy Twilio Media Streams.

use anyhow::{Context, Result};
use std::sync::Arc;
use std::collections::VecDeque;
use std::time::Duration;
use tokio::sync::{RwLock, Mutex, mpsc};
use tokio::net::TcpStream;
use tokio_tungstenite::{accept_async, tungstenite::Message as WsMessage};
use futures_util::{StreamExt, SinkExt};
use tracing::{info, warn, error, debug};
use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};

use crate::audio::{self, AudioResampler};
use crate::audio_output::AudioOutputDevice;
use crate::moshi_personality::{MoshiPersonality, PersonalityManager};
use crate::ConversationMemory;

// Wake word module - inline stub to avoid module import issues
// The full implementation is in the wake_word module
mod wake_word {
    use anyhow::Result;
    use serde::{Deserialize, Serialize};
    use std::sync::Arc;
    use tokio::sync::RwLock;

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct WakeWordConfig {
        pub enabled: bool,
        pub sensitivity: f32,
        pub threshold: f32,
        pub keywords: Vec<String>,
    }

    impl Default for WakeWordConfig {
        fn default() -> Self {
            Self {
                enabled: false,
                sensitivity: 0.5,
                threshold: 0.5,
                keywords: vec!["hey_hal".to_string()],
            }
        }
    }

    pub struct WakeWordSystem {
        _config: Arc<RwLock<WakeWordConfig>>,
    }

    impl WakeWordSystem {
        pub async fn new(config: WakeWordConfig) -> Result<Self> {
            Ok(Self {
                _config: Arc::new(RwLock::new(config)),
            })
        }

        pub async fn start_listening(&self) -> Result<()> {
            tracing::warn!("Wake word system stub - not fully implemented in voice.rs");
            Ok(())
        }

        pub async fn stop_listening(&self) -> Result<()> {
            Ok(())
        }
    }
}

use wake_word::{WakeWordSystem, WakeWordConfig};

// Audio format constants
const TWILIO_SAMPLE_RATE: u32 = 8000;  // Twilio Media Streams (μ-law)
const MOSHI_SAMPLE_RATE: u32 = 24000;  // MOSHI native sample rate
const MIMI_NUM_CODEBOOKS: usize = 32;   // MOSHI codec configuration (32 = full quality 4.4kbps, 8 = low quality 1.1kbps)

/// Twilio Media Stream protocol message types
#[derive(Debug, serde::Deserialize)]
#[serde(tag = "event")]
#[serde(rename_all = "lowercase")]
enum TwilioEvent {
    Connected {
        protocol: String,
        version: String,
    },
    Start {
        #[serde(rename = "streamSid")]
        stream_sid: String,
        #[serde(rename = "customParameters")]
        custom_parameters: Option<serde_json::Value>,
    },
    Media {
        #[serde(rename = "streamSid")]
        stream_sid: String,
        media: MediaPayload,
    },
    Stop {
        #[serde(rename = "streamSid")]
        stream_sid: String,
    },
}

#[derive(Debug, serde::Deserialize)]
struct MediaPayload {
    track: String,
    chunk: String,
    timestamp: String,
    payload: String, // base64 encoded μ-law audio
}

#[derive(Debug, serde::Serialize)]
struct TwilioMediaResponse {
    event: String,
    #[serde(rename = "streamSid")]
    stream_sid: String,
    media: MediaResponsePayload,
}

#[derive(Debug, serde::Serialize)]
struct MediaResponsePayload {
    payload: String, // base64 encoded μ-law audio
}

/// Configuration for MOSHI voice model
#[derive(Debug, Clone)]
pub struct VoiceConfig {
    /// Hugging Face model repository
    pub hf_repo: String,
    /// Path to language model file (auto-downloaded if not present)
    pub lm_model_file: String,
    /// Path to MIMI codec model file (auto-downloaded if not present)
    pub mimi_model_file: String,
    /// Path to text tokenizer file (auto-downloaded if not present)
    pub text_tokenizer_file: String,
    /// Use CPU instead of GPU (slower but portable)
    pub use_cpu: bool,
    /// Use CPU for MIMI codec (can reduce VRAM usage)
    pub use_cpu_for_mimi: bool,
    /// WebSocket server host
    pub host: String,
    /// WebSocket server port
    pub port: u16,
}

impl Default for VoiceConfig {
    fn default() -> Self {
        // Use local cached model files to avoid slow downloads
        let home = std::env::var("HOME").unwrap_or_else(|_| "/Users/chad".to_string());
        let lm_snapshot_path = format!(
            "{}/.cache/huggingface/hub/models--kyutai--moshika-candle-q8/snapshots/4b4a873fc1d3b92ce32b3ae91ff8e95bbb62193f",
            home
        );
        let lm_model_path = format!("{}/model.q8.gguf", lm_snapshot_path);
        // MIMI codec is bundled with the Moshi model in the same repository
        let mimi_model_path = format!("{}/tokenizer-e351c8d8-checkpoint125.safetensors", lm_snapshot_path);
        let tokenizer_path = format!("{}/tokenizer_spm_32k_3.model", lm_snapshot_path);

        Self {
            hf_repo: "kyutai/moshika-candle-q8".to_string(),
            lm_model_file: lm_model_path,
            mimi_model_file: mimi_model_path,
            text_tokenizer_file: tokenizer_path,
            use_cpu: false,
            use_cpu_for_mimi: false,
            host: "127.0.0.1".to_string(),
            port: 9998,
        }
    }
}

/// MOSHI voice model state
pub struct MoshiState {
    pub(crate) lm_model: moshi::lm::LmModel,
    pub(crate) mimi_model: moshi::mimi::Mimi,
    pub(crate) text_tokenizer: sentencepiece::SentencePieceProcessor,
    pub(crate) device: candle::Device,
    pub(crate) config: VoiceConfig,
    /// Language model generation configuration
    pub(crate) lm_config: moshi::lm_generate_multistream::Config,
    /// Queue for injecting text suggestions into MOSHI's inference
    /// Used by supervisor to inject RAG context, tool results, etc.
    pub suggestion_queue: Arc<Mutex<VecDeque<String>>>,
    /// Connected supervisor clients for broadcasting transcriptions
    /// Each client has a channel sender for real-time events
    pub supervisor_clients: Arc<Mutex<Vec<tokio::sync::mpsc::UnboundedSender<crate::supervisor::SupervisorEvent>>>>,
    /// Broadcast channel for AI audio output amplitude (for visualizer)
    /// Sends RMS amplitude values when MOSHI generates audio
    pub audio_amplitude_tx: Arc<RwLock<Option<mpsc::UnboundedSender<f32>>>>,
    /// Personality manager for assistant behavior
    pub personality_manager: Arc<PersonalityManager>,
    /// Conversation memory for maintaining context
    pub conversation_memory: Arc<ConversationMemory>,
    /// Memory conditioner for natural memory incorporation into MOSHI
    pub memory_conditioner: crate::memory_conditioner::MemoryConditioner,
}

impl MoshiState {
    /// Initialize MOSHI models
    pub fn new(config: VoiceConfig) -> Result<Self> {
        info!("Initializing MOSHI voice models...");

        // Select device (Metal on macOS, CUDA on NVIDIA, CPU fallback)
        let device = Self::select_device(config.use_cpu)?;
        info!(?device, "Selected compute device");

        // Set data type based on device
        let dtype = if device.is_cuda() {
            candle::DType::BF16
        } else {
            candle::DType::F32
        };

        // Load language model
        info!(model_file = %config.lm_model_file, "Loading language model");
        let lm_model = moshi::lm::load_streaming(&config.lm_model_file, dtype, &device)
            .context("Failed to load language model")?;

        // CRITICAL DEBUG: Verify depformer exists for audio generation
        let generated_codebooks = lm_model.generated_audio_codebooks();
        if generated_codebooks == 0 {
            anyhow::bail!(
                "CRITICAL: Language model has no depformer! Generated codebooks = {}. \
                This means the model cannot generate audio tokens for voice responses. \
                Check if the GGUF model file contains depformer weights.",
                generated_codebooks
            );
        }
        info!(
            generated_audio_codebooks = generated_codebooks,
            "Language model loaded with depformer for audio generation"
        );

        // Load MIMI codec
        let mimi_device = if config.use_cpu_for_mimi {
            &candle::Device::Cpu
        } else {
            &device
        };
        info!(model_file = %config.mimi_model_file, "Loading MIMI codec");
        let mimi_model = moshi::mimi::load(
            &config.mimi_model_file,
            Some(MIMI_NUM_CODEBOOKS),
            mimi_device,
        )
        .context("Failed to load MIMI codec")?;

        // Load text tokenizer
        info!(tokenizer_file = %config.text_tokenizer_file, "Loading text tokenizer");
        let text_tokenizer = sentencepiece::SentencePieceProcessor::open(&config.text_tokenizer_file)
            .context("Failed to load text tokenizer")?;

        // Warm up models
        Self::warmup(&mut lm_model.clone(), &mut mimi_model.clone(), &device, mimi_device)?;

        // Initialize language model generation config
        let lm_config = moshi::lm_generate_multistream::Config::v0_1();

        // Initialize personality manager with Jarvis personality by default
        let personality_manager = Arc::new(PersonalityManager::new());

        // Initialize conversation memory for context tracking
        let conversation_memory = Arc::new(ConversationMemory::new());

        info!("MOSHI models initialized successfully");
        info!("Personality manager initialized with Jarvis personality");
        info!("Conversation memory initialized for context tracking");

        // Initialize memory conditioner for natural memory incorporation
        let memory_conditioner = crate::memory_conditioner::MemoryConditioner::new();

        Ok(Self {
            lm_model,
            mimi_model,
            text_tokenizer,
            device,
            config,
            lm_config,
            suggestion_queue: Arc::new(Mutex::new(VecDeque::new())),
            supervisor_clients: Arc::new(Mutex::new(Vec::new())),
            audio_amplitude_tx: Arc::new(RwLock::new(None)),
            personality_manager,
            conversation_memory,
            memory_conditioner,
        })
    }

    /// Set the audio amplitude broadcast channel
    /// This allows external components (like the dashboard) to receive real-time amplitude data
    pub async fn set_amplitude_channel(&self, tx: mpsc::UnboundedSender<f32>) {
        let mut amplitude_tx = self.audio_amplitude_tx.write().await;
        *amplitude_tx = Some(tx);
        info!("Audio amplitude channel connected for visualizer");
    }

    /// Broadcast audio amplitude to visualizer
    /// Called whenever MOSHI generates audio output
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
            let _ = tx.send(rms); // Ignore errors if channel is closed
        }
    }

    /// Broadcast transcription to all connected supervisor clients
    pub async fn broadcast_transcription(&self, text: &str) {
        let event = crate::supervisor::SupervisorEvent::UserTranscription {
            text: text.to_string(),
            timestamp: chrono::Utc::now().to_rfc3339(),
        };

        // Get list of clients and send event to each
        let mut clients = self.supervisor_clients.lock().await;
        let mut disconnected_indices = Vec::new();

        for (index, client) in clients.iter().enumerate() {
            if client.send(event.clone()).is_err() {
                // Client disconnected - mark for removal
                disconnected_indices.push(index);
                debug!(index, "Supervisor client disconnected during broadcast");
            }
        }

        // Remove disconnected clients (iterate in reverse to maintain indices)
        for index in disconnected_indices.into_iter().rev() {
            clients.remove(index);
        }

        debug!(
            client_count = clients.len(),
            transcription = %text,
            "Broadcasted transcription to supervisor clients"
        );
    }

    /// Select appropriate compute device
    fn select_device(use_cpu: bool) -> Result<candle::Device> {
        use candle::Device;

        if use_cpu {
            return Ok(Device::Cpu);
        }

        if candle::utils::cuda_is_available() {
            info!("CUDA is available, using GPU");
            Ok(Device::new_cuda(0)?)
        } else if candle::utils::metal_is_available() {
            info!("Metal is available, using Apple Silicon GPU");
            Ok(Device::new_metal(0)?)
        } else {
            warn!("No GPU acceleration available, falling back to CPU");
            Ok(Device::Cpu)
        }
    }

    /// Warm up models with dummy data
    fn warmup(
        lm_model: &mut moshi::lm::LmModel,
        mimi_model: &mut moshi::mimi::Mimi,
        device: &candle::Device,
        mimi_device: &candle::Device,
    ) -> Result<()> {
        info!("Warming up models...");

        // Warm up language model
        let (_v, ys) = lm_model.forward(None, vec![None; MIMI_NUM_CODEBOOKS], &().into())?;
        let mut lp = candle_transformers::generation::LogitsProcessor::new(123, None, None);
        let _ = lm_model.depformer_sample(&ys, None, &[], &mut lp)?;

        // Warm up MIMI codec
        let config = mimi_model.config();
        let frame_length = (config.sample_rate / config.frame_rate).ceil() as usize;
        let fake_pcm = candle::Tensor::zeros((1, 1, frame_length), candle::DType::F32, mimi_device)?;
        let codes = mimi_model.encode_step(&fake_pcm.into(), &().into())?;
        let ys = mimi_model.decode_step(&codes, &().into())?;

        if ys.as_option().is_none() {
            anyhow::bail!("MIMI codec warmup failed - no output generated");
        }

        device.synchronize()?;
        info!("Models warmed up and ready");

        Ok(())
    }
}

/// Per-connection state for language model inference
struct ConnectionState {
    /// Language model generator (stateful, per-connection)
    lm_generator: moshi::lm_generate_multistream::State,
    /// Previous text token for incremental decoding
    prev_text_token: u32,
    /// Audio buffer to accumulate chunks before processing
    audio_buffer: Vec<f32>,
    /// Upsampler: 8kHz → 24kHz
    upsampler: AudioResampler,
    /// Downsampler: 24kHz → 8kHz
    downsampler: AudioResampler,
}

impl ConnectionState {
    /// Create new connection state with initialized LM generator
    fn new(
        moshi_state: &MoshiState,
        max_steps: usize,
    ) -> Result<Self> {
        // Create logits processors for sampling
        let audio_logits_processor = candle_transformers::generation::LogitsProcessor::new(
            299792458, // Random seed
            Some(0.8),  // Temperature for audio tokens
            None,       // Top-p (disabled)
        );

        let text_logits_processor = candle_transformers::generation::LogitsProcessor::new(
            299792458, // Same seed
            Some(0.8),  // Temperature for text tokens
            None,       // Top-p (disabled)
        );

        // Create LM generator state
        // State::new signature: (lm_model, max_steps, audio_lp, text_lp, pad_mult, repetition_penalty, ca_src, config)
        let lm_generator = moshi::lm_generate_multistream::State::new(
            moshi_state.lm_model.clone(),
            max_steps,
            audio_logits_processor,
            text_logits_processor,
            None,       // pad_mult
            None,       // repetition_penalty
            None,       // ca_src (cross-attention source)
            moshi_state.lm_config.clone(),
        );

        // Initialize with start token
        let prev_text_token = moshi_state.lm_config.text_start_token;

        // Create audio resamplers
        let upsampler = AudioResampler::new(8000, 24000, 160)
            .context("Failed to create upsampler")?;
        let downsampler = AudioResampler::new(24000, 8000, 1920)
            .context("Failed to create downsampler")?;

        Ok(Self {
            lm_generator,
            prev_text_token,
            audio_buffer: Vec::with_capacity(1920),
            upsampler,
            downsampler,
        })
    }
}

/// Voice bridge for Twilio Media Streams integration
pub struct VoiceBridge {
    state: Arc<RwLock<MoshiState>>,
    config: VoiceConfig,
    wake_word_system: Option<Arc<WakeWordSystem>>,
}

impl VoiceBridge {
    /// Create a new voice bridge
    pub async fn new(config: VoiceConfig) -> Result<Self> {
        // Download models from Hugging Face if needed
        let config = Self::download_models_if_needed(config).await?;

        // Initialize MOSHI state
        let state = MoshiState::new(config.clone())?;

        Ok(Self {
            state: Arc::new(RwLock::new(state)),
            config,
            wake_word_system: None,
        })
    }

    /// Create a new voice bridge with wake word detection
    pub async fn new_with_wake_word(config: VoiceConfig, wake_word_config: WakeWordConfig) -> Result<Self> {
        // Create voice bridge first
        let mut bridge = Self::new(config).await?;

        // Initialize wake word system
        let wake_word_system = WakeWordSystem::new(wake_word_config).await?;

        // Start wake word detection
        wake_word_system.start_listening().await?;

        bridge.wake_word_system = Some(Arc::new(wake_word_system));

        info!("Voice bridge created with wake word detection enabled");

        Ok(bridge)
    }

    /// Handle wake word detection
    async fn handle_wake_word_detection(&self, keyword: String) -> Result<()> {
        info!("Wake word detected: {}", keyword);

        // Activate voice processing mode
        self.activate_voice_mode().await?;

        // Play acknowledgment sound (optional)
        self.play_activation_sound().await?;

        // Start listening for command
        self.start_command_listening().await?;

        Ok(())
    }

    /// Activate voice mode after wake word detection
    async fn activate_voice_mode(&self) -> Result<()> {
        // Switch from wake word detection to full voice processing
        // Temporarily disable wake word to prevent false triggers
        if let Some(wake_word) = &self.wake_word_system {
            wake_word.stop_listening().await?;
        }

        info!("Voice mode activated");
        Ok(())
    }

    /// Play activation sound to acknowledge wake word
    async fn play_activation_sound(&self) -> Result<()> {
        // Play subtle audio cue that system is listening
        // TODO: Implement audio feedback (optional)
        debug!("Playing activation sound");
        Ok(())
    }

    /// Start listening for voice commands
    async fn start_command_listening(&self) -> Result<()> {
        // Start full voice processing with MOSHI
        info!("Listening for voice commands...");
        // The actual command processing happens through the Twilio stream
        Ok(())
    }

    /// Deactivate voice mode and resume wake word detection
    pub async fn deactivate_voice_mode(&self) -> Result<()> {
        info!("Deactivating voice mode");

        // Resume wake word detection
        if let Some(wake_word) = &self.wake_word_system {
            wake_word.start_listening().await?;
        }

        Ok(())
    }

    /// Get wake word system reference
    pub fn get_wake_word_system(&self) -> Option<Arc<WakeWordSystem>> {
        self.wake_word_system.clone()
    }

    /// Start local voice conversation loop (microphone → MOSHI → speakers)
    /// This is the MISSING PIECE that connects local audio to MOSHI processing
    ///
    /// # Arguments
    /// * `audio_rx` - Receiver for microphone audio frames from LocalAudioSystem
    /// * `playback_tx` - Sender for speaker output to LocalAudioSystem
    ///
    /// # Returns
    /// A task handle that runs the conversation loop
    pub async fn start_local_conversation(
        self: Arc<Self>,
        mut audio_rx: mpsc::UnboundedReceiver<crate::local_audio::AudioFrame>,
        playback_tx: mpsc::UnboundedSender<Vec<f32>>,
    ) -> Result<tokio::task::JoinHandle<()>> {
        info!("Starting local voice conversation loop (microphone → MOSHI → speakers)");

        // Create per-connection state with LM generator
        let moshi_state = self.state.read().await;
        let max_steps = 10000; // Maximum inference steps
        let mut conn_state = ConnectionState::new(&moshi_state, max_steps)
            .context("Failed to create connection state")?;
        drop(moshi_state); // Release lock

        const MOSHI_FRAME_SIZE: usize = 1920; // 80ms at 24kHz

        // Spawn conversation loop task
        let handle = tokio::spawn(async move {
            info!("Local conversation loop started - listening for voice input");
            info!("AUDIO_PIPELINE: Conversation loop initialized, waiting for microphone frames");

            let mut audio_buffer: Vec<f32> = Vec::with_capacity(MOSHI_FRAME_SIZE * 2);
            let mut frame_count = 0u64;

            while let Some(audio_frame) = audio_rx.recv().await {
                frame_count += 1;

                // CRITICAL: Log EVERY received frame to verify microphone connection
                info!(
                    "AUDIO_PIPELINE: [Frame #{}] Received from microphone - samples={}",
                    frame_count,
                    audio_frame.samples.len()
                );

                // Verify audio data is valid (non-zero)
                let non_zero_count = audio_frame.samples.iter().filter(|&&s| s.abs() > 0.001).count();
                let rms = if audio_frame.samples.is_empty() {
                    0.0
                } else {
                    let sum: f32 = audio_frame.samples.iter().map(|&s| s * s).sum();
                    (sum / audio_frame.samples.len() as f32).sqrt()
                };

                info!(
                    "AUDIO_PIPELINE: [Frame #{}] Audio data - non_zero_samples={}/{}, rms={:.6}",
                    frame_count,
                    non_zero_count,
                    audio_frame.samples.len(),
                    rms
                );

                // Add microphone samples to buffer
                audio_buffer.extend_from_slice(&audio_frame.samples);

                info!(
                    "AUDIO_PIPELINE: [Frame #{}] Added to buffer - buffer_size={}, MOSHI_FRAME_SIZE={}, ready={}",
                    frame_count,
                    audio_buffer.len(),
                    MOSHI_FRAME_SIZE,
                    audio_buffer.len() >= MOSHI_FRAME_SIZE
                );

                // Process when we have a full MOSHI frame (1920 samples = 80ms at 24kHz)
                while audio_buffer.len() >= MOSHI_FRAME_SIZE {
                    // Extract exactly one frame
                    let frame: Vec<f32> = audio_buffer.drain(..MOSHI_FRAME_SIZE).collect();

                    info!(
                        "AUDIO_PIPELINE: [Frame #{}] MOSHI frame ready - extracted {} samples, {} remaining in buffer",
                        frame_count,
                        frame.len(),
                        audio_buffer.len()
                    );

                    debug!(
                        frame_size = frame.len(),
                        remaining = audio_buffer.len(),
                        "Processing MOSHI frame from microphone"
                    );

                    // Calculate frame RMS before processing
                    let frame_rms = if frame.is_empty() {
                        0.0
                    } else {
                        let sum: f32 = frame.iter().map(|&s| s * s).sum();
                        (sum / frame.len() as f32).sqrt()
                    };

                    info!(
                        "AUDIO_PIPELINE: [Frame #{}] CALLING process_with_lm() - frame_size={}, frame_rms={:.6}",
                        frame_count,
                        frame.len(),
                        frame_rms
                    );

                    // Process through MOSHI with LM
                    match self.process_with_lm(&mut conn_state, frame).await {
                        Ok(response_pcm) => {
                            info!(
                                "AUDIO_PIPELINE: [Frame #{}] process_with_lm() SUCCESS - response_samples={}",
                                frame_count,
                                response_pcm.len()
                            );

                            // Send MOSHI's voice response to speakers
                            if let Err(e) = playback_tx.send(response_pcm.clone()) {
                                error!("AUDIO_PIPELINE: [Frame #{}] Failed to send audio to speakers: {}", frame_count, e);
                                // Channel closed - conversation ended
                                break;
                            }
                            info!(
                                "AUDIO_PIPELINE: [Frame #{}] Response sent to speakers - samples={}",
                                frame_count,
                                response_pcm.len()
                            );
                            debug!(
                                response_samples = response_pcm.len(),
                                "MOSHI response sent to speakers"
                            );
                        }
                        Err(e) => {
                            error!("AUDIO_PIPELINE: [Frame #{}] process_with_lm() FAILED: {}", frame_count, e);
                            error!("MOSHI processing failed: {}", e);
                            // Continue processing even if one frame fails
                        }
                    }
                }
            }

            info!("Local conversation loop ended");
        });

        info!("Local conversation loop task spawned successfully");
        Ok(handle)
    }

    /// Get shared reference to MOSHI state for supervisor integration
    pub fn get_moshi_state(&self) -> Arc<RwLock<MoshiState>> {
        self.state.clone()
    }

    /// Connect an amplitude channel for real-time audio visualization
    /// Returns a receiver that will get RMS amplitude values when MOSHI generates audio
    pub async fn connect_amplitude_channel(&self) -> mpsc::UnboundedReceiver<f32> {
        let (tx, rx) = mpsc::unbounded_channel();
        let state = self.state.read().await;
        state.set_amplitude_channel(tx).await;
        info!("Amplitude channel created for audio visualizer");
        rx
    }

    /// Get personality manager for customization
    pub async fn get_personality_manager(&self) -> Arc<PersonalityManager> {
        let state = self.state.read().await;
        state.personality_manager.clone()
    }

    /// Get conversation memory for accessing conversation history
    pub async fn get_conversation_memory(&self) -> Arc<ConversationMemory> {
        let state = self.state.read().await;
        state.conversation_memory.clone()
    }

    /// Add a user message to conversation memory
    pub async fn add_user_message(&self, content: String) -> Result<String> {
        let state = self.state.read().await;
        state.conversation_memory.add_user_message(content).await
    }

    /// Add an assistant response to conversation memory
    pub async fn add_assistant_response(&self, content: String) -> Result<String> {
        let state = self.state.read().await;
        state.conversation_memory.add_assistant_response(content).await
    }

    /// Get conversation context for MOSHI prompt injection
    pub async fn get_conversation_context(&self, max_messages: usize) -> String {
        let state = self.state.read().await;
        state.conversation_memory.get_context_for_prompt(max_messages).await
    }

    /// Start a new conversation session
    pub async fn start_new_conversation_session(&self) -> String {
        let state = self.state.read().await;
        state.conversation_memory.start_new_session().await
    }

    /// Set personality for MOSHI assistant
    pub async fn set_personality(&self, personality: MoshiPersonality) -> Result<()> {
        let state = self.state.read().await;
        state.personality_manager.set_personality(personality).await;
        info!("MOSHI personality updated successfully");
        Ok(())
    }

    /// Get current personality configuration
    pub async fn get_personality(&self) -> MoshiPersonality {
        let state = self.state.read().await;
        state.personality_manager.get_personality().await
    }

    /// Generate a greeting based on current personality
    pub async fn generate_personality_greeting(&self) -> String {
        let state = self.state.read().await;
        state.personality_manager.generate_greeting().await
    }

    /// Get personality context prompt for conversation initialization
    pub async fn get_personality_context(&self) -> String {
        let state = self.state.read().await;
        state.personality_manager.generate_context_prompt().await
    }

    /// Inject personality context into conversation
    /// This should be called at the start of a conversation to guide MOSHI's behavior
    pub async fn inject_personality_context(&self) -> Result<()> {
        let context = self.get_personality_context().await;
        let moshi_state = self.state.read().await;

        // Add personality context to suggestion queue
        // This will influence MOSHI's initial responses
        let mut queue = moshi_state.suggestion_queue.lock().await;
        queue.push_back(context.clone());

        info!("Injected personality context into MOSHI conversation");
        debug!("Personality context: {}", context);

        Ok(())
    }

    /// Inject conversation context into MOSHI's suggestion queue
    /// This maintains conversation continuity by providing recent history
    pub async fn inject_conversation_context(&self, max_messages: usize) -> Result<()> {
        let context = self.get_conversation_context(max_messages).await;

        if context.is_empty() {
            debug!("No conversation context to inject");
            return Ok(());
        }

        let moshi_state = self.state.read().await;
        let mut queue = moshi_state.suggestion_queue.lock().await;
        queue.push_back(context.clone());

        info!("Injected conversation context into MOSHI ({} recent messages)", max_messages);
        debug!("Conversation context: {}", context);

        Ok(())
    }

    /// Generate personality-aware response prefix for user input
    /// Returns a suggested response prefix based on personality traits
    pub async fn generate_response_prefix(&self, user_input: &str) -> Option<String> {
        let personality = self.get_personality().await;
        personality.generate_response_prefix(user_input)
    }

    /// Download MOSHI models from Hugging Face if not present locally
    pub async fn download_models_if_needed(mut config: VoiceConfig) -> Result<VoiceConfig> {
        use std::path::Path;

        // Check if all model files exist
        let all_exist = [&config.lm_model_file, &config.mimi_model_file, &config.text_tokenizer_file]
            .iter()
            .all(|f| {
                let exists = Path::new(f).exists();
                if !exists {
                    info!(file = %f, "File not found");
                }
                exists
            });

        if all_exist {
            info!("All model files found locally, skipping download");
            return Ok(config);
        }

        info!(repo = %config.hf_repo, "Downloading models from Hugging Face");

        let api = hf_hub::api::tokio::ApiBuilder::from_env().build()?;
        let repo = api.model(config.hf_repo.clone());

        // Download each file
        for file_path in [
            &mut config.lm_model_file,
            &mut config.mimi_model_file,
            &mut config.text_tokenizer_file,
        ] {
            let filename = Path::new(&**file_path)
                .file_name()
                .and_then(|f| f.to_str())
                .ok_or_else(|| anyhow::anyhow!("Invalid filename: {}", file_path))?;

            info!(file = %filename, "Downloading from Hugging Face");
            let downloaded_path = repo
                .get(filename)
                .await
                .with_context(|| format!("Failed to download {}", filename))?;

            *file_path = downloaded_path
                .into_os_string()
                .into_string()
                .map_err(|_| anyhow::anyhow!("Path is not valid UTF-8"))?;
        }

        info!("All models downloaded successfully");
        Ok(config)
    }

    /// Process audio frame with language model (full bidirectional)
    async fn process_with_lm(
        &self,
        conn_state: &mut ConnectionState,
        audio: Vec<f32>,
    ) -> Result<Vec<f32>> {
        info!(
            "MOSHI_DEBUG: ========== process_with_lm() called - audio_len={} ==========",
            audio.len()
        );

        let mut moshi_state = self.state.write().await;

        // Get MIMI config
        let mimi_config = moshi_state.mimi_model.config();
        let frame_length = (mimi_config.sample_rate / mimi_config.frame_rate).ceil() as usize;

        // Validate audio length
        if audio.len() != frame_length {
            warn!(
                audio_len = audio.len(),
                expected_len = frame_length,
                "Audio length mismatch - padding/truncating"
            );
            info!(
                "MOSHI_DEBUG: Frame length mismatch - got {}, expected {}",
                audio.len(),
                frame_length
            );
            let mut fixed = audio;
            fixed.resize(frame_length, 0.0);
            return self.process_with_lm_impl(&mut moshi_state, conn_state, &fixed).await;
        }

        self.process_with_lm_impl(&mut moshi_state, conn_state, &audio).await
    }

    /// Internal language model processing implementation
    async fn process_with_lm_impl(
        &self,
        moshi_state: &mut tokio::sync::RwLockWriteGuard<'_, MoshiState>,
        conn_state: &mut ConnectionState,
        audio: &[f32],
    ) -> Result<Vec<f32>> {
        use candle::Tensor;

        // Copy values we'll need to avoid borrow checker issues
        let mimi_device_ref = if self.config.use_cpu_for_mimi {
            candle::Device::Cpu
        } else {
            moshi_state.device.clone()
        };
        let mimi_device = &mimi_device_ref;

        // Step 1: Encode audio to MIMI codes
        debug!("Encoding audio to MIMI codes");
        info!(
            "MOSHI_DEBUG: Step 1 - Encoding {} audio samples to MIMI codes",
            audio.len()
        );
        let pcm_tensor = Tensor::from_vec(
            audio.to_vec(),
            (1, 1, audio.len()),
            mimi_device,
        )?;
        info!(
            "MOSHI_DEBUG: PCM tensor created with shape {:?}",
            pcm_tensor.shape()
        );

        let codes_stream = moshi_state.mimi_model.encode_step(&pcm_tensor.into(), &().into())?;
        info!("MOSHI_DEBUG: MIMI encode_step completed");

        // Extract tensor from StreamTensor
        let codes_tensor = match codes_stream.as_option() {
            Some(tensor) => {
                info!(
                    "MOSHI_DEBUG: MIMI encoding produced codes tensor with shape {:?}",
                    tensor.shape()
                );
                tensor
            }
            None => {
                debug!("No codes generated yet, returning silence");
                info!("MOSHI_DEBUG: MIMI encoding returned None - returning silence");
                return Ok(vec![0.0; audio.len()]);
            }
        };

        // Extract codes as Vec<u32> - shape is [batch=1, codebooks, time=1]
        // CRITICAL: Only extract first 8 codebooks to match lm_config.input_audio_codebooks
        // MIMI outputs 32 codebooks, but LM expects only 8 for input
        use candle::IndexOp;
        let input_codebooks = moshi_state.lm_config.input_audio_codebooks as usize;
        let codes = codes_tensor.i((0, 0..input_codebooks, 0))?.to_vec1::<u32>()?;

        debug!(
            code_count = codes.len(),
            expected_count = input_codebooks,
            "Extracted MIMI codes (limited to LM input_audio_codebooks)"
        );
        info!(
            "MOSHI_DEBUG: Extracted {} audio codes from MIMI (limited to {} input_audio_codebooks)",
            codes.len(),
            input_codebooks
        );

        // Log sample codes for inspection
        let sample_codes: Vec<u32> = codes.iter().take(8).cloned().collect();
        info!("MOSHI_DEBUG: Sample MIMI codes (first 8): {:?}", sample_codes);

        // Step 2: Check for supervisor suggestions (force text token)
        let force_text_token = {
            let mut queue = moshi_state.suggestion_queue.lock().await;
            if let Some(_suggestion) = queue.pop_front() {
                // TODO: Encode suggestion text to tokens
                // For now, we just continue with generated text
                info!("Supervisor suggestion received but text encoding not yet implemented");
                None
            } else {
                None
            }
        };

        // Step 3: Run LM inference step
        debug!(prev_text_token = conn_state.prev_text_token, "Running LM step");
        info!(
            "MOSHI_DEBUG: Calling lm_generator.step() - prev_text_token={}, codes_len={}, force_text_token={:?}",
            conn_state.prev_text_token,
            codes.len(),
            force_text_token
        );
        let text_token = conn_state.lm_generator.step(
            conn_state.prev_text_token,
            &codes,
            force_text_token,
            None, // No cross-attention source
        )?;

        debug!(text_token = text_token, "Generated text token");
        info!(
            "MOSHI_DEBUG: lm_generator.step() completed - generated text_token={}",
            text_token
        );

        // Step 4: Decode text token to transcription (incremental)
        let decoded_text = self.decode_text_incremental(
            &moshi_state.text_tokenizer,
            conn_state.prev_text_token,
            text_token,
            &moshi_state.lm_config,
        );

        if let Some(text) = decoded_text {
            info!(transcription = %text, "User speech transcribed");
            info!("MOSHI_DEBUG: Text token decoded - text='{}'", text);

            // Store user transcription in conversation memory
            if let Err(e) = moshi_state.conversation_memory.add_user_message(text.clone()).await {
                warn!("Failed to store user message in memory: {}", e);
            }

            // Broadcast transcription to supervisor clients
            moshi_state.broadcast_transcription(&text).await;
        } else {
            info!(
                "MOSHI_DEBUG: Text token {} did not produce text (likely special token: start={}, pad={}, eop={})",
                text_token,
                moshi_state.lm_config.text_start_token,
                moshi_state.lm_config.text_pad_token,
                moshi_state.lm_config.text_eop_token
            );
        }

        // Update previous text token for next iteration
        conn_state.prev_text_token = text_token;

        // Step 5: Get audio tokens from LM and decode to audio
        // CRITICAL DEBUG: Log step_idx and acoustic delay to understand why last_audio_tokens returns None
        let step_idx = conn_state.lm_generator.step_idx();
        let acoustic_delay = moshi_state.lm_config.acoustic_delay;
        debug!(
            step_idx = step_idx,
            acoustic_delay = acoustic_delay,
            "Checking for audio tokens from LM generator"
        );
        info!(
            "MOSHI_DEBUG: Checking audio tokens - step_idx={}, acoustic_delay={}, threshold={}",
            step_idx,
            acoustic_delay,
            acoustic_delay + 1
        );

        let last_audio_tokens_result = conn_state.lm_generator.last_audio_tokens();
        info!(
            "MOSHI_DEBUG: lm_generator.last_audio_tokens() returned {}",
            if last_audio_tokens_result.is_some() { "Some(tokens)" } else { "None" }
        );

        if let Some(audio_tokens) = last_audio_tokens_result {
            debug!(
                lm_codebooks = audio_tokens.len(),
                expected_codebooks = moshi_state.lm_config.generated_audio_codebooks,
                "Got audio tokens from LM"
            );
            info!(
                "MOSHI_DEBUG: Audio tokens FOUND - token_count={}, expected_codebooks={}",
                audio_tokens.len(),
                moshi_state.lm_config.generated_audio_codebooks
            );

            // Log first few tokens for inspection
            let sample_tokens: Vec<u32> = audio_tokens.iter().take(8).cloned().collect();
            info!("MOSHI_DEBUG: Sample audio tokens (first 8): {:?}", sample_tokens);

            // CRITICAL FIX: MIMI decoder for generated audio expects 8 codebooks, not 32!
            // The LM generates exactly the right number of codebooks for MIMI decode
            // No padding needed - use the LM output directly
            let cb = moshi_state.lm_config.generated_audio_codebooks as usize;
            let audio_tokens_slice = &audio_tokens[..cb.min(audio_tokens.len())];

            debug!(
                actual_tokens = audio_tokens.len(),
                using_tokens = audio_tokens_slice.len(),
                expected_codebooks = cb,
                "Creating audio tensor for MIMI decoder (no padding needed)"
            );

            // Create tensor from LM audio tokens: [batch=1, codebooks=8, time=1]
            // This matches the working pattern from moshi-server examples
            let audio_tensor = Tensor::from_slice(
                audio_tokens_slice,
                (1, cb, 1),
                mimi_device,
            )?;

            // Decode audio tokens to PCM with correct tensor shape
            debug!(tensor_shape = ?audio_tensor.shape(), "Decoding audio tokens to PCM with MIMI");
            info!(
                "MOSHI_DEBUG: Calling MIMI decoder - tensor_shape={:?}",
                audio_tensor.shape()
            );
            let decoded = moshi_state.mimi_model.decode_step(&audio_tensor.into(), &().into())?;

            let audio_tensor = decoded.as_option()
                .ok_or_else(|| anyhow::anyhow!("MIMI decoder returned None"))?;

            let audio_vec = audio_tensor.flatten_all()?.to_vec1::<f32>()?;

            debug!(output_samples = audio_vec.len(), "LM processing complete");
            info!(
                "MOSHI_DEBUG: Audio generation SUCCESS - output_samples={}, will broadcast to speakers",
                audio_vec.len()
            );

            // Calculate RMS for logging
            let rms = if audio_vec.is_empty() {
                0.0
            } else {
                let sum: f32 = audio_vec.iter().map(|&s| s * s).sum();
                (sum / audio_vec.len() as f32).sqrt()
            };
            info!(
                "MOSHI_DEBUG: Generated audio RMS amplitude: {:.6}",
                rms
            );

            // Broadcast amplitude for visualizer
            moshi_state.broadcast_amplitude(&audio_vec).await;

            Ok(audio_vec)
        } else {
            // No audio tokens generated yet (initial steps or pad tokens)
            // CRITICAL DEBUG: Check WHY last_audio_tokens returned None
            if step_idx <= acoustic_delay {
                debug!(
                    step_idx = step_idx,
                    acoustic_delay = acoustic_delay,
                    "No audio tokens: still in acoustic delay period (expected for first {} steps)",
                    acoustic_delay + 1
                );
                info!(
                    "MOSHI_DEBUG: No audio tokens - in acoustic delay period (step {} <= delay {})",
                    step_idx,
                    acoustic_delay
                );
            } else {
                // Check the actual audio tokens to see if they're pad tokens
                let audio_tokens_raw = conn_state.lm_generator.audio_tokens(false);
                info!(
                    "MOSHI_DEBUG: No audio tokens from last_audio_tokens() - checking raw audio_tokens (include_padding=false)"
                );
                info!(
                    "MOSHI_DEBUG: Raw audio_tokens length: {}",
                    audio_tokens_raw.len()
                );

                if !audio_tokens_raw.is_empty() {
                    let last_idx = step_idx.saturating_sub(acoustic_delay + 1);
                    info!(
                        "MOSHI_DEBUG: Checking token at index {} (step_idx {} - acoustic_delay {} - 1)",
                        last_idx,
                        step_idx,
                        acoustic_delay
                    );

                    if last_idx < audio_tokens_raw.len() {
                        let tokens = &audio_tokens_raw[last_idx];
                        let audio_vocab_size = moshi_state.lm_config.audio_vocab_size;
                        let has_pad_tokens = tokens.iter().any(|&t| t as usize >= audio_vocab_size - 1);

                        // Log all tokens for inspection
                        info!(
                            "MOSHI_DEBUG: Raw audio tokens at index {}: {:?}",
                            last_idx,
                            tokens
                        );
                        info!(
                            "MOSHI_DEBUG: audio_vocab_size={}, pad_threshold={}, has_pad_tokens={}",
                            audio_vocab_size,
                            audio_vocab_size - 1,
                            has_pad_tokens
                        );

                        warn!(
                            step_idx = step_idx,
                            token_idx = last_idx,
                            tokens = ?tokens,
                            audio_vocab_size = audio_vocab_size,
                            has_pad_tokens = has_pad_tokens,
                            "Audio tokens generated but last_audio_tokens returned None - likely ALL PAD TOKENS!"
                        );
                    } else {
                        info!(
                            "MOSHI_DEBUG: last_idx {} is out of bounds for audio_tokens_raw (len {})",
                            last_idx,
                            audio_tokens_raw.len()
                        );
                    }
                } else {
                    info!("MOSHI_DEBUG: audio_tokens_raw is empty - no tokens generated yet");
                }
            }
            info!("MOSHI_DEBUG: Returning silence (no audio generated)");
            Ok(vec![0.0; audio.len()])
        }
    }

    /// Decode text token incrementally
    fn decode_text_incremental(
        &self,
        tokenizer: &sentencepiece::SentencePieceProcessor,
        prev_token: u32,
        curr_token: u32,
        config: &moshi::lm_generate_multistream::Config,
    ) -> Option<String> {
        // Filter special tokens
        if curr_token == config.text_start_token
            || curr_token == config.text_pad_token
            || curr_token == config.text_eop_token
        {
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

    /// Start WebSocket server for Twilio Media Streams
    pub async fn start_server(self: Arc<Self>) -> Result<()> {
        let addr = format!("{}:{}", self.config.host, self.config.port);

        // Use helper function that sets SO_REUSEADDR for immediate port reuse
        let listener = crate::net_utils::create_reusable_tcp_listener(&addr).await
            .with_context(|| format!("Failed to bind voice bridge to {}", addr))?;

        info!(
            host = %self.config.host,
            port = self.config.port,
            "Voice bridge WebSocket server listening"
        );

        loop {
            match listener.accept().await {
                Ok((stream, peer_addr)) => {
                    info!(?peer_addr, "New connection from Cloudflare Workers");
                    let bridge = self.clone();
                    tokio::spawn(async move {
                        if let Err(e) = bridge.handle_connection(stream).await {
                            error!(error = ?e, "Connection handler error");
                        }
                    });
                }
                Err(e) => {
                    error!(error = ?e, "Failed to accept connection");
                }
            }
        }
    }

    /// Handle a single WebSocket connection
    async fn handle_connection(&self, stream: TcpStream) -> Result<()> {
        let ws_stream = accept_async(stream)
            .await
            .context("WebSocket handshake failed")?;

        info!("WebSocket connection established");

        let (mut ws_sender, mut ws_receiver) = ws_stream.split();
        let mut stream_sid: Option<String> = None;

        // Create per-connection state with LM generator
        let moshi_state = self.state.read().await;
        let max_steps = 10000; // Maximum inference steps
        let mut conn_state = ConnectionState::new(&moshi_state, max_steps)
            .context("Failed to create connection state")?;
        drop(moshi_state); // Release lock

        const MOSHI_FRAME_SIZE: usize = 1920;

        while let Some(msg) = ws_receiver.next().await {
            match msg {
                Ok(WsMessage::Text(text)) => {
                    debug!(message = %text, "Received Twilio message");

                    match serde_json::from_str::<TwilioEvent>(&text) {
                        Ok(event) => match event {
                            TwilioEvent::Connected { protocol, version } => {
                                info!(?protocol, ?version, "Twilio stream connected");
                            }
                            TwilioEvent::Start { stream_sid: sid, custom_parameters } => {
                                info!(?sid, ?custom_parameters, "Twilio stream started");
                                stream_sid = Some(sid);
                            }
                            TwilioEvent::Media { stream_sid: sid, media } => {
                                // Decode base64 μ-law audio
                                let mulaw_bytes = match BASE64.decode(&media.payload) {
                                    Ok(bytes) => bytes,
                                    Err(e) => {
                                        error!(error = ?e, "Failed to decode base64 audio");
                                        continue;
                                    }
                                };

                                // Convert Twilio μ-law 8kHz to PCM f32 24kHz
                                match audio::twilio_to_moshi(&mulaw_bytes, &mut conn_state.upsampler) {
                                    Ok(samples_24khz) => {
                                        // Add to buffer
                                        conn_state.audio_buffer.extend_from_slice(&samples_24khz);
                                        debug!(
                                            buffer_size = conn_state.audio_buffer.len(),
                                            chunk_size = samples_24khz.len(),
                                            "Added audio chunk to buffer"
                                        );

                                        // Process when we have a full MOSHI frame
                                        if conn_state.audio_buffer.len() >= MOSHI_FRAME_SIZE {
                                            // Extract exactly one frame
                                            let frame: Vec<f32> = conn_state.audio_buffer.drain(..MOSHI_FRAME_SIZE).collect();

                                            debug!(
                                                frame_size = frame.len(),
                                                remaining = conn_state.audio_buffer.len(),
                                                "Processing full MOSHI frame"
                                            );

                                            // Process through MOSHI with LM
                                            match self.process_with_lm(&mut conn_state, frame).await {
                                                Ok(response_24khz) => {
                                                    // Convert back to Twilio format
                                                    match audio::moshi_to_twilio(&response_24khz, &mut conn_state.downsampler) {
                                                        Ok(response_mulaw) => {
                                                            // Encode response as base64
                                                            let response_base64 = BASE64.encode(&response_mulaw);

                                                            // Send back to Twilio
                                                            let response = TwilioMediaResponse {
                                                                event: "media".to_string(),
                                                                stream_sid: sid.clone(),
                                                                media: MediaResponsePayload {
                                                                    payload: response_base64,
                                                                },
                                                            };

                                                            if let Ok(response_json) = serde_json::to_string(&response) {
                                                                if let Err(e) = ws_sender.send(WsMessage::Text(response_json)).await {
                                                                    error!(error = ?e, "Failed to send response");
                                                                    break;
                                                                }
                                                            }
                                                        }
                                                        Err(e) => {
                                                            error!(error = ?e, "Failed to convert MOSHI output to Twilio format");
                                                        }
                                                    }
                                                }
                                                Err(e) => {
                                                    error!(error = ?e, "MOSHI processing failed");
                                                }
                                            }
                                        }
                                    }
                                    Err(e) => {
                                        error!(error = ?e, "Failed to convert Twilio audio to MOSHI format");
                                    }
                                }
                            }
                            TwilioEvent::Stop { stream_sid: sid } => {
                                info!(?sid, "Twilio stream stopped");
                                break;
                            }
                        },
                        Err(e) => {
                            error!(error = ?e, message = %text, "Failed to parse Twilio message");
                        }
                    }
                }
                Ok(WsMessage::Binary(_)) => {
                    warn!("Received unexpected binary message");
                }
                Ok(WsMessage::Close(_)) => {
                    info!("WebSocket connection closed");
                    break;
                }
                Ok(WsMessage::Ping(data)) => {
                    debug!("Received ping, sending pong");
                    if let Err(e) = ws_sender.send(WsMessage::Pong(data)).await {
                        error!(error = ?e, "Failed to send pong");
                        break;
                    }
                }
                Ok(WsMessage::Pong(_)) => {
                    debug!("Received pong");
                }
                Ok(WsMessage::Frame(_)) => {
                    // Raw frames should not be received in normal operation
                    warn!("Received unexpected raw frame");
                }
                Err(e) => {
                    error!(error = ?e, "WebSocket error");
                    break;
                }
            }
        }

        if let Some(sid) = stream_sid {
            info!(?sid, "Connection handler completed");
        } else {
            info!("Connection handler completed (no stream ID)");
        }

        Ok(())
    }
}

/// Generate and play a greeting tone when the voice system starts
///
/// Plays a three-tone sequence (ascending tones) to indicate MOSHI is ready
/// This provides audio feedback that the voice system has started successfully
pub async fn generate_greeting_tone() -> Result<()> {
    info!("=== Starting MOSHI greeting tone sequence ===");

    // Initialize audio output device
    info!("Initializing audio output device for greeting...");
    let audio_output = AudioOutputDevice::new()
        .context("Failed to initialize audio output device for greeting")?;
    info!("Audio output device initialized successfully");

    // Play three-tone ascending greeting to indicate system ready
    // 600Hz -> 800Hz -> 1000Hz creates a pleasant startup chime
    info!("Playing greeting tone 1/3: 600Hz for 150ms");
    audio_output.play_tone(600.0, 150).await
        .context("Failed to play first greeting tone (600Hz)")?;
    info!("Tone 1/3 complete");

    tokio::time::sleep(Duration::from_millis(30)).await;

    info!("Playing greeting tone 2/3: 800Hz for 150ms");
    audio_output.play_tone(800.0, 150).await
        .context("Failed to play second greeting tone (800Hz)")?;
    info!("Tone 2/3 complete");

    tokio::time::sleep(Duration::from_millis(30)).await;

    info!("Playing greeting tone 3/3: 1000Hz for 200ms");
    audio_output.play_tone(1000.0, 200).await
        .context("Failed to play third greeting tone (1000Hz)")?;
    info!("Tone 3/3 complete");

    info!("=== MOSHI greeting tone sequence complete - system ready ===");
    Ok(())
}

/// Generate MOSHI voice greeting on startup using direct speech generation
///
/// ARCHITECTURAL NOTE: This uses force_text_token for greeting (acceptable for scripted greetings).
/// This is NOT TTS - it uses the SAME language model that handles conversations.
/// For memory context injection, use the memory_conditioner module instead.
///
/// # Parameters
/// * `moshi_state` - The shared MOSHI state containing models and config
///
/// # Returns
/// PCM audio samples ready for playback through speakers
pub async fn generate_moshi_voice_greeting(
    moshi_state: Arc<RwLock<MoshiState>>,
) -> Result<()> {
    info!("🎤 Generating MOSHI voice greeting using direct speech");

    // Initialize audio output device
    let audio_output = AudioOutputDevice::new()
        .context("Failed to create audio output device for greeting")?;

    // Generate greeting using the greeting module
    // Need write lock because MIMI decode_step requires mutable access
    let mut moshi_state_guard = moshi_state.write().await;

    let greeting_pcm = crate::greeting::generate_simple_greeting(
        &mut *moshi_state_guard,
        "Hello! I'm ready to help you today.",
    ).await.context("Failed to generate greeting audio")?;

    drop(moshi_state_guard); // Release lock before playing audio

    // Play greeting through speakers
    info!("🔊 Playing greeting through speakers ({} samples)", greeting_pcm.len());
    audio_output.play_audio_samples(&greeting_pcm).await
        .context("Failed to play greeting audio")?;

    info!("✅ MOSHI voice greeting complete");
    Ok(())
}

/// Local Voice Assistant - Placeholder for future implementation
/// Due to CPAL's Stream not being Send, this requires a different architecture
/// TODO: Implement local voice assistant using thread-local audio streams
pub struct LocalVoiceAssistant;

impl LocalVoiceAssistant {
    pub async fn new(_config: VoiceConfig) -> Result<Self> {
        anyhow::bail!("LocalVoiceAssistant not yet implemented - CPAL Stream is not Send")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_voice_config_default() {
        let config = VoiceConfig::default();
        assert_eq!(config.host, "127.0.0.1");
        assert_eq!(config.port, 9998);
    }
}
