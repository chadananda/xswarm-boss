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

    #[serde(default)]
    pub subscription: SubscriptionConfig,

    #[serde(default)]
    pub direct_line: Option<DirectLineConfig>,

    #[serde(default)]
    pub communication: CommunicationConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OverlordConfig {
    #[serde(default = "default_persona")]
    pub persona: String,

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

/// Subscription configuration for premium features
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubscriptionConfig {
    /// Whether the user has an active premium subscription
    #[serde(default)]
    pub active: bool,

    /// Subscription tier (free, premium, enterprise)
    #[serde(default = "default_tier")]
    pub tier: String,

    /// Subscription expiry date (ISO 8601)
    #[serde(default)]
    pub expires_at: Option<String>,
}

/// Direct Line phone configuration (premium feature)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DirectLineConfig {
    /// User's phone number (E.164 format, e.g., +15551234567)
    pub user_phone: String,

    /// Twilio phone number assigned to this xSwarm instance
    pub xswarm_phone: String,

    /// Twilio account configuration
    pub twilio: TwilioConfig,

    /// Whether to call user on blocking issues
    #[serde(default = "default_true")]
    pub call_on_blocking: bool,

    /// Whether to allow user to call xSwarm
    #[serde(default = "default_true")]
    pub accept_inbound: bool,
}

/// Twilio API configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TwilioConfig {
    /// Twilio Account SID
    pub account_sid: String,

    /// Twilio Auth Token (stored securely)
    pub auth_token: String,

    /// Public webhook URL for this xSwarm instance
    pub webhook_url: String,
}

/// Complete communication configuration (email + phone + SMS)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommunicationConfig {
    /// User's real email (whitelist)
    pub user_email: String,

    /// User's real phone number (whitelist)
    pub user_phone: String,

    /// xSwarm's assigned email (username@xswarm.ai)
    pub xswarm_email: String,

    /// xSwarm's assigned phone number (optional, premium only)
    pub xswarm_phone: Option<String>,

    /// Channel configuration
    #[serde(default)]
    pub channels: ChannelConfig,

    /// SendGrid API key (shared across all users)
    pub sendgrid_api_key: Option<String>,

    /// Twilio credentials (shared pool)
    pub twilio: Option<TwilioCredentials>,
}

/// Communication channel settings
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChannelConfig {
    /// Email enabled (always true for free tier)
    #[serde(default = "default_true")]
    pub email_enabled: bool,

    /// Phone calls enabled (premium only)
    #[serde(default)]
    pub phone_enabled: bool,

    /// SMS enabled (premium only)
    #[serde(default)]
    pub sms_enabled: bool,

    /// Accept inbound calls from user
    #[serde(default = "default_true")]
    pub accept_inbound_calls: bool,

    /// Accept inbound SMS from user
    #[serde(default = "default_true")]
    pub accept_inbound_sms: bool,

    /// Accept inbound email from user
    #[serde(default = "default_true")]
    pub accept_inbound_email: bool,
}

/// Twilio credentials for communication (not persona-specific)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TwilioCredentials {
    pub account_sid: String,
    pub auth_token: String,
}

// Default value functions
fn default_persona() -> String {
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

fn default_tier() -> String {
    "free".to_string()
}

// Implement Default trait
impl Default for OverlordConfig {
    fn default() -> Self {
        Self {
            persona: default_persona(),
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

impl Default for SubscriptionConfig {
    fn default() -> Self {
        Self {
            active: false,
            tier: default_tier(),
            expires_at: None,
        }
    }
}

impl Default for ChannelConfig {
    fn default() -> Self {
        Self {
            email_enabled: true,  // Always enabled
            phone_enabled: false, // Premium only
            sms_enabled: false,   // Premium only
            accept_inbound_calls: true,
            accept_inbound_sms: true,
            accept_inbound_email: true,
        }
    }
}

impl Default for CommunicationConfig {
    fn default() -> Self {
        Self {
            user_email: String::new(),
            user_phone: String::new(),
            xswarm_email: String::new(),
            xswarm_phone: None,
            channels: ChannelConfig::default(),
            sendgrid_api_key: None,
            twilio: None,
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
            subscription: SubscriptionConfig::default(),
            direct_line: None,
            communication: CommunicationConfig::default(),
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
            "overlord.persona" => Some(self.overlord.persona.clone()),
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
            "subscription.active" => Some(self.subscription.active.to_string()),
            "subscription.tier" => Some(self.subscription.tier.clone()),
            "direct_line.user_phone" => self.direct_line.as_ref().map(|dl| dl.user_phone.clone()),
            "direct_line.xswarm_phone" => self.direct_line.as_ref().map(|dl| dl.xswarm_phone.clone()),
            _ => None,
        }
    }

    /// Set a configuration value by key (dot notation)
    pub fn set(&mut self, key: &str, value: &str) -> Result<()> {
        match key {
            "overlord.persona" => self.overlord.persona = value.to_string(),
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
