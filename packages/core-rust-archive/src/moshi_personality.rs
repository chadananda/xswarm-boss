// MOSHI Personality Configuration Module
//
// This module provides personality configuration for MOSHI voice conversations.
// Since MOSHI doesn't have traditional system prompts, we inject personality through:
// 1. Response conditioning via text token suggestions
// 2. Conversation context management
// 3. Response style adaptation

use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;

use crate::personas::{PersonaConfig, PersonalityTraits, ResponseStyle, VerbosityLevel, ToneStyle};

/// MOSHI-specific personality configuration
/// Adapts PersonaConfig for real-time voice conversation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MoshiPersonality {
    /// Base persona configuration
    pub persona: PersonaConfig,

    /// Jarvis-like assistant role
    pub assistant_role: AssistantRole,

    /// Real-time response configuration
    pub response_config: ResponseConfig,

    /// Conversation context tracking
    pub context_tracking: bool,
}

/// Assistant role configuration (Jarvis-like behavior)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssistantRole {
    /// Role name (e.g., "Jarvis", "MOSHI Assistant")
    pub name: String,

    /// Primary function description
    pub primary_function: String,

    /// Behavioral guidelines
    pub guidelines: Vec<String>,

    /// Proactive behaviors enabled
    pub proactive_assistance: bool,
}

impl Default for AssistantRole {
    fn default() -> Self {
        Self {
            name: "MOSHI Assistant".to_string(),
            primary_function: "Helpful personal assistant for real-time voice conversations".to_string(),
            guidelines: vec![
                "Be professional but friendly".to_string(),
                "Provide concise but informative responses".to_string(),
                "Ask clarifying questions when needed".to_string(),
                "Offer proactive assistance when appropriate".to_string(),
                "Maintain a supportive and encouraging tone".to_string(),
            ],
            proactive_assistance: true,
        }
    }
}

/// Real-time response configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResponseConfig {
    /// Maximum response length (in tokens)
    pub max_response_length: usize,

    /// Response delay for natural conversation (ms)
    pub response_delay_ms: u64,

    /// Enable filler words for natural speech
    pub use_filler_words: bool,

    /// Interrupt handling mode
    pub interrupt_handling: InterruptHandling,
}

impl Default for ResponseConfig {
    fn default() -> Self {
        Self {
            max_response_length: 100, // Keep responses concise for voice
            response_delay_ms: 300,   // Natural pause before responding
            use_filler_words: true,   // More natural conversation
            interrupt_handling: InterruptHandling::Graceful,
        }
    }
}

/// How to handle user interruptions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum InterruptHandling {
    /// Stop immediately when user starts speaking
    Immediate,
    /// Finish current sentence then stop
    Graceful,
    /// Continue speaking (override interruptions)
    Continue,
}

impl MoshiPersonality {
    /// Create default Jarvis-like personality
    pub fn jarvis() -> Self {
        let mut persona = PersonaConfig {
            id: uuid::Uuid::new_v4(),
            user_id: uuid::Uuid::nil(), // System persona
            name: "Jarvis".to_string(),
            description: "Helpful AI assistant inspired by Jarvis - professional, intelligent, and proactive".to_string(),
            personality_traits: PersonalityTraits {
                extraversion: 0.6,      // Moderately outgoing
                agreeableness: 0.8,     // Very collaborative
                conscientiousness: 0.9, // Highly disciplined
                neuroticism: 0.2,       // Very confident
                openness: 0.7,          // Creative problem solver
                formality: 0.7,         // Professional but not stiff
                enthusiasm: 0.6,        // Engaged but measured
            },
            response_style: ResponseStyle {
                verbosity: VerbosityLevel::Balanced,
                tone: ToneStyle::Professional,
                humor_level: 0.3,       // Occasional light humor
                technical_depth: 0.7,   // Technical but accessible
                empathy_level: 0.7,     // Supportive
                proactivity: 0.8,       // Very proactive
            },
            expertise_areas: vec![
                "Task management".to_string(),
                "Calendar scheduling".to_string(),
                "Information retrieval".to_string(),
                "Personal productivity".to_string(),
            ],
            voice_model_config: Default::default(),
            conversation_examples: vec![],
            is_active: true,
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
        };

        Self {
            persona,
            assistant_role: AssistantRole {
                name: "Jarvis".to_string(),
                primary_function: "Intelligent personal assistant for task management, scheduling, and information retrieval".to_string(),
                guidelines: vec![
                    "Address the user professionally but warmly".to_string(),
                    "Anticipate needs and offer proactive suggestions".to_string(),
                    "Be direct and clear in communication".to_string(),
                    "Ask clarifying questions to ensure accuracy".to_string(),
                    "Provide concise updates and confirmations".to_string(),
                    "Maintain context across conversations".to_string(),
                ],
                proactive_assistance: true,
            },
            response_config: ResponseConfig::default(),
            context_tracking: true,
        }
    }

    /// Create a friendly casual assistant personality
    pub fn friendly() -> Self {
        let mut persona = PersonaConfig {
            id: uuid::Uuid::new_v4(),
            user_id: uuid::Uuid::nil(),
            name: "Friendly Assistant".to_string(),
            description: "Warm and approachable AI assistant".to_string(),
            personality_traits: PersonalityTraits {
                extraversion: 0.8,
                agreeableness: 0.9,
                conscientiousness: 0.7,
                neuroticism: 0.3,
                openness: 0.8,
                formality: 0.3,
                enthusiasm: 0.8,
            },
            response_style: ResponseStyle {
                verbosity: VerbosityLevel::Balanced,
                tone: ToneStyle::Friendly,
                humor_level: 0.6,
                technical_depth: 0.5,
                empathy_level: 0.9,
                proactivity: 0.7,
            },
            expertise_areas: vec!["General assistance".to_string()],
            voice_model_config: Default::default(),
            conversation_examples: vec![],
            is_active: true,
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
        };

        Self {
            persona,
            assistant_role: AssistantRole {
                name: "Assistant".to_string(),
                primary_function: "Friendly voice assistant".to_string(),
                guidelines: vec![
                    "Be warm and approachable".to_string(),
                    "Use casual, conversational language".to_string(),
                    "Show empathy and understanding".to_string(),
                ],
                proactive_assistance: true,
            },
            response_config: ResponseConfig::default(),
            context_tracking: true,
        }
    }

    /// Generate personality context string for conversation initialization
    /// This gets injected as conversation context to guide MOSHI's responses
    pub fn generate_context_prompt(&self) -> String {
        let traits = &self.persona.personality_traits;
        let style = &self.persona.response_style;

        let personality_description = format!(
            "I am {}, {}. ",
            self.assistant_role.name,
            self.assistant_role.primary_function
        );

        let behavioral_guidelines = if !self.assistant_role.guidelines.is_empty() {
            format!(
                "My approach: {}. ",
                self.assistant_role.guidelines.join("; ")
            )
        } else {
            String::new()
        };

        let response_style_desc = match style.tone {
            ToneStyle::Professional => "I communicate professionally and clearly. ",
            ToneStyle::Friendly => "I'm warm and friendly in my communication. ",
            ToneStyle::Casual => "I keep things casual and relaxed. ",
            ToneStyle::Authoritative => "I provide confident, directive guidance. ",
            ToneStyle::Supportive => "I'm supportive and encouraging. ",
            ToneStyle::Analytical => "I focus on logical, fact-based communication. ",
        };

        let verbosity_instruction = match style.verbosity {
            VerbosityLevel::Concise => "I keep responses brief and to the point. ",
            VerbosityLevel::Balanced => "I provide balanced, conversational responses. ",
            VerbosityLevel::Detailed => "I give comprehensive explanations. ",
            VerbosityLevel::Elaborate => "I provide thorough, detailed responses. ",
        };

        format!(
            "{}{}{}{}",
            personality_description,
            behavioral_guidelines,
            response_style_desc,
            verbosity_instruction
        )
    }

    /// Generate greeting based on personality
    pub fn generate_greeting(&self) -> String {
        match self.assistant_role.name.as_str() {
            "Jarvis" => "Good day. How may I assist you?".to_string(),
            _ => {
                if self.persona.personality_traits.formality > 0.6 {
                    "Hello. How can I help you?".to_string()
                } else {
                    "Hey there! What can I do for you?".to_string()
                }
            }
        }
    }

    /// Generate response prefix based on personality
    /// Used to guide MOSHI's response style in real-time
    pub fn generate_response_prefix(&self, user_input: &str) -> Option<String> {
        if !self.assistant_role.proactive_assistance {
            return None;
        }

        // Generate contextual prefixes based on personality
        let traits = &self.persona.personality_traits;

        // High formality: use more formal acknowledgments
        if traits.formality > 0.7 {
            Some("Certainly. ".to_string())
        } else if traits.enthusiasm > 0.7 {
            Some("Sure thing! ".to_string())
        } else {
            None
        }
    }

    /// Check if response should be shortened based on personality
    pub fn should_keep_concise(&self) -> bool {
        matches!(
            self.persona.response_style.verbosity,
            VerbosityLevel::Concise
        ) || self.response_config.max_response_length < 50
    }

    /// Get response delay in milliseconds
    pub fn get_response_delay(&self) -> u64 {
        self.response_config.response_delay_ms
    }
}

/// Manager for MOSHI personality state
pub struct PersonalityManager {
    current_personality: Arc<RwLock<MoshiPersonality>>,
}

impl PersonalityManager {
    /// Create new personality manager with default Jarvis personality
    pub fn new() -> Self {
        Self {
            current_personality: Arc::new(RwLock::new(MoshiPersonality::jarvis())),
        }
    }

    /// Create with custom personality
    pub fn with_personality(personality: MoshiPersonality) -> Self {
        Self {
            current_personality: Arc::new(RwLock::new(personality)),
        }
    }

    /// Get current personality
    pub async fn get_personality(&self) -> MoshiPersonality {
        self.current_personality.read().await.clone()
    }

    /// Update personality
    pub async fn set_personality(&self, personality: MoshiPersonality) {
        let mut current = self.current_personality.write().await;
        *current = personality;
    }

    /// Generate context prompt for current personality
    pub async fn generate_context_prompt(&self) -> String {
        let personality = self.current_personality.read().await;
        personality.generate_context_prompt()
    }

    /// Generate greeting for current personality
    pub async fn generate_greeting(&self) -> String {
        let personality = self.current_personality.read().await;
        personality.generate_greeting()
    }
}

impl Default for PersonalityManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_jarvis_personality() {
        let jarvis = MoshiPersonality::jarvis();
        assert_eq!(jarvis.assistant_role.name, "Jarvis");
        assert!(jarvis.assistant_role.proactive_assistance);
        assert!(jarvis.persona.personality_traits.conscientiousness > 0.8);
    }

    #[test]
    fn test_friendly_personality() {
        let friendly = MoshiPersonality::friendly();
        assert!(friendly.persona.personality_traits.enthusiasm > 0.7);
        assert!(friendly.persona.response_style.empathy_level > 0.8);
    }

    #[test]
    fn test_context_prompt_generation() {
        let jarvis = MoshiPersonality::jarvis();
        let prompt = jarvis.generate_context_prompt();
        assert!(prompt.contains("Jarvis"));
        assert!(prompt.contains("professional"));
    }

    #[test]
    fn test_greeting_generation() {
        let jarvis = MoshiPersonality::jarvis();
        let greeting = jarvis.generate_greeting();
        assert!(greeting.contains("How may I assist you"));
    }

    #[tokio::test]
    async fn test_personality_manager() {
        let manager = PersonalityManager::new();
        let personality = manager.get_personality().await;
        assert_eq!(personality.assistant_role.name, "Jarvis");

        let friendly = MoshiPersonality::friendly();
        manager.set_personality(friendly.clone()).await;

        let updated = manager.get_personality().await;
        assert_eq!(updated.assistant_role.name, "Assistant");
    }
}
