/**
 * Update Team Route
 *
 * PUT /teams/:id
 * Updates team details (admin+ only)
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import { requireTeamAdmin, createTeamErrorResponse } from '../../lib/team-permissions.js';
import { updateTeam } from '../../lib/teams-db.js';

/**
 * Handle update team
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @param {string} teamId - Team ID from URL params
 * @returns {Promise<Response>} JSON response with updated team details
 */
export async function handleUpdateTeam(request, env, teamId) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

    // Verify user is team admin or owner
    await requireTeamAdmin(teamId, user, env);

    // Parse request body
    const body = await request.json();

    // Prepare updates object
    const updates = {};

    if (body.name !== undefined) {
      if (typeof body.name !== 'string' || body.name.length < 1 || body.name.length > 100) {
        return new Response(
          JSON.stringify({
            error: 'Team name must be between 1 and 100 characters',
          }),
          {
            status: 400,
            headers: { 'Content-Type': 'application/json' },
          }
        );
      }
      updates.name = body.name.trim();
    }

    if (body.description !== undefined) {
      if (body.description !== null && body.description.length > 500) {
        return new Response(
          JSON.stringify({
            error: 'Team description must be less than 500 characters',
          }),
          {
            status: 400,
            headers: { 'Content-Type': 'application/json' },
          }
        );
      }
      updates.description = body.description ? body.description.trim() : null;
    }

    // Check if there are any updates
    if (Object.keys(updates).length === 0) {
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

    // Update team
    const team = await updateTeam(teamId, updates, env);

    return new Response(
      JSON.stringify({
        success: true,
        team,
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    // Handle team permission errors
    if (error.name === 'TeamPermissionError') {
      return createTeamErrorResponse(error);
    }

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

    console.error('Update team error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to update team',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
