/**
 * Get Buzz Categories Route
 *
 * GET /buzz/categories
 * Get available categories with listing counts
 */

import { createClient } from '@libsql/client';

/**
 * Handle get categories
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} JSON response
 */
export async function handleGetCategories(request, env) {
  try {
    const db = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN,
    });

    // Get category stats
    const result = await db.execute({
      sql: `
        SELECT * FROM buzz_category_stats
        ORDER BY approved_listings DESC
      `,
    });

    const categories = [
      { id: 'saas', name: 'SaaS Products', description: 'Software as a Service platforms and tools' },
      { id: 'mobile_app', name: 'Mobile Apps', description: 'iOS and Android applications' },
      { id: 'web_app', name: 'Web Applications', description: 'Browser-based applications' },
      { id: 'api', name: 'APIs & Services', description: 'Developer APIs and backend services' },
      { id: 'tool', name: 'Developer Tools', description: 'Development tools and utilities' },
      { id: 'service', name: 'Services', description: 'Professional services and offerings' },
      { id: 'consulting', name: 'Consulting', description: 'Consulting and advisory services' },
      { id: 'other', name: 'Other', description: 'Other products and services' },
    ];

    // Merge stats with category info
    const categoriesWithStats = categories.map(cat => {
      const stats = result.rows.find(row => row.category === cat.id);
      return {
        ...cat,
        total_listings: stats?.total_listings || 0,
        approved_listings: stats?.approved_listings || 0,
        total_views: stats?.total_views || 0,
        total_clicks: stats?.total_clicks || 0,
        avg_views_per_listing: stats?.avg_views_per_listing || 0,
        avg_clicks_per_listing: stats?.avg_clicks_per_listing || 0,
      };
    });

    return new Response(
      JSON.stringify({
        success: true,
        categories: categoriesWithStats,
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('Get categories error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to get categories',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
