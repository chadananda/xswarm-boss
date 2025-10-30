/**
 * Get Buzz Listing Stats Route
 *
 * GET /buzz/stats
 * Get analytics for user's listings
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import { createClient } from '@libsql/client';

/**
 * Handle get stats
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} JSON response
 */
export async function handleGetStats(request, env) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

    // Parse query parameters
    const url = new URL(request.url);
    const listingId = url.searchParams.get('listing_id');

    const db = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN,
    });

    if (listingId) {
      // Get stats for specific listing
      const listingResult = await db.execute({
        sql: 'SELECT * FROM buzz_listings WHERE id = ? AND user_id = ?',
        args: [listingId, user.id],
      });

      if (listingResult.rows.length === 0) {
        return new Response(
          JSON.stringify({
            error: 'Listing not found',
          }),
          {
            status: 404,
            headers: { 'Content-Type': 'application/json' },
          }
        );
      }

      const listing = listingResult.rows[0];

      // Get interaction breakdown
      const interactionsResult = await db.execute({
        sql: `
          SELECT
            action,
            COUNT(*) as count,
            MIN(created_at) as first_interaction,
            MAX(created_at) as last_interaction
          FROM buzz_interactions
          WHERE listing_id = ?
          GROUP BY action
        `,
        args: [listingId],
      });

      const interactions = {};
      interactionsResult.rows.forEach(row => {
        interactions[row.action] = {
          count: row.count,
          first: row.first_interaction,
          last: row.last_interaction,
        };
      });

      // Get daily stats for last 30 days
      const dailyResult = await db.execute({
        sql: `
          SELECT
            date(created_at) as date,
            action,
            COUNT(*) as count
          FROM buzz_interactions
          WHERE listing_id = ?
          AND datetime(created_at) >= datetime('now', '-30 days')
          GROUP BY date(created_at), action
          ORDER BY date DESC
        `,
        args: [listingId],
      });

      // Group by date
      const dailyStats = {};
      dailyResult.rows.forEach(row => {
        if (!dailyStats[row.date]) {
          dailyStats[row.date] = { date: row.date };
        }
        dailyStats[row.date][row.action] = row.count;
      });

      // Calculate CTR
      const views = listing.view_count;
      const clicks = listing.click_count;
      const ctr = views > 0 ? ((clicks / views) * 100).toFixed(2) : 0;

      return new Response(
        JSON.stringify({
          success: true,
          listing: {
            id: listing.id,
            title: listing.title,
            status: listing.status,
            created_at: listing.created_at,
            approved_at: listing.approved_at,
            expires_at: listing.expires_at,
          },
          stats: {
            view_count: views,
            click_count: clicks,
            ctr: parseFloat(ctr),
            interactions,
            daily_stats: Object.values(dailyStats),
          },
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    } else {
      // Get aggregate stats for all user's listings
      const listingsResult = await db.execute({
        sql: `
          SELECT
            COUNT(*) as total_listings,
            COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_listings,
            COUNT(CASE WHEN status = 'pending_review' THEN 1 END) as pending_listings,
            COUNT(CASE WHEN status = 'draft' THEN 1 END) as draft_listings,
            COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_listings,
            COUNT(CASE WHEN status = 'expired' THEN 1 END) as expired_listings,
            SUM(view_count) as total_views,
            SUM(click_count) as total_clicks,
            COUNT(CASE WHEN featured = TRUE THEN 1 END) as featured_listings
          FROM buzz_listings
          WHERE user_id = ?
        `,
        args: [user.id],
      });

      const stats = listingsResult.rows[0];
      const totalViews = stats.total_views || 0;
      const totalClicks = stats.total_clicks || 0;
      const ctr = totalViews > 0 ? ((totalClicks / totalViews) * 100).toFixed(2) : 0;

      // Get individual listing performance
      const listingPerformanceResult = await db.execute({
        sql: `
          SELECT
            id,
            title,
            category,
            status,
            view_count,
            click_count,
            created_at,
            approved_at
          FROM buzz_listings
          WHERE user_id = ?
          ORDER BY view_count DESC
          LIMIT 10
        `,
        args: [user.id],
      });

      const topListings = listingPerformanceResult.rows.map(row => ({
        id: row.id,
        title: row.title,
        category: row.category,
        status: row.status,
        view_count: row.view_count,
        click_count: row.click_count,
        ctr: row.view_count > 0 ? ((row.click_count / row.view_count) * 100).toFixed(2) : 0,
        created_at: row.created_at,
        approved_at: row.approved_at,
      }));

      return new Response(
        JSON.stringify({
          success: true,
          summary: {
            total_listings: stats.total_listings,
            approved_listings: stats.approved_listings,
            pending_listings: stats.pending_listings,
            draft_listings: stats.draft_listings,
            rejected_listings: stats.rejected_listings,
            expired_listings: stats.expired_listings,
            featured_listings: stats.featured_listings,
            total_views: totalViews,
            total_clicks: totalClicks,
            overall_ctr: parseFloat(ctr),
            listings_remaining: 5 - (stats.approved_listings + stats.pending_listings),
          },
          top_listings: topListings,
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }
  } catch (error) {
    // Handle auth errors
    if (error.statusCode) {
      return new Response(
        JSON.stringify({
          error: error.message,
        }),
        {
          status: error.statusCode,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    console.error('Get stats error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to get stats',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
