/**
 * Suggestions API Routes
 *
 * Provides endpoints for:
 * - Public suggestion submission
 * - Listing and filtering suggestions
 * - Voting on suggestions
 * - Admin management
 * - Analytics
 */

import { Router } from 'express';
import { randomUUID } from 'crypto';
import { getDatabase } from '../../lib/database.js';
import { optionalAuth, requireAuth, requireAdmin } from '../../lib/auth-middleware.js';
import { sendEmail } from '../../lib/send-email.js';
import {
  getSuggestionConfirmationTemplate,
  getAdminSuggestionNotificationTemplate,
  getSuggestionStatusUpdateTemplate
} from '../../lib/email-templates.js';

const router = Router();

/**
 * POST /suggestions
 * Submit a new suggestion (public endpoint, optionally authenticated)
 */
router.post('/', optionalAuth, async (req, res) => {
  try {
    const { category, title, description, email } = req.body;

    // Validation
    if (!category || !title || !description) {
      return res.status(400).json({
        error: 'Missing required fields',
        required: ['category', 'title', 'description']
      });
    }

    // Validate category
    const validCategories = ['feature_request', 'bug_report', 'improvement', 'general'];
    if (!validCategories.includes(category)) {
      return res.status(400).json({
        error: 'Invalid category',
        validCategories
      });
    }

    // Validate title length
    if (title.length < 1 || title.length > 100) {
      return res.status(400).json({
        error: 'Title must be between 1 and 100 characters'
      });
    }

    // Validate description length
    if (description.length < 10 || description.length > 2000) {
      return res.status(400).json({
        error: 'Description must be between 10 and 2000 characters'
      });
    }

    // For anonymous submissions, require email
    if (!req.user && !email) {
      return res.status(400).json({
        error: 'Email is required for anonymous submissions'
      });
    }

    // Validate email format if provided
    if (email) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        return res.status(400).json({
          error: 'Invalid email format'
        });
      }
    }

    const db = getDatabase();
    const suggestionId = randomUUID();
    const userId = req.user?.id || null;
    const suggestionEmail = email || req.user?.email || null;

    // Check for spam/duplicates (simple rate limiting)
    if (suggestionEmail) {
      const recentSubmissions = db.prepare(`
        SELECT COUNT(*) as count
        FROM suggestions
        WHERE email = ?
          AND created_at >= datetime('now', '-1 hour')
      `).get(suggestionEmail);

      if (recentSubmissions.count >= 3) {
        return res.status(429).json({
          error: 'Too many submissions. Please wait before submitting again.'
        });
      }
    }

    // Check for duplicate titles
    const duplicateCheck = db.prepare(`
      SELECT id
      FROM suggestions
      WHERE LOWER(title) = LOWER(?)
        AND created_at >= datetime('now', '-7 days')
      LIMIT 1
    `).get(title);

    if (duplicateCheck) {
      return res.status(409).json({
        error: 'A similar suggestion was recently submitted',
        existingId: duplicateCheck.id
      });
    }

    // Insert suggestion
    db.prepare(`
      INSERT INTO suggestions (
        id, user_id, email, category, title, description,
        priority, status, upvotes
      ) VALUES (?, ?, ?, ?, ?, ?, 'medium', 'new', 0)
    `).run(suggestionId, userId, suggestionEmail, category, title, description);

    // Get the created suggestion
    const suggestion = db.prepare(`
      SELECT s.*, u.name as user_name
      FROM suggestions s
      LEFT JOIN users u ON s.user_id = u.id
      WHERE s.id = ?
    `).get(suggestionId);

    // Send confirmation email to submitter
    try {
      const userName = req.user?.name || 'Anonymous';
      const confirmationEmail = getSuggestionConfirmationTemplate(suggestionId, title, userName);

      await sendEmail({
        to: suggestionEmail,
        subject: confirmationEmail.subject,
        text: confirmationEmail.text,
        html: confirmationEmail.html
      });
    } catch (emailError) {
      console.error('Failed to send confirmation email:', emailError);
      // Don't fail the request if email fails
    }

    // Send notification to admin
    try {
      const adminEmail = process.env.ADMIN_EMAIL;
      if (adminEmail) {
        const adminNotification = getAdminSuggestionNotificationTemplate(suggestion);

        await sendEmail({
          to: adminEmail,
          subject: adminNotification.subject,
          text: adminNotification.text,
          html: adminNotification.html
        });
      }
    } catch (emailError) {
      console.error('Failed to send admin notification:', emailError);
      // Don't fail the request if email fails
    }

    res.status(201).json({
      success: true,
      suggestion: {
        id: suggestion.id,
        category: suggestion.category,
        title: suggestion.title,
        description: suggestion.description,
        status: suggestion.status,
        upvotes: suggestion.upvotes,
        created_at: suggestion.created_at
      }
    });
  } catch (error) {
    console.error('Error creating suggestion:', error);
    res.status(500).json({ error: 'Failed to create suggestion' });
  }
});

/**
 * GET /suggestions
 * List suggestions with filtering and sorting
 */
router.get('/', optionalAuth, async (req, res) => {
  try {
    const {
      category,
      status,
      search,
      sort = 'upvotes',
      order = 'desc',
      limit = 50,
      offset = 0
    } = req.query;

    const db = getDatabase();
    let query = `
      SELECT
        s.id,
        s.category,
        s.title,
        s.description,
        s.status,
        s.upvotes,
        s.created_at,
        CASE
          WHEN s.user_id IS NOT NULL THEN u.name
          ELSE 'Anonymous'
        END as submitted_by
      FROM suggestions s
      LEFT JOIN users u ON s.user_id = u.id
      WHERE 1=1
    `;

    const params = [];

    // Filter by category
    if (category) {
      query += ' AND s.category = ?';
      params.push(category);
    }

    // Filter by status
    if (status) {
      query += ' AND s.status = ?';
      params.push(status);
    } else {
      // By default, exclude rejected suggestions for public view
      query += ' AND s.status != ?';
      params.push('rejected');
    }

    // Search functionality (using FTS if available)
    if (search) {
      query += ` AND s.id IN (
        SELECT id FROM suggestions_fts
        WHERE suggestions_fts MATCH ?
      )`;
      params.push(search);
    }

    // Sorting
    const validSorts = ['upvotes', 'created_at', 'status'];
    const sortColumn = validSorts.includes(sort) ? sort : 'upvotes';
    const sortOrder = order.toLowerCase() === 'asc' ? 'ASC' : 'DESC';

    query += ` ORDER BY s.${sortColumn} ${sortOrder}`;

    // Pagination
    query += ' LIMIT ? OFFSET ?';
    params.push(parseInt(limit), parseInt(offset));

    const suggestions = db.prepare(query).all(...params);

    // Get total count for pagination
    let countQuery = 'SELECT COUNT(*) as total FROM suggestions WHERE 1=1';
    const countParams = [];

    if (category) {
      countQuery += ' AND category = ?';
      countParams.push(category);
    }
    if (status) {
      countQuery += ' AND status = ?';
      countParams.push(status);
    } else {
      countQuery += ' AND status != ?';
      countParams.push('rejected');
    }
    if (search) {
      countQuery += ` AND id IN (
        SELECT id FROM suggestions_fts
        WHERE suggestions_fts MATCH ?
      )`;
      countParams.push(search);
    }

    const { total } = db.prepare(countQuery).get(...countParams);

    // If user is authenticated, include their vote status
    if (req.user) {
      const suggestionIds = suggestions.map(s => s.id);
      if (suggestionIds.length > 0) {
        const votes = db.prepare(`
          SELECT suggestion_id
          FROM suggestion_votes
          WHERE user_id = ?
            AND suggestion_id IN (${suggestionIds.map(() => '?').join(',')})
        `).all(req.user.id, ...suggestionIds);

        const votedIds = new Set(votes.map(v => v.suggestion_id));
        suggestions.forEach(s => {
          s.user_voted = votedIds.has(s.id);
        });
      }
    }

    res.json({
      suggestions,
      pagination: {
        total,
        limit: parseInt(limit),
        offset: parseInt(offset),
        hasMore: parseInt(offset) + suggestions.length < total
      }
    });
  } catch (error) {
    console.error('Error listing suggestions:', error);
    res.status(500).json({ error: 'Failed to list suggestions' });
  }
});

/**
 * GET /suggestions/:id
 * Get a specific suggestion by ID
 */
router.get('/:id', optionalAuth, async (req, res) => {
  try {
    const { id } = req.params;
    const db = getDatabase();

    const suggestion = db.prepare(`
      SELECT
        s.*,
        CASE
          WHEN s.user_id IS NOT NULL THEN u.name
          ELSE 'Anonymous'
        END as submitted_by
      FROM suggestions s
      LEFT JOIN users u ON s.user_id = u.id
      WHERE s.id = ?
    `).get(id);

    if (!suggestion) {
      return res.status(404).json({ error: 'Suggestion not found' });
    }

    // Check if user has voted
    if (req.user) {
      const vote = db.prepare(`
        SELECT id
        FROM suggestion_votes
        WHERE suggestion_id = ? AND user_id = ?
      `).get(id, req.user.id);

      suggestion.user_voted = !!vote;
    }

    // Hide email unless admin or owner
    if (!req.user?.is_admin && req.user?.id !== suggestion.user_id) {
      delete suggestion.email;
    }

    // Hide admin notes unless admin
    if (!req.user?.is_admin) {
      delete suggestion.admin_notes;
      delete suggestion.implementation_effort;
    }

    res.json({ suggestion });
  } catch (error) {
    console.error('Error fetching suggestion:', error);
    res.status(500).json({ error: 'Failed to fetch suggestion' });
  }
});

/**
 * POST /suggestions/:id/vote
 * Upvote a suggestion (requires authentication)
 */
router.post('/:id/vote', requireAuth, async (req, res) => {
  try {
    const { id } = req.params;
    const db = getDatabase();

    // Check if suggestion exists
    const suggestion = db.prepare('SELECT id FROM suggestions WHERE id = ?').get(id);
    if (!suggestion) {
      return res.status(404).json({ error: 'Suggestion not found' });
    }

    // Check if user already voted
    const existingVote = db.prepare(`
      SELECT id FROM suggestion_votes
      WHERE suggestion_id = ? AND user_id = ?
    `).get(id, req.user.id);

    if (existingVote) {
      return res.status(409).json({ error: 'Already voted on this suggestion' });
    }

    // Add vote
    const voteId = randomUUID();
    db.prepare(`
      INSERT INTO suggestion_votes (id, suggestion_id, user_id)
      VALUES (?, ?, ?)
    `).run(voteId, id, req.user.id);

    // Get updated suggestion
    const updated = db.prepare('SELECT upvotes FROM suggestions WHERE id = ?').get(id);

    res.json({
      success: true,
      upvotes: updated.upvotes
    });
  } catch (error) {
    console.error('Error voting on suggestion:', error);
    res.status(500).json({ error: 'Failed to vote on suggestion' });
  }
});

/**
 * DELETE /suggestions/:id/vote
 * Remove vote from a suggestion (requires authentication)
 */
router.delete('/:id/vote', requireAuth, async (req, res) => {
  try {
    const { id } = req.params;
    const db = getDatabase();

    // Delete vote
    const result = db.prepare(`
      DELETE FROM suggestion_votes
      WHERE suggestion_id = ? AND user_id = ?
    `).run(id, req.user.id);

    if (result.changes === 0) {
      return res.status(404).json({ error: 'Vote not found' });
    }

    // Get updated suggestion
    const updated = db.prepare('SELECT upvotes FROM suggestions WHERE id = ?').get(id);

    res.json({
      success: true,
      upvotes: updated?.upvotes || 0
    });
  } catch (error) {
    console.error('Error removing vote:', error);
    res.status(500).json({ error: 'Failed to remove vote' });
  }
});

/**
 * PUT /suggestions/:id
 * Update a suggestion (admin only)
 */
router.put('/:id', requireAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const {
      status,
      priority,
      admin_notes,
      implementation_effort
    } = req.body;

    const db = getDatabase();

    // Get current suggestion
    const current = db.prepare(`
      SELECT s.*, u.email as user_email, u.name as user_name
      FROM suggestions s
      LEFT JOIN users u ON s.user_id = u.id
      WHERE s.id = ?
    `).get(id);

    if (!current) {
      return res.status(404).json({ error: 'Suggestion not found' });
    }

    // Build update query
    const updates = [];
    const params = [];

    if (status) {
      const validStatuses = ['new', 'reviewed', 'in_progress', 'completed', 'rejected'];
      if (!validStatuses.includes(status)) {
        return res.status(400).json({ error: 'Invalid status' });
      }
      updates.push('status = ?');
      params.push(status);
    }

    if (priority) {
      const validPriorities = ['low', 'medium', 'high', 'critical'];
      if (!validPriorities.includes(priority)) {
        return res.status(400).json({ error: 'Invalid priority' });
      }
      updates.push('priority = ?');
      params.push(priority);
    }

    if (admin_notes !== undefined) {
      updates.push('admin_notes = ?');
      params.push(admin_notes);
    }

    if (implementation_effort !== undefined) {
      if (implementation_effort < 1 || implementation_effort > 5) {
        return res.status(400).json({ error: 'Implementation effort must be between 1 and 5' });
      }
      updates.push('implementation_effort = ?');
      params.push(implementation_effort);
    }

    if (updates.length === 0) {
      return res.status(400).json({ error: 'No valid fields to update' });
    }

    // Update suggestion
    params.push(id);
    db.prepare(`
      UPDATE suggestions
      SET ${updates.join(', ')}
      WHERE id = ?
    `).run(...params);

    // Get updated suggestion
    const updated = db.prepare(`
      SELECT s.*, u.name as user_name
      FROM suggestions s
      LEFT JOIN users u ON s.user_id = u.id
      WHERE s.id = ?
    `).get(id);

    // Send status update email if status changed
    if (status && status !== current.status) {
      try {
        const notificationEmail = current.user_email || current.email;
        if (notificationEmail) {
          const userName = current.user_name || 'there';
          const statusEmail = getSuggestionStatusUpdateTemplate(updated, status, userName);

          await sendEmail({
            to: notificationEmail,
            subject: statusEmail.subject,
            text: statusEmail.text,
            html: statusEmail.html
          });
        }
      } catch (emailError) {
        console.error('Failed to send status update email:', emailError);
        // Don't fail the request if email fails
      }
    }

    res.json({
      success: true,
      suggestion: updated
    });
  } catch (error) {
    console.error('Error updating suggestion:', error);
    res.status(500).json({ error: 'Failed to update suggestion' });
  }
});

/**
 * DELETE /suggestions/:id
 * Delete a suggestion (admin only)
 */
router.delete('/:id', requireAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const db = getDatabase();

    const result = db.prepare('DELETE FROM suggestions WHERE id = ?').run(id);

    if (result.changes === 0) {
      return res.status(404).json({ error: 'Suggestion not found' });
    }

    res.json({ success: true });
  } catch (error) {
    console.error('Error deleting suggestion:', error);
    res.status(500).json({ error: 'Failed to delete suggestion' });
  }
});

/**
 * GET /suggestions/stats
 * Get suggestion analytics (admin only)
 */
router.get('/admin/stats', requireAdmin, async (req, res) => {
  try {
    const db = getDatabase();

    // Get overall stats
    const stats = db.prepare('SELECT * FROM suggestion_stats').get();

    // Get category breakdown
    const categories = db.prepare('SELECT * FROM suggestions_by_category').all();

    // Get suggestions needing review
    const needsReview = db.prepare('SELECT * FROM suggestions_need_review').all();

    // Get recent activity (last 7 days)
    const recentActivity = db.prepare(`
      SELECT
        DATE(created_at) as date,
        COUNT(*) as count
      FROM suggestions
      WHERE created_at >= datetime('now', '-7 days')
      GROUP BY DATE(created_at)
      ORDER BY date DESC
    `).all();

    res.json({
      stats,
      categories,
      needsReview,
      recentActivity
    });
  } catch (error) {
    console.error('Error fetching suggestion stats:', error);
    res.status(500).json({ error: 'Failed to fetch suggestion stats' });
  }
});

export default router;
