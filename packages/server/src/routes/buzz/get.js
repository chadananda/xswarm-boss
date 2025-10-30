/**
 * Get Buzz Listing Route
 *
 * GET /buzz/listings/:id
 * Get listing details (increments view count)
 */

import { optionalAuth } from '../../lib/auth-middleware.js';
import { createClient } from '@libsql/client';

/**
 * Handle get listing
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @param {string} listingId - Listing ID from URL
 * @returns {Promise<Response>} JSON response
 */
export async function handleGetListing(request, env, listingId) {
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

    // Check if user can view this listing
    const isOwner = user && user.id === listing.user_id;
    const isApproved = listing.status === 'approved' &&
      (listing.expires_at === null || new Date(listing.expires_at) > new Date());

    if (!isOwner && !isApproved) {
      return new Response(
        JSON.stringify({
          error: 'Listing not available',
          message: 'This listing is not currently available for viewing',
        }),
        {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Track view (only for approved listings, not for owner viewing their own)
    if (isApproved && !isOwner) {
      // Increment view count
      await db.execute({
        sql: 'UPDATE buzz_listings SET view_count = view_count + 1 WHERE id = ?',
        args: [listingId],
      });

      // Record interaction
      const interactionId = crypto.randomUUID();
      await db.execute({
        sql: `
          INSERT INTO buzz_interactions (
            id, listing_id, user_id, action, ip_address, user_agent, created_at
          ) VALUES (?, ?, ?, 'view', ?, ?, datetime('now'))
        `,
        args: [interactionId, listingId, user?.id || null, clientIp, userAgent],
      });
    }

    // Return listing
    return new Response(
      JSON.stringify({
        success: true,
        listing: {
          id: listing.id,
          user_id: listing.user_id,
          team_id: listing.team_id,
          title: listing.title,
          description: listing.description,
          category: listing.category,
          url: listing.url,
          image_url: listing.image_url,
          price_type: listing.price_type,
          price_range: listing.price_range,
          tags: JSON.parse(listing.tags || '[]'),
          status: listing.status,
          featured: listing.featured,
          view_count: listing.view_count + (isApproved && !isOwner ? 1 : 0),
          click_count: listing.click_count,
          expires_at: listing.expires_at,
          created_at: listing.created_at,
          updated_at: listing.updated_at,
          approved_at: listing.approved_at,
        },
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('Get listing error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to get listing',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
