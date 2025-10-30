/**
 * Reset Password Route
 *
 * POST /auth/reset-password
 * Resets user password with token
 */

import { getUserByResetToken, updatePasswordHash, clearResetToken, incrementJwtVersion } from '../../lib/users.js';
import { hashPassword, validatePasswordStrength } from '../../lib/password.js';

/**
 * Handle password reset
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} JSON response
 */
export async function handleResetPassword(request, env) {
  try {
    // Parse request body
    const body = await request.json();
    const { token, newPassword } = body;

    // Validate required fields
    if (!token || !newPassword) {
      return new Response(
        JSON.stringify({
          error: 'Missing required fields: token, newPassword',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Validate password strength
    const passwordValidation = validatePasswordStrength(newPassword);
    if (!passwordValidation.valid) {
      return new Response(
        JSON.stringify({
          error: 'Password does not meet requirements',
          details: passwordValidation.errors,
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Get user by reset token
    const user = await getUserByResetToken(token, env);

    if (!user) {
      return new Response(
        JSON.stringify({
          error: 'Invalid or expired reset token',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Hash new password
    const passwordHash = await hashPassword(newPassword);

    // Update password
    await updatePasswordHash(user.id, passwordHash, env);

    // Clear reset token
    await clearResetToken(user.id, env);

    // Increment JWT version to invalidate all existing sessions
    await incrementJwtVersion(user.id, env);

    console.log(`Password reset successful for user: ${user.email}`);

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Password reset successful. Please login with your new password.',
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('Password reset error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to reset password',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
