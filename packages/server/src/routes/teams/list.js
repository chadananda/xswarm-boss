/**
 * List Teams Route
 *
 * GET /teams
 * Lists all teams the authenticated user is a member of
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import { listUserTeams } from '../../lib/teams-db.js';

/**
 * Handle list teams
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} JSON response with teams list
 */
export async function handleListTeams(request, env) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

    // Get user's teams
    const teams = await listUserTeams(user.id, env);

    return new Response(
      JSON.stringify({
        success: true,
        teams,
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

    console.error('List teams error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to list teams',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
