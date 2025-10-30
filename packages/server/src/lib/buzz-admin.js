/**
 * Buzz Admin Management Utilities
 *
 * Functions for admin operations on Buzz listings
 */

import { createClient } from '@libsql/client';

/**
 * Create Turso client
 */
function getDbClient(env) {
  return createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });
}

/**
 * Approve a listing
 *
 * @param {string} listingId - Listing ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Updated listing
 */
export async function approveListing(listingId, env) {
  const db = getDbClient(env);

  // Set expiration to 90 days from now
  const expiresAt = new Date();
  expiresAt.setDate(expiresAt.getDate() + 90);

  await db.execute({
    sql: `
      UPDATE buzz_listings
      SET status = 'approved',
          approved_at = datetime('now'),
          expires_at = ?,
          updated_at = datetime('now')
      WHERE id = ?
    `,
    args: [expiresAt.toISOString(), listingId],
  });

  const result = await db.execute({
    sql: 'SELECT * FROM buzz_listings WHERE id = ?',
    args: [listingId],
  });

  return result.rows[0];
}

/**
 * Reject a listing
 *
 * @param {string} listingId - Listing ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Updated listing
 */
export async function rejectListing(listingId, env) {
  const db = getDbClient(env);

  await db.execute({
    sql: `
      UPDATE buzz_listings
      SET status = 'rejected',
          updated_at = datetime('now')
      WHERE id = ?
    `,
    args: [listingId],
  });

  const result = await db.execute({
    sql: 'SELECT * FROM buzz_listings WHERE id = ?',
    args: [listingId],
  });

  return result.rows[0];
}

/**
 * Feature a listing
 *
 * @param {string} listingId - Listing ID
 * @param {boolean} featured - Featured status
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Updated listing
 */
export async function featureListing(listingId, featured, env) {
  const db = getDbClient(env);

  await db.execute({
    sql: `
      UPDATE buzz_listings
      SET featured = ?,
          updated_at = datetime('now')
      WHERE id = ?
    `,
    args: [featured, listingId],
  });

  const result = await db.execute({
    sql: 'SELECT * FROM buzz_listings WHERE id = ?',
    args: [listingId],
  });

  return result.rows[0];
}

/**
 * Get moderation queue
 *
 * @param {Object} env - Environment variables
 * @param {number} limit - Maximum number of listings
 * @param {number} offset - Offset for pagination
 * @returns {Promise<Array>} Pending listings
 */
export async function getModerationQueue(env, limit = 50, offset = 0) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: `
      SELECT * FROM buzz_moderation_queue
      LIMIT ? OFFSET ?
    `,
    args: [limit, offset],
  });

  return result.rows;
}

/**
 * Get reported listings
 *
 * @param {Object} env - Environment variables
 * @param {number} minReports - Minimum number of reports
 * @returns {Promise<Array>} Reported listings
 */
export async function getReportedListings(env, minReports = 1) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: `
      SELECT * FROM buzz_reported_listings
      WHERE report_count >= ?
      ORDER BY report_count DESC, last_reported DESC
    `,
    args: [minReports],
  });

  return result.rows;
}

/**
 * Get expiring listings (7 days warning)
 *
 * @param {Object} env - Environment variables
 * @returns {Promise<Array>} Expiring listings
 */
export async function getExpiringListings(env) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: 'SELECT * FROM buzz_expiring_listings',
  });

  return result.rows;
}

/**
 * Renew a listing (extend expiration by 90 days)
 *
 * @param {string} listingId - Listing ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Updated listing
 */
export async function renewListing(listingId, env) {
  const db = getDbClient(env);

  // Get current listing
  const result = await db.execute({
    sql: 'SELECT * FROM buzz_listings WHERE id = ?',
    args: [listingId],
  });

  if (result.rows.length === 0) {
    throw new Error('Listing not found');
  }

  const listing = result.rows[0];

  // Calculate new expiration (90 days from now or from current expiration, whichever is later)
  const now = new Date();
  const currentExpiration = listing.expires_at ? new Date(listing.expires_at) : now;
  const baseDate = currentExpiration > now ? currentExpiration : now;

  const newExpiration = new Date(baseDate);
  newExpiration.setDate(newExpiration.getDate() + 90);

  await db.execute({
    sql: `
      UPDATE buzz_listings
      SET expires_at = ?,
          status = CASE WHEN status = 'expired' THEN 'approved' ELSE status END,
          updated_at = datetime('now')
      WHERE id = ?
    `,
    args: [newExpiration.toISOString(), listingId],
  });

  const updatedResult = await db.execute({
    sql: 'SELECT * FROM buzz_listings WHERE id = ?',
    args: [listingId],
  });

  return updatedResult.rows[0];
}

/**
 * Expire listings (mark as expired)
 *
 * @param {Object} env - Environment variables
 * @returns {Promise<number>} Number of expired listings
 */
export async function expireListings(env) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: `
      UPDATE buzz_listings
      SET status = 'expired',
          updated_at = datetime('now')
      WHERE status = 'approved'
      AND expires_at IS NOT NULL
      AND datetime(expires_at) <= datetime('now')
    `,
  });

  return result.rowsAffected || 0;
}

/**
 * Get admin dashboard analytics
 *
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Dashboard analytics
 */
export async function getAdminAnalytics(env) {
  const db = getDbClient(env);

  // Overall stats
  const overallResult = await db.execute({
    sql: `
      SELECT
        COUNT(*) as total_listings,
        COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_listings,
        COUNT(CASE WHEN status = 'pending_review' THEN 1 END) as pending_listings,
        COUNT(CASE WHEN status = 'draft' THEN 1 END) as draft_listings,
        COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_listings,
        COUNT(CASE WHEN status = 'expired' THEN 1 END) as expired_listings,
        COUNT(CASE WHEN featured = TRUE THEN 1 END) as featured_listings,
        SUM(view_count) as total_views,
        SUM(click_count) as total_clicks
      FROM buzz_listings
    `,
  });

  const overall = overallResult.rows[0];

  // Category breakdown
  const categoryResult = await db.execute({
    sql: 'SELECT * FROM buzz_category_stats ORDER BY approved_listings DESC',
  });

  // Recent activity
  const recentResult = await db.execute({
    sql: `
      SELECT
        date(created_at) as date,
        COUNT(*) as count
      FROM buzz_listings
      WHERE datetime(created_at) >= datetime('now', '-30 days')
      GROUP BY date(created_at)
      ORDER BY date DESC
    `,
  });

  // Top listings by views
  const topViewsResult = await db.execute({
    sql: `
      SELECT id, title, category, view_count, click_count
      FROM buzz_listings
      WHERE status = 'approved'
      ORDER BY view_count DESC
      LIMIT 10
    `,
  });

  // Top listings by clicks
  const topClicksResult = await db.execute({
    sql: `
      SELECT id, title, category, view_count, click_count
      FROM buzz_listings
      WHERE status = 'approved'
      ORDER BY click_count DESC
      LIMIT 10
    `,
  });

  return {
    overall: {
      total_listings: overall.total_listings,
      approved_listings: overall.approved_listings,
      pending_listings: overall.pending_listings,
      draft_listings: overall.draft_listings,
      rejected_listings: overall.rejected_listings,
      expired_listings: overall.expired_listings,
      featured_listings: overall.featured_listings,
      total_views: overall.total_views || 0,
      total_clicks: overall.total_clicks || 0,
      overall_ctr: overall.total_views > 0 ?
        ((overall.total_clicks / overall.total_views) * 100).toFixed(2) : 0,
    },
    categories: categoryResult.rows,
    recent_activity: recentResult.rows,
    top_by_views: topViewsResult.rows,
    top_by_clicks: topClicksResult.rows,
  };
}

/**
 * Bulk approve listings
 *
 * @param {Array<string>} listingIds - Array of listing IDs
 * @param {Object} env - Environment variables
 * @returns {Promise<number>} Number of approved listings
 */
export async function bulkApproveListings(listingIds, env) {
  const db = getDbClient(env);

  const expiresAt = new Date();
  expiresAt.setDate(expiresAt.getDate() + 90);

  let approved = 0;
  for (const listingId of listingIds) {
    try {
      await approveListing(listingId, env);
      approved++;
    } catch (error) {
      console.error(`Failed to approve listing ${listingId}:`, error);
    }
  }

  return approved;
}

/**
 * Bulk reject listings
 *
 * @param {Array<string>} listingIds - Array of listing IDs
 * @param {Object} env - Environment variables
 * @returns {Promise<number>} Number of rejected listings
 */
export async function bulkRejectListings(listingIds, env) {
  const db = getDbClient(env);

  let rejected = 0;
  for (const listingId of listingIds) {
    try {
      await rejectListing(listingId, env);
      rejected++;
    } catch (error) {
      console.error(`Failed to reject listing ${listingId}:`, error);
    }
  }

  return rejected;
}

/**
 * Bulk delete listings
 *
 * @param {Array<string>} listingIds - Array of listing IDs
 * @param {Object} env - Environment variables
 * @returns {Promise<number>} Number of deleted listings
 */
export async function bulkDeleteListings(listingIds, env) {
  const db = getDbClient(env);

  const placeholders = listingIds.map(() => '?').join(',');

  const result = await db.execute({
    sql: `DELETE FROM buzz_listings WHERE id IN (${placeholders})`,
    args: listingIds,
  });

  return result.rowsAffected || 0;
}
