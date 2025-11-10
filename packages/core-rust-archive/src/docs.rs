//! Documentation indexing and AI self-awareness module
//!
//! This module handles:
//! - Finding and reading static HTML documentation
//! - Extracting text content from HTML
//! - Indexing documentation for AI queries
//! - Providing docs path resolution

use anyhow::{Context, Result};
use scraper::{Html, Selector};
use serde::{Deserialize, Serialize};
use std::env;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

/// Default documentation path (installed location)
const DEFAULT_DOCS_PATH: &str = "/usr/share/xswarm/docs";

/// Environment variable to override docs path (for development)
const DOCS_PATH_ENV: &str = "XSWARM_DOCS_PATH";

/// Represents a documentation page
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocPage {
    /// Page title
    pub title: String,
    /// Extracted text content
    pub content: String,
    /// File path relative to docs root
    pub path: String,
    /// URL path (for linking)
    pub url: String,
}

/// Documentation indexer
pub struct DocsIndexer {
    docs_path: PathBuf,
    pages: Vec<DocPage>,
}

impl DocsIndexer {
    /// Create a new documentation indexer
    pub fn new() -> Result<Self> {
        let docs_path = get_docs_path()?;
        Ok(Self {
            docs_path,
            pages: Vec::new(),
        })
    }

    /// Index all documentation pages
    pub async fn index(&mut self) -> Result<()> {
        tracing::info!("Indexing documentation from: {:?}", self.docs_path);

        if !self.docs_path.exists() {
            tracing::warn!("Documentation path does not exist: {:?}", self.docs_path);
            return Ok(());
        }

        for entry in WalkDir::new(&self.docs_path)
            .follow_links(true)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let path = entry.path();

            // Only process HTML files
            if path.extension().and_then(|s| s.to_str()) != Some("html") {
                continue;
            }

            match self.index_page(path).await {
                Ok(Some(page)) => {
                    tracing::debug!("Indexed page: {}", page.title);
                    self.pages.push(page);
                }
                Ok(None) => {
                    tracing::debug!("Skipped page: {:?}", path);
                }
                Err(e) => {
                    tracing::warn!("Failed to index {:?}: {}", path, e);
                }
            }
        }

        tracing::info!("Indexed {} documentation pages", self.pages.len());
        Ok(())
    }

    /// Index a single documentation page
    async fn index_page(&self, path: &Path) -> Result<Option<DocPage>> {
        let html = tokio::fs::read_to_string(path)
            .await
            .with_context(|| format!("Failed to read {:?}", path))?;

        let document = Html::parse_document(&html);

        // Extract title
        let title = extract_title(&document)?;

        // Extract main content (skip nav, footer, etc.)
        let content = extract_content(&document)?;

        // Calculate relative path and URL
        let relative_path = path
            .strip_prefix(&self.docs_path)
            .unwrap_or(path)
            .to_string_lossy()
            .to_string();

        let url = relative_path
            .strip_suffix(".html")
            .unwrap_or(&relative_path)
            .to_string();

        Ok(Some(DocPage {
            title,
            content,
            path: relative_path,
            url,
        }))
    }

    /// Search documentation pages
    pub fn search(&self, query: &str) -> Vec<&DocPage> {
        let query_lower = query.to_lowercase();

        self.pages
            .iter()
            .filter(|page| {
                page.title.to_lowercase().contains(&query_lower)
                    || page.content.to_lowercase().contains(&query_lower)
            })
            .collect()
    }

    /// Get all indexed pages
    pub fn pages(&self) -> &[DocPage] {
        &self.pages
    }

    /// Get documentation path
    pub fn docs_path(&self) -> &Path {
        &self.docs_path
    }
}

impl Default for DocsIndexer {
    fn default() -> Self {
        Self::new().unwrap_or_else(|e| {
            tracing::error!("Failed to create DocsIndexer: {}", e);
            Self {
                docs_path: PathBuf::from(DEFAULT_DOCS_PATH),
                pages: Vec::new(),
            }
        })
    }
}

/// Get the documentation path
///
/// Priority:
/// 1. XSWARM_DOCS_PATH environment variable
/// 2. Default installation path (/usr/share/xswarm/docs)
pub fn get_docs_path() -> Result<PathBuf> {
    if let Ok(path) = env::var(DOCS_PATH_ENV) {
        let path = PathBuf::from(path);
        if path.exists() {
            tracing::debug!("Using docs path from {}: {:?}", DOCS_PATH_ENV, path);
            return Ok(path);
        } else {
            tracing::warn!(
                "Docs path from {} does not exist: {:?}",
                DOCS_PATH_ENV,
                path
            );
        }
    }

    // Fallback to default
    let default = PathBuf::from(DEFAULT_DOCS_PATH);
    tracing::debug!("Using default docs path: {:?}", default);
    Ok(default)
}

/// Extract title from HTML document
fn extract_title(document: &Html) -> Result<String> {
    // Try <title> tag first
    if let Ok(selector) = Selector::parse("title") {
        if let Some(element) = document.select(&selector).next() {
            let title = element.text().collect::<String>().trim().to_string();
            if !title.is_empty() {
                return Ok(title);
            }
        }
    }

    // Try <h1> tag
    if let Ok(selector) = Selector::parse("h1") {
        if let Some(element) = document.select(&selector).next() {
            let title = element.text().collect::<String>().trim().to_string();
            if !title.is_empty() {
                return Ok(title);
            }
        }
    }

    Ok("Untitled".to_string())
}

/// Extract main content from HTML document
fn extract_content(document: &Html) -> Result<String> {
    // Target main content area (Astro Starlight uses <main>)
    let content_selectors = [
        "main",
        "article",
        ".content",
        "#content",
        "body",
    ];

    for selector_str in &content_selectors {
        if let Ok(selector) = Selector::parse(selector_str) {
            if let Some(element) = document.select(&selector).next() {
                let text = element.text().collect::<Vec<_>>().join(" ");
                let cleaned = text
                    .split_whitespace()
                    .collect::<Vec<_>>()
                    .join(" ")
                    .trim()
                    .to_string();

                if !cleaned.is_empty() {
                    return Ok(cleaned);
                }
            }
        }
    }

    // Fallback: extract all text
    let text = document
        .root_element()
        .text()
        .collect::<Vec<_>>()
        .join(" ");

    Ok(text
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .trim()
        .to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_title() {
        let html = r#"
            <!DOCTYPE html>
            <html>
                <head><title>Test Page</title></head>
                <body><h1>Test Page</h1></body>
            </html>
        "#;
        let document = Html::parse_document(html);
        let title = extract_title(&document).unwrap();
        assert_eq!(title, "Test Page");
    }

    #[test]
    fn test_extract_content() {
        let html = r#"
            <!DOCTYPE html>
            <html>
                <body>
                    <main>
                        <h1>Title</h1>
                        <p>This is the main content.</p>
                    </main>
                </body>
            </html>
        "#;
        let document = Html::parse_document(html);
        let content = extract_content(&document).unwrap();
        assert!(content.contains("main content"));
    }
}
