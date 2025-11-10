// Wake Word Detection System
//
// This module provides wake word detection capabilities using Rustpotter,
// an open-source wake word spotter. It supports:
// - Multiple wake words (Hey HAL, Hey xSwarm, custom)
// - Background listening with minimal CPU usage
// - Privacy-first local processing
// - Proactive suggestion system
// - Integration with existing MOSHI voice system

pub mod config;
pub mod detector;
pub mod suggestions;

use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::{RwLock, Mutex};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WakeWordConfig {
    /// Enable wake word detection
    pub enabled: bool,
    /// Detection sensitivity (0.0 - 1.0, higher = more sensitive but more false positives)
    pub sensitivity: f32,
    /// Detection threshold (0.0 - 1.0, higher = more strict)
    pub threshold: f32,
    /// Active wake words to listen for
    pub keywords: Vec<String>,
    /// Path to custom wake word models
    pub custom_models_path: String,
    /// Enable proactive suggestion system
    pub enable_suggestions: bool,
    /// Interval between suggestions (minutes)
    pub suggestion_interval_minutes: u32,
    /// Privacy mode (disable all audio logging)
    pub privacy_mode: bool,
    /// Specific audio input device (None = default)
    pub audio_device: Option<String>,
}

impl Default for WakeWordConfig {
    fn default() -> Self {
        Self {
            enabled: false,  // Disabled by default due to Send/Sync constraints
            sensitivity: 0.5,
            threshold: 0.5,
            keywords: vec!["hey_hal".to_string(), "hey_xswarm".to_string()],
            custom_models_path: "~/.xswarm/wake_words/".to_string(),
            enable_suggestions: true,
            suggestion_interval_minutes: 30,
            privacy_mode: true,
            audio_device: None,
        }
    }
}

/// Main wake word detection system
///
/// NOTE: Wake word detection is currently disabled by default because the underlying
/// cpal::Stream is not Send/Sync. This needs to be run in a LocalSet or refactored.
pub struct WakeWordSystem {
    config: Arc<RwLock<WakeWordConfig>>,
    suggestions: Arc<suggestions::SuggestionEngine>,
    is_listening: Arc<RwLock<bool>>,
}

impl WakeWordSystem {
    /// Create a new wake word detection system
    pub async fn new(config: WakeWordConfig) -> Result<Self> {
        let (suggestion_tx, _suggestion_rx) = tokio::sync::mpsc::channel::<String>(100);

        let suggestions = suggestions::SuggestionEngine::new(
            suggestion_tx,
            config.suggestion_interval_minutes,
        );

        Ok(Self {
            config: Arc::new(RwLock::new(config)),
            suggestions: Arc::new(suggestions),
            is_listening: Arc::new(RwLock::new(false)),
        })
    }

    /// Start listening for wake words
    ///
    /// NOTE: This is currently a no-op stub because wake word detection
    /// requires refactoring to handle Send/Sync constraints properly.
    pub async fn start_listening(&self) -> Result<()> {
        let config = self.config.read().await;

        if !config.enabled {
            tracing::warn!("Wake word detection is disabled in config");
            return Ok(());
        }

        tracing::warn!("Wake word detection start requested but not yet implemented");
        tracing::warn!("This feature requires LocalSet or refactoring for Send/Sync safety");

        // Start suggestion system if enabled
        if config.enable_suggestions {
            self.suggestions.start_suggestion_loop().await?;
        }

        Ok(())
    }

    /// Stop listening for wake words
    pub async fn stop_listening(&self) -> Result<()> {
        *self.is_listening.write().await = false;
        tracing::info!("Wake word detection stopped");
        Ok(())
    }

    /// Check if currently listening
    pub async fn is_listening(&self) -> bool {
        *self.is_listening.read().await
    }

    /// Add a custom wake word
    pub async fn add_custom_wake_word(&self, keyword: &str, model_path: &str) -> Result<()> {
        let mut config = self.config.write().await;

        if !config.keywords.contains(&keyword.to_string()) {
            config.keywords.push(keyword.to_string());
        }

        tracing::info!("Custom wake word added: {} (model: {})", keyword, model_path);

        Ok(())
    }

    /// Update sensitivity
    pub async fn set_sensitivity(&self, sensitivity: f32) -> Result<()> {
        let mut config = self.config.write().await;
        config.sensitivity = sensitivity.max(0.0).min(1.0);

        // If detector is running, restart it with new sensitivity
        if *self.is_listening.read().await {
            drop(config);
            self.stop_listening().await?;
            self.start_listening().await?;
        }

        Ok(())
    }

    /// Update threshold
    pub async fn set_threshold(&self, threshold: f32) -> Result<()> {
        let mut config = self.config.write().await;
        config.threshold = threshold.max(0.0).min(1.0);

        // If detector is running, restart it with new threshold
        if *self.is_listening.read().await {
            drop(config);
            self.stop_listening().await?;
            self.start_listening().await?;
        }

        Ok(())
    }

    /// Enable or disable suggestions
    pub async fn enable_suggestions(&self, enabled: bool) -> Result<()> {
        let mut config = self.config.write().await;
        config.enable_suggestions = enabled;

        if enabled && *self.is_listening.read().await {
            self.suggestions.start_suggestion_loop().await?;
        }

        Ok(())
    }
}
