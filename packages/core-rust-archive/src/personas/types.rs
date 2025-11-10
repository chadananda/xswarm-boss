// Persona types and DTOs

use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Request to create a new persona
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreatePersonaRequest {
    pub name: String,
    pub description: Option<String>,
    pub personality_traits: Option<super::PersonalityTraits>,
    pub response_style: Option<super::ResponseStyle>,
    pub expertise_areas: Option<Vec<String>>,
}

/// Request to update a persona
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdatePersonaRequest {
    pub name: Option<String>,
    pub description: Option<String>,
    pub personality_traits: Option<super::PersonalityTraits>,
    pub response_style: Option<super::ResponseStyle>,
    pub expertise_areas: Option<Vec<String>>,
}

/// Response for persona list operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ListPersonasResponse {
    pub success: bool,
    pub personas: Vec<super::PersonaConfig>,
    pub meta: PersonaListMeta,
}

/// Metadata for persona list
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PersonaListMeta {
    pub total: usize,
    pub limit: i32, // -1 for unlimited
    pub can_create_more: bool,
    pub tier: String,
}

/// Response for single persona operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PersonaResponse {
    pub success: bool,
    pub persona: super::PersonaConfig,
}

/// Request to add conversation example
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddExampleRequest {
    pub user_message: String,
    pub persona_response: String,
    pub context: Option<String>,
    pub quality_score: Option<f32>,
}

/// Request to train voice model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainVoiceRequest {
    pub audio_samples: Vec<String>, // Base64 encoded audio
    pub sample_texts: Option<Vec<String>>,
}

/// Training session status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingSession {
    pub id: Uuid,
    pub persona_id: Uuid,
    pub training_type: String,
    pub status: String,
    pub progress_percent: u8,
    pub error_message: Option<String>,
    pub started_at: Option<String>,
    pub completed_at: Option<String>,
    pub created_at: String,
}

/// Training status response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingStatusResponse {
    pub success: bool,
    pub sessions: Vec<TrainingSession>,
}

/// Error response from persona API
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PersonaError {
    pub error: String,
    pub code: String,
    pub upgrade_cta: Option<UpgradeCta>,
}

/// Upgrade call-to-action for tier limits
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpgradeCta {
    pub tier: String,
    pub feature: String,
    pub benefit: String,
    pub message: String,
}
