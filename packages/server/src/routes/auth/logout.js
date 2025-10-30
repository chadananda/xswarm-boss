/**
 * User Logout Route
 *
 * POST /auth/logout
 * Invalidates all user's JWT tokens
 */

import { requireAuth } from '../../lib/auth-middleware.js';
import { incrementJwtVersion } from '../../lib/users.js';

/**
 * Handle user logout
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} JSON response
 */
export async function handleLogout(request, env) {
  try {
    // Require authentication
    const user = await requireAuth(request, env);

    // Increment JWT version to invalidate all existing tokens
    await incrementJwtVersion(user.id, env);

    console.log(`User logout successful: ${user.email}`);

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Logout successful',
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

    console.error('Logout error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to logout',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
