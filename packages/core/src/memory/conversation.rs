/// Conversation Memory - Real-time conversation tracking for voice assistants
///
/// Provides lightweight in-memory conversation history without requiring
/// embeddings or external APIs. Designed for MOSHI voice integration.

use anyhow::Result;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Speaker in a conversation
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Speaker {
    User,
    Assistant,
}

/// A single message in a conversation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversationMessage {
    pub id: String,
    pub timestamp: DateTime<Utc>,
    pub speaker: Speaker,
    pub content: String,
    pub importance: f32, // 0.0-1.0 for memory prioritization
}

/// Conversation session tracking
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversationSession {
    pub session_id: String,
    pub start_time: DateTime<Utc>,
    pub end_time: Option<DateTime<Utc>>,
    pub messages: Vec<ConversationMessage>,
    pub summary: Option<String>,
}

/// In-memory conversation memory for real-time voice interactions
pub struct ConversationMemory {
    /// Current active session
    current_session: Arc<RwLock<ConversationSession>>,
    /// Recent message buffer for quick context access
    recent_messages: Arc<RwLock<VecDeque<ConversationMessage>>>,
    /// Maximum number of messages to keep in recent buffer
    max_recent_messages: usize,
    /// Past sessions (for multi-session context)
    past_sessions: Arc<RwLock<Vec<ConversationSession>>>,
    /// Maximum number of past sessions to retain
    max_past_sessions: usize,
}

impl ConversationMemory {
    /// Create a new conversation memory
    pub fn new() -> Self {
        Self::with_config(50, 10)
    }

    /// Create with custom buffer sizes
    pub fn with_config(max_recent_messages: usize, max_past_sessions: usize) -> Self {
        let session_id = uuid::Uuid::new_v4().to_string();
        let now = Utc::now();

        Self {
            current_session: Arc::new(RwLock::new(ConversationSession {
                session_id,
                start_time: now,
                end_time: None,
                messages: Vec::new(),
                summary: None,
            })),
            recent_messages: Arc::new(RwLock::new(VecDeque::with_capacity(max_recent_messages))),
            max_recent_messages,
            past_sessions: Arc::new(RwLock::new(Vec::new())),
            max_past_sessions,
        }
    }

    /// Add a user message to the conversation
    pub async fn add_user_message(&self, content: String) -> Result<String> {
        self.add_message(Speaker::User, content, 0.8).await
    }

    /// Add an assistant response to the conversation
    pub async fn add_assistant_response(&self, content: String) -> Result<String> {
        self.add_message(Speaker::Assistant, content, 0.7).await
    }

    /// Add a message to the conversation
    async fn add_message(&self, speaker: Speaker, content: String, importance: f32) -> Result<String> {
        let message_id = uuid::Uuid::new_v4().to_string();
        let message = ConversationMessage {
            id: message_id.clone(),
            timestamp: Utc::now(),
            speaker,
            content,
            importance,
        };

        // Add to current session
        let mut session = self.current_session.write().await;
        session.messages.push(message.clone());
        drop(session);

        // Add to recent messages buffer
        let mut recent = self.recent_messages.write().await;
        recent.push_back(message.clone());

        // Trim buffer if needed
        if recent.len() > self.max_recent_messages {
            recent.pop_front();
        }

        tracing::debug!(
            "Added {:?} message to conversation: {} chars",
            speaker,
            message.content.len()
        );

        Ok(message_id)
    }

    /// Get recent messages for context
    pub async fn get_recent_messages(&self, limit: usize) -> Vec<ConversationMessage> {
        let recent = self.recent_messages.read().await;
        recent
            .iter()
            .rev()
            .take(limit)
            .rev()
            .cloned()
            .collect()
    }

    /// Get conversation context formatted for MOSHI prompt
    pub async fn get_context_for_prompt(&self, max_messages: usize) -> String {
        let messages = self.get_recent_messages(max_messages).await;

        if messages.is_empty() {
            return String::new();
        }

        let mut context = String::from("Conversation history:\n");
        for msg in messages {
            let speaker = match msg.speaker {
                Speaker::User => "User",
                Speaker::Assistant => "Assistant",
            };
            context.push_str(&format!("{}: {}\n", speaker, msg.content));
        }

        context
    }

    /// Start a new conversation session
    pub async fn start_new_session(&self) -> String {
        // Archive current session
        let mut current = self.current_session.write().await;
        current.end_time = Some(Utc::now());

        let archived = current.clone();
        drop(current);

        // Store in past sessions
        let mut past = self.past_sessions.write().await;
        past.push(archived);

        // Trim past sessions if needed
        if past.len() > self.max_past_sessions {
            past.remove(0);
        }
        drop(past);

        // Create new session
        let session_id = uuid::Uuid::new_v4().to_string();
        let new_session = ConversationSession {
            session_id: session_id.clone(),
            start_time: Utc::now(),
            end_time: None,
            messages: Vec::new(),
            summary: None,
        };

        let mut current = self.current_session.write().await;
        *current = new_session;

        tracing::info!("Started new conversation session: {}", session_id);

        session_id
    }

    /// Get current session info
    pub async fn get_current_session(&self) -> ConversationSession {
        self.current_session.read().await.clone()
    }

    /// Get message count in current session
    pub async fn get_message_count(&self) -> usize {
        self.current_session.read().await.messages.len()
    }

    /// Clear all conversation memory
    pub async fn clear(&self) {
        let mut recent = self.recent_messages.write().await;
        recent.clear();

        let mut session = self.current_session.write().await;
        session.messages.clear();

        let mut past = self.past_sessions.write().await;
        past.clear();

        tracing::info!("Cleared all conversation memory");
    }

    /// Get conversation summary
    pub async fn get_summary(&self) -> String {
        let session = self.current_session.read().await;
        let total_messages = session.messages.len();
        let user_messages = session.messages.iter().filter(|m| m.speaker == Speaker::User).count();
        let assistant_messages = total_messages - user_messages;

        format!(
            "Session: {} | Duration: {:?} | Messages: {} (User: {}, Assistant: {})",
            session.session_id,
            Utc::now().signed_duration_since(session.start_time),
            total_messages,
            user_messages,
            assistant_messages
        )
    }
}

impl Default for ConversationMemory {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_add_messages() {
        let memory = ConversationMemory::new();

        let msg_id = memory.add_user_message("Hello".to_string()).await.unwrap();
        assert!(!msg_id.is_empty());

        let count = memory.get_message_count().await;
        assert_eq!(count, 1);
    }

    #[tokio::test]
    async fn test_get_recent_messages() {
        let memory = ConversationMemory::new();

        memory.add_user_message("Message 1".to_string()).await.unwrap();
        memory.add_assistant_response("Response 1".to_string()).await.unwrap();
        memory.add_user_message("Message 2".to_string()).await.unwrap();

        let recent = memory.get_recent_messages(2).await;
        assert_eq!(recent.len(), 2);
        assert_eq!(recent[0].content, "Response 1");
        assert_eq!(recent[1].content, "Message 2");
    }

    #[tokio::test]
    async fn test_context_for_prompt() {
        let memory = ConversationMemory::new();

        memory.add_user_message("What's the weather?".to_string()).await.unwrap();
        memory.add_assistant_response("It's sunny today.".to_string()).await.unwrap();

        let context = memory.get_context_for_prompt(10).await;
        assert!(context.contains("User: What's the weather?"));
        assert!(context.contains("Assistant: It's sunny today."));
    }

    #[tokio::test]
    async fn test_new_session() {
        let memory = ConversationMemory::new();

        memory.add_user_message("Test".to_string()).await.unwrap();
        let old_session_id = memory.get_current_session().await.session_id;

        let new_session_id = memory.start_new_session().await;
        assert_ne!(old_session_id, new_session_id);

        let count = memory.get_message_count().await;
        assert_eq!(count, 0);
    }

    #[tokio::test]
    async fn test_clear() {
        let memory = ConversationMemory::new();

        memory.add_user_message("Test".to_string()).await.unwrap();
        assert_eq!(memory.get_message_count().await, 1);

        memory.clear().await;
        assert_eq!(memory.get_message_count().await, 0);
    }
}
