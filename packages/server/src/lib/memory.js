/**
 * Semantic Memory System API
 *
 * Provides memory storage, retrieval, and management with:
 * - Vector embeddings for semantic search
 * - Tier-based retention policies
 * - Fact extraction and entity recognition
 * - GDPR-compliant data deletion
 */

import { createClient } from '@libsql/client';

/**
 * Memory API class for managing user memories
 */
export class MemoryAPI {
  constructor(db) {
    this.db = db;
  }

  /**
   * Store a conversation session with embedding
   */
  async storeConversation(userId, text, embedding, metadata = {}) {
    const sessionId = crypto.randomUUID();
    const keyTopics = metadata.topics || [];

    await this.db.execute({
      sql: `INSERT INTO memory_sessions
            (id, user_id, summary, key_topics, embedding)
            VALUES (?, ?, ?, ?, ?)`,
      args: [
        sessionId,
        userId,
        text,
        JSON.stringify(keyTopics),
        JSON.stringify(embedding)
      ]
    });

    return sessionId;
  }

  /**
   * Retrieve relevant memories using semantic search
   */
  async retrieveContext(userId, queryEmbedding, options = {}) {
    const { limit = 10, minSimilarity = 0.7, includeEntities = true, includeFacts = true } = options;

    // Get all sessions for user
    const sessions = await this.db.execute({
      sql: `SELECT id, user_id, summary, key_topics, embedding, session_start, created_at
            FROM memory_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?`,
      args: [userId, limit * 3] // Get more candidates for filtering
    });

    // Calculate similarity scores
    const scoredSessions = sessions.rows.map(row => {
      const embedding = JSON.parse(row.embedding);
      const similarity = this.cosineSimilarity(queryEmbedding, embedding);

      return {
        id: row.id,
        userId: row.user_id,
        content: row.summary,
        keyTopics: JSON.parse(row.key_topics),
        relevanceScore: similarity,
        createdAt: row.created_at,
        type: 'session'
      };
    });

    // Filter and sort by similarity
    const relevantSessions = scoredSessions
      .filter(s => s.relevanceScore >= minSimilarity)
      .sort((a, b) => b.relevanceScore - a.relevanceScore)
      .slice(0, limit);

    // Build context object
    const context = {
      memories: relevantSessions,
      entities: [],
      facts: []
    };

    // Optionally include entities
    if (includeEntities) {
      context.entities = await this.getEntities(userId);
    }

    // Optionally include relevant facts
    if (includeFacts) {
      context.facts = await this.getRelevantFacts(userId, queryEmbedding, limit);
    }

    return context;
  }

  /**
   * Store a fact with its embedding
   */
  async storeFact(userId, factText, embedding, options = {}) {
    const { confidence = 0.8, category = null, sourceSession = null } = options;

    const factId = crypto.randomUUID();

    await this.db.execute({
      sql: `INSERT INTO memory_facts
            (id, user_id, fact_text, confidence, category, embedding, source_session)
            VALUES (?, ?, ?, ?, ?, ?, ?)`,
      args: [
        factId,
        userId,
        factText,
        confidence,
        category,
        JSON.stringify(embedding),
        sourceSession
      ]
    });

    return factId;
  }

  /**
   * Get relevant facts using semantic search
   */
  async getRelevantFacts(userId, queryEmbedding, limit = 10) {
    const facts = await this.db.execute({
      sql: `SELECT id, fact_text, category, confidence, embedding, access_count, created_at
            FROM memory_facts
            WHERE user_id = ?
            ORDER BY confidence DESC, access_count DESC
            LIMIT ?`,
      args: [userId, limit * 2]
    });

    // Calculate similarity and sort
    const scoredFacts = facts.rows.map(row => {
      const embedding = JSON.parse(row.embedding);
      const similarity = this.cosineSimilarity(queryEmbedding, embedding);

      return {
        id: row.id,
        text: row.fact_text,
        category: row.category,
        confidence: row.confidence,
        relevanceScore: similarity,
        accessCount: row.access_count,
        createdAt: row.created_at
      };
    });

    return scoredFacts
      .sort((a, b) => b.relevanceScore - a.relevanceScore)
      .slice(0, limit);
  }

  /**
   * Store or update an entity
   */
  async storeEntity(userId, entityType, name, attributes = {}) {
    // Check if entity exists
    const existing = await this.db.execute({
      sql: `SELECT id, mention_count FROM memory_entities
            WHERE user_id = ? AND entity_type = ? AND name = ?`,
      args: [userId, entityType, name]
    });

    if (existing.rows.length > 0) {
      // Update existing entity
      const entityId = existing.rows[0].id;
      await this.db.execute({
        sql: `UPDATE memory_entities
              SET mention_count = mention_count + 1,
                  last_mentioned = datetime('now'),
                  attributes = ?
              WHERE id = ?`,
        args: [JSON.stringify(attributes), entityId]
      });
      return entityId;
    } else {
      // Create new entity
      const entityId = crypto.randomUUID();
      await this.db.execute({
        sql: `INSERT INTO memory_entities
              (id, user_id, entity_type, name, attributes)
              VALUES (?, ?, ?, ?, ?)`,
        args: [entityId, userId, entityType, name, JSON.stringify(attributes)]
      });
      return entityId;
    }
  }

  /**
   * Get all entities for a user
   */
  async getEntities(userId, options = {}) {
    const { entityType = null, minMentions = 1 } = options;

    let sql = `SELECT id, entity_type, name, attributes, mention_count,
                      first_mentioned, last_mentioned
               FROM memory_entities
               WHERE user_id = ? AND mention_count >= ?`;
    const args = [userId, minMentions];

    if (entityType) {
      sql += ' AND entity_type = ?';
      args.push(entityType);
    }

    sql += ' ORDER BY mention_count DESC';

    const result = await this.db.execute({ sql, args });

    return result.rows.map(row => ({
      id: row.id,
      type: row.entity_type,
      name: row.name,
      attributes: JSON.parse(row.attributes),
      mentionCount: row.mention_count,
      firstMentioned: row.first_mentioned,
      lastMentioned: row.last_mentioned
    }));
  }

  /**
   * Get memory statistics for a user
   */
  async getMemoryStats(userId) {
    const metadata = await this.db.execute({
      sql: `SELECT total_sessions, total_facts, total_entities,
                   retention_days, last_cleanup
            FROM memory_metadata
            WHERE user_id = ?`,
      args: [userId]
    });

    if (metadata.rows.length === 0) {
      return {
        totalSessions: 0,
        totalFacts: 0,
        totalEntities: 0,
        retentionDays: null,
        lastCleanup: null
      };
    }

    const row = metadata.rows[0];
    return {
      totalSessions: row.total_sessions,
      totalFacts: row.total_facts,
      totalEntities: row.total_entities,
      retentionDays: row.retention_days,
      lastCleanup: row.last_cleanup
    };
  }

  /**
   * Clean up old memories based on retention policy
   */
  async cleanupOldMemories(userId, retentionDays) {
    if (!retentionDays) {
      return { deleted: 0 }; // Permanent storage, no cleanup
    }

    const result = await this.db.execute({
      sql: `DELETE FROM memory_sessions
            WHERE user_id = ?
            AND datetime(created_at) < datetime('now', '-${retentionDays} days')`,
      args: [userId]
    });

    // Update last cleanup time
    await this.db.execute({
      sql: `INSERT INTO memory_metadata (user_id, last_cleanup, retention_days)
            VALUES (?, datetime('now'), ?)
            ON CONFLICT(user_id) DO UPDATE SET
              last_cleanup = datetime('now'),
              retention_days = ?`,
      args: [userId, retentionDays, retentionDays]
    });

    return { deleted: result.rowsAffected || 0 };
  }

  /**
   * Delete all memories for a user (GDPR compliance)
   */
  async deleteUserMemories(userId) {
    // Delete sessions (cascades to facts via foreign key)
    await this.db.execute({
      sql: 'DELETE FROM memory_sessions WHERE user_id = ?',
      args: [userId]
    });

    // Delete entities
    await this.db.execute({
      sql: 'DELETE FROM memory_entities WHERE user_id = ?',
      args: [userId]
    });

    // Delete metadata
    await this.db.execute({
      sql: 'DELETE FROM memory_metadata WHERE user_id = ?',
      args: [userId]
    });

    return { deleted: true };
  }

  /**
   * Delete a specific session
   */
  async deleteSession(userId, sessionId) {
    const result = await this.db.execute({
      sql: 'DELETE FROM memory_sessions WHERE id = ? AND user_id = ?',
      args: [sessionId, userId]
    });

    return { deleted: result.rowsAffected > 0 };
  }

  /**
   * Calculate cosine similarity between two vectors
   */
  cosineSimilarity(a, b) {
    if (a.length !== b.length) return 0;

    const dotProduct = a.reduce((sum, val, i) => sum + val * b[i], 0);
    const magnitudeA = Math.sqrt(a.reduce((sum, val) => sum + val * val, 0));
    const magnitudeB = Math.sqrt(b.reduce((sum, val) => sum + val * val, 0));

    if (magnitudeA === 0 || magnitudeB === 0) return 0;

    return dotProduct / (magnitudeA * magnitudeB);
  }

  /**
   * Get retention days based on user tier
   */
  getRetentionDays(tier) {
    const retentionMap = {
      free: 30,
      personal: 365,
      professional: 730, // 2 years
      enterprise: null // permanent
    };
    return retentionMap[tier] || 30;
  }
}

/**
 * Create a memory API instance
 */
export function createMemoryAPI(dbUrl, authToken) {
  const db = createClient({
    url: dbUrl,
    authToken: authToken
  });

  return new MemoryAPI(db);
}

export default MemoryAPI;
