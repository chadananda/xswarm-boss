use crate::document::{Chunk, Document};
use crate::embeddings::{self, EmbeddingProvider};
use anyhow::{Context, Result};
use meilisearch_sdk::client::Client;
use meilisearch_sdk::indexes::Index;
use serde::{Deserialize, Serialize};
use std::env;

const DEFAULT_MEILISEARCH_URL: &str = "http://localhost:7700";
const DOCUMENTS_INDEX: &str = "documents";
const CHUNKS_INDEX: &str = "chunks";

/// Search client for indexing and querying documents
pub struct SearchClient {
    client: Client,
    embedding_provider: Box<dyn EmbeddingProvider>,
    documents_index: Index,
    chunks_index: Index,
}

impl SearchClient {
    /// Create a new search client
    pub async fn new() -> Result<Self> {
        let url = env::var("MEILISEARCH_URL")
            .unwrap_or_else(|_| DEFAULT_MEILISEARCH_URL.to_string());

        let master_key = env::var("MEILI_MASTER_KEY").ok();

        let client = Client::new(url, master_key)
            .map_err(|e| anyhow::anyhow!("Failed to create Meilisearch client: {}", e))?;

        // Initialize embedding provider
        let embedding_provider = embeddings::create_provider()
            .await
            .context("Failed to create embedding provider")?;

        tracing::info!(
            "Using embedding model: {} (dimension: {})",
            embedding_provider.model_name(),
            embedding_provider.dimension()
        );

        // Get or create indexes
        let documents_index = client
            .index(DOCUMENTS_INDEX)
            .create(None)
            .await
            .or_else(|_| async { client.index(DOCUMENTS_INDEX) })
            .await?;

        let chunks_index = client
            .index(CHUNKS_INDEX)
            .create(None)
            .await
            .or_else(|_| async { client.index(CHUNKS_INDEX) })
            .await?;

        // Configure indexes
        Self::configure_index(&documents_index).await?;
        Self::configure_index(&chunks_index).await?;

        Ok(Self {
            client,
            embedding_provider,
            documents_index,
            chunks_index,
        })
    }

    /// Configure index settings
    async fn configure_index(index: &Index) -> Result<()> {
        // Set searchable attributes
        index
            .set_searchable_attributes(&["title", "content", "tags"])
            .await
            .context("Failed to set searchable attributes")?;

        // Set filterable attributes
        index
            .set_filterable_attributes(&[
                "type",
                "project",
                "language",
                "extension",
                "tags",
                "indexed_at",
            ])
            .await
            .context("Failed to set filterable attributes")?;

        // Set sortable attributes
        index
            .set_sortable_attributes(&["indexed_at", "modified_at"])
            .await
            .context("Failed to set sortable attributes")?;

        Ok(())
    }

    /// Index a single document
    pub async fn index_document(&self, mut document: Document) -> Result<()> {
        tracing::debug!("Indexing document: {}", document.title);

        // Chunk the document if not already chunked
        if document.chunks.is_empty() {
            document.chunk(500); // 500 char chunks
        }

        // Generate embeddings for chunks
        let chunk_texts: Vec<String> = document
            .chunks
            .iter()
            .map(|c| c.content.clone())
            .collect();

        if !chunk_texts.is_empty() {
            let embeddings = self
                .embedding_provider
                .embed(&chunk_texts)
                .await
                .context("Failed to generate embeddings")?;

            // Attach embeddings to chunks
            for (chunk, embedding) in document.chunks.iter_mut().zip(embeddings.iter()) {
                chunk.embedding = Some(embedding.clone());
            }
        }

        // Index document
        self.documents_index
            .add_documents(&[&document], Some("id"))
            .await
            .context("Failed to index document")?;

        // Index chunks separately for semantic search
        if !document.chunks.is_empty() {
            self.chunks_index
                .add_documents(&document.chunks, Some("id"))
                .await
                .context("Failed to index chunks")?;
        }

        tracing::debug!("Indexed document with {} chunks", document.chunks.len());

        Ok(())
    }

    /// Index multiple documents
    pub async fn index_documents(&self, documents: Vec<Document>) -> Result<()> {
        for document in documents {
            self.index_document(document).await?;
        }
        Ok(())
    }

    /// Search documents by keyword
    pub async fn search_documents(&self, query: &str, limit: usize) -> Result<Vec<Document>> {
        let results = self
            .documents_index
            .search()
            .with_query(query)
            .with_limit(limit)
            .execute::<Document>()
            .await
            .context("Failed to search documents")?;

        Ok(results.hits.into_iter().map(|hit| hit.result).collect())
    }

    /// Search with filters
    pub async fn search_with_filter(
        &self,
        query: &str,
        filter: &str,
        limit: usize,
    ) -> Result<Vec<Document>> {
        let results = self
            .documents_index
            .search()
            .with_query(query)
            .with_filter(filter)
            .with_limit(limit)
            .execute::<Document>()
            .await
            .context("Failed to search with filter")?;

        Ok(results.hits.into_iter().map(|hit| hit.result).collect())
    }

    /// Semantic search using embeddings
    pub async fn semantic_search(&self, query: &str, limit: usize) -> Result<Vec<SearchResult>> {
        // Generate embedding for query
        let query_embedding = self
            .embedding_provider
            .embed(&[query.to_string()])
            .await
            .context("Failed to generate query embedding")?;

        if query_embedding.is_empty() {
            anyhow::bail!("No embedding generated for query");
        }

        let query_vec = &query_embedding[0];

        // Get all chunks (we'll need vector search plugin for real semantic search)
        // For now, do keyword search and re-rank by similarity
        let chunks_results = self
            .chunks_index
            .search()
            .with_query(query)
            .with_limit(limit * 3) // Get more candidates for re-ranking
            .execute::<Chunk>()
            .await
            .context("Failed to search chunks")?;

        let mut results: Vec<SearchResult> = chunks_results
            .hits
            .into_iter()
            .filter_map(|hit| {
                let chunk = hit.result;
                let embedding = chunk.embedding.as_ref()?;

                // Calculate cosine similarity
                let similarity = cosine_similarity(query_vec, embedding);

                Some(SearchResult {
                    chunk,
                    score: similarity,
                })
            })
            .collect();

        // Sort by similarity score (descending)
        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());

        // Take top N
        results.truncate(limit);

        Ok(results)
    }

    /// Get document by ID
    pub async fn get_document(&self, id: &str) -> Result<Option<Document>> {
        let document = self
            .documents_index
            .get_document::<Document>(id)
            .await
            .ok();

        Ok(document)
    }

    /// Delete document by ID
    pub async fn delete_document(&self, id: &str) -> Result<()> {
        self.documents_index
            .delete_document(id)
            .await
            .context("Failed to delete document")?;

        Ok(())
    }

    /// Get index stats
    pub async fn stats(&self) -> Result<IndexStats> {
        let docs_stats = self
            .documents_index
            .get_stats()
            .await
            .context("Failed to get documents stats")?;

        let chunks_stats = self
            .chunks_index
            .get_stats()
            .await
            .context("Failed to get chunks stats")?;

        Ok(IndexStats {
            documents_count: docs_stats.number_of_documents as u64,
            chunks_count: chunks_stats.number_of_documents as u64,
            is_indexing: docs_stats.is_indexing || chunks_stats.is_indexing,
        })
    }
}

/// Search result with similarity score
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub chunk: Chunk,
    pub score: f32,
}

/// Index statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexStats {
    pub documents_count: u64,
    pub chunks_count: u64,
    pub is_indexing: bool,
}

/// Calculate cosine similarity between two vectors
fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() {
        return 0.0;
    }

    let dot_product: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let magnitude_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let magnitude_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();

    if magnitude_a == 0.0 || magnitude_b == 0.0 {
        return 0.0;
    }

    dot_product / (magnitude_a * magnitude_b)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cosine_similarity() {
        let a = vec![1.0, 0.0, 0.0];
        let b = vec![1.0, 0.0, 0.0];

        let similarity = cosine_similarity(&a, &b);
        assert!((similarity - 1.0).abs() < 0.0001);

        let c = vec![0.0, 1.0, 0.0];
        let similarity2 = cosine_similarity(&a, &c);
        assert!((similarity2 - 0.0).abs() < 0.0001);
    }

    #[tokio::test]
    async fn test_client_creation() {
        // This will fail without Meilisearch running, but tests compilation
        let result = SearchClient::new().await;
        if result.is_ok() {
            println!("SearchClient created successfully");
        }
    }
}
