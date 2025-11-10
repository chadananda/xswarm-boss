// Server Client Module - Identity & User Management
//
// This module provides HTTP/WebSocket client for connecting to the Node.js server
// to fetch user identity and configuration. The server maintains the main libsql
// database (backed up to Turso), and the Rust client connects to get its identity.
//
// Architecture:
// - Server owns all user data (via libsql → Turso)
// - Client is stateless regarding user identity
// - Authentication handled by server
// - Client caches identity during session

use anyhow::{Context, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, warn, error, debug};
use std::env;
use chrono;

/// Server connection configuration (from config.toml [server] section)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    /// Server host (e.g., "localhost" or "api.xswarm.ai")
    #[serde(default = "default_host")]
    pub host: String,

    /// Server port (e.g., 8787 for Cloudflare Workers dev)
    #[serde(default = "default_port")]
    pub port: u16,

    /// API base path (e.g., "/api")
    #[serde(default = "default_api_base")]
    pub api_base: String,

    /// Client authentication token (from environment or config)
    pub auth_token: Option<String>,

    /// Use HTTPS (true for production, false for local dev)
    #[serde(default)]
    pub use_https: bool,
}

fn default_host() -> String {
    "localhost".to_string()
}

fn default_port() -> u16 {
    8787
}

fn default_api_base() -> String {
    "/api".to_string()
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            host: default_host(),
            port: default_port(),
            api_base: default_api_base(),
            auth_token: std::env::var("XSWARM_AUTH_TOKEN").ok(),
            use_https: false,
        }
    }
}

impl ServerConfig {
    /// Get the base URL for the server
    pub fn base_url(&self) -> String {
        let protocol = if self.use_https { "https" } else { "http" };
        if self.use_https && self.port == 443 {
            format!("{}://{}", protocol, self.host)
        } else if !self.use_https && self.port == 80 {
            format!("{}://{}", protocol, self.host)
        } else {
            format!("{}://{}:{}", protocol, self.host, self.port)
        }
    }

    /// Get the full API URL
    pub fn api_url(&self) -> String {
        format!("{}{}", self.base_url(), self.api_base)
    }
}

/// User identity returned from server
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserIdentity {
    pub id: String,
    pub username: String,
    pub name: Option<String>,
    pub email: String,
    pub user_phone: String,
    pub xswarm_email: String,
    pub xswarm_phone: Option<String>,
    pub subscription_tier: String,
    pub persona: String,
    pub wake_word: Option<String>,

    // Permissions
    pub can_use_voice: bool,
    pub can_use_sms: bool,
    pub can_use_email: bool,
    pub can_provision_numbers: bool,

    // Usage limits
    pub voice_minutes_remaining: Option<u32>,
    pub sms_messages_remaining: Option<u32>,

    pub created_at: String,
    pub updated_at: Option<String>,
}

/// Server client for fetching identity and user data
pub struct ServerClient {
    config: ServerConfig,
    http_client: Client,
    cached_identity: Arc<RwLock<Option<UserIdentity>>>,
}

impl ServerClient {
    /// Create a new server client
    pub fn new(config: ServerConfig) -> Result<Self> {
        let http_client = Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .context("Failed to create HTTP client")?;

        Ok(Self {
            config,
            http_client,
            cached_identity: Arc::new(RwLock::new(None)),
        })
    }

    /// Check if dev mode is active
    /// Returns true if XSWARM_DEV_ADMIN_EMAIL and XSWARM_DEV_ADMIN_PASS are both present and valid
    fn is_dev_mode() -> bool {
        let dev_email = env::var("XSWARM_DEV_ADMIN_EMAIL").ok();
        let dev_password = env::var("XSWARM_DEV_ADMIN_PASS").ok();

        // Both must be present
        if dev_email.is_none() || dev_password.is_none() {
            return false;
        }

        let dev_password = dev_password.unwrap();

        // Password must not be empty
        if dev_password.is_empty() {
            return false;
        }

        true
    }

    /// Create a mock admin identity for dev mode
    /// Uses admin details from config.toml and environment variables
    fn create_mock_admin_identity() -> UserIdentity {
        let dev_email = env::var("XSWARM_DEV_ADMIN_EMAIL")
            .unwrap_or_else(|_| "admin@xswarm.dev".to_string());

        let now = chrono::Utc::now().to_rfc3339();

        UserIdentity {
            id: "dev-admin-001".to_string(),
            username: "admin".to_string(),
            name: Some("Dev Admin".to_string()),
            email: dev_email.clone(),
            user_phone: "+15555550001".to_string(),
            xswarm_email: dev_email,
            xswarm_phone: Some("+15555550001".to_string()),
            subscription_tier: "admin".to_string(),
            persona: "professional".to_string(),
            wake_word: Some("hey assistant".to_string()),

            // Admin has all permissions
            can_use_voice: true,
            can_use_sms: true,
            can_use_email: true,
            can_provision_numbers: true,

            // Unlimited usage limits (None = unlimited)
            voice_minutes_remaining: None,
            sms_messages_remaining: None,

            created_at: now.clone(),
            updated_at: Some(now),
        }
    }

    /// Get user identity from server (cached during session)
    pub async fn get_identity(&self) -> Result<UserIdentity> {
        // Check if dev mode is active
        if Self::is_dev_mode() {
            info!("Dev mode active - using mock admin identity (bypassing server)");
            let mock_identity = Self::create_mock_admin_identity();

            // Cache the mock identity
            {
                let mut cached = self.cached_identity.write().await;
                *cached = Some(mock_identity.clone());
            }

            return Ok(mock_identity);
        }

        // Check cache first
        {
            let cached = self.cached_identity.read().await;
            if let Some(identity) = cached.as_ref() {
                debug!(user_id = %identity.id, "Using cached identity");
                return Ok(identity.clone());
            }
        }

        // Fetch from server
        info!("Fetching user identity from server");
        let identity = self.fetch_identity().await?;

        // Cache it
        {
            let mut cached = self.cached_identity.write().await;
            *cached = Some(identity.clone());
        }

        Ok(identity)
    }

    /// Fetch user identity from server (bypasses cache)
    async fn fetch_identity(&self) -> Result<UserIdentity> {
        let url = format!("{}/identity", self.config.api_url());

        debug!(url = %url, "Fetching identity from server");

        let mut request = self.http_client.get(&url);

        // Add auth token if available
        if let Some(token) = &self.config.auth_token {
            request = request.bearer_auth(token);
        }

        let response = request
            .send()
            .await
            .context("Failed to connect to server")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!(
                "Server returned error {}: {}",
                status,
                error_text
            );
        }

        let identity: UserIdentity = response
            .json()
            .await
            .context("Failed to parse identity response")?;

        info!(
            user_id = %identity.id,
            username = %identity.username,
            tier = %identity.subscription_tier,
            "Fetched user identity from server"
        );

        Ok(identity)
    }

    /// Invalidate cached identity (force refresh on next get)
    pub async fn invalidate_cache(&self) {
        let mut cached = self.cached_identity.write().await;
        *cached = None;
        debug!("Identity cache invalidated");
    }

    /// Check if server is reachable
    pub async fn health_check(&self) -> Result<bool> {
        // In dev mode, always return healthy (skip server check)
        if Self::is_dev_mode() {
            debug!("Dev mode active - health check bypassed (returning OK)");
            return Ok(true);
        }

        let url = format!("{}/health", self.config.base_url());

        match self.http_client.get(&url).send().await {
            Ok(response) => {
                let is_healthy = response.status().is_success();
                if is_healthy {
                    debug!("Server health check: OK");
                } else {
                    warn!(status = %response.status(), "Server health check: unhealthy");
                }
                Ok(is_healthy)
            }
            Err(e) => {
                error!(error = ?e, "Server health check: failed");
                Ok(false)
            }
        }
    }

    /// Authenticate with the server and validate token
    pub async fn authenticate(&self) -> Result<bool> {
        // In dev mode, always return authenticated (skip server auth)
        if Self::is_dev_mode() {
            info!("Dev mode active - authentication bypassed (returning OK)");
            return Ok(true);
        }

        let url = format!("{}/auth/validate", self.config.api_url());

        let mut request = self.http_client.post(&url);

        if let Some(token) = &self.config.auth_token {
            request = request.bearer_auth(token);
        } else {
            warn!("No auth token configured");
            return Ok(false);
        }

        match request.send().await {
            Ok(response) => {
                let is_valid = response.status().is_success();
                if is_valid {
                    info!("Authentication successful");
                } else {
                    warn!(status = %response.status(), "Authentication failed");
                }
                Ok(is_valid)
            }
            Err(e) => {
                error!(error = ?e, "Authentication request failed");
                anyhow::bail!("Authentication failed: {}", e)
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_server_config_default() {
        let config = ServerConfig::default();
        assert_eq!(config.host, "localhost");
        assert_eq!(config.port, 8787);
        assert_eq!(config.api_base, "/api");
        assert!(!config.use_https);
    }

    #[test]
    fn test_server_config_base_url() {
        let config = ServerConfig {
            host: "api.example.com".to_string(),
            port: 443,
            api_base: "/api".to_string(),
            auth_token: None,
            use_https: true,
        };
        assert_eq!(config.base_url(), "https://api.example.com");

        let config = ServerConfig {
            host: "localhost".to_string(),
            port: 8787,
            api_base: "/api".to_string(),
            auth_token: None,
            use_https: false,
        };
        assert_eq!(config.base_url(), "http://localhost:8787");
    }

    #[test]
    fn test_server_config_api_url() {
        let config = ServerConfig::default();
        assert_eq!(config.api_url(), "http://localhost:8787/api");
    }
}
