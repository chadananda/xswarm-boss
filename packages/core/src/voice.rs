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
use tokio::sync::{RwLock, Mutex};
use tokio::net::{TcpListener, TcpStream};
use tokio_tungstenite::{accept_async, tungstenite::Message as WsMessage};
use futures_util::{StreamExt, SinkExt};
use tracing::{info, warn, error, debug};
use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};

use crate::audio::{self, AudioResampler};

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

        info!("MOSHI models initialized successfully");

        Ok(Self {
            lm_model,
            mimi_model,
            text_tokenizer,
            device,
            config,
            lm_config,
            suggestion_queue: Arc::new(Mutex::new(VecDeque::new())),
            supervisor_clients: Arc::new(Mutex::new(Vec::new())),
        })
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
        })
    }

    /// Get shared reference to MOSHI state for supervisor integration
    pub fn get_moshi_state(&self) -> Arc<RwLock<MoshiState>> {
        self.state.clone()
    }

    /// Download MOSHI models from Hugging Face if not present locally
    async fn download_models_if_needed(mut config: VoiceConfig) -> Result<VoiceConfig> {
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
        use candle::Tensor;

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
        let pcm_tensor = Tensor::from_vec(
            audio.to_vec(),
            (1, 1, audio.len()),
            mimi_device,
        )?;
        let codes_stream = moshi_state.mimi_model.encode_step(&pcm_tensor.into(), &().into())?;

        // Extract tensor from StreamTensor
        let codes_tensor = match codes_stream.as_option() {
            Some(tensor) => tensor,
            None => {
                debug!("No codes generated yet, returning silence");
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
        let text_token = conn_state.lm_generator.step(
            conn_state.prev_text_token,
            &codes,
            force_text_token,
            None, // No cross-attention source
        )?;

        debug!(text_token = text_token, "Generated text token");

        // Step 4: Decode text token to transcription (incremental)
        if let Some(text) = self.decode_text_incremental(
            &moshi_state.text_tokenizer,
            conn_state.prev_text_token,
            text_token,
            &moshi_state.lm_config,
        ) {
            info!(transcription = %text, "User speech transcribed");
            // Broadcast transcription to supervisor clients
            moshi_state.broadcast_transcription(&text).await;
        }

        // Update previous text token for next iteration
        conn_state.prev_text_token = text_token;

        // Step 5: Get audio tokens from LM and decode to audio
        if let Some(audio_tokens) = conn_state.lm_generator.last_audio_tokens() {
            debug!(
                lm_codebooks = audio_tokens.len(),
                expected_codebooks = moshi_state.lm_config.generated_audio_codebooks,
                "Got audio tokens from LM"
            );

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
            let decoded = moshi_state.mimi_model.decode_step(&audio_tensor.into(), &().into())?;

            let audio_tensor = decoded.as_option()
                .ok_or_else(|| anyhow::anyhow!("MIMI decoder returned None"))?;

            let audio_vec = audio_tensor.flatten_all()?.to_vec1::<f32>()?;

            debug!(output_samples = audio_vec.len(), "LM processing complete");

            Ok(audio_vec)
        } else {
            // No audio tokens generated yet (initial steps)
            debug!("No audio tokens available yet, returning silence");
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
        let listener = TcpListener::bind(&addr).await
            .with_context(|| format!("Failed to bind to {}", addr))?;

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
