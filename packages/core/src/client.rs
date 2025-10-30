// Boss AI Client - Simple HTTP client for message API
//
// This module provides a minimal client for sending messages to Boss AI
// and receiving responses. It's designed to be simple and testable.
//
// Architecture:
// - Pure HTTP client using reqwest
// - JSON request/response format
// - No caching or state management
// - Clean error handling

use anyhow::{Context, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};

/// Configuration for Boss AI client
#[derive(Debug, Clone)]
pub struct BossClientConfig {
    /// Server URL (e.g., "http://localhost:8787")
    pub server_url: String,

    /// API endpoint path (default: "/api/message")
    pub api_path: String,

    /// Channel identifier (e.g., "cli", "sms", "email")
    pub channel: String,

    /// User identifier (phone or email)
    pub from: String,
}

impl Default for BossClientConfig {
    fn default() -> Self {
        Self {
            server_url: "http://localhost:8787".to_string(),
            api_path: "/api/message".to_string(),
            channel: "cli".to_string(),
            from: "admin".to_string(),
        }
    }
}

impl BossClientConfig {
    /// Get the full API URL
    pub fn api_url(&self) -> String {
        format!("{}{}", self.server_url, self.api_path)
    }
}

/// Request payload for Boss AI message API
#[derive(Debug, Serialize)]
struct MessageRequest {
    channel: String,
    from: String,
    content: String,
}

/// Response payload from Boss AI message API
#[derive(Debug, Deserialize)]
struct MessageResponse {
    #[serde(default)]
    message: Option<String>,
    #[serde(default)]
    error: Option<String>,
}

/// Boss AI client for sending messages
pub struct BossClient {
    config: BossClientConfig,
    http_client: Client,
}

impl BossClient {
    /// Create a new Boss AI client
    pub fn new(config: BossClientConfig) -> Result<Self> {
        let http_client = Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .context("Failed to create HTTP client")?;

        Ok(Self {
            config,
            http_client,
        })
    }

    /// Send a message to Boss AI and get a response
    pub async fn send_message(&self, content: &str) -> Result<String> {
        let url = self.config.api_url();

        let request = MessageRequest {
            channel: self.config.channel.clone(),
            from: self.config.from.clone(),
            content: content.to_string(),
        };

        let response = self.http_client
            .post(&url)
            .json(&request)
            .send()
            .await
            .context("Failed to send message to Boss AI")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Boss AI returned error {}: {}", status, error_text);
        }

        let response_data: MessageResponse = response
            .json()
            .await
            .context("Failed to parse Boss AI response")?;

        // Return the message or error
        if let Some(error) = response_data.error {
            anyhow::bail!("Boss AI error: {}", error);
        }

        Ok(response_data.message.unwrap_or_else(|| "No response".to_string()))
    }

    /// Check if Boss AI server is reachable
    pub async fn health_check(&self) -> Result<bool> {
        let url = format!("{}/health", self.config.server_url);

        match self.http_client.get(&url).send().await {
            Ok(response) => Ok(response.status().is_success()),
            Err(_) => Ok(false),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_boss_client_config_default() {
        let config = BossClientConfig::default();
        assert_eq!(config.server_url, "http://localhost:8787");
        assert_eq!(config.api_path, "/api/message");
        assert_eq!(config.channel, "cli");
        assert_eq!(config.from, "admin");
    }

    #[test]
    fn test_boss_client_config_api_url() {
        let config = BossClientConfig::default();
        assert_eq!(config.api_url(), "http://localhost:8787/api/message");

        let config = BossClientConfig {
            server_url: "https://api.xswarm.ai".to_string(),
            api_path: "/api/message".to_string(),
            channel: "cli".to_string(),
            from: "admin".to_string(),
        };
        assert_eq!(config.api_url(), "https://api.xswarm.ai/api/message");
    }
}
