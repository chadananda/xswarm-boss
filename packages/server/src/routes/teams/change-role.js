/**
 * Change Team Member Role Route
 *
 * PUT /teams/:id/members/:userId/role
 * Changes a team member's role (owner only)
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import { requireTeamOwner, getTeamOrFail, createTeamErrorResponse } from '../../lib/team-permissions.js';
import { updateMemberRole } from '../../lib/teams-db.js';

/**
 * Handle change member role
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @param {string} teamId - Team ID from URL params
 * @param {string} userIdToUpdate - User ID to update from URL params
 * @returns {Promise<Response>} JSON response confirming role change
 */
export async function handleChangeMemberRole(request, env, teamId, userIdToUpdate) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

    // Verify user is team owner
    await requireTeamOwner(teamId, user, env);

    // Get team details
    const team = await getTeamOrFail(teamId, env);

    // Parse request body
    const body = await request.json();

    // Validate role
    const validRoles = ['admin', 'member', 'viewer'];
    if (!body.role || !validRoles.includes(body.role)) {
      return new Response(
        JSON.stringify({
          error: 'Invalid role. Must be admin, member, or viewer',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Prevent changing owner's role
    if (team.owner_id === userIdToUpdate) {
      return new Response(
        JSON.stringify({
          error: 'Cannot change the owner\'s role. Transfer ownership first if needed.',
        }),
        {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Update member role
    await updateMemberRole(teamId, userIdToUpdate, body.role, env);

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Member role updated successfully',
        role: body.role,
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

    console.error('Change member role error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to change member role',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
