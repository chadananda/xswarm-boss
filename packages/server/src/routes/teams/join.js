/**
 * Join Team Route
 *
 * POST /teams/join/:token
 * Accepts a team invitation and adds user to team
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import { createTeamErrorResponse } from '../../lib/team-permissions.js';
import {
  getInvitationByToken,
  deleteInvitation,
  addTeamMember,
  getTeamById,
} from '../../lib/teams-db.js';
import { sendEmail } from '../../lib/send-email.js';
import { getTeamWelcomeEmailTemplate } from '../../lib/email-templates.js';

/**
 * Handle join team
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @param {string} token - Invitation token from URL params
 * @returns {Promise<Response>} JSON response with team details
 */
export async function handleJoinTeam(request, env, token) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

    // Get invitation by token
    const invitation = await getInvitationByToken(token, env);

    if (!invitation) {
      return new Response(
        JSON.stringify({
          error: 'Invalid or expired invitation',
        }),
        {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Verify email matches invitation
    if (user.email.toLowerCase() !== invitation.email.toLowerCase()) {
      return new Response(
        JSON.stringify({
          error: 'This invitation was sent to a different email address',
        }),
        {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Get team details
    const team = await getTeamById(invitation.team_id, env);

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

    // Add user to team
    try {
      await addTeamMember(
        {
          team_id: invitation.team_id,
          user_id: user.id,
          role: invitation.role,
          invited_by: invitation.created_by,
        },
        env
      );
    } catch (error) {
      // Check if user is already a member
      if (error.message && error.message.includes('UNIQUE constraint failed')) {
        return new Response(
          JSON.stringify({
            error: 'You are already a member of this team',
          }),
          {
            status: 409,
            headers: { 'Content-Type': 'application/json' },
          }
        );
      }
      throw error;
    }

    // Delete invitation
    await deleteInvitation(invitation.id, env);

    // Send welcome email
    const emailTemplate = getTeamWelcomeEmailTemplate(team.name, user.name || 'there', invitation.role);

    try {
      await sendEmail(
        {
          to: user.email,
          ...emailTemplate,
        },
        env
      );
    } catch (emailError) {
      console.error('Failed to send welcome email:', emailError);
      // Continue even if email fails
    }

    return new Response(
      JSON.stringify({
        success: true,
        team: {
          id: team.id,
          name: team.name,
          description: team.description,
          role: invitation.role,
        },
        message: 'Successfully joined team',
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

    console.error('Join team error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to join team',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
