/// Semantic Memory System
///
/// Provides 3-tier memory architecture with vector embeddings:
/// - Session Memory: Current conversation context (short-term)
/// - Episodic Memory: Recent interactions (tier-based retention)
/// - Semantic Memory: Long-term facts and knowledge (permanent)
///
/// Note: Currently uses JSON-serialized vectors with application-level
/// similarity search. Can be migrated to native vector DB later.

pub mod storage;
pub mod embeddings;
pub mod extraction;
pub mod retrieval;
pub mod conversation;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

// Re-export conversation types
pub use conversation::{ConversationMemory, ConversationMessage, ConversationSession, Speaker};

/// Memory system configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryConfig {
    /// Embedding model to use (e.g., "text-embedding-ada-002")
    pub embedding_model: String,

    /// Minimum confidence threshold for fact extraction (0.0-1.0)
    pub fact_confidence_threshold: f32,

    /// Enable entity recognition
    pub entity_recognition_enabled: bool,

    /// Memory retention period in days (None = permanent)
    pub retention_days: Option<u32>,

    /// OpenAI API key for embeddings
    pub openai_api_key: Option<String>,
}

impl Default for MemoryConfig {
    fn default() -> Self {
        Self {
            embedding_model: "text-embedding-ada-002".to_string(),
            fact_confidence_threshold: 0.8,
            entity_recognition_enabled: true,
            retention_days: Some(30), // Default to free tier
            openai_api_key: None,
        }
    }
}

/// Main memory system coordinator
pub struct MemorySystem {
    config: MemoryConfig,
    storage: storage::MemoryStorage,
    embeddings: embeddings::EmbeddingEngine,
    extraction: extraction::FactExtractor,
    retrieval: retrieval::MemoryRetriever,
}

/// Memory item returned from retrieval
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryItem {
    pub id: Uuid,
    pub user_id: Uuid,
    pub content: String,
    pub memory_type: MemoryType,
    pub relevance_score: f32,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub metadata: serde_json::Value,
}

/// Type of memory
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum MemoryType {
    Session,
    Episodic,
    Semantic,
}

/// Extracted fact from conversation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Fact {
    pub id: Uuid,
    pub user_id: Uuid,
    pub fact_text: String,
    pub category: Option<String>,
    pub confidence: f32,
    pub source_session: Option<Uuid>,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

/// Entity extracted from conversation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Entity {
    pub id: Uuid,
    pub user_id: Uuid,
    pub entity_type: EntityType,
    pub name: String,
    pub attributes: serde_json::Value,
    pub mention_count: u32,
    pub first_mentioned: chrono::DateTime<chrono::Utc>,
    pub last_mentioned: chrono::DateTime<chrono::Utc>,
}

/// Type of entity
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum EntityType {
    Person,
    Place,
    Project,
    Company,
    Concept,
    Other,
}

impl MemorySystem {
    /// Create a new memory system with the given configuration
    pub async fn new(config: MemoryConfig) -> Result<Self> {
        let storage = storage::MemoryStorage::new().await
            .context("Failed to initialize memory storage")?;

        let embeddings = embeddings::EmbeddingEngine::new(
            config.embedding_model.clone(),
            config.openai_api_key.clone(),
        ).await.context("Failed to initialize embedding engine")?;

        let extraction = extraction::FactExtractor::new(
            config.fact_confidence_threshold,
            config.entity_recognition_enabled,
        );

        let retrieval = retrieval::MemoryRetriever::new();

        Ok(Self {
            config,
            storage,
            embeddings,
            extraction,
            retrieval,
        })
    }

    /// Store a conversation in memory
    pub async fn store_conversation(
        &self,
        user_id: Uuid,
        text: &str,
    ) -> Result<Uuid> {
        // Generate embedding for the text
        let embedding = self.embeddings.generate(text).await?;

        // Store in session memory
        let session_id = self.storage.store_session(
            user_id,
            text,
            &embedding,
        ).await?;

        // Extract facts asynchronously (non-blocking)
        if self.config.entity_recognition_enabled {
            let _ = self.extract_facts(user_id, session_id).await;
        }

        Ok(session_id)
    }

    /// Retrieve relevant memories for a query
    pub async fn retrieve_context(
        &self,
        user_id: Uuid,
        query: &str,
        limit: usize,
    ) -> Result<Vec<MemoryItem>> {
        // Generate embedding for query
        let query_embedding = self.embeddings.generate(query).await?;

        // Retrieve from all memory tiers
        self.retrieval.search(
            &self.storage,
            user_id,
            &query_embedding,
            limit,
        ).await
    }

    /// Extract facts from a conversation session
    pub async fn extract_facts(
        &self,
        user_id: Uuid,
        session_id: Uuid,
    ) -> Result<Vec<Fact>> {
        // Get the session text
        let session_text = self.storage.get_session_text(session_id).await?;

        // Extract facts using the fact extractor
        let facts = self.extraction.extract_facts(&session_text).await?;

        // Store facts with embeddings
        for fact in &facts {
            let embedding = self.embeddings.generate(&fact.fact_text).await?;
            self.storage.store_fact_from_obj(user_id, fact, &embedding, Some(session_id)).await?;
        }

        Ok(facts)
    }

    /// Get all entities for a user
    pub async fn get_entities(&self, user_id: Uuid) -> Result<Vec<Entity>> {
        self.storage.get_entities(user_id).await
    }

    /// Clean up old memories based on retention policy
    pub async fn cleanup_old_memories(&self, user_id: Uuid) -> Result<u64> {
        if let Some(retention_days) = self.config.retention_days {
            self.storage.cleanup_old_sessions(user_id, retention_days).await
        } else {
            Ok(0) // No cleanup for permanent storage
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_memory_system_creation() {
        let config = MemoryConfig::default();
        let result = MemorySystem::new(config).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_memory_config_defaults() {
        let config = MemoryConfig::default();
        assert_eq!(config.embedding_model, "text-embedding-ada-002");
        assert_eq!(config.fact_confidence_threshold, 0.8);
        assert!(config.entity_recognition_enabled);
        assert_eq!(config.retention_days, Some(30));
    }
}
