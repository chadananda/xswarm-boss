/**
 * Delete Buzz Listing Route
 *
 * DELETE /buzz/listings/:id
 * Delete listing (owner or admin only)
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import { createClient } from '@libsql/client';

/**
 * Handle delete listing
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @param {string} listingId - Listing ID from URL
 * @returns {Promise<Response>} JSON response
 */
export async function handleDeleteListing(request, env, listingId) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

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

    // Check ownership
    const isOwner = user.id === listing.user_id;
    const isAdmin = user.subscription_tier === 'admin';

    if (!isOwner && !isAdmin) {
      return new Response(
        JSON.stringify({
          error: 'Unauthorized',
          message: 'You do not have permission to delete this listing',
        }),
        {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Delete listing (cascade will delete interactions)
    await db.execute({
      sql: 'DELETE FROM buzz_listings WHERE id = ?',
      args: [listingId],
    });

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Listing deleted successfully',
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
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

    console.error('Delete listing error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to delete listing',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
