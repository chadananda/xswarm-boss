use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::env;

/// AI Provider selection
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AiProvider {
    Anthropic,
    OpenAI,
    Local,
}

/// Message role in a conversation
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Role {
    User,
    Assistant,
    System,
}

/// A single message in a conversation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: Role,
    pub content: String,
}

/// AI Client for remote API communication
pub struct AiClient {
    provider: AiProvider,
    api_key: Option<String>,
    model: String,
    http_client: reqwest::Client,
}

impl AiClient {
    /// Create a new AI client with Anthropic provider
    pub fn anthropic(api_key: Option<String>, model: Option<String>) -> Self {
        let api_key = api_key.or_else(|| env::var("ANTHROPIC_API_KEY").ok());
        let model = model.unwrap_or_else(|| "claude-3-5-sonnet-20241022".to_string());

        Self {
            provider: AiProvider::Anthropic,
            api_key,
            model,
            http_client: reqwest::Client::new(),
        }
    }

    /// Create a new AI client with OpenAI provider
    pub fn openai(api_key: Option<String>, model: Option<String>) -> Self {
        let api_key = api_key.or_else(|| env::var("OPENAI_API_KEY").ok());
        let model = model.unwrap_or_else(|| "gpt-4o".to_string());

        Self {
            provider: AiProvider::OpenAI,
            api_key,
            model,
            http_client: reqwest::Client::new(),
        }
    }

    /// Check if API key is configured
    pub fn is_configured(&self) -> bool {
        self.api_key.is_some()
    }

    /// Get the model name
    pub fn model(&self) -> &str {
        &self.model
    }

    /// Send a message and get a response
    pub async fn send_message(
        &self,
        messages: Vec<Message>,
        system_prompt: Option<String>,
    ) -> Result<String> {
        if !self.is_configured() {
            anyhow::bail!(
                "AI provider {} is not configured. Please set API key in environment or config.",
                match self.provider {
                    AiProvider::Anthropic => "Anthropic",
                    AiProvider::OpenAI => "OpenAI",
                    AiProvider::Local => "Local",
                }
            );
        }

        match self.provider {
            AiProvider::Anthropic => self.send_anthropic(messages, system_prompt).await,
            AiProvider::OpenAI => self.send_openai(messages, system_prompt).await,
            AiProvider::Local => anyhow::bail!("Local AI not yet implemented"),
        }
    }

    /// Send request to Anthropic API
    async fn send_anthropic(
        &self,
        messages: Vec<Message>,
        system_prompt: Option<String>,
    ) -> Result<String> {
        #[derive(Serialize)]
        struct AnthropicRequest {
            model: String,
            max_tokens: u32,
            messages: Vec<Message>,
            #[serde(skip_serializing_if = "Option::is_none")]
            system: Option<String>,
        }

        #[derive(Deserialize)]
        struct AnthropicResponse {
            content: Vec<ContentBlock>,
        }

        #[derive(Deserialize)]
        struct ContentBlock {
            text: String,
        }

        let request = AnthropicRequest {
            model: self.model.clone(),
            max_tokens: 4096,
            messages,
            system: system_prompt,
        };

        let response = self
            .http_client
            .post("https://api.anthropic.com/v1/messages")
            .header("x-api-key", self.api_key.as_ref().unwrap())
            .header("anthropic-version", "2023-06-01")
            .header("content-type", "application/json")
            .json(&request)
            .send()
            .await
            .context("Failed to send request to Anthropic API")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Anthropic API error ({}): {}", status, error_text);
        }

        let api_response: AnthropicResponse = response
            .json()
            .await
            .context("Failed to parse Anthropic response")?;

        Ok(api_response
            .content
            .first()
            .map(|c| c.text.clone())
            .unwrap_or_default())
    }

    /// Send request to OpenAI API
    async fn send_openai(
        &self,
        mut messages: Vec<Message>,
        system_prompt: Option<String>,
    ) -> Result<String> {
        #[derive(Serialize)]
        struct OpenAIRequest {
            model: String,
            messages: Vec<Message>,
        }

        #[derive(Deserialize)]
        struct OpenAIResponse {
            choices: Vec<Choice>,
        }

        #[derive(Deserialize)]
        struct Choice {
            message: Message,
        }

        // OpenAI puts system prompt as a message
        if let Some(system) = system_prompt {
            messages.insert(
                0,
                Message {
                    role: Role::System,
                    content: system,
                },
            );
        }

        let request = OpenAIRequest {
            model: self.model.clone(),
            messages,
        };

        let response = self
            .http_client
            .post("https://api.openai.com/v1/chat/completions")
            .header("Authorization", format!("Bearer {}", self.api_key.as_ref().unwrap()))
            .header("content-type", "application/json")
            .json(&request)
            .send()
            .await
            .context("Failed to send request to OpenAI API")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("OpenAI API error ({}): {}", status, error_text);
        }

        let api_response: OpenAIResponse = response
            .json()
            .await
            .context("Failed to parse OpenAI response")?;

        Ok(api_response
            .choices
            .first()
            .map(|c| c.message.content.clone())
            .unwrap_or_default())
    }
}

/// Stub: Voice interface (not yet implemented)
pub struct VoiceClient {
    _provider: String,
}

impl VoiceClient {
    /// Create a new voice client (stub)
    pub fn new(provider: String) -> Self {
        Self { _provider: provider }
    }

    /// Check if voice is available
    pub fn is_available(&self) -> bool {
        false // Stubbed - not yet implemented
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ai_client_creation() {
        let client = AiClient::anthropic(None, None);
        assert_eq!(client.model(), "claude-3-5-sonnet-20241022");
    }

    #[test]
    fn test_voice_client_stub() {
        let client = VoiceClient::new("moshi".to_string());
        assert!(!client.is_available());
    }
}
