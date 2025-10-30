/**
 * Create Team Route
 *
 * POST /teams
 * Creates a new team (Pro+ tier only)
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import { checkTeamTier, createTeamErrorResponse } from '../../lib/team-permissions.js';
import { createTeam } from '../../lib/teams-db.js';

/**
 * Handle create team
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} JSON response with team details
 */
export async function handleCreateTeam(request, env) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

    // Check if user has Pro+ tier
    checkTeamTier(user);

    // Parse request body
    const body = await request.json();

    // Validate required fields
    if (!body.name || typeof body.name !== 'string') {
      return new Response(
        JSON.stringify({
          error: 'Team name is required',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Validate name length
    if (body.name.length < 1 || body.name.length > 100) {
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

    // Validate description length if provided
    if (body.description && body.description.length > 500) {
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

    // Create team
    const team = await createTeam(
      {
        name: body.name.trim(),
        description: body.description ? body.description.trim() : null,
        owner_id: user.id,
        subscription_tier: user.subscription_tier,
      },
      env
    );

    return new Response(
      JSON.stringify({
        success: true,
        team,
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

    console.error('Create team error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to create team',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
