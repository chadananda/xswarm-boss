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
use cpal::{Device, StreamConfig, SampleFormat};
use std::sync::{Arc, Mutex};
use tracing::{debug, info, warn};

/// Audio output device manager for speaker playback
pub struct AudioOutputDevice {
    device: Device,
    config: StreamConfig,
    sample_format: SampleFormat,
}

impl AudioOutputDevice {
    /// Create a new audio output device using the system's default output
    pub fn new() -> Result<Self> {
        info!("Initializing audio output device");

        // Get the default host (CoreAudio on macOS, WASAPI on Windows, ALSA on Linux)
        let host = cpal::default_host();

        // Get the default output device
        let device = host
            .default_output_device()
            .context("No default audio output device found")?;

        info!(device_name = ?device.name(), "Found audio output device");

        // Get the default output configuration
        let config = device
            .default_output_config()
            .context("Failed to get default output config")?;

        let sample_format = config.sample_format();

        debug!(
            channels = config.channels(),
            sample_rate = config.sample_rate().0,
            sample_format = ?sample_format,
            "Audio output config"
        );

        // Convert to StreamConfig
        let stream_config = config.into();

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
