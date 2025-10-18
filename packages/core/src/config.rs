use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

/// Main configuration structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    #[serde(default)]
    pub overlord: OverlordConfig,

    #[serde(default)]
    pub voice: VoiceConfig,

    #[serde(default)]
    pub audio: AudioConfig,

    #[serde(default)]
    pub wake_word: WakeWordConfig,

    #[serde(default)]
    pub gpu: GpuConfig,

    #[serde(default)]
    pub vassal: Option<VassalConfig>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OverlordConfig {
    #[serde(default = "default_theme")]
    pub theme: String,

    #[serde(default = "default_true")]
    pub voice_enabled: bool,

    #[serde(default = "default_wake_word")]
    pub wake_word: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoiceConfig {
    #[serde(default = "default_voice_provider")]
    pub provider: String,

    #[serde(default)]
    pub model: Option<String>,

    #[serde(default = "default_true")]
    pub include_personality: bool,

    #[serde(default)]
    pub pipeline: Option<PipelineConfig>,

    #[serde(default)]
    pub local: Option<LocalVoiceConfig>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineConfig {
    pub stt_provider: String,
    pub llm_provider: String,
    pub tts_provider: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocalVoiceConfig {
    pub stt_model: String,
    pub llm_model: String,
    pub tts_model: String,
    pub model_path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioConfig {
    #[serde(default = "default_audio_device")]
    pub input_device: String,

    #[serde(default = "default_audio_device")]
    pub output_device: String,

    #[serde(default = "default_sample_rate")]
    pub sample_rate: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WakeWordConfig {
    #[serde(default = "default_wake_word_engine")]
    pub engine: String,

    #[serde(default = "default_sensitivity")]
    pub sensitivity: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GpuConfig {
    #[serde(default)]
    pub use_local: bool,

    #[serde(default = "default_fallback")]
    pub fallback: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VassalConfig {
    pub name: String,
    pub host: String,
    pub port: u16,
}

// Default value functions
fn default_theme() -> String {
    "hal-9000".to_string()
}

fn default_true() -> bool {
    true
}

fn default_wake_word() -> String {
    "hey hal".to_string()
}

fn default_voice_provider() -> String {
    "openai_realtime".to_string()
}

fn default_audio_device() -> String {
    "default".to_string()
}

fn default_sample_rate() -> u32 {
    16000
}

fn default_wake_word_engine() -> String {
    "porcupine".to_string()
}

fn default_sensitivity() -> f32 {
    0.5
}

fn default_fallback() -> Vec<String> {
    vec!["runpod".to_string(), "anthropic".to_string()]
}

// Implement Default trait
impl Default for OverlordConfig {
    fn default() -> Self {
        Self {
            theme: default_theme(),
            voice_enabled: default_true(),
            wake_word: default_wake_word(),
        }
    }
}

impl Default for VoiceConfig {
    fn default() -> Self {
        Self {
            provider: default_voice_provider(),
            model: Some("gpt-4o-realtime-preview".to_string()),
            include_personality: default_true(),
            pipeline: None,
            local: None,
        }
    }
}

impl Default for AudioConfig {
    fn default() -> Self {
        Self {
            input_device: default_audio_device(),
            output_device: default_audio_device(),
            sample_rate: default_sample_rate(),
        }
    }
}

impl Default for WakeWordConfig {
    fn default() -> Self {
        Self {
            engine: default_wake_word_engine(),
            sensitivity: default_sensitivity(),
        }
    }
}

impl Default for GpuConfig {
    fn default() -> Self {
        Self {
            use_local: false,
            fallback: default_fallback(),
        }
    }
}

impl Default for Config {
    fn default() -> Self {
        Self {
            overlord: OverlordConfig::default(),
            voice: VoiceConfig::default(),
            audio: AudioConfig::default(),
            wake_word: WakeWordConfig::default(),
            gpu: GpuConfig::default(),
            vassal: None,
        }
    }
}

impl Config {
    /// Get the config file path
    pub fn config_path() -> Result<PathBuf> {
        let config_dir = dirs::config_dir()
            .context("Could not determine config directory")?
            .join("xswarm");

        Ok(config_dir.join("config.toml"))
    }

    /// Get the config directory path
    pub fn config_dir() -> Result<PathBuf> {
        let config_dir = dirs::config_dir()
            .context("Could not determine config directory")?
            .join("xswarm");

        Ok(config_dir)
    }

    /// Load configuration from file, or create default if it doesn't exist
    pub fn load() -> Result<Self> {
        let config_path = Self::config_path()?;

        if config_path.exists() {
            let contents = fs::read_to_string(&config_path)
                .context("Failed to read config file")?;

            let config: Config = toml::from_str(&contents)
                .context("Failed to parse config file")?;

            Ok(config)
        } else {
            // Create default config
            let config = Config::default();
            config.save()?;
            Ok(config)
        }
    }

    /// Save configuration to file
    pub fn save(&self) -> Result<()> {
        let config_dir = Self::config_dir()?;
        let config_path = Self::config_path()?;

        // Create config directory if it doesn't exist
        fs::create_dir_all(&config_dir)
            .context("Failed to create config directory")?;

        // Serialize to TOML
        let toml_string = toml::to_string_pretty(self)
            .context("Failed to serialize config")?;

        // Write to file
        fs::write(&config_path, toml_string)
            .context("Failed to write config file")?;

        Ok(())
    }

    /// Get a configuration value by key (dot notation)
    pub fn get(&self, key: &str) -> Option<String> {
        match key {
            "overlord.theme" => Some(self.overlord.theme.clone()),
            "overlord.voice_enabled" => Some(self.overlord.voice_enabled.to_string()),
            "overlord.wake_word" => Some(self.overlord.wake_word.clone()),
            "voice.provider" => Some(self.voice.provider.clone()),
            "voice.model" => self.voice.model.clone(),
            "voice.include_personality" => Some(self.voice.include_personality.to_string()),
            "audio.input_device" => Some(self.audio.input_device.clone()),
            "audio.output_device" => Some(self.audio.output_device.clone()),
            "audio.sample_rate" => Some(self.audio.sample_rate.to_string()),
            "wake_word.engine" => Some(self.wake_word.engine.clone()),
            "wake_word.sensitivity" => Some(self.wake_word.sensitivity.to_string()),
            "gpu.use_local" => Some(self.gpu.use_local.to_string()),
            _ => None,
        }
    }

    /// Set a configuration value by key (dot notation)
    pub fn set(&mut self, key: &str, value: &str) -> Result<()> {
        match key {
            "overlord.theme" => self.overlord.theme = value.to_string(),
            "overlord.voice_enabled" => {
                self.overlord.voice_enabled = value.parse()
                    .context("Invalid boolean value")?;
            }
            "overlord.wake_word" => self.overlord.wake_word = value.to_string(),
            "voice.provider" => self.voice.provider = value.to_string(),
            "voice.model" => self.voice.model = Some(value.to_string()),
            "voice.include_personality" => {
                self.voice.include_personality = value.parse()
                    .context("Invalid boolean value")?;
            }
            "audio.input_device" => self.audio.input_device = value.to_string(),
            "audio.output_device" => self.audio.output_device = value.to_string(),
            "audio.sample_rate" => {
                self.audio.sample_rate = value.parse()
                    .context("Invalid sample rate")?;
            }
            "wake_word.engine" => self.wake_word.engine = value.to_string(),
            "wake_word.sensitivity" => {
                self.wake_word.sensitivity = value.parse()
                    .context("Invalid sensitivity value")?;
            }
            "gpu.use_local" => {
                self.gpu.use_local = value.parse()
                    .context("Invalid boolean value")?;
            }
            _ => anyhow::bail!("Unknown config key: {}", key),
        }

        Ok(())
    }
}
