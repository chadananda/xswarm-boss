/// Embedding Engine - Vector embeddings for semantic search
///
/// Integrates with OpenAI's embedding API to generate vector representations
/// of text for semantic similarity search.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Embedding engine for generating vector representations
pub struct EmbeddingEngine {
    model: String,
    api_key: Option<String>,
    cache: std::sync::RwLock<EmbeddingCache>,
}

/// Simple in-memory cache for embeddings
struct EmbeddingCache {
    cache: HashMap<String, Vec<f32>>,
    max_size: usize,
}

/// OpenAI embedding API request
#[derive(Debug, Serialize)]
struct EmbeddingRequest {
    input: String,
    model: String,
}

/// OpenAI embedding API response
#[derive(Debug, Deserialize)]
struct EmbeddingResponse {
    data: Vec<EmbeddingData>,
}

#[derive(Debug, Deserialize)]
struct EmbeddingData {
    embedding: Vec<f32>,
}

impl EmbeddingEngine {
    /// Create a new embedding engine
    pub async fn new(model: String, api_key: Option<String>) -> Result<Self> {
        Ok(Self {
            model,
            api_key,
            cache: std::sync::RwLock::new(EmbeddingCache::new(1000)), // Cache up to 1000 embeddings
        })
    }

    /// Generate an embedding for the given text
    pub async fn generate(&self, text: &str) -> Result<Vec<f32>> {
        // Check cache first
        {
            let cache = self.cache.read().unwrap();
            if let Some(cached) = cache.get(text) {
                return Ok(cached);
            }
        }

        // Generate new embedding via API
        let embedding = self.generate_from_api(text).await?;

        // Store in cache
        {
            let mut cache = self.cache.write().unwrap();
            cache.put(text.to_string(), embedding.clone());
        }

        Ok(embedding)
    }

    /// Generate embedding from OpenAI API
    async fn generate_from_api(&self, text: &str) -> Result<Vec<f32>> {
        let api_key = self.api_key.as_ref()
            .context("OpenAI API key not configured")?;

        let client = reqwest::Client::new();
        let request = EmbeddingRequest {
            input: text.to_string(),
            model: self.model.clone(),
        };

        let response = client
            .post("https://api.openai.com/v1/embeddings")
            .header("Authorization", format!("Bearer {}", api_key))
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .context("Failed to send embedding request")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("OpenAI API error: {}", error_text);
        }

        let embedding_response: EmbeddingResponse = response
            .json()
            .await
            .context("Failed to parse embedding response")?;

        let embedding = embedding_response.data
            .first()
            .context("No embedding data in response")?
            .embedding
            .clone();

        tracing::debug!(
            "Generated embedding for text (len={}, dims={})",
            text.len(),
            embedding.len()
        );

        Ok(embedding)
    }

    /// Generate embeddings for multiple texts in batch
    pub async fn generate_batch(&self, texts: &[String]) -> Result<Vec<Vec<f32>>> {
        let mut embeddings = Vec::with_capacity(texts.len());

        for text in texts {
            let embedding = self.generate(text).await?;
            embeddings.push(embedding);
        }

        Ok(embeddings)
    }

    /// Get the dimension of embeddings produced by this model
    pub fn embedding_dimension(&self) -> usize {
        // text-embedding-ada-002 produces 1536-dimensional vectors
        match self.model.as_str() {
            "text-embedding-ada-002" => 1536,
            "text-embedding-3-small" => 1536,
            "text-embedding-3-large" => 3072,
            _ => 1536, // Default
        }
    }
}

impl EmbeddingCache {
    fn new(max_size: usize) -> Self {
        Self {
            cache: HashMap::new(),
            max_size,
        }
    }

    fn get(&self, key: &str) -> Option<Vec<f32>> {
        self.cache.get(key).cloned()
    }

    fn put(&mut self, key: String, value: Vec<f32>) {
        // Simple LRU-like eviction: clear cache when full
        if self.cache.len() >= self.max_size {
            tracing::debug!("Embedding cache full, clearing");
            self.cache.clear();
        }
        self.cache.insert(key, value);
    }

    #[allow(dead_code)]
    fn clear(&mut self) {
        self.cache.clear();
    }
}

/// Normalize a vector to unit length
pub fn normalize_vector(v: &[f32]) -> Vec<f32> {
    let magnitude: f32 = v.iter().map(|x| x * x).sum::<f32>().sqrt();
    if magnitude == 0.0 {
        return v.to_vec();
    }
    v.iter().map(|x| x / magnitude).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_vector() {
        let v = vec![3.0, 4.0];
        let normalized = normalize_vector(&v);
        let magnitude: f32 = normalized.iter().map(|x| x * x).sum::<f32>().sqrt();
        assert!((magnitude - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_embedding_dimension() {
        let engine = EmbeddingEngine {
            model: "text-embedding-ada-002".to_string(),
            api_key: None,
            cache: std::cell::RefCell::new(EmbeddingCache::new(100)),
        };
        assert_eq!(engine.embedding_dimension(), 1536);
    }

    #[test]
    fn test_embedding_cache() {
        let mut cache = EmbeddingCache::new(2);
        cache.put("test1".to_string(), vec![1.0, 2.0]);
        cache.put("test2".to_string(), vec![3.0, 4.0]);

        assert!(cache.get("test1").is_some());
        assert!(cache.get("test2").is_some());

        // Adding third item should clear cache
        cache.put("test3".to_string(), vec![5.0, 6.0]);
        assert!(cache.cache.len() <= 2);
    }
}
