use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

// Re-export server configuration
pub use crate::server_client::{ServerConfig, UserIdentity};

/// Admin user configuration from config.toml [admin] section
/// This represents the SINGLE admin user configured in config.toml
/// Regular users are stored in the database, NOT in config files
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdminUserConfig {
    pub username: String,
    pub name: String,
    pub email: String,
    pub phone: String,
    pub xswarm_email: String,
    pub xswarm_phone: String,
    #[serde(default = "default_persona")]
    pub persona: String,
    #[serde(default = "default_wake_word")]
    pub wake_word: String,
    #[serde(default = "default_admin_tier")]
    pub subscription_tier: String,

    // Admin-only permissions
    #[serde(default = "default_access_level")]
    pub access_level: String,
    #[serde(default = "default_true")]
    pub can_provision_numbers: bool,
    #[serde(default = "default_true")]
    pub can_view_all_users: bool,
    #[serde(default = "default_true")]
    pub can_manage_subscriptions: bool,
    #[serde(default = "default_true")]
    pub can_manage_config: bool,
    #[serde(default = "default_true")]
    pub can_access_all_channels: bool,
}

fn default_admin_tier() -> String {
    "admin".to_string()
}

/// Project-level configuration (loaded from config.toml)
/// Contains non-secret configuration safe to commit to version control
/// Note: Environment (dev/staging/prod) is detected from ENVIRONMENT or NODE_ENV env vars
///
/// IMPORTANT: User configuration architecture:
/// - Admin user: Configured in [admin] section of config.toml (single user, full access)
/// - Regular users: Stored in Turso database (multiple users, limited permissions)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectConfig {
    // NOTE: Admin user is the ONLY user in config.toml
    // Regular users are in the database
    #[serde(default)]
    pub admin: AdminUserConfig,

    #[serde(default)]
    pub twilio: TwilioProjectConfig,

    #[serde(default)]
    pub stripe: StripeProjectConfig,

    #[serde(default)]
    pub sendgrid: SendGridProjectConfig,

    #[serde(default)]
    pub turso: TursoProjectConfig,

    #[serde(default)]
    pub storage: StorageConfig,

    #[serde(default)]
    pub features: FeaturesConfig,

    #[serde(default)]
    pub ai: AiProjectConfig,

    #[serde(default)]
    pub voice: VoiceProjectConfig,

    #[serde(default)]
    pub test_user: TestUserConfig,

    #[serde(default)]
    pub development: DevelopmentConfig,

    // Subscription tier configurations (templates for users)
    #[serde(default)]
    pub subscription: SubscriptionTiers,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TwilioProjectConfig {
    pub account_sid: Option<String>,
    pub test_account_sid: Option<String>,
    pub test_receive_number: Option<String>,
    pub test_send_number: Option<String>,
    pub test_receive_webhook: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StripeProjectConfig {
    pub publishable_key: Option<String>,
    #[serde(default)]
    pub prices: StripePrices,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StripePrices {
    pub premium: Option<String>,
    pub voice: Option<String>,
    pub sms: Option<String>,
    pub phone: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SendGridProjectConfig {
    #[serde(default = "default_sendgrid_domain")]
    pub domain: String,
    pub test_user_email: Option<String>,
    pub test_xswarm_email: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TursoProjectConfig {
    pub database_name: Option<String>,
    pub organization: Option<String>,
    pub database_url: Option<String>,
    #[serde(default = "default_primary_region")]
    pub primary_region: String,
    #[serde(default)]
    pub replica_regions: Vec<String>,
    #[serde(default)]
    pub local_replica: TursoLocalReplicaConfig,
    #[serde(default)]
    pub backup: TursoBackupConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TursoLocalReplicaConfig {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_sync_interval")]
    pub sync_interval_seconds: u64,
    pub local_db_path: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TursoBackupConfig {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_retention_days")]
    pub retention_days: u32,
    #[serde(default)]
    pub manual_backup_enabled: bool,
    pub backup_schedule: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StorageConfig {
    /// Provider: "s3" (AWS), "r2" (Cloudflare R2), or "custom"
    #[serde(default = "default_storage_provider")]
    pub provider: String,

    /// Primary bucket for assets (user uploads, generated files, etc.)
    #[serde(default = "default_bucket_name")]
    pub bucket_name: String,

    /// AWS region or hint for R2
    #[serde(default = "default_storage_region")]
    pub region: String,

    /// Custom endpoint (required for R2, optional for S3-compatible services)
    pub endpoint: Option<String>,

    /// Public URL for assets (if using CDN or public bucket)
    pub public_url: Option<String>,

    /// Backup bucket configuration
    #[serde(default)]
    pub backup: StorageBackupConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StorageBackupConfig {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_backup_bucket")]
    pub bucket_name: String,
    #[serde(default = "default_backup_retention_days")]
    pub retention_days: u32,
    /// Automatic backup schedule (cron format)
    pub backup_schedule: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeaturesConfig {
    #[serde(default = "default_true")]
    pub voice_enabled: bool,
    #[serde(default = "default_true")]
    pub sms_enabled: bool,
    #[serde(default = "default_true")]
    pub email_enabled: bool,
    #[serde(default = "default_true")]
    pub stripe_enabled: bool,
    #[serde(default = "default_true")]
    pub direct_line_enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AiProjectConfig {
    #[serde(default = "default_text_provider")]
    pub default_text_provider: String,
    #[serde(default = "default_voice_provider")]
    pub default_voice_provider: String,
    #[serde(default)]
    pub models: AiModels,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AiModels {
    pub anthropic_model: Option<String>,
    pub openai_model: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoiceProjectConfig {
    #[serde(default = "default_persona")]
    pub default_persona: String,
    #[serde(default = "default_wake_word")]
    pub default_wake_word: String,
    #[serde(default = "default_sample_rate")]
    pub sample_rate: u32,
    #[serde(default = "default_true")]
    pub include_personality: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DevelopmentConfig {
    #[serde(default)]
    pub debug: bool,
    #[serde(default)]
    pub use_test_credentials: bool,
    #[serde(default = "default_server_port")]
    pub server_port: u16,
    #[serde(default = "default_server_host")]
    pub server_host: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestUserConfig {
    pub email: String,
    pub phone: String,
    #[serde(default = "default_tier")]
    pub subscription_tier: String,
    #[serde(default = "default_persona")]
    pub persona: String,
    #[serde(default = "default_wake_word")]
    pub wake_word: String,
    pub xswarm_email: Option<String>,
    pub xswarm_phone: Option<String>,
}

impl Default for TestUserConfig {
    fn default() -> Self {
        Self {
            email: "test@example.com".to_string(),
            phone: "+15551234567".to_string(),
            subscription_tier: default_tier(),
            persona: default_persona(),
            wake_word: default_wake_word(),
            xswarm_email: Some("test@xswarm.ai".to_string()),
            xswarm_phone: Some("+18005551001".to_string()),
        }
    }
}

impl Default for AdminUserConfig {
    fn default() -> Self {
        Self {
            username: "admin".to_string(),
            name: "Admin User".to_string(),
            email: "admin@xswarm.dev".to_string(),
            phone: "+15559876543".to_string(),
            xswarm_email: "admin@xswarm.ai".to_string(),
            xswarm_phone: "+18005559876".to_string(),
            persona: default_persona(),
            wake_word: default_wake_word(),
            subscription_tier: default_admin_tier(),
            access_level: default_access_level(),
            can_provision_numbers: true,
            can_view_all_users: true,
            can_manage_subscriptions: true,
            can_manage_config: true,
            can_access_all_channels: true,
        }
    }
}

/// Regular user data structure (loaded from DATABASE, not config files!)
/// This represents users stored in Turso, NOT the admin user in config.toml
///
/// Architecture:
/// - Admin user: config.toml [admin] section (AdminUserConfig)
/// - Regular users: Turso database (UserData)
///
/// Regular users have LIMITED permissions compared to admin:
/// - Cannot provision phone numbers
/// - Cannot view all users
/// - Cannot manage subscriptions
/// - Cannot modify config
/// - Access to channels based on subscription tier
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserData {
    pub id: String,
    pub username: String,
    pub name: Option<String>,
    pub email: String,
    pub user_phone: String,  // User's real phone number
    pub xswarm_email: String,  // Assigned xSwarm email
    pub xswarm_phone: Option<String>,  // Assigned xSwarm phone (premium only)
    pub subscription_tier: String,  // free, premium, enterprise
    pub persona: String,  // Selected persona (boss, hal-9000, etc.)
    pub wake_word: Option<String>,  // Custom wake word
    pub stripe_customer_id: Option<String>,
    pub stripe_subscription_id: Option<String>,
    pub created_at: String,  // ISO 8601 timestamp
    pub updated_at: Option<String>,  // ISO 8601 timestamp
}

/// Main configuration structure (loaded from project config.toml)
/// NOTE: User settings are stored in DATABASE, not config files!
/// The Rust client connects to the Node.js server to get user identity.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Server connection configuration (for identity and user management)
    /// The Node.js server maintains the libsql database (backed up to Turso)
    #[serde(default)]
    pub server: ServerConfig,

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

    /// Stripe billing configuration
    #[serde(default)]
    pub stripe: Option<StripeConfig>,
}

/// Stripe subscription and billing configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StripeConfig {
    /// Stripe customer ID
    pub customer_id: String,

    /// Stripe subscription ID (for premium tier)
    pub subscription_id: Option<String>,

    /// Stripe subscription item IDs for metered billing
    pub subscription_items: Option<StripeSubscriptionItems>,

    /// Current billing period usage
    #[serde(default)]
    pub usage: UsageTracking,
}

/// Stripe subscription item IDs for metered billing
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StripeSubscriptionItems {
    /// Voice minutes subscription item ID
    pub voice_item_id: String,

    /// SMS messages subscription item ID
    pub sms_item_id: String,
}

/// Usage tracking for current billing period
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UsageTracking {
    /// Voice minutes used this billing period
    #[serde(default)]
    pub voice_minutes: u32,

    /// SMS messages sent/received this billing period
    #[serde(default)]
    pub sms_messages: u32,

    /// Number of phone numbers provisioned
    #[serde(default)]
    pub phone_numbers: u32,

    /// Billing period start date (ISO 8601)
    pub period_start: Option<String>,

    /// Billing period end date (ISO 8601)
    pub period_end: Option<String>,
}

impl Default for UsageTracking {
    fn default() -> Self {
        Self {
            voice_minutes: 0,
            sms_messages: 0,
            phone_numbers: 0,
            period_start: None,
            period_end: None,
        }
    }
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
    "moshi".to_string()
}

fn default_audio_device() -> String {
    "default".to_string()
}

fn default_sample_rate() -> u32 {
    24000  // MOSHI requires 24kHz audio
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

fn default_sendgrid_domain() -> String {
    "xswarm.ai".to_string()
}

fn default_sync_interval() -> u64 {
    60
}

fn default_primary_region() -> String {
    "sjc".to_string()  // San Jose (closest to SF)
}

fn default_retention_days() -> u32 {
    30
}

fn default_text_provider() -> String {
    "anthropic".to_string()
}

fn default_server_port() -> u16 {
    8787
}

fn default_server_host() -> String {
    "localhost".to_string()
}

fn default_access_level() -> String {
    "superadmin".to_string()
}

fn default_storage_provider() -> String {
    "r2".to_string()  // Cloudflare R2 recommended for Workers integration
}

fn default_bucket_name() -> String {
    "xswarm-assets".to_string()
}

fn default_storage_region() -> String {
    "auto".to_string()
}

fn default_backup_bucket() -> String {
    "xswarm-backups".to_string()
}

fn default_backup_retention_days() -> u32 {
    90  // 90 days for backup retention
}

// Implement Default trait for ProjectConfig structs
impl Default for TwilioProjectConfig {
    fn default() -> Self {
        Self {
            account_sid: None,
            test_account_sid: None,
            test_receive_number: None,
            test_send_number: None,
            test_receive_webhook: None,
        }
    }
}

impl Default for StripeProjectConfig {
    fn default() -> Self {
        Self {
            publishable_key: None,
            prices: StripePrices::default(),
        }
    }
}

impl Default for StripePrices {
    fn default() -> Self {
        Self {
            premium: None,
            voice: None,
            sms: None,
            phone: None,
        }
    }
}

impl Default for SendGridProjectConfig {
    fn default() -> Self {
        Self {
            domain: default_sendgrid_domain(),
            test_user_email: None,
            test_xswarm_email: None,
        }
    }
}

impl Default for TursoProjectConfig {
    fn default() -> Self {
        Self {
            database_name: None,
            organization: None,
            database_url: None,
            primary_region: default_primary_region(),
            replica_regions: vec![],
            local_replica: TursoLocalReplicaConfig::default(),
            backup: TursoBackupConfig::default(),
        }
    }
}

impl Default for TursoLocalReplicaConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            sync_interval_seconds: default_sync_interval(),
            local_db_path: None,
        }
    }
}

impl Default for TursoBackupConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            retention_days: default_retention_days(),
            manual_backup_enabled: false,
            backup_schedule: None,
        }
    }
}

impl Default for StorageConfig {
    fn default() -> Self {
        Self {
            provider: default_storage_provider(),
            bucket_name: default_bucket_name(),
            region: default_storage_region(),
            endpoint: None,
            public_url: None,
            backup: StorageBackupConfig::default(),
        }
    }
}

impl Default for StorageBackupConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            bucket_name: default_backup_bucket(),
            retention_days: default_backup_retention_days(),
            backup_schedule: None,
        }
    }
}

impl Default for FeaturesConfig {
    fn default() -> Self {
        Self {
            voice_enabled: true,
            sms_enabled: true,
            email_enabled: true,
            stripe_enabled: true,
            direct_line_enabled: true,
        }
    }
}

impl Default for AiProjectConfig {
    fn default() -> Self {
        Self {
            default_text_provider: default_text_provider(),
            default_voice_provider: default_voice_provider(),
            models: AiModels::default(),
        }
    }
}

impl Default for AiModels {
    fn default() -> Self {
        Self {
            anthropic_model: None,
            openai_model: None,
        }
    }
}

impl Default for VoiceProjectConfig {
    fn default() -> Self {
        Self {
            default_persona: default_persona(),
            default_wake_word: default_wake_word(),
            sample_rate: default_sample_rate(),
            include_personality: true,
        }
    }
}

impl Default for DevelopmentConfig {
    fn default() -> Self {
        Self {
            debug: false,
            use_test_credentials: false,
            server_port: default_server_port(),
            server_host: default_server_host(),
        }
    }
}

/// Subscription tier configurations (used as templates for user limits)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubscriptionTiers {
    #[serde(default)]
    pub free: TierConfig,
    #[serde(default)]
    pub premium: TierConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TierConfig {
    #[serde(default)]
    pub tier: String,
    #[serde(default)]
    pub email_limit: i32,  // -1 = unlimited
    #[serde(default)]
    pub voice_minutes: u32,
    #[serde(default)]
    pub sms_messages: u32,
    #[serde(default)]
    pub phone_numbers: u32,
    #[serde(default)]
    pub price: Option<f64>,
    #[serde(default)]
    pub voice_minutes_included: Option<u32>,
    #[serde(default)]
    pub sms_messages_included: Option<u32>,
    #[serde(default)]
    pub phone_numbers_included: Option<u32>,
    #[serde(default)]
    pub voice_overage_rate: Option<f64>,
    #[serde(default)]
    pub sms_overage_rate: Option<f64>,
    #[serde(default)]
    pub phone_overage_rate: Option<f64>,
}

impl Default for SubscriptionTiers {
    fn default() -> Self {
        Self {
            free: TierConfig {
                tier: "free".to_string(),
                email_limit: 100,
                voice_minutes: 0,
                sms_messages: 0,
                phone_numbers: 0,
                price: None,
                voice_minutes_included: None,
                sms_messages_included: None,
                phone_numbers_included: None,
                voice_overage_rate: None,
                sms_overage_rate: None,
                phone_overage_rate: None,
            },
            premium: TierConfig {
                tier: "premium".to_string(),
                email_limit: -1,  // unlimited
                voice_minutes: 100,
                sms_messages: 100,
                phone_numbers: 1,
                price: Some(9.99),
                voice_minutes_included: Some(100),
                sms_messages_included: Some(100),
                phone_numbers_included: Some(1),
                voice_overage_rate: Some(0.013),
                sms_overage_rate: Some(0.0075),
                phone_overage_rate: Some(2.00),
            },
        }
    }
}

impl Default for ProjectConfig {
    fn default() -> Self {
        Self {
            admin: AdminUserConfig::default(),
            twilio: TwilioProjectConfig::default(),
            stripe: StripeProjectConfig::default(),
            sendgrid: SendGridProjectConfig::default(),
            turso: TursoProjectConfig::default(),
            storage: StorageConfig::default(),
            features: FeaturesConfig::default(),
            ai: AiProjectConfig::default(),
            voice: VoiceProjectConfig::default(),
            test_user: TestUserConfig::default(),
            development: DevelopmentConfig::default(),
            subscription: SubscriptionTiers::default(),
        }
    }
}

impl ProjectConfig {
    /// Get the admin user configuration
    /// Admin is the ONLY user configured in config.toml
    pub fn get_admin(&self) -> &AdminUserConfig {
        &self.admin
    }

    /// Check if a given email/phone belongs to the admin user
    pub fn is_admin_by_email(&self, email: &str) -> bool {
        self.admin.email == email || self.admin.xswarm_email == email
    }

    pub fn is_admin_by_phone(&self, phone: &str) -> bool {
        self.admin.phone == phone || self.admin.xswarm_phone == phone
    }

    /// Get subscription tier configuration by name
    pub fn get_tier_config(&self, tier: &str) -> Option<&TierConfig> {
        match tier {
            "free" => Some(&self.subscription.free),
            "premium" => Some(&self.subscription.premium),
            "admin" => None,  // Admin has unlimited access
            _ => None,
        }
    }

    /// Get the current environment (development, staging, or production)
    /// Checks ENVIRONMENT or NODE_ENV environment variables
    /// Defaults to "development" if not set
    pub fn environment() -> String {
        std::env::var("ENVIRONMENT")
            .or_else(|_| std::env::var("NODE_ENV"))
            .unwrap_or_else(|_| "development".to_string())
    }

    /// Check if running in production environment
    pub fn is_production() -> bool {
        Self::environment() == "production"
    }

    /// Check if running in development environment
    pub fn is_development() -> bool {
        let env = Self::environment();
        env == "development" || env == "dev"
    }

    /// Get the project config file path (project root)
    pub fn config_path() -> Result<PathBuf> {
        let current_dir = std::env::current_dir()
            .context("Could not determine current directory")?;

        Ok(current_dir.join("config.toml"))
    }

    /// Load project configuration from config.toml
    pub fn load() -> Result<Self> {
        let config_path = Self::config_path()?;

        if config_path.exists() {
            let contents = fs::read_to_string(&config_path)
                .context("Failed to read config.toml")?;

            let config: ProjectConfig = toml::from_str(&contents)
                .context("Failed to parse config.toml")?;

            Ok(config)
        } else {
            // Return default if config.toml doesn't exist
            Ok(ProjectConfig::default())
        }
    }

    /// Save project configuration to config.toml
    pub fn save(&self) -> Result<()> {
        let config_path = Self::config_path()?;

        // Serialize to TOML
        let toml_string = toml::to_string_pretty(self)
            .context("Failed to serialize project config")?;

        // Write to file
        fs::write(&config_path, toml_string)
            .context("Failed to write config.toml")?;

        Ok(())
    }
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
            model: Some("kyutai/moshika-mlx-q4".to_string()),
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
            stripe: None,
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
            server: ServerConfig::default(),
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
