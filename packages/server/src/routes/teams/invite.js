/**
 * Invite Team Member Route
 *
 * POST /teams/:id/invite
 * Invites a new member to the team (admin+ only)
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import {
  requireTeamAdmin,
  checkMemberLimit,
  getTeamOrFail,
  createTeamErrorResponse,
} from '../../lib/team-permissions.js';
import { createInvitation } from '../../lib/teams-db.js';
import { sendEmail } from '../../lib/send-email.js';
import { getTeamInvitationEmailTemplate } from '../../lib/email-templates.js';

/**
 * Handle invite team member
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @param {string} teamId - Team ID from URL params
 * @returns {Promise<Response>} JSON response with invitation details
 */
export async function handleInviteMember(request, env, teamId) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

    // Verify user is team admin or owner
    await requireTeamAdmin(teamId, user, env);

    // Check member limit
    await checkMemberLimit(teamId, env);

    // Get team details
    const team = await getTeamOrFail(teamId, env);

    // Parse request body
    const body = await request.json();

    // Validate email
    if (!body.email || typeof body.email !== 'string') {
      return new Response(
        JSON.stringify({
          error: 'Email is required',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    const email = body.email.toLowerCase().trim();

    // Basic email validation
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return new Response(
        JSON.stringify({
          error: 'Invalid email address',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Validate role
    const validRoles = ['admin', 'member', 'viewer'];
    const role = body.role || 'member';

    if (!validRoles.includes(role)) {
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

    // Create invitation
    const invitation = await createInvitation(
      {
        team_id: teamId,
        email,
        role,
        created_by: user.id,
      },
      env
    );

    // Send invitation email
    const invitationLink = `${env.APP_URL || 'https://xswarm.ai'}/teams/join/${invitation.token}`;

    const emailTemplate = getTeamInvitationEmailTemplate(
      team.name,
      user.name || 'A team member',
      invitationLink,
      role
    );

    try {
      await sendEmail(
        {
          to: email,
          ...emailTemplate,
        },
        env
      );
    } catch (emailError) {
      console.error('Failed to send invitation email:', emailError);
      // Continue even if email fails - invitation is still created
    }

    return new Response(
      JSON.stringify({
        success: true,
        invitation: {
          id: invitation.id,
          email: invitation.email,
          role: invitation.role,
          expires_at: invitation.expires_at,
          created_at: invitation.created_at,
        },
      }),
      {
        status: 201,
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

    console.error('Invite member error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to invite member',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
