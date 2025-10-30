/**
 * Delete Team Route
 *
 * DELETE /teams/:id
 * Deletes a team (owner only)
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import { requireTeamOwner, createTeamErrorResponse } from '../../lib/team-permissions.js';
import { deleteTeam } from '../../lib/teams-db.js';

/**
 * Handle delete team
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @param {string} teamId - Team ID from URL params
 * @returns {Promise<Response>} JSON response confirming deletion
 */
export async function handleDeleteTeam(request, env, teamId) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

    // Verify user is team owner
    await requireTeamOwner(teamId, user, env);

    // Delete team (cascade deletes members and invitations)
    await deleteTeam(teamId, env);

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Team deleted successfully',
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

    console.error('Delete team error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to delete team',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
