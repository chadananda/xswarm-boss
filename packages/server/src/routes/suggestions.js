/**
 * Suggestions API Routes for Cloudflare Workers
 *
 * Provides endpoints for:
 * - Public suggestion submission
 * - Listing and filtering suggestions
 * - Voting on suggestions
 * - Admin management
 * - Analytics
 */

import { randomUUID } from 'crypto';
import { sendEmail } from '../lib/send-email.js';
import {
  getSuggestionConfirmationTemplate,
  getAdminSuggestionNotificationTemplate,
  getSuggestionStatusUpdateTemplate
} from '../lib/email-templates.js';

/**
 * Helper to get authenticated user from request
 */
function getAuthUser(request, env) {
  // Extract JWT token from Authorization header
  const authHeader = request.headers.get('Authorization');
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return null;
  }

  // In a real implementation, you would verify the JWT here
  // For now, returning null for unauthenticated requests
  return null;
}

/**
 * Helper to require authentication
 */
function requireAuth(request, env) {
  const user = getAuthUser(request, env);
  if (!user) {
    return new Response(JSON.stringify({ error: 'Authentication required' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    });
  }
  return user;
}

/**
 * Helper to require admin access
 */
function requireAdmin(request, env) {
  const user = requireAuth(request, env);
  if (user instanceof Response) return user;

  if (!user.is_admin) {
    return new Response(JSON.stringify({ error: 'Admin access required' }), {
      status: 403,
      headers: { 'Content-Type': 'application/json' }
    });
  }
  return user;
}

/**
 * POST /api/suggestions
 * Submit a new suggestion (public endpoint, optionally authenticated)
 */
export async function handleCreateSuggestion(request, env) {
  try {
    const body = await request.json();
    const { category, title, description, email } = body;

    // Validation
    if (!category || !title || !description) {
      return new Response(JSON.stringify({
        error: 'Missing required fields',
        required: ['category', 'title', 'description']
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Validate category
    const validCategories = ['feature_request', 'bug_report', 'improvement', 'general'];
    if (!validCategories.includes(category)) {
      return new Response(JSON.stringify({
        error: 'Invalid category',
        validCategories
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Validate lengths
    if (title.length < 1 || title.length > 100) {
      return new Response(JSON.stringify({
        error: 'Title must be between 1 and 100 characters'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    if (description.length < 10 || description.length > 2000) {
      return new Response(JSON.stringify({
        error: 'Description must be between 10 and 2000 characters'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const user = getAuthUser(request, env);

    // For anonymous submissions, require email
    if (!user && !email) {
      return new Response(JSON.stringify({
        error: 'Email is required for anonymous submissions'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Validate email format if provided
    if (email) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        return new Response(JSON.stringify({
          error: 'Invalid email format'
        }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    const suggestionId = randomUUID();
    const userId = user?.id || null;
    const suggestionEmail = email || user?.email || null;

    // Check for spam/duplicates (simple rate limiting)
    if (suggestionEmail) {
      const recentSubmissions = await env.DB.prepare(`
        SELECT COUNT(*) as count
        FROM suggestions
        WHERE email = ?
          AND created_at >= datetime('now', '-1 hour')
      `).bind(suggestionEmail).first();

      if (recentSubmissions?.count >= 3) {
        return new Response(JSON.stringify({
          error: 'Too many submissions. Please wait before submitting again.'
        }), {
          status: 429,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    // Check for duplicate titles
    const duplicateCheck = await env.DB.prepare(`
      SELECT id
      FROM suggestions
      WHERE LOWER(title) = LOWER(?)
        AND created_at >= datetime('now', '-7 days')
      LIMIT 1
    `).bind(title).first();

    if (duplicateCheck) {
      return new Response(JSON.stringify({
        error: 'A similar suggestion was recently submitted',
        existingId: duplicateCheck.id
      }), {
        status: 409,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Insert suggestion
    await env.DB.prepare(`
      INSERT INTO suggestions (
        id, user_id, email, category, title, description,
        priority, status, upvotes
      ) VALUES (?, ?, ?, ?, ?, ?, 'medium', 'new', 0)
    `).bind(suggestionId, userId, suggestionEmail, category, title, description).run();

    // Get the created suggestion
    const suggestion = await env.DB.prepare(`
      SELECT s.*, u.name as user_name
      FROM suggestions s
      LEFT JOIN users u ON s.user_id = u.id
      WHERE s.id = ?
    `).bind(suggestionId).first();

    // Send confirmation email to submitter
    try {
      const userName = user?.name || 'Anonymous';
      const confirmationEmail = getSuggestionConfirmationTemplate(suggestionId, title, userName);

      await sendEmail(env, {
        to: suggestionEmail,
        subject: confirmationEmail.subject,
        text: confirmationEmail.text,
        html: confirmationEmail.html
      });
    } catch (emailError) {
      console.error('Failed to send confirmation email:', emailError);
    }

    // Send notification to admin
    try {
      const adminEmail = env.ADMIN_EMAIL;
      if (adminEmail) {
        const adminNotification = getAdminSuggestionNotificationTemplate(suggestion);

        await sendEmail(env, {
          to: adminEmail,
          subject: adminNotification.subject,
          text: adminNotification.text,
          html: adminNotification.html
        });
      }
    } catch (emailError) {
      console.error('Failed to send admin notification:', emailError);
    }

    return new Response(JSON.stringify({
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
    }), {
      status: 201,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error creating suggestion:', error);
    return new Response(JSON.stringify({ error: 'Failed to create suggestion' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * GET /api/suggestions
 * List suggestions with filtering and sorting
 */
export async function handleListSuggestions(request, env) {
  try {
    const url = new URL(request.url);
    const category = url.searchParams.get('category');
    const status = url.searchParams.get('status');
    const search = url.searchParams.get('search');
    const sort = url.searchParams.get('sort') || 'upvotes';
    const order = url.searchParams.get('order') || 'desc';
    const limit = parseInt(url.searchParams.get('limit') || '50');
    const offset = parseInt(url.searchParams.get('offset') || '0');

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
      // By default, exclude rejected suggestions
      query += ' AND s.status != ?';
      params.push('rejected');
    }

    // Search functionality
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
    params.push(limit, offset);

    const stmt = env.DB.prepare(query);
    for (const param of params) {
      stmt.bind(param);
    }

    const results = await stmt.all();
    const suggestions = results.results || [];

    // Get total count
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
      countQuery += ` AND id IN (SELECT id FROM suggestions_fts WHERE suggestions_fts MATCH ?)`;
      countParams.push(search);
    }

    const countStmt = env.DB.prepare(countQuery);
    for (const param of countParams) {
      countStmt.bind(param);
    }

    const countResult = await countStmt.first();
    const total = countResult?.total || 0;

    return new Response(JSON.stringify({
      suggestions,
      pagination: {
        total,
        limit,
        offset,
        hasMore: offset + suggestions.length < total
      }
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error listing suggestions:', error);
    return new Response(JSON.stringify({ error: 'Failed to list suggestions' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * GET /api/suggestions/:id
 * Get a specific suggestion by ID
 */
export async function handleGetSuggestion(request, env, suggestionId) {
  try {
    const suggestion = await env.DB.prepare(`
      SELECT
        s.*,
        CASE
          WHEN s.user_id IS NOT NULL THEN u.name
          ELSE 'Anonymous'
        END as submitted_by
      FROM suggestions s
      LEFT JOIN users u ON s.user_id = u.id
      WHERE s.id = ?
    `).bind(suggestionId).first();

    if (!suggestion) {
      return new Response(JSON.stringify({ error: 'Suggestion not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const user = getAuthUser(request, env);

    // Check if user has voted
    if (user) {
      const vote = await env.DB.prepare(`
        SELECT id
        FROM suggestion_votes
        WHERE suggestion_id = ? AND user_id = ?
      `).bind(suggestionId, user.id).first();

      suggestion.user_voted = !!vote;
    }

    // Hide email unless admin or owner
    if (!user?.is_admin && user?.id !== suggestion.user_id) {
      delete suggestion.email;
    }

    // Hide admin notes unless admin
    if (!user?.is_admin) {
      delete suggestion.admin_notes;
      delete suggestion.implementation_effort;
    }

    return new Response(JSON.stringify({ suggestion }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error fetching suggestion:', error);
    return new Response(JSON.stringify({ error: 'Failed to fetch suggestion' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * POST /api/suggestions/:id/vote
 * Upvote a suggestion (requires authentication)
 */
export async function handleVoteSuggestion(request, env, suggestionId) {
  const user = requireAuth(request, env);
  if (user instanceof Response) return user;

  try {
    // Check if suggestion exists
    const suggestion = await env.DB.prepare('SELECT id FROM suggestions WHERE id = ?').bind(suggestionId).first();
    if (!suggestion) {
      return new Response(JSON.stringify({ error: 'Suggestion not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Check if user already voted
    const existingVote = await env.DB.prepare(`
      SELECT id FROM suggestion_votes
      WHERE suggestion_id = ? AND user_id = ?
    `).bind(suggestionId, user.id).first();

    if (existingVote) {
      return new Response(JSON.stringify({ error: 'Already voted on this suggestion' }), {
        status: 409,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Add vote
    const voteId = randomUUID();
    await env.DB.prepare(`
      INSERT INTO suggestion_votes (id, suggestion_id, user_id)
      VALUES (?, ?, ?)
    `).bind(voteId, suggestionId, user.id).run();

    // Get updated suggestion
    const updated = await env.DB.prepare('SELECT upvotes FROM suggestions WHERE id = ?').bind(suggestionId).first();

    return new Response(JSON.stringify({
      success: true,
      upvotes: updated.upvotes
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error voting on suggestion:', error);
    return new Response(JSON.stringify({ error: 'Failed to vote on suggestion' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * DELETE /api/suggestions/:id/vote
 * Remove vote from a suggestion (requires authentication)
 */
export async function handleUnvoteSuggestion(request, env, suggestionId) {
  const user = requireAuth(request, env);
  if (user instanceof Response) return user;

  try {
    // Delete vote
    await env.DB.prepare(`
      DELETE FROM suggestion_votes
      WHERE suggestion_id = ? AND user_id = ?
    `).bind(suggestionId, user.id).run();

    // Get updated suggestion
    const updated = await env.DB.prepare('SELECT upvotes FROM suggestions WHERE id = ?').bind(suggestionId).first();

    return new Response(JSON.stringify({
      success: true,
      upvotes: updated?.upvotes || 0
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error removing vote:', error);
    return new Response(JSON.stringify({ error: 'Failed to remove vote' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * PUT /api/suggestions/:id
 * Update a suggestion (admin only)
 */
export async function handleUpdateSuggestion(request, env, suggestionId) {
  const user = requireAdmin(request, env);
  if (user instanceof Response) return user;

  try {
    const body = await request.json();
    const { status, priority, admin_notes, implementation_effort } = body;

    // Get current suggestion
    const current = await env.DB.prepare(`
      SELECT s.*, u.email as user_email, u.name as user_name
      FROM suggestions s
      LEFT JOIN users u ON s.user_id = u.id
      WHERE s.id = ?
    `).bind(suggestionId).first();

    if (!current) {
      return new Response(JSON.stringify({ error: 'Suggestion not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Build update query
    const updates = [];
    const params = [];

    if (status) {
      const validStatuses = ['new', 'reviewed', 'in_progress', 'completed', 'rejected'];
      if (!validStatuses.includes(status)) {
        return new Response(JSON.stringify({ error: 'Invalid status' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      updates.push('status = ?');
      params.push(status);
    }

    if (priority) {
      const validPriorities = ['low', 'medium', 'high', 'critical'];
      if (!validPriorities.includes(priority)) {
        return new Response(JSON.stringify({ error: 'Invalid priority' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
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
        return new Response(JSON.stringify({ error: 'Implementation effort must be between 1 and 5' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      updates.push('implementation_effort = ?');
      params.push(implementation_effort);
    }

    if (updates.length === 0) {
      return new Response(JSON.stringify({ error: 'No valid fields to update' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Update suggestion
    params.push(suggestionId);
    await env.DB.prepare(`
      UPDATE suggestions
      SET ${updates.join(', ')}
      WHERE id = ?
    `).bind(...params).run();

    // Get updated suggestion
    const updated = await env.DB.prepare(`
      SELECT s.*, u.name as user_name
      FROM suggestions s
      LEFT JOIN users u ON s.user_id = u.id
      WHERE s.id = ?
    `).bind(suggestionId).first();

    // Send status update email if status changed
    if (status && status !== current.status) {
      try {
        const notificationEmail = current.user_email || current.email;
        if (notificationEmail) {
          const userName = current.user_name || 'there';
          const statusEmail = getSuggestionStatusUpdateTemplate(updated, status, userName);

          await sendEmail(env, {
            to: notificationEmail,
            subject: statusEmail.subject,
            text: statusEmail.text,
            html: statusEmail.html
          });
        }
      } catch (emailError) {
        console.error('Failed to send status update email:', emailError);
      }
    }

    return new Response(JSON.stringify({
      success: true,
      suggestion: updated
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error updating suggestion:', error);
    return new Response(JSON.stringify({ error: 'Failed to update suggestion' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * DELETE /api/suggestions/:id
 * Delete a suggestion (admin only)
 */
export async function handleDeleteSuggestion(request, env, suggestionId) {
  const user = requireAdmin(request, env);
  if (user instanceof Response) return user;

  try {
    await env.DB.prepare('DELETE FROM suggestions WHERE id = ?').bind(suggestionId).run();

    return new Response(JSON.stringify({ success: true }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error deleting suggestion:', error);
    return new Response(JSON.stringify({ error: 'Failed to delete suggestion' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * GET /api/suggestions/stats
 * Get suggestion analytics (admin only)
 */
export async function handleGetSuggestionStats(request, env) {
  const user = requireAdmin(request, env);
  if (user instanceof Response) return user;

  try {
    // Get overall stats
    const stats = await env.DB.prepare('SELECT * FROM suggestion_stats').first();

    // Get category breakdown
    const categories = await env.DB.prepare('SELECT * FROM suggestions_by_category').all();

    // Get suggestions needing review
    const needsReview = await env.DB.prepare('SELECT * FROM suggestions_need_review').all();

    // Get recent activity (last 7 days)
    const recentActivity = await env.DB.prepare(`
      SELECT
        DATE(created_at) as date,
        COUNT(*) as count
      FROM suggestions
      WHERE created_at >= datetime('now', '-7 days')
      GROUP BY DATE(created_at)
      ORDER BY date DESC
    `).all();

    return new Response(JSON.stringify({
      stats,
      categories: categories.results || [],
      needsReview: needsReview.results || [],
      recentActivity: recentActivity.results || []
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error fetching suggestion stats:', error);
    return new Response(JSON.stringify({ error: 'Failed to fetch suggestion stats' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
