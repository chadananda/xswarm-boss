use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use uuid::Uuid;

/// Type of document being indexed
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum DocumentType {
    /// Source code file
    Code,
    /// Documentation (markdown, HTML, PDF)
    Documentation,
    /// Configuration file
    Config,
    /// Conversation/chat history
    Conversation,
    /// Email message
    Email,
    /// General text document
    Text,
    /// Unknown/other
    Other,
}

/// A document to be indexed
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Document {
    /// Unique identifier
    pub id: String,

    /// Document title
    pub title: String,

    /// Full content (for display)
    pub content: String,

    /// File path (if from filesystem)
    pub path: Option<PathBuf>,

    /// Document type
    #[serde(rename = "type")]
    pub doc_type: DocumentType,

    /// Project name (if associated with a project)
    pub project: Option<String>,

    /// Programming language (for code files)
    pub language: Option<String>,

    /// File extension
    pub extension: Option<String>,

    /// When the document was indexed
    pub indexed_at: DateTime<Utc>,

    /// When the document was last modified
    pub modified_at: Option<DateTime<Utc>>,

    /// Chunks for semantic search
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub chunks: Vec<Chunk>,

    /// Tags for categorization
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub tags: Vec<String>,

    /// Custom metadata
    #[serde(skip_serializing_if = "serde_json::Value::is_null", default)]
    pub metadata: serde_json::Value,
}

/// A chunk of a document for semantic search
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Chunk {
    /// Unique chunk identifier
    pub id: String,

    /// Parent document ID
    pub document_id: String,

    /// Chunk content
    pub content: String,

    /// Chunk index in document
    pub index: usize,

    /// Start position in original content
    pub start_pos: usize,

    /// End position in original content
    pub end_pos: usize,

    /// Embedding vector (if computed)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub embedding: Option<Vec<f32>>,

    /// Chunk type (paragraph, code_block, function, etc.)
    pub chunk_type: Option<String>,
}

impl Document {
    /// Create a new document
    pub fn new(title: String, content: String, doc_type: DocumentType) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            title,
            content,
            path: None,
            doc_type,
            project: None,
            language: None,
            extension: None,
            indexed_at: Utc::now(),
            modified_at: None,
            chunks: Vec::new(),
            tags: Vec::new(),
            metadata: serde_json::Value::Null,
        }
    }

    /// Create a document from a file path
    pub fn from_path(path: PathBuf, content: String, doc_type: DocumentType) -> Self {
        let title = path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("Untitled")
            .to_string();

        let extension = path
            .extension()
            .and_then(|e| e.to_str())
            .map(|s| s.to_string());

        let language = extension.as_ref().and_then(|ext| match ext.as_str() {
            "rs" => Some("rust".to_string()),
            "ts" | "tsx" => Some("typescript".to_string()),
            "js" | "jsx" => Some("javascript".to_string()),
            "py" => Some("python".to_string()),
            "go" => Some("go".to_string()),
            "java" => Some("java".to_string()),
            "c" | "h" => Some("c".to_string()),
            "cpp" | "cc" | "hpp" => Some("cpp".to_string()),
            _ => None,
        });

        Self {
            id: Uuid::new_v4().to_string(),
            title,
            content,
            path: Some(path),
            doc_type,
            project: None,
            language,
            extension,
            indexed_at: Utc::now(),
            modified_at: None,
            chunks: Vec::new(),
            tags: Vec::new(),
            metadata: serde_json::Value::Null,
        }
    }

    /// Chunk the document content
    pub fn chunk(&mut self, max_chunk_size: usize) {
        self.chunks = chunk_text(&self.content, &self.id, max_chunk_size);
    }

    /// Add tags
    pub fn with_tags(mut self, tags: Vec<String>) -> Self {
        self.tags = tags;
        self
    }

    /// Add project
    pub fn with_project(mut self, project: String) -> Self {
        self.project = Some(project);
        self
    }

    /// Add metadata
    pub fn with_metadata(mut self, metadata: serde_json::Value) -> Self {
        self.metadata = metadata;
        self
    }
}

/// Chunk text content into smaller pieces
pub fn chunk_text(content: &str, document_id: &str, max_size: usize) -> Vec<Chunk> {
    let mut chunks = Vec::new();
    let mut current_chunk = String::new();
    let mut chunk_start = 0;
    let mut chunk_index = 0;

    // Simple sentence-based chunking
    // TODO: Improve with semantic chunking (preserve code blocks, sections)
    for (_pos, sentence) in content.split(|c| c == '.' || c == '\n').enumerate() {
        let sentence = sentence.trim();
        if sentence.is_empty() {
            continue;
        }

        if current_chunk.len() + sentence.len() > max_size && !current_chunk.is_empty() {
            // Save current chunk
            let chunk_end = chunk_start + current_chunk.len();
            chunks.push(Chunk {
                id: format!("{}_{}", document_id, chunk_index),
                document_id: document_id.to_string(),
                content: current_chunk.clone(),
                index: chunk_index,
                start_pos: chunk_start,
                end_pos: chunk_end,
                embedding: None,
                chunk_type: Some("text".to_string()),
            });

            chunk_index += 1;
            chunk_start = chunk_end;
            current_chunk.clear();
        }

        if !current_chunk.is_empty() {
            current_chunk.push(' ');
        }
        current_chunk.push_str(sentence);
    }

    // Add final chunk
    if !current_chunk.is_empty() {
        let chunk_end = chunk_start + current_chunk.len();
        chunks.push(Chunk {
            id: format!("{}_{}", document_id, chunk_index),
            document_id: document_id.to_string(),
            content: current_chunk,
            index: chunk_index,
            start_pos: chunk_start,
            end_pos: chunk_end,
            embedding: None,
            chunk_type: Some("text".to_string()),
        });
    }

    chunks
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_document_creation() {
        let doc = Document::new(
            "Test".to_string(),
            "Content".to_string(),
            DocumentType::Text,
        );

        assert_eq!(doc.title, "Test");
        assert_eq!(doc.content, "Content");
        assert_eq!(doc.doc_type, DocumentType::Text);
    }

    #[test]
    fn test_document_from_path() {
        let path = PathBuf::from("test.rs");
        let doc = Document::from_path(path.clone(), "fn main() {}".to_string(), DocumentType::Code);

        assert_eq!(doc.title, "test.rs");
        assert_eq!(doc.language, Some("rust".to_string()));
        assert_eq!(doc.extension, Some("rs".to_string()));
        assert_eq!(doc.path, Some(path));
    }

    #[test]
    fn test_chunking() {
        let content = "This is sentence one. This is sentence two. This is sentence three.";
        let chunks = chunk_text(content, "doc1", 30);

        assert!(chunks.len() > 1);
        assert_eq!(chunks[0].document_id, "doc1");
        assert_eq!(chunks[0].index, 0);
    }
}
