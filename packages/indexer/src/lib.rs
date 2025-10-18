use anyhow::Result;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct Document {
    pub id: String,
    pub title: String,
    pub content: String,
    pub path: String,
    pub project: Option<String>,
}

pub struct Indexer {
    meilisearch_url: String,
}

impl Indexer {
    pub fn new(meilisearch_url: String) -> Self {
        Self { meilisearch_url }
    }

    pub async fn index_document(&self, document: Document) -> Result<()> {
        // TODO: Implement Meilisearch indexing
        println!("Indexing document: {}", document.title);
        Ok(())
    }

    pub async fn search(&self, query: &str) -> Result<Vec<Document>> {
        // TODO: Implement Meilisearch search
        println!("Searching for: {}", query);
        Ok(vec![])
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_indexer_creation() {
        let indexer = Indexer::new("http://localhost:7700".to_string());
        assert_eq!(indexer.meilisearch_url, "http://localhost:7700");
    }
}
