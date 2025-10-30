/**
 * List Buzz Listings Route
 *
 * GET /buzz/listings
 * Browse listings with filtering, search, and pagination
 */

import { optionalAuth } from '../../lib/auth-middleware.js';
import { createClient } from '@libsql/client';

/**
 * Handle list listings
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} JSON response
 */
export async function handleListListings(request, env) {
  try {
    // Optional authentication (allows public browsing)
    const user = await optionalAuth(request, env);

    // Parse query parameters
    const url = new URL(request.url);
    const category = url.searchParams.get('category');
    const search = url.searchParams.get('search');
    const price_type = url.searchParams.get('price_type');
    const price_range = url.searchParams.get('price_range');
    const featured = url.searchParams.get('featured');
    const user_id = url.searchParams.get('user_id');
    const status = url.searchParams.get('status');
    const limit = parseInt(url.searchParams.get('limit') || '50');
    const offset = parseInt(url.searchParams.get('offset') || '0');
    const sort = url.searchParams.get('sort') || 'created_desc';

    // Build query
    const conditions = [];
    const args = [];

    // Public users only see approved, non-expired listings
    // Authenticated users can see their own listings in any status
    if (user && user_id === user.id) {
      // User viewing their own listings
      conditions.push('user_id = ?');
      args.push(user.id);

      if (status) {
        conditions.push('status = ?');
        args.push(status);
      }
    } else {
      // Public viewing or browsing other users' listings
      conditions.push("status = 'approved'");
      conditions.push("(expires_at IS NULL OR datetime(expires_at) > datetime('now'))");
    }

    // Apply filters
    if (category) {
      conditions.push('category = ?');
      args.push(category);
    }

    if (price_type) {
      conditions.push('price_type = ?');
      args.push(price_type);
    }

    if (price_range) {
      conditions.push('price_range = ?');
      args.push(price_range);
    }

    if (featured === 'true') {
      conditions.push('featured = TRUE');
    }

    // Apply search
    if (search) {
      conditions.push('(title LIKE ? OR description LIKE ?)');
      const searchPattern = `%${search}%`;
      args.push(searchPattern, searchPattern);
    }

    // Build WHERE clause
    const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

    // Determine sort order
    let orderClause = 'ORDER BY featured DESC, created_at DESC';
    switch (sort) {
      case 'created_asc':
        orderClause = 'ORDER BY featured DESC, created_at ASC';
        break;
      case 'created_desc':
        orderClause = 'ORDER BY featured DESC, created_at DESC';
        break;
      case 'views_desc':
        orderClause = 'ORDER BY featured DESC, view_count DESC';
        break;
      case 'clicks_desc':
        orderClause = 'ORDER BY featured DESC, click_count DESC';
        break;
      case 'title_asc':
        orderClause = 'ORDER BY featured DESC, title ASC';
        break;
    }

    // Execute query
    const db = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN,
    });

    const result = await db.execute({
      sql: `
        SELECT * FROM buzz_listings
        ${whereClause}
        ${orderClause}
        LIMIT ? OFFSET ?
      `,
      args: [...args, limit, offset],
    });

    // Get total count
    const countResult = await db.execute({
      sql: `
        SELECT COUNT(*) as count FROM buzz_listings
        ${whereClause}
      `,
      args: args,
    });

    const total = countResult.rows[0].count;

    // Format listings
    const listings = result.rows.map(row => ({
      id: row.id,
      user_id: row.user_id,
      team_id: row.team_id,
      title: row.title,
      description: row.description,
      category: row.category,
      url: row.url,
      image_url: row.image_url,
      price_type: row.price_type,
      price_range: row.price_range,
      tags: JSON.parse(row.tags || '[]'),
      status: row.status,
      featured: row.featured,
      view_count: row.view_count,
      click_count: row.click_count,
      expires_at: row.expires_at,
      created_at: row.created_at,
      updated_at: row.updated_at,
      approved_at: row.approved_at,
    }));

    return new Response(
      JSON.stringify({
        success: true,
        listings,
        pagination: {
          total,
          limit,
          offset,
          has_more: offset + limit < total,
        },
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('List listings error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to list listings',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
