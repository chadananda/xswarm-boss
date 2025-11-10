// Wake Word Configuration Management
//
// This module handles loading, saving, and validating wake word configurations.

use anyhow::{Result, Context};
use serde::{Deserialize, Serialize};
use std::path::Path;
use tokio::fs;

use super::WakeWordConfig;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WakeWordUserConfig {
    pub wake_words: WakeWordConfig,
    pub voice_training: VoiceTrainingConfig,
    pub privacy: PrivacyConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoiceTrainingConfig {
    /// Enable custom wake word training
    pub enable_custom_training: bool,
    /// Number of sample recordings required for training
    pub training_samples_count: u32,
    /// Path to store trained voice models
    pub voice_model_path: Option<String>,
}

impl Default for VoiceTrainingConfig {
    fn default() -> Self {
        Self {
            enable_custom_training: false,
            training_samples_count: 20,
            voice_model_path: Some("~/.xswarm/voice_models/".to_string()),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrivacyConfig {
    /// Only process audio locally, never send to cloud
    pub local_processing_only: bool,
    /// Enable audio logging for debugging
    pub audio_logging_enabled: bool,
    /// Automatically delete audio recordings after processing
    pub auto_delete_recordings: bool,
    /// How long to retain recordings (hours)
    pub retention_hours: u32,
}

impl Default for PrivacyConfig {
    fn default() -> Self {
        Self {
            local_processing_only: true,
            audio_logging_enabled: false,
            auto_delete_recordings: true,
            retention_hours: 24,
        }
    }
}

impl Default for WakeWordUserConfig {
    fn default() -> Self {
        Self {
            wake_words: WakeWordConfig::default(),
            voice_training: VoiceTrainingConfig::default(),
            privacy: PrivacyConfig::default(),
        }
    }
}

impl WakeWordUserConfig {
    /// Load configuration from TOML file
    pub async fn load_from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let content = fs::read_to_string(&path)
            .await
            .with_context(|| {
                format!("Failed to read config file: {}", path.as_ref().display())
            })?;

        let config: Self = toml::from_str(&content)
            .with_context(|| {
                format!("Failed to parse config file: {}", path.as_ref().display())
            })?;

        config.validate()?;

        Ok(config)
    }

    /// Save configuration to TOML file
    pub async fn save_to_file<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        self.validate()?;

        let content = toml::to_string_pretty(self)
            .context("Failed to serialize config to TOML")?;

        // Create parent directory if it doesn't exist
        if let Some(parent) = path.as_ref().parent() {
            fs::create_dir_all(parent).await.with_context(|| {
                format!("Failed to create config directory: {}", parent.display())
            })?;
        }

        fs::write(&path, content).await.with_context(|| {
            format!("Failed to write config file: {}", path.as_ref().display())
        })?;

        Ok(())
    }

    /// Validate the configuration
    pub fn validate(&self) -> Result<()> {
        // Validate wake word config
        if self.wake_words.sensitivity < 0.0 || self.wake_words.sensitivity > 1.0 {
            anyhow::bail!(
                "Wake word sensitivity must be between 0.0 and 1.0, got: {}",
                self.wake_words.sensitivity
            );
        }

        if self.wake_words.threshold < 0.0 || self.wake_words.threshold > 1.0 {
            anyhow::bail!(
                "Wake word threshold must be between 0.0 and 1.0, got: {}",
                self.wake_words.threshold
            );
        }

        if self.wake_words.keywords.is_empty() {
            anyhow::bail!("At least one wake word must be configured");
        }

        // Validate voice training config
        if self.voice_training.training_samples_count < 5 {
            anyhow::bail!(
                "Training samples count must be at least 5, got: {}",
                self.voice_training.training_samples_count
            );
        }

        // Validate privacy config
        if self.privacy.retention_hours == 0 && !self.privacy.auto_delete_recordings {
            anyhow::bail!(
                "If auto_delete_recordings is false, retention_hours must be greater than 0"
            );
        }

        Ok(())
    }

    /// Get the default configuration file path
    pub fn default_config_path() -> Result<std::path::PathBuf> {
        let home = dirs::home_dir().context("Could not determine home directory")?;
        Ok(home.join(".xswarm").join("config").join("wake-word.toml"))
    }

    /// Load configuration from default location, or create default if not exists
    pub async fn load_or_default() -> Result<Self> {
        let config_path = Self::default_config_path()?;

        if config_path.exists() {
            Self::load_from_file(&config_path).await
        } else {
            let config = Self::default();
            config.save_to_file(&config_path).await?;
            Ok(config)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config_validation() {
        let config = WakeWordUserConfig::default();
        assert!(config.validate().is_ok());
    }

    #[test]
    fn test_invalid_sensitivity() {
        let mut config = WakeWordUserConfig::default();
        config.wake_words.sensitivity = 1.5;
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_invalid_threshold() {
        let mut config = WakeWordUserConfig::default();
        config.wake_words.threshold = -0.1;
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_empty_keywords() {
        let mut config = WakeWordUserConfig::default();
        config.wake_words.keywords.clear();
        assert!(config.validate().is_err());
    }

    #[tokio::test]
    async fn test_config_serialization() {
        let config = WakeWordUserConfig::default();
        let toml = toml::to_string_pretty(&config).unwrap();
        let deserialized: WakeWordUserConfig = toml::from_str(&toml).unwrap();
        assert!(deserialized.validate().is_ok());
    }
}
