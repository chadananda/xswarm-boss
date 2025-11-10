// HTTP client for Persona API

use anyhow::{Context, Result};
use reqwest;
use uuid::Uuid;

use super::types::*;
use super::PersonaConfig;

/// Client for interacting with Persona API
pub struct PersonaClient {
    base_url: String,
    user_id: Uuid,
    auth_token: String,
    client: reqwest::Client,
}

impl PersonaClient {
    /// Create a new PersonaClient
    pub fn new(base_url: String, user_id: Uuid, auth_token: String) -> Self {
        Self {
            base_url,
            user_id,
            auth_token,
            client: reqwest::Client::new(),
        }
    }

    /// Create a new persona
    pub async fn create_persona(&self, request: CreatePersonaRequest) -> Result<PersonaConfig> {
        let url = format!("{}/api/personas", self.base_url);

        let response = self
            .client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.auth_token))
            .header("X-User-Id", self.user_id.to_string())
            .json(&request)
            .send()
            .await
            .context("Failed to send create persona request")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Failed to create persona: {}", error_text);
        }

        let result: PersonaResponse = response
            .json()
            .await
            .context("Failed to parse create persona response")?;

        Ok(result.persona)
    }

    /// List all personas
    pub async fn list_personas(&self) -> Result<ListPersonasResponse> {
        let url = format!("{}/api/personas", self.base_url);

        let response = self
            .client
            .get(&url)
            .header("Authorization", format!("Bearer {}", self.auth_token))
            .header("X-User-Id", self.user_id.to_string())
            .send()
            .await
            .context("Failed to send list personas request")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Failed to list personas: {}", error_text);
        }

        response
            .json()
            .await
            .context("Failed to parse list personas response")
    }

    /// Get active persona
    pub async fn get_active_persona(&self) -> Result<Option<PersonaConfig>> {
        let url = format!("{}/api/personas/active", self.base_url);

        let response = self
            .client
            .get(&url)
            .header("Authorization", format!("Bearer {}", self.auth_token))
            .header("X-User-Id", self.user_id.to_string())
            .send()
            .await
            .context("Failed to send get active persona request")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Failed to get active persona: {}", error_text);
        }

        let result: PersonaResponse = response
            .json()
            .await
            .context("Failed to parse active persona response")?;

        Ok(Some(result.persona))
    }

    /// Get specific persona by ID
    pub async fn get_persona(&self, persona_id: Uuid) -> Result<PersonaConfig> {
        let url = format!("{}/api/personas/{}", self.base_url, persona_id);

        let response = self
            .client
            .get(&url)
            .header("Authorization", format!("Bearer {}", self.auth_token))
            .header("X-User-Id", self.user_id.to_string())
            .send()
            .await
            .context("Failed to send get persona request")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Failed to get persona: {}", error_text);
        }

        let result: PersonaResponse = response
            .json()
            .await
            .context("Failed to parse get persona response")?;

        Ok(result.persona)
    }

    /// Update persona
    pub async fn update_persona(
        &self,
        persona_id: Uuid,
        request: UpdatePersonaRequest,
    ) -> Result<PersonaConfig> {
        let url = format!("{}/api/personas/{}", self.base_url, persona_id);

        let response = self
            .client
            .put(&url)
            .header("Authorization", format!("Bearer {}", self.auth_token))
            .header("X-User-Id", self.user_id.to_string())
            .json(&request)
            .send()
            .await
            .context("Failed to send update persona request")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Failed to update persona: {}", error_text);
        }

        let result: PersonaResponse = response
            .json()
            .await
            .context("Failed to parse update persona response")?;

        Ok(result.persona)
    }

    /// Delete persona
    pub async fn delete_persona(&self, persona_id: Uuid) -> Result<()> {
        let url = format!("{}/api/personas/{}", self.base_url, persona_id);

        let response = self
            .client
            .delete(&url)
            .header("Authorization", format!("Bearer {}", self.auth_token))
            .header("X-User-Id", self.user_id.to_string())
            .send()
            .await
            .context("Failed to send delete persona request")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Failed to delete persona: {}", error_text);
        }

        Ok(())
    }

    /// Activate persona
    pub async fn activate_persona(&self, persona_id: Uuid) -> Result<PersonaConfig> {
        let url = format!("{}/api/personas/{}/activate", self.base_url, persona_id);

        let response = self
            .client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.auth_token))
            .header("X-User-Id", self.user_id.to_string())
            .send()
            .await
            .context("Failed to send activate persona request")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Failed to activate persona: {}", error_text);
        }

        let result: PersonaResponse = response
            .json()
            .await
            .context("Failed to parse activate persona response")?;

        Ok(result.persona)
    }

    /// Add conversation example for learning
    pub async fn add_example(
        &self,
        persona_id: Uuid,
        request: AddExampleRequest,
    ) -> Result<PersonaConfig> {
        let url = format!("{}/api/personas/{}/learn", self.base_url, persona_id);

        let response = self
            .client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.auth_token))
            .header("X-User-Id", self.user_id.to_string())
            .json(&request)
            .send()
            .await
            .context("Failed to send add example request")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Failed to add example: {}", error_text);
        }

        let result: PersonaResponse = response
            .json()
            .await
            .context("Failed to parse add example response")?;

        Ok(result.persona)
    }

    /// Train voice model (Personal tier feature)
    pub async fn train_voice(
        &self,
        persona_id: Uuid,
        request: TrainVoiceRequest,
    ) -> Result<TrainingSession> {
        let url = format!("{}/api/personas/{}/train-voice", self.base_url, persona_id);

        let response = self
            .client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.auth_token))
            .header("X-User-Id", self.user_id.to_string())
            .json(&request)
            .send()
            .await
            .context("Failed to send train voice request")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Failed to train voice: {}", error_text);
        }

        #[derive(serde::Deserialize)]
        struct TrainVoiceResponse {
            session: TrainingSession,
        }

        let result: TrainVoiceResponse = response
            .json()
            .await
            .context("Failed to parse train voice response")?;

        Ok(result.session)
    }

    /// Get training status
    pub async fn get_training_status(&self, persona_id: Uuid) -> Result<Vec<TrainingSession>> {
        let url = format!(
            "{}/api/personas/{}/training-status",
            self.base_url, persona_id
        );

        let response = self
            .client
            .get(&url)
            .header("Authorization", format!("Bearer {}", self.auth_token))
            .header("X-User-Id", self.user_id.to_string())
            .send()
            .await
            .context("Failed to send get training status request")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Failed to get training status: {}", error_text);
        }

        let result: TrainingStatusResponse = response
            .json()
            .await
            .context("Failed to parse training status response")?;

        Ok(result.sessions)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_persona_client_creation() {
        let client = PersonaClient::new(
            "http://localhost:8787".to_string(),
            Uuid::new_v4(),
            "test_token".to_string(),
        );

        assert_eq!(client.base_url, "http://localhost:8787");
    }
}
