// Persona Management System
//
// Provides types and utilities for AI persona management with personality traits,
// voice models, and tier-based access control.

pub mod types;
pub mod client;

pub use types::*;
pub use client::PersonaClient;

use anyhow::Result;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Persona configuration with personality traits and response style
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PersonaConfig {
    pub id: Uuid,
    pub user_id: Uuid,
    pub name: String,
    pub description: String,
    pub personality_traits: PersonalityTraits,
    pub response_style: ResponseStyle,
    pub expertise_areas: Vec<String>,
    pub voice_model_config: VoiceModelConfig,
    pub conversation_examples: Vec<ConversationExample>,
    pub is_active: bool,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

/// Big Five personality traits + custom dimensions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PersonalityTraits {
    /// Extraversion: 0.0 (introvert) - 1.0 (extravert)
    pub extraversion: f32,
    /// Agreeableness: 0.0 (competitive) - 1.0 (collaborative)
    pub agreeableness: f32,
    /// Conscientiousness: 0.0 (flexible) - 1.0 (disciplined)
    pub conscientiousness: f32,
    /// Neuroticism: 0.0 (confident) - 1.0 (sensitive)
    pub neuroticism: f32,
    /// Openness: 0.0 (practical) - 1.0 (creative)
    pub openness: f32,
    /// Formality: 0.0 (casual) - 1.0 (formal)
    pub formality: f32,
    /// Enthusiasm: 0.0 (reserved) - 1.0 (enthusiastic)
    pub enthusiasm: f32,
}

impl Default for PersonalityTraits {
    fn default() -> Self {
        Self {
            extraversion: 0.5,
            agreeableness: 0.5,
            conscientiousness: 0.5,
            neuroticism: 0.5,
            openness: 0.5,
            formality: 0.5,
            enthusiasm: 0.5,
        }
    }
}

/// Response style configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResponseStyle {
    pub verbosity: VerbosityLevel,
    pub tone: ToneStyle,
    /// Humor level: 0.0 - 1.0
    pub humor_level: f32,
    /// Technical depth: 0.0 (simple) - 1.0 (technical)
    pub technical_depth: f32,
    /// Empathy level: 0.0 - 1.0
    pub empathy_level: f32,
    /// Proactivity: 0.0 (reactive) - 1.0 (proactive)
    pub proactivity: f32,
}

impl Default for ResponseStyle {
    fn default() -> Self {
        Self {
            verbosity: VerbosityLevel::Balanced,
            tone: ToneStyle::Friendly,
            humor_level: 0.5,
            technical_depth: 0.5,
            empathy_level: 0.5,
            proactivity: 0.5,
        }
    }
}

/// Verbosity level for responses
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VerbosityLevel {
    Concise,   // Brief, to-the-point responses
    Balanced,  // Normal conversational length
    Detailed,  // Comprehensive explanations
    Elaborate, // Extensive, thorough responses
}

/// Tone style for responses
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ToneStyle {
    Professional,  // Business-like, formal
    Friendly,      // Warm, approachable
    Casual,        // Relaxed, informal
    Authoritative, // Confident, directive
    Supportive,    // Encouraging, empathetic
    Analytical,    // Logical, fact-based
}

/// Voice model configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoiceModelConfig {
    pub voice_id: String,
    /// Speed: 0.5 - 2.0
    pub speed: f32,
    /// Pitch: 0.5 - 2.0
    pub pitch: f32,
    pub custom_model_path: Option<String>,
    pub training_status: TrainingStatus,
}

impl Default for VoiceModelConfig {
    fn default() -> Self {
        Self {
            voice_id: "default".to_string(),
            speed: 1.0,
            pitch: 1.0,
            custom_model_path: None,
            training_status: TrainingStatus::NotStarted,
        }
    }
}

/// Training status for voice models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TrainingStatus {
    NotStarted,
    InProgress { progress_percent: u8 },
    Completed,
    Failed { error: String },
}

/// Conversation example for learning
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversationExample {
    pub user_message: String,
    pub persona_response: String,
    pub context: String,
    /// Quality score: 0.0 - 1.0
    pub quality_score: f32,
}

/// Build persona-aware prompt for AI generation
pub fn build_persona_prompt(persona: &PersonaConfig, message: &str) -> String {
    let traits = &persona.personality_traits;
    let style = &persona.response_style;

    let personality_context = format!(
        "You are {}, an AI assistant with these characteristics:
- Extraversion: {:.1} (social energy level)
- Formality: {:.1} (casual to formal communication)
- Enthusiasm: {:.1} (energy and excitement level)
- Humor: {:.1} (use of humor and playfulness)
- Technical depth: {:.1} (complexity of explanations)
- Empathy: {:.1} (emotional understanding and support)",
        persona.name,
        traits.extraversion,
        traits.formality,
        traits.enthusiasm,
        style.humor_level,
        style.technical_depth,
        style.empathy_level
    );

    let expertise_context = if !persona.expertise_areas.is_empty() {
        format!(
            "Your areas of expertise include: {}",
            persona.expertise_areas.join(", ")
        )
    } else {
        "You're a general purpose assistant".to_string()
    };

    let verbosity_instruction = match style.verbosity {
        VerbosityLevel::Concise => "Keep responses brief and to the point.",
        VerbosityLevel::Balanced => "Provide balanced, conversational responses.",
        VerbosityLevel::Detailed => "Give comprehensive explanations with examples.",
        VerbosityLevel::Elaborate => "Provide thorough, extensive detail in responses.",
    };

    format!(
        "{}\n{}\n{}\n\nUser message: {}",
        personality_context, expertise_context, verbosity_instruction, message
    )
}

/// Apply persona-specific post-processing to generated text
pub fn apply_persona_style(persona: &PersonaConfig, mut text: String) -> String {
    let style = &persona.response_style;

    // Adjust formality
    if persona.personality_traits.formality > 0.7 {
        // Make more formal: remove contractions
        text = text.replace("don't", "do not");
        text = text.replace("can't", "cannot");
        text = text.replace("won't", "will not");
        text = text.replace("I'm", "I am");
        text = text.replace("you're", "you are");
    }

    // Add enthusiasm markers if high enthusiasm
    if persona.personality_traits.enthusiasm > 0.8 {
        // Already has natural enthusiasm from generation
        // Could add more exclamation points if needed
    }

    text
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_personality_traits() {
        let traits = PersonalityTraits::default();
        assert_eq!(traits.extraversion, 0.5);
        assert_eq!(traits.formality, 0.5);
    }

    #[test]
    fn test_default_response_style() {
        let style = ResponseStyle::default();
        assert_eq!(style.humor_level, 0.5);
        assert_eq!(style.technical_depth, 0.5);
    }

    #[test]
    fn test_build_persona_prompt() {
        let persona = PersonaConfig {
            id: Uuid::new_v4(),
            user_id: Uuid::new_v4(),
            name: "TestBot".to_string(),
            description: "A test persona".to_string(),
            personality_traits: PersonalityTraits::default(),
            response_style: ResponseStyle::default(),
            expertise_areas: vec!["programming".to_string()],
            voice_model_config: VoiceModelConfig::default(),
            conversation_examples: vec![],
            is_active: true,
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
        };

        let prompt = build_persona_prompt(&persona, "Hello!");
        assert!(prompt.contains("TestBot"));
        assert!(prompt.contains("programming"));
        assert!(prompt.contains("Hello!"));
    }
}
