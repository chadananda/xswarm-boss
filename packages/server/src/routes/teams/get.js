/**
 * Get Team Route
 *
 * GET /teams/:id
 * Gets team details including members (requires team membership)
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import { requireTeamMembership, createTeamErrorResponse } from '../../lib/team-permissions.js';
import { getTeamById, getTeamMembers } from '../../lib/teams-db.js';

/**
 * Handle get team
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @param {string} teamId - Team ID from URL params
 * @returns {Promise<Response>} JSON response with team details
 */
export async function handleGetTeam(request, env, teamId) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

    // Verify team membership
    const membership = await requireTeamMembership(teamId, user, env);

    // Get team details
    const team = await getTeamById(teamId, env);

    if (!team) {
      return new Response(
        JSON.stringify({
          error: 'Team not found',
        }),
        {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Get team members
    const members = await getTeamMembers(teamId, env);

    return new Response(
      JSON.stringify({
        success: true,
        team: {
          ...team,
          user_role: membership.role,
          member_count: members.length,
          members,
        },
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

    console.error('Get team error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to get team',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
