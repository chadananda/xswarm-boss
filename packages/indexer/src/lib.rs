mod client;
mod document;
mod embeddings;

pub use client::SearchClient;
pub use document::{Document, DocumentType, Chunk};
pub use embeddings::{EmbeddingProvider, OpenAIEmbeddings};

#[cfg(feature = "local-embeddings")]
pub use embeddings::LocalEmbeddings;

use anyhow::Result;

/// Initialize the indexer with default settings
pub async fn init() -> Result<SearchClient> {
    SearchClient::new().await
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_init() {
        let result = init().await;
        assert!(result.is_ok());
    }
}
