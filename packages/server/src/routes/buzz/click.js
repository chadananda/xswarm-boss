/**
 * Track Click on Buzz Listing Route
 *
 * POST /buzz/listings/:id/click
 * Track click and redirect to product URL
 */

import { optionalAuth } from '../../lib/auth-middleware.js';
import { createClient } from '@libsql/client';

/**
 * Handle listing click
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @param {string} listingId - Listing ID from URL
 * @returns {Promise<Response>} Redirect or JSON response
 */
export async function handleListingClick(request, env, listingId) {
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

    const listing = result.rows[0];

    // Check if listing is available
    const isApproved = listing.status === 'approved' &&
      (listing.expires_at === null || new Date(listing.expires_at) > new Date());

    if (!isApproved) {
      return new Response(
        JSON.stringify({
          error: 'Listing not available',
        }),
        {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Track click
    await db.execute({
      sql: 'UPDATE buzz_listings SET click_count = click_count + 1 WHERE id = ?',
      args: [listingId],
    });

    // Record interaction
    const interactionId = crypto.randomUUID();
    await db.execute({
      sql: `
        INSERT INTO buzz_interactions (
          id, listing_id, user_id, action, ip_address, user_agent, created_at
        ) VALUES (?, ?, ?, 'click', ?, ?, datetime('now'))
      `,
      args: [interactionId, listingId, user?.id || null, clientIp, userAgent],
    });

    // Redirect to product URL
    return Response.redirect(listing.url, 302);
  } catch (error) {
    console.error('Track click error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to track click',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
