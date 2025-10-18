use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::env;

/// Trait for embedding providers
#[async_trait::async_trait]
pub trait EmbeddingProvider: Send + Sync {
    /// Generate embeddings for a list of texts
    async fn embed(&self, texts: &[String]) -> Result<Vec<Vec<f32>>>;

    /// Get the dimension of embeddings produced
    fn dimension(&self) -> usize;

    /// Get the model name
    fn model_name(&self) -> &str;
}

/// OpenAI embeddings provider
pub struct OpenAIEmbeddings {
    api_key: String,
    model: String,
    client: reqwest::Client,
}

impl OpenAIEmbeddings {
    /// Create a new OpenAI embeddings provider
    pub fn new() -> Result<Self> {
        let api_key = env::var("OPENAI_API_KEY")
            .context("OPENAI_API_KEY not found in environment")?;

        Ok(Self {
            api_key,
            model: "text-embedding-3-small".to_string(),
            client: reqwest::Client::new(),
        })
    }

    /// Create with custom model
    pub fn with_model(mut self, model: String) -> Self {
        self.model = model;
        self
    }
}

#[derive(Serialize)]
struct OpenAIRequest {
    input: Vec<String>,
    model: String,
}

#[derive(Deserialize)]
struct OpenAIResponse {
    data: Vec<OpenAIEmbedding>,
}

#[derive(Deserialize)]
struct OpenAIEmbedding {
    embedding: Vec<f32>,
}

#[async_trait::async_trait]
impl EmbeddingProvider for OpenAIEmbeddings {
    async fn embed(&self, texts: &[String]) -> Result<Vec<Vec<f32>>> {
        let request = OpenAIRequest {
            input: texts.to_vec(),
            model: self.model.clone(),
        };

        let response = self
            .client
            .post("https://api.openai.com/v1/embeddings")
            .header("Authorization", format!("Bearer {}", self.api_key))
            .json(&request)
            .send()
            .await
            .context("Failed to send request to OpenAI")?;

        if !response.status().is_success() {
            let status = response.status();
            let body = response.text().await.unwrap_or_default();
            anyhow::bail!("OpenAI API error ({}): {}", status, body);
        }

        let api_response: OpenAIResponse = response
            .json()
            .await
            .context("Failed to parse OpenAI response")?;

        Ok(api_response
            .data
            .into_iter()
            .map(|e| e.embedding)
            .collect())
    }

    fn dimension(&self) -> usize {
        match self.model.as_str() {
            "text-embedding-3-small" => 1536,
            "text-embedding-3-large" => 3072,
            "text-embedding-ada-002" => 1536,
            _ => 1536, // Default
        }
    }

    fn model_name(&self) -> &str {
        &self.model
    }
}

/// Local embeddings provider using fastembed
#[cfg(feature = "local-embeddings")]
pub struct LocalEmbeddings {
    model: fastembed::TextEmbedding,
    model_name: String,
}

#[cfg(feature = "local-embeddings")]
impl LocalEmbeddings {
    /// Create a new local embeddings provider
    pub fn new() -> Result<Self> {
        use fastembed::{InitOptions, TextEmbedding};

        tracing::info!("Initializing local embedding model...");

        let model = TextEmbedding::try_new(InitOptions {
            model_name: fastembed::EmbeddingModel::AllMiniLML6V2,
            show_download_progress: true,
            ..Default::default()
        })
        .context("Failed to initialize local embedding model")?;

        Ok(Self {
            model,
            model_name: "all-MiniLM-L6-v2".to_string(),
        })
    }

    /// Try to create local embeddings, fall back to OpenAI if it fails
    pub async fn new_or_fallback() -> Result<Box<dyn EmbeddingProvider>> {
        match Self::new() {
            Ok(local) => {
                tracing::info!("Using local embeddings");
                Ok(Box::new(local))
            }
            Err(e) => {
                tracing::warn!("Failed to initialize local embeddings: {}", e);
                tracing::info!("Falling back to OpenAI embeddings");
                Ok(Box::new(OpenAIEmbeddings::new()?))
            }
        }
    }
}

#[cfg(feature = "local-embeddings")]
#[async_trait::async_trait]
impl EmbeddingProvider for LocalEmbeddings {
    async fn embed(&self, texts: &[String]) -> Result<Vec<Vec<f32>>> {
        use fastembed::Embedding;

        // Convert &[String] to Vec<&str>
        let text_refs: Vec<&str> = texts.iter().map(|s| s.as_str()).collect();

        // Generate embeddings (this is CPU-bound, run in blocking task)
        let model = self.model.clone();
        let embeddings = tokio::task::spawn_blocking(move || -> Result<Vec<Vec<f32>>> {
            let embeddings: Vec<Embedding> = model
                .embed(text_refs, None)
                .context("Failed to generate embeddings")?;

            Ok(embeddings)
        })
        .await
        .context("Embedding task panicked")??;

        Ok(embeddings)
    }

    fn dimension(&self) -> usize {
        384 // all-MiniLM-L6-v2 dimension
    }

    fn model_name(&self) -> &str {
        &self.model_name
    }
}

/// Create the best available embedding provider
pub async fn create_provider() -> Result<Box<dyn EmbeddingProvider>> {
    #[cfg(feature = "local-embeddings")]
    {
        LocalEmbeddings::new_or_fallback().await
    }

    #[cfg(not(feature = "local-embeddings"))]
    {
        Ok(Box::new(OpenAIEmbeddings::new()?))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_openai_embeddings() {
        if env::var("OPENAI_API_KEY").is_err() {
            eprintln!("Skipping OpenAI test - no API key");
            return;
        }

        let provider = OpenAIEmbeddings::new().unwrap();
        let texts = vec!["Hello, world!".to_string()];

        let embeddings = provider.embed(&texts).await.unwrap();

        assert_eq!(embeddings.len(), 1);
        assert_eq!(embeddings[0].len(), provider.dimension());
    }

    #[cfg(feature = "local-embeddings")]
    #[tokio::test]
    async fn test_local_embeddings() {
        let provider = match LocalEmbeddings::new() {
            Ok(p) => p,
            Err(e) => {
                eprintln!("Skipping local embeddings test: {}", e);
                return;
            }
        };

        let texts = vec!["Hello, world!".to_string()];
        let embeddings = provider.embed(&texts).await.unwrap();

        assert_eq!(embeddings.len(), 1);
        assert_eq!(embeddings[0].len(), provider.dimension());
    }
}
