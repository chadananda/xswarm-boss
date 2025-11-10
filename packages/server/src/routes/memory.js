/**
 * Memory API Routes
 *
 * RESTful API endpoints for semantic memory system with:
 * - Tier-based feature gating
 * - Vector embedding integration
 * - GDPR-compliant data management
 */

import { requireAuth } from '../middleware/auth-middleware.js';
import { requireFeature, checkFeatureAccess } from '../lib/features.js';
import { MemoryAPI } from '../lib/memory.js';

/**
 * Register memory routes
 */
export function registerMemoryRoutes(app, db) {
  const memoryAPI = new MemoryAPI(db);

  // =============================================================================
  // CONVERSATION STORAGE
  // =============================================================================

  /**
   * Store a conversation in memory
   * POST /api/memory/store
   */
  app.post('/api/memory/store', requireAuth(db), async (req, res) => {
    try {
      const { text, embedding, metadata } = req.body;

      if (!text || !embedding) {
        return res.status(400).json({
          error: 'Missing required fields: text, embedding'
        });
      }

      // Check if user has semantic memory feature
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'semantic_memory');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Semantic memory requires Personal tier or higher',
          upgrade: {
            feature: 'semantic_memory',
            availableIn: ['personal', 'professional', 'enterprise']
          }
        });
      }

      const sessionId = await memoryAPI.storeConversation(
        req.user.id,
        text,
        embedding,
        metadata
      );

      res.json({
        success: true,
        sessionId,
        stored: true
      });
    } catch (error) {
      console.error('Error storing conversation:', error);
      res.status(500).json({ error: error.message });
    }
  });

  // =============================================================================
  // MEMORY RETRIEVAL
  // =============================================================================

  /**
   * Retrieve relevant memories for a query
   * POST /api/memory/retrieve
   */
  app.post('/api/memory/retrieve', requireAuth(db), async (req, res) => {
    try {
      const { embedding, limit = 10, minSimilarity = 0.7 } = req.body;

      if (!embedding) {
        return res.status(400).json({
          error: 'Missing required field: embedding'
        });
      }

      // Check feature access
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'semantic_memory');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Semantic memory requires Personal tier or higher'
        });
      }

      const context = await memoryAPI.retrieveContext(req.user.id, embedding, {
        limit,
        minSimilarity,
        includeEntities: true,
        includeFacts: true
      });

      res.json(context);
    } catch (error) {
      console.error('Error retrieving memories:', error);
      res.status(500).json({ error: error.message });
    }
  });

  /**
   * Get specific memory by ID
   * GET /api/memory/session/:sessionId
   */
  app.get('/api/memory/session/:sessionId', requireAuth(db), async (req, res) => {
    try {
      const { sessionId } = req.params;

      const result = await db.execute({
        sql: `SELECT id, user_id, summary, key_topics, session_start, created_at
              FROM memory_sessions
              WHERE id = ? AND user_id = ?`,
        args: [sessionId, req.user.id]
      });

      if (result.rows.length === 0) {
        return res.status(404).json({ error: 'Session not found' });
      }

      const session = result.rows[0];
      res.json({
        id: session.id,
        summary: session.summary,
        keyTopics: JSON.parse(session.key_topics),
        sessionStart: session.session_start,
        createdAt: session.created_at
      });
    } catch (error) {
      console.error('Error fetching session:', error);
      res.status(500).json({ error: error.message });
    }
  });

  // =============================================================================
  // FACT MANAGEMENT
  // =============================================================================

  /**
   * Store a fact
   * POST /api/memory/facts
   */
  app.post('/api/memory/facts', requireAuth(db), async (req, res) => {
    try {
      const { text, embedding, confidence, category, sourceSession } = req.body;

      if (!text || !embedding) {
        return res.status(400).json({
          error: 'Missing required fields: text, embedding'
        });
      }

      const hasFeature = await checkFeatureAccess(db, req.user.id, 'semantic_memory');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Fact storage requires Personal tier or higher'
        });
      }

      const factId = await memoryAPI.storeFact(req.user.id, text, embedding, {
        confidence,
        category,
        sourceSession
      });

      res.json({
        success: true,
        factId
      });
    } catch (error) {
      console.error('Error storing fact:', error);
      res.status(500).json({ error: error.message });
    }
  });

  /**
   * Get relevant facts
   * POST /api/memory/facts/search
   */
  app.post('/api/memory/facts/search', requireAuth(db), async (req, res) => {
    try {
      const { embedding, limit = 10 } = req.body;

      if (!embedding) {
        return res.status(400).json({
          error: 'Missing required field: embedding'
        });
      }

      const facts = await memoryAPI.getRelevantFacts(req.user.id, embedding, limit);

      res.json({ facts });
    } catch (error) {
      console.error('Error searching facts:', error);
      res.status(500).json({ error: error.message });
    }
  });

  // =============================================================================
  // ENTITY MANAGEMENT
  // =============================================================================

  /**
   * Get user entities
   * GET /api/memory/entities
   */
  app.get('/api/memory/entities', requireAuth(db), async (req, res) => {
    try {
      const { type, minMentions = 1 } = req.query;

      const entities = await memoryAPI.getEntities(req.user.id, {
        entityType: type,
        minMentions: parseInt(minMentions)
      });

      res.json({ entities });
    } catch (error) {
      console.error('Error fetching entities:', error);
      res.status(500).json({ error: error.message });
    }
  });

  /**
   * Store or update an entity
   * POST /api/memory/entities
   */
  app.post('/api/memory/entities', requireAuth(db), async (req, res) => {
    try {
      const { type, name, attributes = {} } = req.body;

      if (!type || !name) {
        return res.status(400).json({
          error: 'Missing required fields: type, name'
        });
      }

      const entityId = await memoryAPI.storeEntity(
        req.user.id,
        type,
        name,
        attributes
      );

      res.json({
        success: true,
        entityId
      });
    } catch (error) {
      console.error('Error storing entity:', error);
      res.status(500).json({ error: error.message });
    }
  });

  // =============================================================================
  // MEMORY STATISTICS
  // =============================================================================

  /**
   * Get memory statistics for user
   * GET /api/memory/stats
   */
  app.get('/api/memory/stats', requireAuth(db), async (req, res) => {
    try {
      const stats = await memoryAPI.getMemoryStats(req.user.id);
      res.json(stats);
    } catch (error) {
      console.error('Error fetching stats:', error);
      res.status(500).json({ error: error.message });
    }
  });

  // =============================================================================
  // MEMORY MANAGEMENT
  // =============================================================================

  /**
   * Clean up old memories based on tier retention policy
   * POST /api/memory/cleanup
   */
  app.post('/api/memory/cleanup', requireAuth(db), async (req, res) => {
    try {
      // Get user's subscription tier
      const userResult = await db.execute({
        sql: 'SELECT subscription_tier FROM users WHERE id = ?',
        args: [req.user.id]
      });

      if (userResult.rows.length === 0) {
        return res.status(404).json({ error: 'User not found' });
      }

      const tier = userResult.rows[0].subscription_tier;
      const retentionDays = memoryAPI.getRetentionDays(tier);

      const result = await memoryAPI.cleanupOldMemories(req.user.id, retentionDays);

      res.json({
        success: true,
        deleted: result.deleted,
        retentionDays
      });
    } catch (error) {
      console.error('Error cleaning up memories:', error);
      res.status(500).json({ error: error.message });
    }
  });

  /**
   * Delete a specific session (GDPR compliance)
   * DELETE /api/memory/session/:sessionId
   */
  app.delete('/api/memory/session/:sessionId', requireAuth(db), async (req, res) => {
    try {
      const { sessionId } = req.params;

      const result = await memoryAPI.deleteSession(req.user.id, sessionId);

      if (!result.deleted) {
        return res.status(404).json({ error: 'Session not found' });
      }

      res.json({
        success: true,
        deleted: true
      });
    } catch (error) {
      console.error('Error deleting session:', error);
      res.status(500).json({ error: error.message });
    }
  });

  /**
   * Delete all memories for user (GDPR compliance)
   * DELETE /api/memory/all
   */
  app.delete('/api/memory/all', requireAuth(db), async (req, res) => {
    try {
      // Require confirmation
      const { confirm } = req.body;

      if (confirm !== 'DELETE_ALL_MEMORIES') {
        return res.status(400).json({
          error: 'Please confirm deletion by sending: { "confirm": "DELETE_ALL_MEMORIES" }'
        });
      }

      await memoryAPI.deleteUserMemories(req.user.id);

      res.json({
        success: true,
        deleted: true,
        message: 'All memories have been permanently deleted'
      });
    } catch (error) {
      console.error('Error deleting user memories:', error);
      res.status(500).json({ error: error.message });
    }
  });
}

export default registerMemoryRoutes;
