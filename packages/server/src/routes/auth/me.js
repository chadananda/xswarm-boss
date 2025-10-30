/**
 * Get Current User Route
 *
 * GET /auth/me
 * Returns current authenticated user's information
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import { userHasFeature } from '../../lib/users.js';

/**
 * Handle get current user
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} JSON response with user info
 */
export async function handleGetMe(request, env) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

    // Get available features based on subscription tier
    const features = {
      email: userHasFeature(user, 'email'),
      sms: userHasFeature(user, 'sms'),
      voice: userHasFeature(user, 'voice'),
      phone: userHasFeature(user, 'phone'),
    };

    return new Response(
      JSON.stringify({
        success: true,
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
          subscription_tier: user.subscription_tier,
          email_verified: user.email_verified,
          xswarm_email: user.xswarm_email,
          xswarm_phone: user.xswarm_phone,
          persona: user.persona,
          created_at: user.created_at,
          features,
        },
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

    console.error('Get user error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to get user information',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
