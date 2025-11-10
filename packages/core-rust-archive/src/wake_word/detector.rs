// Wake Word Detector using OpenWakeWord (oww-rs)
//
// This module handles wake word detection using oww-rs, which is a Rust
// implementation of OpenWakeWord using ONNX Runtime.

use anyhow::{Result, anyhow};
use cpal::{Stream, StreamConfig, traits::*};
use std::sync::Arc;
use tokio::sync::Mutex;
use tracing::{info, warn, error};

/// Wake word detector using OpenWakeWord (oww-rs)
///
/// Note: This detector is not Send because it contains cpal::Stream.
/// It should only be used in a single-threaded context or wrapped properly.
pub struct WakeWordDetector {
    audio_stream: Option<Stream>,
    detection_sender: tokio::sync::mpsc::Sender<String>,
    keywords: Vec<String>,
    threshold: f32,
    is_running: Arc<Mutex<bool>>,
}

// SAFETY: WakeWordDetector is deliberately not Send because cpal::Stream
// contains raw pointers. Do not add Send/Sync implementations.

impl WakeWordDetector {
    /// Create a new wake word detector
    pub async fn new(
        keywords: Vec<String>,
        _sensitivity: f32,
        threshold: f32,
        detection_sender: tokio::sync::mpsc::Sender<String>,
    ) -> Result<Self> {
        info!("Initializing wake word detector (simplified implementation)");

        // For now, we'll use a simplified detector that doesn't require ONNX models
        // In production, this would load the oww-rs models

        Ok(Self {
            audio_stream: None,
            detection_sender,
            keywords,
            threshold,
            is_running: Arc::new(Mutex::new(false)),
        })
    }

    /// Start audio stream and detection
    pub async fn start_detection(&mut self) -> Result<()> {
        use crate::permissions;

        // Check microphone permissions (especially on macOS)
        if !permissions::ensure_microphone_permission(false)? {
            return Err(anyhow!("Microphone permission denied"));
        }

        let host = cpal::default_host();
        let device = host
            .default_input_device()
            .ok_or_else(|| anyhow!("No input device available"))?;

        info!("Using audio input device: {}", device.name()?);

        // OpenWakeWord expects 16kHz 16-bit mono PCM
        let stream_config = StreamConfig {
            channels: 1,
            sample_rate: cpal::SampleRate(16000),
            buffer_size: cpal::BufferSize::Default,
        };

        info!("Audio config: {:?}", stream_config);

        let sender = self.detection_sender.clone();
        let threshold = self.threshold;
        let is_running = self.is_running.clone();
        let keywords = self.keywords.clone();

        // Set running state
        *is_running.lock().await = true;
        let is_running_clone = is_running.clone();

        // Build audio input stream
        let stream = device
            .build_input_stream(
                &stream_config,
                move |data: &[i16], _: &cpal::InputCallbackInfo| {
                    let sender = sender.clone();
                    let keywords = keywords.clone();
                    let samples = data.to_vec();

                    // Process audio in a separate thread to avoid blocking
                    tokio::spawn(async move {
                        // Convert i16 samples to f32
                        let audio: Vec<f32> = samples
                            .iter()
                            .map(|&s| s as f32 / 32768.0)
                            .collect();

                        // TODO: Implement actual wake word detection with oww-rs
                        // For now, this is a placeholder that simulates detection

                        // Calculate RMS to detect voice activity
                        let rms: f32 = audio.iter().map(|&x| x * x).sum::<f32>() / audio.len() as f32;
                        let rms = rms.sqrt();

                        // If voice activity detected (simple threshold)
                        if rms > threshold {
                            // In production, this would check against actual wake word models
                            // For now, we'll just log voice activity
                            if rand::random::<f32>() < 0.001 {  // Very rare random detection for testing
                                if let Some(keyword) = keywords.first() {
                                    info!("Voice activity detected (simulated wake word: {})", keyword);
                                    let _ = sender.send(keyword.clone()).await;
                                }
                            }
                        }
                    });
                },
                move |err| {
                    error!("Audio stream error: {}", err);
                    if let Ok(mut running) = is_running_clone.try_lock() {
                        *running = false;
                    }
                },
                None,
            )
            .map_err(|e| anyhow!("Failed to build input stream: {}", e))?;

        // Start the stream
        stream
            .play()
            .map_err(|e| anyhow!("Failed to start stream: {}", e))?;

        self.audio_stream = Some(stream);

        info!("Wake word detection started, listening for keywords: {:?}", self.keywords);
        info!("NOTE: Using simplified detector - full oww-rs integration pending");

        Ok(())
    }

    /// Stop detection
    pub fn stop_detection(mut self) {
        if let Some(stream) = self.audio_stream.take() {
            drop(stream); // Automatically stops the stream
            info!("Wake word detection stopped");
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_detector_creation() {
        let (tx, _rx) = tokio::sync::mpsc::channel(10);

        let result = WakeWordDetector::new(
            vec!["hey_hal".to_string()],
            0.5,
            0.5,
            tx,
        )
        .await;

        assert!(result.is_ok(), "Detector should be created successfully");
    }

    #[tokio::test]
    async fn test_detector_keywords() {
        let (tx, _rx) = tokio::sync::mpsc::channel(10);
        let keywords = vec!["hey_hal".to_string(), "hey_xswarm".to_string()];

        let detector = WakeWordDetector::new(
            keywords.clone(),
            0.5,
            0.5,
            tx,
        )
        .await
        .expect("Failed to create detector");

        assert_eq!(detector.keywords, keywords);
    }
}
