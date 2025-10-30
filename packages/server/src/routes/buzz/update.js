/**
 * Update Buzz Listing Route
 *
 * PUT /buzz/listings/:id
 * Update listing (owner or admin only)
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import { createClient } from '@libsql/client';

/**
 * Handle update listing
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @param {string} listingId - Listing ID from URL
 * @returns {Promise<Response>} JSON response
 */
export async function handleUpdateListing(request, env, listingId) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

    // Parse request body
    const body = await request.json();

    // Fetch existing listing
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
          message: 'You do not have permission to update this listing',
        }),
        {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Build update query
    const updates = [];
    const args = [];

    // Only owner can update these fields
    if (isOwner) {
      if (body.title !== undefined) {
        if (body.title.length < 1 || body.title.length > 100) {
          return new Response(
            JSON.stringify({
              error: 'Invalid title length',
              message: 'Title must be between 1 and 100 characters',
            }),
            {
              status: 400,
              headers: { 'Content-Type': 'application/json' },
            }
          );
        }
        updates.push('title = ?');
        args.push(body.title);
      }

      if (body.description !== undefined) {
        if (body.description.length < 10 || body.description.length > 500) {
          return new Response(
            JSON.stringify({
              error: 'Invalid description length',
              message: 'Description must be between 10 and 500 characters',
            }),
            {
              status: 400,
              headers: { 'Content-Type': 'application/json' },
            }
          );
        }
        updates.push('description = ?');
        args.push(body.description);
      }

      if (body.category !== undefined) {
        const validCategories = ['saas', 'mobile_app', 'web_app', 'api', 'tool', 'service', 'consulting', 'other'];
        if (!validCategories.includes(body.category)) {
          return new Response(
            JSON.stringify({
              error: 'Invalid category',
              valid_categories: validCategories,
            }),
            {
              status: 400,
              headers: { 'Content-Type': 'application/json' },
            }
          );
        }
        updates.push('category = ?');
        args.push(body.category);
      }

      if (body.url !== undefined) {
        try {
          new URL(body.url);
          updates.push('url = ?');
          args.push(body.url);
        } catch (error) {
          return new Response(
            JSON.stringify({
              error: 'Invalid URL',
            }),
            {
              status: 400,
              headers: { 'Content-Type': 'application/json' },
            }
          );
        }
      }

      if (body.image_url !== undefined) {
        if (body.image_url) {
          try {
            new URL(body.image_url);
          } catch (error) {
            return new Response(
              JSON.stringify({
                error: 'Invalid image URL',
              }),
              {
                status: 400,
                headers: { 'Content-Type': 'application/json' },
              }
            );
          }
        }
        updates.push('image_url = ?');
        args.push(body.image_url || null);
      }

      if (body.price_type !== undefined) {
        const validPriceTypes = ['free', 'freemium', 'paid', 'custom'];
        if (!validPriceTypes.includes(body.price_type)) {
          return new Response(
            JSON.stringify({
              error: 'Invalid price_type',
              valid_price_types: validPriceTypes,
            }),
            {
              status: 400,
              headers: { 'Content-Type': 'application/json' },
            }
          );
        }
        updates.push('price_type = ?');
        args.push(body.price_type);
      }

      if (body.price_range !== undefined) {
        if (body.price_range) {
          const validPriceRanges = ['under_10', '10_50', '50_200', '200_plus', 'custom'];
          if (!validPriceRanges.includes(body.price_range)) {
            return new Response(
              JSON.stringify({
                error: 'Invalid price_range',
                valid_price_ranges: validPriceRanges,
              }),
              {
                status: 400,
                headers: { 'Content-Type': 'application/json' },
              }
            );
          }
        }
        updates.push('price_range = ?');
        args.push(body.price_range || null);
      }

      if (body.tags !== undefined) {
        updates.push('tags = ?');
        args.push(JSON.stringify(body.tags));
      }

      if (body.status !== undefined) {
        const validStatuses = ['draft', 'pending_review'];
        if (!validStatuses.includes(body.status)) {
          return new Response(
            JSON.stringify({
              error: 'Invalid status',
              message: 'Users can only set status to draft or pending_review',
            }),
            {
              status: 400,
              headers: { 'Content-Type': 'application/json' },
            }
          );
        }
        updates.push('status = ?');
        args.push(body.status);
      }
    }

    // Only admin can update these fields
    if (isAdmin) {
      if (body.featured !== undefined) {
        updates.push('featured = ?');
        args.push(body.featured);
      }
    }

    if (updates.length === 0) {
      return new Response(
        JSON.stringify({
          error: 'No valid fields to update',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Execute update
    updates.push("updated_at = datetime('now')");
    args.push(listingId);

    await db.execute({
      sql: `
        UPDATE buzz_listings
        SET ${updates.join(', ')}
        WHERE id = ?
      `,
      args,
    });

    // Fetch updated listing
    const updatedResult = await db.execute({
      sql: 'SELECT * FROM buzz_listings WHERE id = ?',
      args: [listingId],
    });

    const updatedListing = updatedResult.rows[0];

    return new Response(
      JSON.stringify({
        success: true,
        listing: {
          id: updatedListing.id,
          user_id: updatedListing.user_id,
          team_id: updatedListing.team_id,
          title: updatedListing.title,
          description: updatedListing.description,
          category: updatedListing.category,
          url: updatedListing.url,
          image_url: updatedListing.image_url,
          price_type: updatedListing.price_type,
          price_range: updatedListing.price_range,
          tags: JSON.parse(updatedListing.tags || '[]'),
          status: updatedListing.status,
          featured: updatedListing.featured,
          view_count: updatedListing.view_count,
          click_count: updatedListing.click_count,
          expires_at: updatedListing.expires_at,
          created_at: updatedListing.created_at,
          updated_at: updatedListing.updated_at,
          approved_at: updatedListing.approved_at,
        },
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

    console.error('Update listing error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to update listing',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
