/// Memory Storage - Local libsql database for semantic memory
///
/// IMPORTANT: This is LOCAL storage only, separate from server libsql (Turso).
/// - Local database: ~/.xswarm/memory.db (persistent, offline-capable)
/// - Server database: Turso (multi-user, multi-device - accessed via API)
///
/// Why local libsql?
/// - MOSHI has tiny context window (needs persistent memory)
/// - Works offline (no server dependency)
/// - Vector embeddings for semantic search
/// - Survives app restarts

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use libsql::Database;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use uuid::Uuid;

use super::{Entity, MemoryItem, MemoryType};

/// Memory storage engine using local libsql
pub struct MemoryStorage {
    /// Local SQLite database connection
    db: Database,
    /// Database file path
    db_path: PathBuf,
}

/// Session data stored in database
#[derive(Debug, Clone, Serialize, Deserialize)]
struct SessionRecord {
    id: String,
    user_id: String,
    session_start: String,
    session_end: Option<String>,
    summary: Option<String>,
    key_topics: String, // JSON array
    embedding: String,  // JSON array of f32
}

/// Fact record stored in database
#[derive(Debug, Clone, Serialize, Deserialize)]
struct FactRecord {
    id: String,
    user_id: String,
    fact_text: String,
    source_session: Option<String>,
    confidence: f32,
    category: Option<String>,
    embedding: String, // JSON array of f32
    created_at: String,
    last_accessed: String,
    access_count: i64,
}

impl MemoryStorage {
    /// Create a new memory storage engine with local libsql database
    ///
    /// Database location: ~/.xswarm/memory.db
    pub async fn new() -> Result<Self> {
        // Get database path
        let db_path = Self::get_db_path()?;

        // Ensure directory exists
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent)
                .context("Failed to create xswarm data directory")?;
        }

        tracing::info!("Opening local memory database at: {}", db_path.display());

        // Open local database (synchronous operation in libsql 0.6)
        let db = Database::open(db_path.to_str().unwrap())
            .context("Failed to open local memory database")?;

        // Initialize schema
        Self::init_schema(&db).await?;

        Ok(Self {
            db,
            db_path: db_path.clone(),
        })
    }

    /// Get database file path
    fn get_db_path() -> Result<PathBuf> {
        let home = dirs::home_dir()
            .context("Could not determine home directory")?;

        Ok(home.join(".xswarm").join("memory.db"))
    }

    /// Initialize database schema
    async fn init_schema(db: &Database) -> Result<()> {
        let conn = db.connect()?;

        // Create memory_sessions table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS memory_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_start TEXT NOT NULL,
                session_end TEXT,
                summary TEXT,
                key_topics TEXT DEFAULT '[]',
                embedding TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )",
            (),
        )
        .await
        .context("Failed to create memory_sessions table")?;

        // Create memory_facts table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS memory_facts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                fact_text TEXT NOT NULL,
                source_session TEXT,
                confidence REAL NOT NULL DEFAULT 0.8,
                category TEXT,
                embedding TEXT NOT NULL,
                access_count INTEGER DEFAULT 1,
                last_accessed TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )",
            (),
        )
        .await
        .context("Failed to create memory_facts table")?;

        // Create memory_entities table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS memory_entities (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                entity_type TEXT NOT NULL CHECK(entity_type IN
                    ('person', 'place', 'project', 'company', 'concept', 'other')),
                name TEXT NOT NULL,
                attributes TEXT DEFAULT '{}',
                mention_count INTEGER DEFAULT 1,
                first_mentioned TEXT,
                last_mentioned TEXT,
                UNIQUE(user_id, entity_type, name)
            )",
            (),
        )
        .await
        .context("Failed to create memory_entities table")?;

        // Create indices for performance
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_user ON memory_sessions(user_id)",
            (),
        )
        .await?;

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_facts_user ON memory_facts(user_id)",
            (),
        )
        .await?;

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entities_user ON memory_entities(user_id)",
            (),
        )
        .await?;

        tracing::info!("Local memory database schema initialized");

        Ok(())
    }

    /// Store a conversation session
    pub async fn store_session(
        &self,
        user_id: Uuid,
        text: &str,
        embedding: &[f32],
    ) -> Result<Uuid> {
        let session_id = Uuid::new_v4();
        let now = Utc::now();
        let conn = self.db.connect()?;

        let embedding_json = serde_json::to_string(embedding)
            .context("Failed to serialize embedding")?;

        conn.execute(
            "INSERT INTO memory_sessions
             (id, user_id, session_start, summary, key_topics, embedding, created_at)
             VALUES (?, ?, ?, ?, '[]', ?, ?)",
            libsql::params![
                session_id.to_string(),
                user_id.to_string(),
                now.to_rfc3339(),
                text,
                embedding_json,
                now.to_rfc3339()
            ],
        )
        .await
        .context("Failed to insert session")?;

        tracing::info!(
            "Stored session {} for user {} ({} chars)",
            session_id,
            user_id,
            text.len()
        );

        Ok(session_id)
    }

    /// Store a fact with embedding
    pub async fn store_fact(
        &self,
        user_id: Uuid,
        fact_text: &str,
        embedding: &[f32],
        confidence: f32,
        category: Option<String>,
        source_session: Option<Uuid>,
    ) -> Result<Uuid> {
        let fact_id = Uuid::new_v4();
        let now = Utc::now();
        let conn = self.db.connect()?;

        let embedding_json = serde_json::to_string(embedding)
            .context("Failed to serialize embedding")?;

        conn.execute(
            "INSERT INTO memory_facts
             (id, user_id, fact_text, confidence, category, embedding, source_session, created_at, last_accessed)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            libsql::params![
                fact_id.to_string(),
                user_id.to_string(),
                fact_text,
                confidence,
                category,
                embedding_json,
                source_session.map(|id| id.to_string()),
                now.to_rfc3339(),
                now.to_rfc3339()
            ],
        )
        .await
        .context("Failed to insert fact")?;

        tracing::debug!("Stored fact {} for user {}", fact_id, user_id);

        Ok(fact_id)
    }

    /// Retrieve relevant memories using semantic search
    /// (Alias: search_similar for API compatibility with retrieval module)
    pub async fn search_similar(
        &self,
        user_id: Uuid,
        query_embedding: &[f32],
        limit: usize,
    ) -> Result<Vec<MemoryItem>> {
        // Use default min_similarity of 0.7
        self.search(user_id, query_embedding, limit, 0.7).await
    }

    /// Retrieve relevant memories using semantic search (internal implementation)
    pub async fn search(
        &self,
        user_id: Uuid,
        query_embedding: &[f32],
        limit: usize,
        min_similarity: f32,
    ) -> Result<Vec<MemoryItem>> {
        let conn = self.db.connect()?;

        // Get sessions
        let sessions = conn
            .query(
                "SELECT id, user_id, summary, embedding, created_at
                 FROM memory_sessions
                 WHERE user_id = ?
                 ORDER BY created_at DESC
                 LIMIT ?",
                libsql::params![user_id.to_string(), (limit * 3) as i64],
            )
            .await
            .context("Failed to query sessions")?;

        let mut results = Vec::new();

        // Calculate similarity for each session
        // libsql 0.6: Rows is an iterator, use next() in loop
        let mut rows = sessions;
        while let Some(row) = rows.next().await? {
            let id_str: String = row.get(0)?;
            let user_id_str: String = row.get(1)?;
            let content: String = row.get(2)?;
            let embedding_json: String = row.get(3)?;
            let created_at_str: String = row.get(4)?;

            let embedding: Vec<f32> = serde_json::from_str(&embedding_json)
                .context("Failed to deserialize embedding")?;

            let similarity = cosine_similarity(query_embedding, &embedding);

            if similarity >= min_similarity {
                results.push(MemoryItem {
                    id: Uuid::parse_str(&id_str)?,
                    user_id: Uuid::parse_str(&user_id_str)?,
                    content,
                    memory_type: MemoryType::Session,
                    relevance_score: similarity,
                    created_at: DateTime::parse_from_rfc3339(&created_at_str)?
                        .with_timezone(&Utc),
                    metadata: serde_json::Value::Null,
                });
            }
        }

        // Sort by relevance
        results.sort_by(|a, b| {
            b.relevance_score
                .partial_cmp(&a.relevance_score)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        // Limit results
        results.truncate(limit);

        tracing::debug!(
            "Found {} relevant memories for user {} (min_similarity={})",
            results.len(),
            user_id,
            min_similarity
        );

        Ok(results)
    }

    /// Get recent conversation context (last N messages)
    pub async fn get_recent_sessions(
        &self,
        user_id: Uuid,
        limit: usize,
    ) -> Result<Vec<MemoryItem>> {
        let conn = self.db.connect()?;

        let sessions = conn
            .query(
                "SELECT id, user_id, summary, embedding, created_at
                 FROM memory_sessions
                 WHERE user_id = ?
                 ORDER BY created_at DESC
                 LIMIT ?",
                libsql::params![user_id.to_string(), limit as i64],
            )
            .await
            .context("Failed to query recent sessions")?;

        let mut results = Vec::new();

        // libsql 0.6: Rows is an iterator
        let mut rows = sessions;
        while let Some(row) = rows.next().await? {
            let id_str: String = row.get(0)?;
            let user_id_str: String = row.get(1)?;
            let content: String = row.get(2)?;
            let created_at_str: String = row.get(4)?;

            results.push(MemoryItem {
                id: Uuid::parse_str(&id_str)?,
                user_id: Uuid::parse_str(&user_id_str)?,
                content,
                memory_type: MemoryType::Session,
                relevance_score: 1.0, // Not using similarity for recent
                created_at: DateTime::parse_from_rfc3339(&created_at_str)?
                    .with_timezone(&Utc),
                metadata: serde_json::Value::Null,
            });
        }

        Ok(results)
    }

    /// Store an entity
    pub async fn store_entity(
        &self,
        user_id: Uuid,
        entity: &Entity,
    ) -> Result<()> {
        let conn = self.db.connect()?;
        let now = Utc::now();

        let entity_type_str = match entity.entity_type {
            super::EntityType::Person => "person",
            super::EntityType::Place => "place",
            super::EntityType::Project => "project",
            super::EntityType::Company => "company",
            super::EntityType::Concept => "concept",
            super::EntityType::Other => "other",
        };

        let attributes_json = serde_json::to_string(&entity.attributes)
            .unwrap_or_else(|_| "{}".to_string());

        // Upsert entity (update if exists, insert if not)
        conn.execute(
            "INSERT INTO memory_entities
             (id, user_id, entity_type, name, attributes, mention_count, first_mentioned, last_mentioned)
             VALUES (?, ?, ?, ?, ?, 1, ?, ?)
             ON CONFLICT(user_id, entity_type, name) DO UPDATE SET
                mention_count = mention_count + 1,
                last_mentioned = ?,
                attributes = ?",
            libsql::params![
                entity.id.to_string(),
                user_id.to_string(),
                entity_type_str,
                entity.name.clone(), // Clone to avoid move from shared reference
                attributes_json.clone(),
                now.to_rfc3339(),
                now.to_rfc3339(),
                now.to_rfc3339(),
                attributes_json
            ],
        )
        .await
        .context("Failed to upsert entity")?;

        Ok(())
    }

    /// Get all entities for a user
    pub async fn get_entities(&self, user_id: Uuid) -> Result<Vec<Entity>> {
        let conn = self.db.connect()?;

        let entities = conn
            .query(
                "SELECT id, entity_type, name, attributes, mention_count, first_mentioned, last_mentioned
                 FROM memory_entities
                 WHERE user_id = ?
                 ORDER BY mention_count DESC",
                libsql::params![user_id.to_string()],
            )
            .await
            .context("Failed to query entities")?;

        let mut results = Vec::new();

        // libsql 0.6: Rows is an iterator
        let mut rows = entities;
        while let Some(row) = rows.next().await? {
            let id_str: String = row.get(0)?;
            let entity_type_str: String = row.get(1)?;
            let name: String = row.get(2)?;
            let attributes_json: String = row.get(3)?;
            let mention_count: i64 = row.get(4)?;
            let first_mentioned_str: String = row.get(5)?;
            let last_mentioned_str: String = row.get(6)?;

            let entity_type = match entity_type_str.as_str() {
                "person" => super::EntityType::Person,
                "place" => super::EntityType::Place,
                "project" => super::EntityType::Project,
                "company" => super::EntityType::Company,
                "concept" => super::EntityType::Concept,
                _ => super::EntityType::Other,
            };

            let attributes = serde_json::from_str(&attributes_json)
                .unwrap_or_else(|_| serde_json::Value::Object(serde_json::Map::new()));

            results.push(Entity {
                id: Uuid::parse_str(&id_str)?,
                user_id,
                entity_type,
                name,
                attributes,
                mention_count: mention_count as u32,
                first_mentioned: DateTime::parse_from_rfc3339(&first_mentioned_str)?
                    .with_timezone(&Utc),
                last_mentioned: DateTime::parse_from_rfc3339(&last_mentioned_str)?
                    .with_timezone(&Utc),
            });
        }

        Ok(results)
    }

    /// Get session text by ID (for fact extraction)
    pub async fn get_session_text(&self, session_id: Uuid) -> Result<String> {
        let conn = self.db.connect()?;

        let mut rows = conn
            .query(
                "SELECT summary FROM memory_sessions WHERE id = ?",
                libsql::params![session_id.to_string()],
            )
            .await
            .context("Failed to query session text")?;

        if let Some(row) = rows.next().await? {
            let text: String = row.get(0)?;
            Ok(text)
        } else {
            anyhow::bail!("Session not found: {}", session_id)
        }
    }

    /// Clean up old sessions based on retention policy
    pub async fn cleanup_old_sessions(
        &self,
        user_id: Uuid,
        retention_days: u32,
    ) -> Result<u64> {
        let conn = self.db.connect()?;
        let cutoff_date = Utc::now() - chrono::Duration::days(retention_days as i64);

        let result = conn
            .execute(
                "DELETE FROM memory_sessions
                 WHERE user_id = ? AND created_at < ?",
                libsql::params![user_id.to_string(), cutoff_date.to_rfc3339()],
            )
            .await
            .context("Failed to cleanup old sessions")?;

        tracing::info!(
            "Cleaned up {} old sessions for user {} (retention: {} days)",
            result,
            user_id,
            retention_days
        );

        Ok(result)
    }

    /// Store a fact from a Fact object (convenience wrapper)
    pub async fn store_fact_from_obj(
        &self,
        user_id: Uuid,
        fact: &super::Fact,
        embedding: &[f32],
        source_session: Option<Uuid>,
    ) -> Result<Uuid> {
        self.store_fact(
            user_id,
            &fact.fact_text,
            embedding,
            fact.confidence,
            fact.category.clone(),
            source_session,
        )
        .await
    }

    /// Get database file path for debugging
    pub fn db_path(&self) -> &PathBuf {
        &self.db_path
    }
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

    #[tokio::test]
    async fn test_cosine_similarity() {
        let a = vec![1.0, 0.0, 0.0];
        let b = vec![1.0, 0.0, 0.0];
        assert!((cosine_similarity(&a, &b) - 1.0).abs() < 0.001);

        let a = vec![1.0, 0.0, 0.0];
        let b = vec![0.0, 1.0, 0.0];
        assert!((cosine_similarity(&a, &b) - 0.0).abs() < 0.001);
    }

    #[tokio::test]
    async fn test_memory_storage_init() {
        let storage = MemoryStorage::new().await;
        assert!(storage.is_ok());
    }
}
