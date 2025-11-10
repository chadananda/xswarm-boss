// Local Audio Module - Microphone Input and Speaker Output
//
// This module provides direct audio capture from microphone and playback
// to speakers using CPAL (Cross-Platform Audio Library).
//
// Key features:
// - Real-time microphone capture at 24kHz (MOSHI native rate)
// - Speaker output at 24kHz
// - Voice Activity Detection (VAD)
// - Proper device selection and error handling
// - Clean start/stop functionality

use anyhow::{Context, Result};
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use cpal::{Device, Stream, StreamConfig, SampleRate};
use std::sync::Arc;
use tokio::sync::{mpsc, Mutex, RwLock};
use tracing::{info, warn, error, debug};

/// Sample rate for local audio (MOSHI native rate)
pub const LOCAL_AUDIO_SAMPLE_RATE: u32 = 24000;

/// Frame size in samples (20ms at 24kHz = 480 samples)
pub const FRAME_SIZE: usize = 480;

/// Audio frame containing samples from microphone
#[derive(Debug, Clone)]
pub struct AudioFrame {
    pub samples: Vec<f32>,
    pub timestamp: std::time::Instant,
}

/// Voice Activity Detection threshold
/// Values below this are considered silence
const VAD_THRESHOLD: f32 = 0.01;

/// Number of consecutive silent frames before marking as inactive
const VAD_SILENCE_FRAMES: usize = 10;

/// Voice Activity Detector
pub struct VoiceActivityDetector {
    silent_frames: usize,
    is_speaking: bool,
}

impl VoiceActivityDetector {
    pub fn new() -> Self {
        Self {
            silent_frames: 0,
            is_speaking: false,
        }
    }

    /// Process audio frame and detect voice activity
    /// Returns true if voice is detected
    pub fn process(&mut self, samples: &[f32]) -> bool {
        // Calculate RMS (Root Mean Square) energy
        let energy: f32 = samples.iter()
            .map(|&s| s * s)
            .sum::<f32>() / samples.len() as f32;
        let rms = energy.sqrt();

        if rms > VAD_THRESHOLD {
            // Voice detected
            self.silent_frames = 0;
            if !self.is_speaking {
                self.is_speaking = true;
                debug!("Voice activity detected (RMS: {:.4})", rms);
            }
        } else {
            // Silence
            self.silent_frames += 1;
            if self.is_speaking && self.silent_frames >= VAD_SILENCE_FRAMES {
                self.is_speaking = false;
                debug!("Voice activity ended (silent frames: {})", self.silent_frames);
            }
        }

        self.is_speaking
    }

    /// Check if currently speaking
    pub fn is_speaking(&self) -> bool {
        self.is_speaking
    }

    /// Reset the detector
    pub fn reset(&mut self) {
        self.silent_frames = 0;
        self.is_speaking = false;
    }
}

/// Local audio system for microphone capture and speaker output
/// Note: This struct cannot be Send because cpal::Stream is not Send.
/// Audio streams are managed on the main thread only.
pub struct LocalAudioSystem {
    /// Audio host (CPAL)
    host: cpal::Host,

    /// Input device (microphone)
    input_device: Device,

    /// Output device (speakers)
    output_device: Device,

    /// Input stream (microphone) - not Send!
    input_stream: Option<Stream>,

    /// Output stream (speakers) - not Send!
    output_stream: Option<Stream>,

    /// Channel for sending captured audio frames
    audio_tx: mpsc::UnboundedSender<AudioFrame>,

    /// Voice Activity Detector
    vad: Arc<RwLock<VoiceActivityDetector>>,

    /// Audio buffer for accumulating samples
    input_buffer: Arc<Mutex<Vec<f32>>>,

    /// Playback buffer for queuing output
    output_buffer: Arc<Mutex<Vec<f32>>>,
}

impl LocalAudioSystem {
    /// Create a new local audio system
    pub fn new() -> Result<(Self, mpsc::UnboundedReceiver<AudioFrame>, mpsc::UnboundedSender<Vec<f32>>)> {
        info!("Initializing local audio system");

        // Get default host
        let host = cpal::default_host();

        // Get default input device (microphone)
        let input_device = host
            .default_input_device()
            .context("No default input device available")?;
        info!("Input device: {}", input_device.name()?);

        // Get default output device (speakers)
        let output_device = host
            .default_output_device()
            .context("No default output device available")?;
        info!("Output device: {}", output_device.name()?);

        // Create channels for audio communication
        let (audio_tx, audio_rx) = mpsc::unbounded_channel();
        let (playback_tx, mut playback_rx) = mpsc::unbounded_channel::<Vec<f32>>();

        // Create output buffer for speaker playback
        let output_buffer = Arc::new(Mutex::new(Vec::new()));
        let output_buffer_clone = output_buffer.clone();

        // Spawn background task to bridge playback_rx -> output_buffer
        // This is the critical link: MOSHI sends audio to playback_tx,
        // this task reads from playback_rx and writes to output_buffer,
        // and the speaker callback reads from output_buffer
        tokio::spawn(async move {
            info!("PLAYBACK_BRIDGE: Task started successfully");
            info!("PLAYBACK_BRIDGE: Entering receive loop...");

            // Maximum buffer size to prevent unbounded growth (5 seconds at 24kHz)
            const MAX_BUFFER_SIZE: usize = LOCAL_AUDIO_SAMPLE_RATE as usize * 5;

            let mut frame_count = 0;
            loop {
                debug!("PLAYBACK_BRIDGE: Waiting for samples from channel (frame #{})", frame_count);

                match playback_rx.recv().await {
                    Some(samples) => {
                        frame_count += 1;
                        info!(
                            "PLAYBACK_BRIDGE: Received {} samples from channel (frame #{})",
                            samples.len(),
                            frame_count
                        );

                        // Lock the output buffer and add samples
                        let mut buffer = output_buffer_clone.lock().await;

                        // Check buffer size to prevent memory issues
                        let buffer_len = buffer.len();
                        if buffer_len > MAX_BUFFER_SIZE {
                            warn!("PLAYBACK_BRIDGE: Output buffer overflow ({} samples), dropping oldest samples", buffer_len);
                            let drain_end = buffer_len - MAX_BUFFER_SIZE + samples.len();
                            buffer.drain(0..drain_end);
                        }

                        buffer.extend(samples);
                        info!(
                            "PLAYBACK_BRIDGE: Added {} samples to output buffer (total buffer size: {} samples)",
                            buffer.len() - buffer_len,
                            buffer.len()
                        );
                    }
                    None => {
                        info!("PLAYBACK_BRIDGE: Channel closed (recv returned None) - exiting after {} frames", frame_count);
                        break;
                    }
                }
            }

            info!("PLAYBACK_BRIDGE: Task ended - processed {} total frames", frame_count);
        });

        Ok((
            Self {
                host,
                input_device,
                output_device,
                input_stream: None,
                output_stream: None,
                audio_tx,
                vad: Arc::new(RwLock::new(VoiceActivityDetector::new())),
                input_buffer: Arc::new(Mutex::new(Vec::with_capacity(FRAME_SIZE * 2))),
                output_buffer,
            },
            audio_rx,
            playback_tx,
        ))
    }

    /// Start audio capture from microphone
    pub fn start_input(&mut self) -> Result<()> {
        info!("Starting microphone input");

        // Get supported input config
        let config = self.get_input_config()
            .context("Failed to get input configuration")?;
        info!("Using input config: {:?}", config);

        // Build input stream
        let audio_tx = self.audio_tx.clone();
        let vad = self.vad.clone();
        let input_buffer = self.input_buffer.clone();

        let stream = self.input_device.build_input_stream(
            &config,
            move |data: &[f32], _: &cpal::InputCallbackInfo| {
                // Process incoming audio data
                Self::process_input_callback(data, audio_tx.clone(), vad.clone(), input_buffer.clone());
            },
            |err| {
                error!("Audio input stream error: {}", err);
            },
            None,
        )
        .context("Failed to build input stream with selected configuration")?;

        // Start the stream
        stream.play()
            .context("Failed to start input stream playback")?;

        // Store the stream
        self.input_stream = Some(stream);

        info!("✓ Microphone input started successfully at {} Hz", config.sample_rate.0);
        Ok(())
    }

    /// Stop audio capture
    pub fn stop_input(&mut self) -> Result<()> {
        info!("Stopping microphone input");
        self.input_stream = None;
        info!("Microphone input stopped");
        Ok(())
    }

    /// Start audio playback to speakers
    pub fn start_output(&mut self) -> Result<()> {
        info!("Starting speaker output");

        // Get supported output config
        let config = self.get_output_config()
            .context("Failed to get output configuration")?;
        info!("Using output config: {:?}", config);

        // Build output stream
        // We need to move playback_rx into the closure
        // This is tricky because we can't clone UnboundedReceiver
        // We'll need a different approach - use a channel that can be cloned
        let output_buffer = self.output_buffer.clone();

        // For output, we'll need to receive data differently
        // We cannot move playback_rx into the callback
        // Instead, we'll poll from output_buffer which is Arc<Mutex<Vec<f32>>>

        let stream = self.output_device.build_output_stream(
            &config,
            move |data: &mut [f32], _: &cpal::OutputCallbackInfo| {
                // Process outgoing audio data - just use buffer
                let mut buffer = match output_buffer.try_lock() {
                    Ok(b) => b,
                    Err(_) => {
                        data.fill(0.0);
                        return;
                    }
                };

                // Fill output buffer with available samples
                let available = buffer.len().min(data.len());
                if available > 0 {
                    data[..available].copy_from_slice(&buffer[..available]);
                    buffer.drain(..available);

                    // Fill remainder with silence if needed
                    if available < data.len() {
                        data[available..].fill(0.0);
                    }
                } else {
                    // No samples available, output silence
                    data.fill(0.0);
                }
            },
            |err| {
                error!("Audio output stream error: {}", err);
            },
            None,
        )
        .context("Failed to build output stream with selected configuration")?;

        // Start the stream
        stream.play()
            .context("Failed to start output stream playback")?;

        // Store the stream
        self.output_stream = Some(stream);

        info!("✓ Speaker output started successfully at {} Hz", config.sample_rate.0);
        Ok(())
    }

    /// Stop audio playback
    pub fn stop_output(&mut self) -> Result<()> {
        info!("Stopping speaker output");
        self.output_stream = None;
        info!("Speaker output stopped");
        Ok(())
    }

    /// Start both input and output streams
    pub fn start(&mut self) -> Result<()> {
        info!("Starting local audio system (input + output)");
        self.start_input()?;
        self.start_output()?;
        info!("Local audio system started successfully");
        Ok(())
    }

    /// Stop both input and output streams
    pub fn stop(&mut self) -> Result<()> {
        info!("Stopping local audio system");
        self.stop_input()?;
        self.stop_output()?;
        info!("Local audio system stopped");
        Ok(())
    }

    /// Queue audio for playback (called from async context)
    pub async fn queue_playback(&self, samples: Vec<f32>) -> Result<()> {
        let mut buffer = self.output_buffer.lock().await;
        buffer.extend(samples);
        Ok(())
    }

    /// Get input device configuration with fallbacks
    fn get_input_config(&self) -> Result<StreamConfig> {
        let default_config = self.input_device.default_input_config()?;

        info!("Default input config - Sample rate: {} Hz, Channels: {}, Format: {:?}",
              default_config.sample_rate().0,
              default_config.channels(),
              default_config.sample_format());

        // Get supported config ranges
        let supported_configs: Vec<_> = self.input_device
            .supported_input_configs()
            .context("Failed to get supported input configs")?
            .collect();

        // Try our preferred configs in order
        let preferred_rates = vec![
            LOCAL_AUDIO_SAMPLE_RATE, // 24kHz - MOSHI native
            48000,                    // 48kHz - common high quality
            44100,                    // 44.1kHz - CD quality
            default_config.sample_rate().0, // Device default
        ];

        for &rate in &preferred_rates {
            // Check if this rate is supported
            let is_supported = supported_configs.iter().any(|config| {
                rate >= config.min_sample_rate().0 && rate <= config.max_sample_rate().0
            });

            if is_supported {
                let config = StreamConfig {
                    channels: 1, // Mono - if device doesn't support, CPAL will handle
                    sample_rate: SampleRate(rate),
                    // Use fixed buffer size for consistent 20ms frames (480 samples at 24kHz)
                    buffer_size: cpal::BufferSize::Fixed(FRAME_SIZE as u32),
                };

                info!("Selected input config - Sample rate: {} Hz, Channels: {}, Buffer: {} samples", rate, 1, FRAME_SIZE);
                return Ok(config);
            } else {
                debug!("Sample rate {} Hz not supported for input, trying next option", rate);
            }
        }

        // Fallback to device default if nothing else works
        warn!("Using device default input config as fallback");
        Ok(StreamConfig {
            channels: default_config.channels().min(2), // Prefer mono/stereo
            sample_rate: default_config.sample_rate(),
            buffer_size: cpal::BufferSize::Default,
        })
    }

    /// Get output device configuration with fallbacks
    fn get_output_config(&self) -> Result<StreamConfig> {
        let default_config = self.output_device.default_output_config()?;

        info!("Default output config - Sample rate: {} Hz, Channels: {}, Format: {:?}",
              default_config.sample_rate().0,
              default_config.channels(),
              default_config.sample_format());

        // Get supported config ranges
        let supported_configs: Vec<_> = self.output_device
            .supported_output_configs()
            .context("Failed to get supported output configs")?
            .collect();

        // Try our preferred configs in order
        let preferred_rates = vec![
            LOCAL_AUDIO_SAMPLE_RATE, // 24kHz - MOSHI native
            48000,                    // 48kHz - common high quality
            44100,                    // 44.1kHz - CD quality
            default_config.sample_rate().0, // Device default
        ];

        for &rate in &preferred_rates {
            // Check if this rate is supported
            let is_supported = supported_configs.iter().any(|config| {
                rate >= config.min_sample_rate().0 && rate <= config.max_sample_rate().0
            });

            if is_supported {
                let config = StreamConfig {
                    channels: 1, // Mono - if device doesn't support, CPAL will handle
                    sample_rate: SampleRate(rate),
                    // Use fixed buffer size for consistent 20ms frames (480 samples at 24kHz)
                    buffer_size: cpal::BufferSize::Fixed(FRAME_SIZE as u32),
                };

                info!("Selected output config - Sample rate: {} Hz, Channels: {}, Buffer: {} samples", rate, 1, FRAME_SIZE);
                return Ok(config);
            } else {
                debug!("Sample rate {} Hz not supported for output, trying next option", rate);
            }
        }

        // Fallback to device default if nothing else works
        warn!("Using device default output config as fallback");
        Ok(StreamConfig {
            channels: default_config.channels().min(2), // Prefer mono/stereo
            sample_rate: default_config.sample_rate(),
            // Even in fallback, use fixed buffer for consistent timing
            buffer_size: cpal::BufferSize::Fixed(FRAME_SIZE as u32),
        })
    }

    /// Process input callback (runs in audio thread)
    fn process_input_callback(
        data: &[f32],
        audio_tx: mpsc::UnboundedSender<AudioFrame>,
        vad: Arc<RwLock<VoiceActivityDetector>>,
        input_buffer: Arc<Mutex<Vec<f32>>>,
    ) {
        // Add to buffer (blocking is OK in audio callback for Mutex)
        let mut buffer = match input_buffer.try_lock() {
            Ok(buf) => buf,
            Err(_) => return, // Skip this callback if buffer is locked
        };

        buffer.extend_from_slice(data);

        // Process complete frames
        while buffer.len() >= FRAME_SIZE {
            let frame: Vec<f32> = buffer.drain(..FRAME_SIZE).collect();

            // Run VAD (for potential future use)
            let _is_speaking = {
                let mut vad_detector = match vad.try_write() {
                    Ok(v) => v,
                    Err(_) => return, // Skip if VAD is locked
                };
                vad_detector.process(&frame)
            };

            // ALWAYS send frames to visualizer (not just when voice detected)
            // This allows the microphone amplitude visualizer to show real-time
            // audio levels even during silence, which is critical for UX feedback
            let audio_frame = AudioFrame {
                samples: frame,
                timestamp: std::time::Instant::now(),
            };

            // Send frame (ignore if channel is full)
            let _ = audio_tx.send(audio_frame);
        }
    }

    /// Check if voice is currently being detected
    pub async fn is_speaking(&self) -> bool {
        self.vad.read().await.is_speaking()
    }

    /// Reset voice activity detector
    pub async fn reset_vad(&self) {
        self.vad.write().await.reset();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vad_detection() {
        let mut vad = VoiceActivityDetector::new();

        // Test silence
        let silence = vec![0.0; 480];
        assert!(!vad.process(&silence));

        // Test voice
        let voice: Vec<f32> = (0..480)
            .map(|i| (2.0 * std::f32::consts::PI * 440.0 * i as f32 / 24000.0).sin() * 0.1)
            .collect();
        assert!(vad.process(&voice));

        // Test silence again (should stay active for a few frames)
        assert!(vad.process(&silence));
    }
}
