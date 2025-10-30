/**
 * Suggestions Admin Utilities
 *
 * Helper functions for managing suggestions:
 * - Bulk operations
 * - Duplicate detection
 * - Analytics
 * - Weekly digest generation
 */

import { getDatabase } from './database.js';
import { sendEmail } from './send-email.js';
import { getWeeklySuggestionDigestTemplate } from './email-templates.js';

/**
 * Detect potential duplicate suggestions
 *
 * @param {string} title - Suggestion title to check
 * @param {string} description - Suggestion description
 * @returns {Array} Array of potential duplicates
 */
export function findPotentialDuplicates(title, description) {
  const db = getDatabase();

  // Search using FTS for similar titles and descriptions
  const searchQuery = title.split(' ').slice(0, 5).join(' OR ');

  const duplicates = db.prepare(`
    SELECT
      s.id,
      s.title,
      s.description,
      s.status,
      s.upvotes,
      s.created_at
    FROM suggestions s
    WHERE s.id IN (
      SELECT id FROM suggestions_fts
      WHERE suggestions_fts MATCH ?
    )
    AND s.status != 'rejected'
    ORDER BY s.upvotes DESC
    LIMIT 10
  `).all(searchQuery);

  return duplicates;
}

/**
 * Bulk update suggestion status
 *
 * @param {Array} suggestionIds - Array of suggestion IDs
 * @param {string} newStatus - New status to set
 * @param {string} adminNotes - Optional admin notes
 * @returns {number} Number of updated suggestions
 */
export function bulkUpdateStatus(suggestionIds, newStatus, adminNotes = null) {
  if (!suggestionIds || suggestionIds.length === 0) {
    return 0;
  }

  const validStatuses = ['new', 'reviewed', 'in_progress', 'completed', 'rejected'];
  if (!validStatuses.includes(newStatus)) {
    throw new Error('Invalid status');
  }

  const db = getDatabase();
  const placeholders = suggestionIds.map(() => '?').join(',');

  const query = adminNotes
    ? `UPDATE suggestions SET status = ?, admin_notes = ? WHERE id IN (${placeholders})`
    : `UPDATE suggestions SET status = ? WHERE id IN (${placeholders})`;

  const params = adminNotes
    ? [newStatus, adminNotes, ...suggestionIds]
    : [newStatus, ...suggestionIds];

  const result = db.prepare(query).run(...params);

  return result.changes;
}

/**
 * Bulk update suggestion priority
 *
 * @param {Array} suggestionIds - Array of suggestion IDs
 * @param {string} newPriority - New priority to set
 * @returns {number} Number of updated suggestions
 */
export function bulkUpdatePriority(suggestionIds, newPriority) {
  if (!suggestionIds || suggestionIds.length === 0) {
    return 0;
  }

  const validPriorities = ['low', 'medium', 'high', 'critical'];
  if (!validPriorities.includes(newPriority)) {
    throw new Error('Invalid priority');
  }

  const db = getDatabase();
  const placeholders = suggestionIds.map(() => '?').join(',');

  const result = db.prepare(`
    UPDATE suggestions
    SET priority = ?
    WHERE id IN (${placeholders})
  `).run(newPriority, ...suggestionIds);

  return result.changes;
}

/**
 * Get suggestions by status with full details
 *
 * @param {string} status - Status to filter by
 * @param {number} limit - Maximum number of results
 * @returns {Array} Array of suggestions
 */
export function getSuggestionsByStatus(status, limit = 100) {
  const db = getDatabase();

  const suggestions = db.prepare(`
    SELECT
      s.*,
      u.name as user_name,
      u.email as user_email,
      COUNT(DISTINCT sv.id) as vote_count
    FROM suggestions s
    LEFT JOIN users u ON s.user_id = u.id
    LEFT JOIN suggestion_votes sv ON s.id = sv.suggestion_id
    WHERE s.status = ?
    GROUP BY s.id
    ORDER BY s.upvotes DESC, s.created_at DESC
    LIMIT ?
  `).all(status, limit);

  return suggestions;
}

/**
 * Get top voted suggestions
 *
 * @param {number} limit - Number of suggestions to return
 * @param {string} status - Optional status filter
 * @returns {Array} Top suggestions
 */
export function getTopSuggestions(limit = 10, status = null) {
  const db = getDatabase();

  const query = status
    ? `SELECT * FROM suggestions WHERE status = ? ORDER BY upvotes DESC LIMIT ?`
    : `SELECT * FROM suggestions ORDER BY upvotes DESC LIMIT ?`;

  const params = status ? [status, limit] : [limit];

  return db.prepare(query).all(...params);
}

/**
 * Get suggestions needing attention
 * (high votes but not reviewed, or old and unreviewed)
 *
 * @returns {Array} Suggestions needing review
 */
export function getSuggestionsNeedingAttention() {
  const db = getDatabase();

  return db.prepare('SELECT * FROM suggestions_need_review').all();
}

/**
 * Generate weekly digest data
 *
 * @returns {Object} Weekly statistics and top suggestions
 */
export function generateWeeklyDigest() {
  const db = getDatabase();

  // Get stats for the last week
  const stats = db.prepare(`
    SELECT
      COUNT(*) as new_count,
      SUM(upvotes) as total_votes,
      COUNT(CASE WHEN status = 'new' AND (upvotes >= 5 OR datetime(created_at) <= datetime('now', '-7 days')) THEN 1 END) as needs_review
    FROM suggestions
    WHERE created_at >= datetime('now', '-7 days')
  `).get();

  // Get top suggestions from the last week
  const topSuggestions = db.prepare(`
    SELECT
      id,
      title,
      category,
      status,
      upvotes,
      created_at
    FROM suggestions
    WHERE created_at >= datetime('now', '-7 days')
    ORDER BY upvotes DESC
    LIMIT 10
  `).all();

  return {
    stats,
    topSuggestions
  };
}

/**
 * Send weekly digest email to admin
 *
 * @param {string} adminEmail - Admin email address
 * @returns {Promise<boolean>} Success status
 */
export async function sendWeeklyDigest(adminEmail) {
  try {
    const digest = generateWeeklyDigest();

    if (digest.stats.new_count === 0) {
      console.log('No new suggestions this week, skipping digest');
      return true;
    }

    const emailTemplate = getWeeklySuggestionDigestTemplate(
      digest.topSuggestions,
      digest.stats
    );

    await sendEmail({
      to: adminEmail,
      subject: emailTemplate.subject,
      text: emailTemplate.text,
      html: emailTemplate.html
    });

    return true;
  } catch (error) {
    console.error('Failed to send weekly digest:', error);
    return false;
  }
}

/**
 * Get suggestions by category with stats
 *
 * @param {string} category - Category to filter by
 * @returns {Object} Category data and suggestions
 */
export function getSuggestionsByCategory(category) {
  const db = getDatabase();

  const categoryStats = db.prepare(`
    SELECT * FROM suggestions_by_category
    WHERE category = ?
  `).get(category);

  const suggestions = db.prepare(`
    SELECT
      s.*,
      u.name as user_name
    FROM suggestions s
    LEFT JOIN users u ON s.user_id = u.id
    WHERE s.category = ?
    ORDER BY s.upvotes DESC, s.created_at DESC
    LIMIT 100
  `).all(category);

  return {
    stats: categoryStats,
    suggestions
  };
}

/**
 * Merge duplicate suggestions
 *
 * @param {string} keepId - ID of suggestion to keep
 * @param {Array} mergeIds - IDs of suggestions to merge
 * @returns {Object} Updated suggestion
 */
export function mergeDuplicateSuggestions(keepId, mergeIds) {
  if (!mergeIds || mergeIds.length === 0) {
    throw new Error('No suggestions to merge');
  }

  const db = getDatabase();

  // Get the suggestion we're keeping
  const keepSuggestion = db.prepare('SELECT * FROM suggestions WHERE id = ?').get(keepId);
  if (!keepSuggestion) {
    throw new Error('Keep suggestion not found');
  }

  // Transfer votes from duplicate suggestions
  const placeholders = mergeIds.map(() => '?').join(',');

  // Get all votes from duplicates that don't already exist on keep suggestion
  db.prepare(`
    INSERT OR IGNORE INTO suggestion_votes (id, suggestion_id, user_id, created_at)
    SELECT
      LOWER(HEX(RANDOMBLOB(16))),
      ?,
      user_id,
      created_at
    FROM suggestion_votes
    WHERE suggestion_id IN (${placeholders})
  `).run(keepId, ...mergeIds);

  // Mark duplicates as rejected with note
  db.prepare(`
    UPDATE suggestions
    SET status = 'rejected',
        admin_notes = 'Merged into suggestion ' || ?
    WHERE id IN (${placeholders})
  `).run(keepId, ...mergeIds);

  // Get updated suggestion with new vote count
  const updated = db.prepare(`
    SELECT
      s.*,
      COUNT(DISTINCT sv.id) as vote_count
    FROM suggestions s
    LEFT JOIN suggestion_votes sv ON s.id = sv.suggestion_id
    WHERE s.id = ?
    GROUP BY s.id
  `).get(keepId);

  return updated;
}

/**
 * Export suggestions to CSV format
 *
 * @param {Object} filters - Optional filters (status, category, etc.)
 * @returns {string} CSV data
 */
export function exportSuggestionsToCSV(filters = {}) {
  const db = getDatabase();

  let query = `
    SELECT
      s.id,
      s.category,
      s.title,
      s.description,
      s.status,
      s.priority,
      s.upvotes,
      s.implementation_effort,
      s.admin_notes,
      s.created_at,
      s.updated_at,
      CASE WHEN s.user_id IS NOT NULL THEN u.name ELSE 'Anonymous' END as submitted_by,
      CASE WHEN s.user_id IS NOT NULL THEN u.email ELSE s.email END as email
    FROM suggestions s
    LEFT JOIN users u ON s.user_id = u.id
    WHERE 1=1
  `;

  const params = [];

  if (filters.status) {
    query += ' AND s.status = ?';
    params.push(filters.status);
  }

  if (filters.category) {
    query += ' AND s.category = ?';
    params.push(filters.category);
  }

  if (filters.priority) {
    query += ' AND s.priority = ?';
    params.push(filters.priority);
  }

  query += ' ORDER BY s.created_at DESC';

  const suggestions = db.prepare(query).all(...params);

  // Generate CSV
  const headers = [
    'ID',
    'Category',
    'Title',
    'Description',
    'Status',
    'Priority',
    'Upvotes',
    'Implementation Effort',
    'Admin Notes',
    'Created At',
    'Updated At',
    'Submitted By',
    'Email'
  ];

  const rows = suggestions.map(s => [
    s.id,
    s.category,
    `"${s.title.replace(/"/g, '""')}"`,
    `"${s.description.replace(/"/g, '""')}"`,
    s.status,
    s.priority,
    s.upvotes,
    s.implementation_effort || '',
    s.admin_notes ? `"${s.admin_notes.replace(/"/g, '""')}"` : '',
    s.created_at,
    s.updated_at || '',
    s.submitted_by,
    s.email
  ]);

  const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');

  return csv;
}

/**
 * Get suggestion activity timeline
 *
 * @param {number} days - Number of days to look back
 * @returns {Array} Daily activity data
 */
export function getSuggestionActivity(days = 30) {
  const db = getDatabase();

  return db.prepare(`
    SELECT
      DATE(created_at) as date,
      category,
      COUNT(*) as count
    FROM suggestions
    WHERE created_at >= datetime('now', '-' || ? || ' days')
    GROUP BY DATE(created_at), category
    ORDER BY date DESC
  `).all(days);
}

/**
 * Calculate suggestion sentiment/priority score
 *
 * @param {string} suggestionId - Suggestion ID
 * @returns {Object} Scoring metrics
 */
export function calculateSuggestionScore(suggestionId) {
  const db = getDatabase();

  const suggestion = db.prepare(`
    SELECT
      s.*,
      COUNT(DISTINCT sv.id) as vote_count,
      CAST((julianday('now') - julianday(s.created_at)) AS INTEGER) as age_days
    FROM suggestions s
    LEFT JOIN suggestion_votes sv ON s.id = sv.suggestion_id
    WHERE s.id = ?
    GROUP BY s.id
  `).get(suggestionId);

  if (!suggestion) {
    return null;
  }

  // Calculate score based on:
  // - Upvotes (weight: 10)
  // - Age (newer = higher score)
  // - Priority level
  // - Implementation effort (lower = higher score)

  const priorityWeights = { low: 1, medium: 2, high: 3, critical: 4 };
  const priorityScore = priorityWeights[suggestion.priority] || 2;

  const effortScore = suggestion.implementation_effort
    ? (6 - suggestion.implementation_effort) / 5 // Invert: lower effort = higher score
    : 0.5;

  const ageScore = Math.max(0, (30 - suggestion.age_days) / 30); // Newer = higher score

  const totalScore =
    (suggestion.upvotes * 10) +
    (priorityScore * 5) +
    (effortScore * 10) +
    (ageScore * 5);

  return {
    suggestionId,
    totalScore: Math.round(totalScore * 10) / 10,
    upvotes: suggestion.upvotes,
    priority: suggestion.priority,
    priorityScore,
    implementationEffort: suggestion.implementation_effort,
    effortScore: Math.round(effortScore * 10) / 10,
    ageDays: suggestion.age_days,
    ageScore: Math.round(ageScore * 10) / 10
  };
}

/**
 * Get roadmap-ready suggestions
 * (high-priority, well-voted, low-effort suggestions)
 *
 * @param {number} limit - Maximum number of suggestions
 * @returns {Array} Prioritized suggestions
 */
export function getRoadmapSuggestions(limit = 20) {
  const db = getDatabase();

  const suggestions = db.prepare(`
    SELECT
      s.*,
      COUNT(DISTINCT sv.id) as vote_count
    FROM suggestions s
    LEFT JOIN suggestion_votes sv ON s.id = sv.suggestion_id
    WHERE s.status IN ('new', 'reviewed')
      AND s.upvotes >= 3
    GROUP BY s.id
    ORDER BY
      CASE s.priority
        WHEN 'critical' THEN 4
        WHEN 'high' THEN 3
        WHEN 'medium' THEN 2
        ELSE 1
      END DESC,
      s.upvotes DESC,
      CASE WHEN s.implementation_effort IS NULL THEN 999 ELSE s.implementation_effort END ASC
    LIMIT ?
  `).all(limit);

  return suggestions.map(s => ({
    ...s,
    score: calculateSuggestionScore(s.id)
  }));
}
