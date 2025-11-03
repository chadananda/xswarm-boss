/// Memory Retrieval - Context-aware memory search
///
/// Implements semantic similarity search with temporal relevance scoring
/// and multi-modal retrieval across all memory tiers.

use anyhow::Result;
use uuid::Uuid;

use super::{storage::MemoryStorage, MemoryItem, MemoryType};

/// Memory retriever with context-aware ranking
pub struct MemoryRetriever {
    // Configuration for retrieval strategies
    recency_weight: f32,
    similarity_weight: f32,
    frequency_weight: f32,
}

/// Search result with scoring breakdown
#[derive(Debug, Clone)]
struct ScoredMemory {
    item: MemoryItem,
    similarity_score: f32,
    recency_score: f32,
    frequency_score: f32,
    final_score: f32,
}

impl MemoryRetriever {
    /// Create a new memory retriever with default weights
    pub fn new() -> Self {
        Self {
            similarity_weight: 0.6,  // 60% weight on semantic similarity
            recency_weight: 0.3,     // 30% weight on recency
            frequency_weight: 0.1,   // 10% weight on access frequency
        }
    }

    /// Create a retriever with custom weights
    #[allow(dead_code)]
    pub fn with_weights(
        similarity_weight: f32,
        recency_weight: f32,
        frequency_weight: f32,
    ) -> Self {
        Self {
            similarity_weight,
            recency_weight,
            frequency_weight,
        }
    }

    /// Search for relevant memories using semantic similarity
    pub async fn search(
        &self,
        storage: &MemoryStorage,
        user_id: Uuid,
        query_embedding: &[f32],
        limit: usize,
    ) -> Result<Vec<MemoryItem>> {
        // Retrieve all potential matches from storage
        let candidates = storage
            .search_similar(user_id, query_embedding, limit * 3)
            .await?;

        // Score and rank candidates
        let mut scored = self.score_candidates(candidates, query_embedding);

        // Sort by final score (descending)
        scored.sort_by(|a, b| {
            b.final_score
                .partial_cmp(&a.final_score)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        // Take top N results
        let results: Vec<MemoryItem> = scored
            .into_iter()
            .take(limit)
            .map(|s| s.item)
            .collect();

        tracing::debug!(
            "Retrieved {} memories for user {} (query dim: {})",
            results.len(),
            user_id,
            query_embedding.len()
        );

        Ok(results)
    }

    /// Score candidates using multiple factors
    fn score_candidates(
        &self,
        candidates: Vec<MemoryItem>,
        query_embedding: &[f32],
    ) -> Vec<ScoredMemory> {
        candidates
            .into_iter()
            .map(|item| {
                let similarity_score = item.relevance_score; // Already computed by storage
                let recency_score = self.calculate_recency_score(&item);
                let frequency_score = self.calculate_frequency_score(&item);

                let final_score = (similarity_score * self.similarity_weight)
                    + (recency_score * self.recency_weight)
                    + (frequency_score * self.frequency_weight);

                ScoredMemory {
                    item,
                    similarity_score,
                    recency_score,
                    frequency_score,
                    final_score,
                }
            })
            .collect()
    }

    /// Calculate recency score (more recent = higher score)
    fn calculate_recency_score(&self, item: &MemoryItem) -> f32 {
        let now = chrono::Utc::now();
        let age = now.signed_duration_since(item.created_at);

        // Exponential decay: score = exp(-age_in_days / decay_constant)
        let age_in_days = age.num_days() as f32;
        let decay_constant = 30.0; // Half-life of 30 days

        (-age_in_days / decay_constant).exp()
    }

    /// Calculate frequency score based on access count
    fn calculate_frequency_score(&self, item: &MemoryItem) -> f32 {
        // Extract access_count from metadata if available
        let access_count = item
            .metadata
            .get("access_count")
            .and_then(|v| v.as_u64())
            .unwrap_or(1) as f32;

        // Logarithmic scaling: score = log(1 + access_count) / log(100)
        ((1.0 + access_count).ln() / 100.0_f32.ln()).min(1.0)
    }

    /// Search with type filtering
    pub async fn search_by_type(
        &self,
        storage: &MemoryStorage,
        user_id: Uuid,
        query_embedding: &[f32],
        memory_type: MemoryType,
        limit: usize,
    ) -> Result<Vec<MemoryItem>> {
        // Get all results
        let all_results = self.search(storage, user_id, query_embedding, limit * 2).await?;

        // Filter by type
        let filtered: Vec<MemoryItem> = all_results
            .into_iter()
            .filter(|item| item.memory_type == memory_type)
            .take(limit)
            .collect();

        Ok(filtered)
    }

    /// Search for facts related to a query
    pub async fn search_facts(
        &self,
        storage: &MemoryStorage,
        user_id: Uuid,
        query_embedding: &[f32],
        limit: usize,
    ) -> Result<Vec<MemoryItem>> {
        self.search_by_type(
            storage,
            user_id,
            query_embedding,
            MemoryType::Semantic,
            limit,
        )
        .await
    }

    /// Search for recent conversations
    pub async fn search_conversations(
        &self,
        storage: &MemoryStorage,
        user_id: Uuid,
        query_embedding: &[f32],
        limit: usize,
    ) -> Result<Vec<MemoryItem>> {
        self.search_by_type(
            storage,
            user_id,
            query_embedding,
            MemoryType::Episodic,
            limit,
        )
        .await
    }
}

impl Default for MemoryRetriever {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::{Duration, Utc};

    #[test]
    fn test_calculate_recency_score() {
        let retriever = MemoryRetriever::new();

        // Recent item (today)
        let recent_item = MemoryItem {
            id: Uuid::new_v4(),
            user_id: Uuid::new_v4(),
            content: "test".to_string(),
            memory_type: MemoryType::Session,
            relevance_score: 0.8,
            created_at: Utc::now(),
            metadata: serde_json::json!({}),
        };
        let recent_score = retriever.calculate_recency_score(&recent_item);
        assert!(recent_score > 0.9); // Should be close to 1.0

        // Old item (90 days ago)
        let old_item = MemoryItem {
            id: Uuid::new_v4(),
            user_id: Uuid::new_v4(),
            content: "test".to_string(),
            memory_type: MemoryType::Semantic,
            relevance_score: 0.8,
            created_at: Utc::now() - Duration::days(90),
            metadata: serde_json::json!({}),
        };
        let old_score = retriever.calculate_recency_score(&old_item);
        assert!(old_score < 0.1); // Should be much lower
    }

    #[test]
    fn test_calculate_frequency_score() {
        let retriever = MemoryRetriever::new();

        // Low frequency item
        let low_freq_item = MemoryItem {
            id: Uuid::new_v4(),
            user_id: Uuid::new_v4(),
            content: "test".to_string(),
            memory_type: MemoryType::Session,
            relevance_score: 0.8,
            created_at: Utc::now(),
            metadata: serde_json::json!({ "access_count": 1 }),
        };
        let low_score = retriever.calculate_frequency_score(&low_freq_item);

        // High frequency item
        let high_freq_item = MemoryItem {
            id: Uuid::new_v4(),
            user_id: Uuid::new_v4(),
            content: "test".to_string(),
            memory_type: MemoryType::Semantic,
            relevance_score: 0.8,
            created_at: Utc::now(),
            metadata: serde_json::json!({ "access_count": 50 }),
        };
        let high_score = retriever.calculate_frequency_score(&high_freq_item);

        assert!(high_score > low_score);
    }

    #[test]
    fn test_custom_weights() {
        let retriever = MemoryRetriever::with_weights(0.5, 0.3, 0.2);
        assert_eq!(retriever.similarity_weight, 0.5);
        assert_eq!(retriever.recency_weight, 0.3);
        assert_eq!(retriever.frequency_weight, 0.2);
    }
}
