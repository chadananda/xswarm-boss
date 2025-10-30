/**
 * Create Buzz Listing Route
 *
 * POST /buzz/listings
 * Creates a new product/service listing (Pro+ users only)
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import { userHasFeature } from '../../lib/users.js';
import { createClient } from '@libsql/client';

/**
 * Handle create listing
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} JSON response
 */
export async function handleCreateListing(request, env) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

    // Check if user has Pro+ tier (ai_project_manager or ai_cto)
    const tier = user.subscription_tier;
    if (tier !== 'ai_project_manager' && tier !== 'ai_cto') {
      return new Response(
        JSON.stringify({
          error: 'Pro+ subscription required',
          message: 'Buzz listings are only available for AI Project Manager and AI CTO tiers',
        }),
        {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Parse request body
    const body = await request.json();
    const {
      title,
      description,
      category,
      url,
      image_url,
      price_type,
      price_range,
      tags,
      team_id,
      status,
    } = body;

    // Validate required fields
    if (!title || !description || !category || !url || !price_type) {
      return new Response(
        JSON.stringify({
          error: 'Missing required fields',
          required: ['title', 'description', 'category', 'url', 'price_type'],
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Validate title length
    if (title.length < 1 || title.length > 100) {
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

    // Validate description length
    if (description.length < 10 || description.length > 500) {
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

    // Validate category
    const validCategories = ['saas', 'mobile_app', 'web_app', 'api', 'tool', 'service', 'consulting', 'other'];
    if (!validCategories.includes(category)) {
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

    // Validate price_type
    const validPriceTypes = ['free', 'freemium', 'paid', 'custom'];
    if (!validPriceTypes.includes(price_type)) {
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

    // Validate price_range if provided
    if (price_range) {
      const validPriceRanges = ['under_10', '10_50', '50_200', '200_plus', 'custom'];
      if (!validPriceRanges.includes(price_range)) {
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

    // Validate URL
    try {
      new URL(url);
    } catch (error) {
      return new Response(
        JSON.stringify({
          error: 'Invalid URL',
          message: 'Please provide a valid product/service URL',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Validate image_url if provided
    if (image_url) {
      try {
        new URL(image_url);
      } catch (error) {
        return new Response(
          JSON.stringify({
            error: 'Invalid image URL',
            message: 'Please provide a valid image URL',
          }),
          {
            status: 400,
            headers: { 'Content-Type': 'application/json' },
          }
        );
      }
    }

    // Check active listing count (max 5 per user)
    const db = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN,
    });

    const countResult = await db.execute({
      sql: `
        SELECT COUNT(*) as count
        FROM buzz_listings
        WHERE user_id = ?
        AND status IN ('approved', 'pending_review')
      `,
      args: [user.id],
    });

    const activeCount = countResult.rows[0].count;
    if (activeCount >= 5) {
      return new Response(
        JSON.stringify({
          error: 'Maximum listings reached',
          message: 'You can have a maximum of 5 active listings. Please delete or wait for expiration of existing listings.',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Validate team ownership if team_id provided
    if (team_id) {
      const teamResult = await db.execute({
        sql: `
          SELECT tm.role
          FROM team_members tm
          WHERE tm.team_id = ? AND tm.user_id = ?
        `,
        args: [team_id, user.id],
      });

      if (teamResult.rows.length === 0) {
        return new Response(
          JSON.stringify({
            error: 'Not a team member',
            message: 'You are not a member of this team',
          }),
          {
            status: 403,
            headers: { 'Content-Type': 'application/json' },
          }
        );
      }

      // Check if user has permission to create listings for team (owner or admin)
      const role = teamResult.rows[0].role;
      if (role !== 'owner' && role !== 'admin') {
        return new Response(
          JSON.stringify({
            error: 'Insufficient permissions',
            message: 'Only team owners and admins can create listings',
          }),
          {
            status: 403,
            headers: { 'Content-Type': 'application/json' },
          }
        );
      }
    }

    // Create listing
    const listingId = crypto.randomUUID();
    const listingStatus = status === 'draft' ? 'draft' : 'pending_review';
    const tagsJson = tags ? JSON.stringify(tags) : '[]';

    await db.execute({
      sql: `
        INSERT INTO buzz_listings (
          id, user_id, team_id, title, description,
          category, url, image_url, price_type, price_range,
          tags, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
      `,
      args: [
        listingId,
        user.id,
        team_id || null,
        title,
        description,
        category,
        url,
        image_url || null,
        price_type,
        price_range || null,
        tagsJson,
        listingStatus,
      ],
    });

    // Fetch created listing
    const result = await db.execute({
      sql: 'SELECT * FROM buzz_listings WHERE id = ?',
      args: [listingId],
    });

    const listing = result.rows[0];

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
          tags: JSON.parse(listing.tags),
          status: listing.status,
          featured: listing.featured,
          view_count: listing.view_count,
          click_count: listing.click_count,
          expires_at: listing.expires_at,
          created_at: listing.created_at,
          updated_at: listing.updated_at,
          approved_at: listing.approved_at,
        },
      }),
      {
        status: 201,
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

    console.error('Create listing error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to create listing',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
