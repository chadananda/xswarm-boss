/**
 * Report Buzz Listing Route
 *
 * POST /buzz/listings/:id/report
 * Report inappropriate listing
 */

import { optionalAuth } from '../../lib/auth-middleware.js';
import { createClient } from '@libsql/client';

/**
 * Handle listing report
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @param {string} listingId - Listing ID from URL
 * @returns {Promise<Response>} JSON response
 */
export async function handleListingReport(request, env, listingId) {
  try {
    // Optional authentication
    const user = await optionalAuth(request, env);

    // Get client IP for tracking
    const clientIp = request.headers.get('CF-Connecting-IP') || request.headers.get('X-Forwarded-For') || 'unknown';
    const userAgent = request.headers.get('User-Agent') || 'unknown';

    // Fetch listing
    const db = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN,
    });

    const result = await db.execute({
      sql: 'SELECT * FROM buzz_listings WHERE id = ?',
      args: [listingId],
    });

    if (result.rows.length === 0) {
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

    // Check if user/IP has already reported this listing (prevent spam)
    const checkResult = await db.execute({
      sql: `
        SELECT COUNT(*) as count
        FROM buzz_interactions
        WHERE listing_id = ?
        AND action = 'report'
        AND (
          (user_id IS NOT NULL AND user_id = ?) OR
          (user_id IS NULL AND ip_address = ?)
        )
        AND datetime(created_at) > datetime('now', '-24 hours')
      `,
      args: [listingId, user?.id || null, clientIp],
    });

    if (checkResult.rows[0].count > 0) {
      return new Response(
        JSON.stringify({
          error: 'Already reported',
          message: 'You have already reported this listing in the last 24 hours',
        }),
        {
          status: 429,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Record report
    const interactionId = crypto.randomUUID();
    await db.execute({
      sql: `
        INSERT INTO buzz_interactions (
          id, listing_id, user_id, action, ip_address, user_agent, created_at
        ) VALUES (?, ?, ?, 'report', ?, ?, datetime('now'))
      `,
      args: [interactionId, listingId, user?.id || null, clientIp, userAgent],
    });

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Listing reported successfully. Our moderation team will review it.',
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('Report listing error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to report listing',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
