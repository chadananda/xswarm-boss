/**
 * Remove Team Member Route
 *
 * DELETE /teams/:id/members/:userId
 * Removes a member from the team (admin+ only)
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import { requireTeamAdmin, getTeamOrFail, createTeamErrorResponse } from '../../lib/team-permissions.js';
import { removeTeamMember, getTeamById } from '../../lib/teams-db.js';
import { getUserById } from '../../lib/users.js';
import { sendEmail } from '../../lib/send-email.js';
import { getTeamRemovedEmailTemplate } from '../../lib/email-templates.js';

/**
 * Handle remove team member
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @param {string} teamId - Team ID from URL params
 * @param {string} userIdToRemove - User ID to remove from URL params
 * @returns {Promise<Response>} JSON response confirming removal
 */
export async function handleRemoveMember(request, env, teamId, userIdToRemove) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

    // Verify user is team admin or owner
    const membership = await requireTeamAdmin(teamId, user, env);

    // Get team details
    const team = await getTeamOrFail(teamId, env);

    // Prevent removing the owner
    if (team.owner_id === userIdToRemove) {
      return new Response(
        JSON.stringify({
          error: 'Cannot remove the team owner. Transfer ownership first or delete the team.',
        }),
        {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Prevent removing yourself (use leave endpoint instead)
    if (user.id === userIdToRemove) {
      return new Response(
        JSON.stringify({
          error: 'Cannot remove yourself. Use the leave team endpoint instead.',
        }),
        {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Get user being removed for email
    const removedUser = await getUserById(userIdToRemove, env);

    // Remove member
    await removeTeamMember(teamId, userIdToRemove, env);

    // Send removal notification email
    if (removedUser && removedUser.email) {
      const emailTemplate = getTeamRemovedEmailTemplate(team.name, removedUser.name || 'there');

      try {
        await sendEmail(
          {
            to: removedUser.email,
            ...emailTemplate,
          },
          env
        );
      } catch (emailError) {
        console.error('Failed to send removal notification email:', emailError);
        // Continue even if email fails
      }
    }

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Member removed successfully',
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

    console.error('Remove member error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to remove member',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
