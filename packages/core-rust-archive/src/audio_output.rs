// Audio Output Module - Local Speaker Playback
//
// This module provides audio output functionality for playing sounds through
// the system's default audio output device (speakers/headphones).
//
// Features:
// - Simple tone generation for system notifications
// - Raw PCM audio playback for voice synthesis
// - Async-compatible interface
// - Error handling for device initialization failures

use anyhow::{Context, Result};
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use cpal::{Device, Stream, StreamConfig, SampleFormat};
use hound::{WavSpec, WavWriter};
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};
use tokio::sync::mpsc;
use tracing::{debug, info, warn};

// v0.1.0-2025.11.5.24: PERIODIC WAV FLUSHING (write samples as they arrive)
// Signal handlers don't work in this environment (Tokio/TUI interference)
// Solution: Write samples to WAV file incrementally with periodic finalization
use once_cell::sync::Lazy;
use std::fs;

// Global WAV writer (opened once, written continuously)
// Mutex guards concurrent access from audio playback task
static WAV_WRITER: Lazy<Arc<Mutex<Option<hound::WavWriter<std::io::BufWriter<std::fs::File>>>>>> =
    Lazy::new(|| Arc::new(Mutex::new(None)));

/// Initialize WAV export (create file and writer)
pub fn init_wav_export(sample_rate: u32) -> Result<()> {
    // Ensure tmp directory exists
    fs::create_dir_all("./tmp")?;

    let spec = hound::WavSpec {
        channels: 1,
        sample_rate,
        bits_per_sample: 16,
        sample_format: hound::SampleFormat::Int,
    };

    let writer = hound::WavWriter::create("./tmp/moshi-debug-audio.wav", spec)?;
    *WAV_WRITER.lock().unwrap() = Some(writer);

    info!("MOSHI_DEBUG: WAV export initialized at {}Hz (periodic flush mode)", sample_rate);
    Ok(())
}

/// Write samples to WAV file (called continuously as samples arrive)
pub fn write_wav_samples(samples: &[i16]) {
    if let Some(ref mut writer) = *WAV_WRITER.lock().unwrap() {
        for &sample in samples {
            if let Err(e) = writer.write_sample(sample) {
                warn!("MOSHI_DEBUG: Failed to write WAV sample: {}", e);
                return;
            }
        }
        // Flush to disk every write to survive abrupt termination
        if let Err(e) = writer.flush() {
            warn!("MOSHI_DEBUG: Failed to flush WAV writer: {}", e);
        }
    }
}

/// Finalize WAV file (update header, close file)
pub fn finalize_wav_export() {
    if let Some(writer) = WAV_WRITER.lock().unwrap().take() {
        match writer.finalize() {
            Ok(()) => {
                info!("MOSHI_DEBUG: ✅ WAV file finalized successfully!");
            }
            Err(e) => {
                warn!("MOSHI_DEBUG: Failed to finalize WAV file: {}", e);
            }
        }
    }
}

/// Audio output device manager for speaker playback
pub struct AudioOutputDevice {
    device: Device,
    config: StreamConfig,
    sample_format: SampleFormat,
}

impl AudioOutputDevice {
    /// Create a new audio output device using the system's default output
    /// Attempts to use 44.1kHz sample rate for compatibility with MOSHI audio
    pub fn new() -> Result<Self> {
        Self::with_sample_rate(44100)
    }

    /// Get the actual sample rate of this audio device
    pub fn get_sample_rate(&self) -> u32 {
        self.config.sample_rate.0
    }

    /// Create a new audio output device with a specific sample rate
    ///
    /// # Arguments
    /// * `target_sample_rate` - Desired sample rate in Hz (e.g., 44100)
    pub fn with_sample_rate(target_sample_rate: u32) -> Result<Self> {
        info!(
            target_sample_rate,
            "Initializing audio output device with specific sample rate"
        );

        // Get the default host (CoreAudio on macOS, WASAPI on Windows, ALSA on Linux)
        let host = cpal::default_host();

        // Get the default output device
        let device = host
            .default_output_device()
            .context("No default audio output device found")?;

        info!(device_name = ?device.name(), "Found audio output device");

        // Try to get a config that supports our target sample rate
        let supported_configs = device
            .supported_output_configs()
            .context("Failed to query supported output configs")?;

        // Find a config that supports our target sample rate
        let mut config_option = None;
        for supported_config in supported_configs {
            let min_rate = supported_config.min_sample_rate().0;
            let max_rate = supported_config.max_sample_rate().0;

            if target_sample_rate >= min_rate && target_sample_rate <= max_rate {
                info!(
                    min_rate,
                    max_rate,
                    channels = supported_config.channels(),
                    sample_format = ?supported_config.sample_format(),
                    "Found supported config for target sample rate"
                );
                config_option = Some(supported_config);
                break;
            }
        }

        let (stream_config, sample_format) = if let Some(supported_config) = config_option {
            // Use the config with our target sample rate
            let sample_format = supported_config.sample_format();
            let config = StreamConfig {
                channels: supported_config.channels(),
                sample_rate: cpal::SampleRate(target_sample_rate),
                buffer_size: cpal::BufferSize::Default,
            };

            info!(
                channels = config.channels,
                sample_rate = config.sample_rate.0,
                sample_format = ?sample_format,
                "Using target sample rate"
            );

            (config, sample_format)
        } else {
            // Fall back to device default if target rate not supported
            warn!(
                target_sample_rate,
                "Target sample rate not supported, falling back to device default"
            );

            let default_config = device
                .default_output_config()
                .context("Failed to get default output config")?;

            let sample_format = default_config.sample_format();

            info!(
                channels = default_config.channels(),
                sample_rate = default_config.sample_rate().0,
                sample_format = ?sample_format,
                "Using device default sample rate (target not supported)"
            );

            (default_config.into(), sample_format)
        };

        Ok(Self {
            device,
            config: stream_config,
            sample_format,
        })
    }

    /// Play a simple tone at the specified frequency and duration
    ///
    /// # Arguments
    /// * `frequency` - Frequency in Hz (e.g., 440.0 for A4 note)
    /// * `duration_ms` - Duration in milliseconds
    pub async fn play_tone(&self, frequency: f32, duration_ms: u32) -> Result<()> {
        info!(
            frequency,
            duration_ms,
            device = ?self.device.name().unwrap_or_else(|_| "Unknown".to_string()),
            "Playing tone through audio output"
        );

        let sample_rate = self.config.sample_rate.0 as f32;
        let num_samples = (sample_rate * duration_ms as f32 / 1000.0) as usize;

        // Generate sine wave samples with envelope to avoid clicks
        let mut samples = Vec::with_capacity(num_samples);
        let fade_samples = (sample_rate * 0.005) as usize; // 5ms fade in/out

        for i in 0..num_samples {
            let t = i as f32 / sample_rate;
            let mut sample = (t * frequency * 2.0 * std::f32::consts::PI).sin() * 0.5; // 50% volume for better audibility

            // Apply fade in/out envelope to prevent clicks
            if i < fade_samples {
                sample *= i as f32 / fade_samples as f32;
            } else if i > num_samples - fade_samples {
                sample *= (num_samples - i) as f32 / fade_samples as f32;
            }

            samples.push(sample);
        }

        debug!(sample_count = samples.len(), "Generated tone samples");
        self.play_audio_samples(&samples).await
    }

    /// Play raw PCM audio samples (f32 format, -1.0 to 1.0 range)
    ///
    /// # Arguments
    /// * `samples` - Audio samples in f32 format, normalized to [-1.0, 1.0]
    pub async fn play_audio_samples(&self, samples: &[f32]) -> Result<()> {
        info!(
            sample_count = samples.len(),
            channels = self.config.channels,
            sample_rate = self.config.sample_rate.0,
            format = ?self.sample_format,
            "Starting audio playback"
        );

        // Clone device and config for the playback thread
        let device = self.device.clone();
        let config = self.config.clone();
        let sample_format = self.sample_format;
        let samples_vec = samples.to_vec();

        // Calculate playback duration
        let sample_rate = config.sample_rate.0 as f32;
        let duration_secs = samples_vec.len() as f32 / sample_rate;
        let duration_ms = (duration_secs * 1000.0) as u64;

        // Spawn blocking task for audio playback
        // This avoids holding cpal::Stream across await points
        let handle = tokio::task::spawn_blocking(move || -> Result<()> {
            // Clone samples into an Arc for thread-safe sharing
            let samples = Arc::new(samples_vec);
            let sample_index = Arc::new(Mutex::new(0usize));
            let channels = config.channels as usize;

            // Create audio stream
            let samples_clone = samples.clone();
            let sample_index_clone = sample_index.clone();

            let stream = match sample_format {
                SampleFormat::F32 => {
                    device.build_output_stream(
                        &config,
                        move |data: &mut [f32], _: &cpal::OutputCallbackInfo| {
                            Self::write_samples_f32(
                                data,
                                &samples_clone,
                                &sample_index_clone,
                                channels,
                            );
                        },
                        move |err| {
                            warn!("Audio stream error: {}", err);
                        },
                        None,
                    )?
                }
                SampleFormat::I16 => {
                    device.build_output_stream(
                        &config,
                        move |data: &mut [i16], _: &cpal::OutputCallbackInfo| {
                            Self::write_samples_i16(
                                data,
                                &samples_clone,
                                &sample_index_clone,
                                channels,
                            );
                        },
                        move |err| {
                            warn!("Audio stream error: {}", err);
                        },
                        None,
                    )?
                }
                SampleFormat::U16 => {
                    device.build_output_stream(
                        &config,
                        move |data: &mut [u16], _: &cpal::OutputCallbackInfo| {
                            Self::write_samples_u16(
                                data,
                                &samples_clone,
                                &sample_index_clone,
                                channels,
                            );
                        },
                        move |err| {
                            warn!("Audio stream error: {}", err);
                        },
                        None,
                    )?
                }
                format => {
                    anyhow::bail!("Unsupported sample format: {:?}", format);
                }
            };

            // Start the stream
            info!("Starting audio stream...");
            stream.play().context("Failed to start audio stream")?;
            info!("Audio stream started successfully");

            info!(
                duration_ms,
                "Waiting for audio playback to complete"
            );

            // Use std::thread::sleep since we're in a blocking task
            std::thread::sleep(std::time::Duration::from_millis(duration_ms + 100));

            // Check how many samples were actually played
            let final_index = *sample_index.lock().unwrap();
            let samples_played = final_index.min(samples.len());
            let playback_percentage = (samples_played as f32 / samples.len() as f32 * 100.0) as u32;

            // Stream will be dropped here, stopping playback
            drop(stream);

            info!(
                samples_played,
                total_samples = samples.len(),
                playback_percentage,
                "Audio playback complete"
            );

            if playback_percentage < 95 {
                warn!(
                    "Audio playback may have been incomplete ({}/{}% played)",
                    samples_played, playback_percentage
                );
            }

            Ok(())
        });

        // Await the blocking task
        handle.await.context("Audio playback task panicked")??;

        Ok(())
    }

    /// Write samples to f32 output buffer
    fn write_samples_f32(
        data: &mut [f32],
        samples: &[f32],
        sample_index: &Arc<Mutex<usize>>,
        channels: usize,
    ) {
        let mut idx = sample_index.lock().unwrap();

        for frame in data.chunks_mut(channels) {
            if *idx >= samples.len() {
                // Fill with silence when we run out of samples
                for sample in frame.iter_mut() {
                    *sample = 0.0;
                }
            } else {
                let sample_value = samples[*idx];
                *idx += 1;

                // Duplicate sample across all channels (mono -> stereo/multi)
                for sample in frame.iter_mut() {
                    *sample = sample_value;
                }
            }
        }
    }

    /// Write samples to i16 output buffer
    fn write_samples_i16(
        data: &mut [i16],
        samples: &[f32],
        sample_index: &Arc<Mutex<usize>>,
        channels: usize,
    ) {
        let mut idx = sample_index.lock().unwrap();

        for frame in data.chunks_mut(channels) {
            if *idx >= samples.len() {
                // Fill with silence
                for sample in frame.iter_mut() {
                    *sample = 0;
                }
            } else {
                let sample_value = samples[*idx];
                *idx += 1;

                // Convert f32 [-1.0, 1.0] to i16 [i16::MIN, i16::MAX]
                let sample_i16 = (sample_value * i16::MAX as f32) as i16;

                for sample in frame.iter_mut() {
                    *sample = sample_i16;
                }
            }
        }
    }

    /// Write samples to u16 output buffer
    fn write_samples_u16(
        data: &mut [u16],
        samples: &[f32],
        sample_index: &Arc<Mutex<usize>>,
        channels: usize,
    ) {
        let mut idx = sample_index.lock().unwrap();

        for frame in data.chunks_mut(channels) {
            if *idx >= samples.len() {
                // Fill with silence (u16 center is 32768)
                for sample in frame.iter_mut() {
                    *sample = u16::MAX / 2;
                }
            } else {
                let sample_value = samples[*idx];
                *idx += 1;

                // Convert f32 [-1.0, 1.0] to u16 [0, u16::MAX]
                let sample_u16 = ((sample_value + 1.0) * 0.5 * u16::MAX as f32) as u16;

                for sample in frame.iter_mut() {
                    *sample = sample_u16;
                }
            }
        }
    }

    /// Start a continuous audio stream with a buffer queue
    ///
    /// Returns only the sender for audio frames. The stream is kept alive internally
    /// in a blocking thread until the sender is dropped.
    /// Audio frames sent via the sender will play continuously without gaps.
    ///
    /// # Returns
    /// * `mpsc::Sender<Vec<f32>>` - Send audio frames here to play them
    pub fn start_continuous_stream(&self) -> Result<mpsc::Sender<Vec<f32>>> {
        info!("Starting continuous audio stream with buffer queue");

        // Create buffer queue for audio samples
        let buffer_queue: Arc<Mutex<VecDeque<f32>>> = Arc::new(Mutex::new(VecDeque::new()));
        let buffer_queue_clone = buffer_queue.clone();

        // Create channel for receiving audio frames
        let (tx, mut rx) = mpsc::channel::<Vec<f32>>(100); // Buffer up to 100 frames (~8 seconds at 80ms/frame)

        // Capture sample rate before spawning (avoid lifetime issues)
        let sample_rate = self.config.sample_rate.0;

        // Spawn task to receive frames and add to buffer queue
        tokio::spawn(async move {
            info!("CONTINUOUS_STREAM: Frame receiver task started");
            let mut total_frames = 0;

            // v0.1.0-2025.11.5.24: Initialize WAV export with periodic flushing
            // Signal handlers don't work (Tokio/TUI interference) - write samples incrementally instead
            if std::env::var("MOSHI_DEBUG_WAV").is_ok() {
                if let Err(e) = crate::audio_output::init_wav_export(sample_rate) {
                    warn!("MOSHI_DEBUG: Failed to initialize WAV export: {}", e);
                }
            }

            while let Some(samples) = rx.recv().await {
                total_frames += 1;

                // CRITICAL DEBUG: Analyze sample values
                let num_samples = samples.len();
                let non_zero_count = samples.iter().filter(|&&s| s.abs() > 1e-6).count();
                let min_val = samples.iter().cloned().fold(f32::INFINITY, f32::min);
                let max_val = samples.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
                let avg_val = samples.iter().sum::<f32>() / num_samples as f32;

                info!(
                    "MOSHI_AUDIO_DEBUG: Frame #{} | {} samples | non-zero: {} ({:.1}%) | min: {:.6} | max: {:.6} | avg: {:.6}",
                    total_frames,
                    num_samples,
                    non_zero_count,
                    (non_zero_count as f32 / num_samples as f32) * 100.0,
                    min_val,
                    max_val,
                    avg_val
                );

                let mut queue = buffer_queue_clone.lock().unwrap();
                let queue_len_before = queue.len();

                // v0.1.0-2025.11.5.30: Add samples to queue in FIFO order
                // FIX: Changed push_front() to push_back() - audio was playing backward!
                // Each frame was being reversed, causing garbled+choppy sound
                for &sample in samples.iter() {
                    queue.push_back(sample);
                }

                let queue_len_after = queue.len();
                debug!(
                    "CONTINUOUS_STREAM: Frame #{} added to queue (before: {} samples, after: {} samples)",
                    total_frames,
                    queue_len_before,
                    queue_len_after
                );

                // v0.1.0-2025.11.5.24: Write samples to WAV file IMMEDIATELY (periodic flush mode)
                // Samples written to disk as they arrive - survives process termination
                if std::env::var("MOSHI_DEBUG_WAV").is_ok() {
                    // Convert f32 to i16
                    let samples_i16: Vec<i16> = samples
                        .iter()
                        .map(|&s| (s.clamp(-1.0, 1.0) * 32767.0) as i16)
                        .collect();
                    crate::audio_output::write_wav_samples(&samples_i16);
                }

                // Warn if queue is getting too large (>5 seconds of audio)
                let max_buffer_samples = (sample_rate as usize) * 5;
                if queue_len_after > max_buffer_samples {
                    warn!(
                        "CONTINUOUS_STREAM: Buffer queue is large ({} samples = {:.2}s) - may indicate slow playback",
                        queue_len_after,
                        queue_len_after as f32 / sample_rate as f32
                    );
                }
            }

            // v0.1.0-2025.11.5.22: WAV writing happens in signal handler (write_wav_on_exit)
            // Removed old finalization code that never executed on SIGTERM
            info!("CONTINUOUS_STREAM: Frame receiver task ended - channel closed (processed {} frames)", total_frames);
        });

        // Create continuous audio stream
        let sample_format = self.sample_format;
        let channels = self.config.channels as usize;
        let buffer_queue_stream = buffer_queue.clone();

        info!(
            channels,
            sample_rate = self.config.sample_rate.0,
            format = ?sample_format,
            "CONTINUOUS_STREAM: Creating continuous audio stream"
        );

        let stream = match sample_format {
            SampleFormat::F32 => {
                self.device.build_output_stream(
                    &self.config,
                    move |data: &mut [f32], _: &cpal::OutputCallbackInfo| {
                        let mut queue = buffer_queue_stream.lock().unwrap();

                        for frame in data.chunks_mut(channels) {
                            // v0.1.0-2025.11.5.30: FIFO order (was pop_back, now pop_front)
                            if let Some(sample_value) = queue.pop_front() {
                                // We have audio - play it
                                for sample in frame.iter_mut() {
                                    *sample = sample_value;
                                }
                            } else {
                                // Buffer empty - play silence to avoid gaps
                                for sample in frame.iter_mut() {
                                    *sample = 0.0;
                                }
                            }
                        }
                    },
                    move |err| {
                        warn!("CONTINUOUS_STREAM: Audio stream error: {}", err);
                    },
                    None,
                )?
            }
            SampleFormat::I16 => {
                self.device.build_output_stream(
                    &self.config,
                    move |data: &mut [i16], _: &cpal::OutputCallbackInfo| {
                        let mut queue = buffer_queue_stream.lock().unwrap();

                        for frame in data.chunks_mut(channels) {
                            if let Some(sample_value) = queue.pop_front() {
                                let sample_i16 = (sample_value * i16::MAX as f32) as i16;
                                for sample in frame.iter_mut() {
                                    *sample = sample_i16;
                                }
                            } else {
                                for sample in frame.iter_mut() {
                                    *sample = 0;
                                }
                            }
                        }
                    },
                    move |err| {
                        warn!("CONTINUOUS_STREAM: Audio stream error: {}", err);
                    },
                    None,
                )?
            }
            SampleFormat::U16 => {
                self.device.build_output_stream(
                    &self.config,
                    move |data: &mut [u16], _: &cpal::OutputCallbackInfo| {
                        let mut queue = buffer_queue_stream.lock().unwrap();

                        for frame in data.chunks_mut(channels) {
                            if let Some(sample_value) = queue.pop_front() {
                                let sample_u16 = ((sample_value + 1.0) * 0.5 * u16::MAX as f32) as u16;
                                for sample in frame.iter_mut() {
                                    *sample = sample_u16;
                                }
                            } else {
                                for sample in frame.iter_mut() {
                                    *sample = u16::MAX / 2; // Center value for silence
                                }
                            }
                        }
                    },
                    move |err| {
                        warn!("CONTINUOUS_STREAM: Audio stream error: {}", err);
                    },
                    None,
                )?
            }
            format => {
                anyhow::bail!("Unsupported sample format: {:?}", format);
            }
        };

        // Start the stream
        stream.play().context("Failed to start continuous audio stream")?;
        info!("CONTINUOUS_STREAM: Stream started successfully");

        // Leak the stream - it will live for the entire program lifetime
        // This is intentional: we want continuous audio playback until program exit
        // The stream is not Send, so we can't move it to another thread safely
        let _ = Box::leak(Box::new(stream));
        info!("CONTINUOUS_STREAM: Stream leaked (will live until program exit)");

        Ok(tx)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_audio_output_device_creation() {
        // This test may fail in CI environments without audio devices
        if let Ok(device) = AudioOutputDevice::new() {
            assert!(device.config.sample_rate.0 > 0);
            assert!(device.config.channels > 0);
        }
    }
}
