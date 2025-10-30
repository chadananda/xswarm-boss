/**
 * Forgot Password Route
 *
 * POST /auth/forgot-password
 * Sends password reset email
 */

import { getUserByEmail, setResetToken } from '../../lib/users.js';
import { generatePasswordResetToken } from '../../lib/jwt.js';
import { getPasswordResetEmailTemplate } from '../../lib/email-templates.js';
import { sendEmail } from '../../lib/send-email.js';

/**
 * Handle forgot password request
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} JSON response
 */
export async function handleForgotPassword(request, env) {
  try {
    // Parse request body
    const body = await request.json();
    const { email } = body;

    // Validate required fields
    if (!email) {
      return new Response(
        JSON.stringify({
          error: 'Missing required field: email',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Get user by email
    const user = await getUserByEmail(email, env);

    // Always return success (prevent email enumeration)
    // But only send email if user exists
    if (user && user.password_hash) {
      // Generate password reset token
      const resetToken = generatePasswordResetToken();

      // Set reset token
      await setResetToken(user.id, resetToken.token, resetToken.expires, env);

      // Send password reset email
      const baseUrl = env.BASE_URL || 'https://xswarm.ai';
      const resetLink = `${baseUrl}/reset-password?token=${resetToken.token}`;

      const userName = user.name ? user.name.split(' ')[0] : 'there';
      const emailTemplate = getPasswordResetEmailTemplate(resetLink, userName);

      try {
        await sendEmail(
          {
            to: user.email,
            from: env.FROM_EMAIL || 'noreply@xswarm.ai',
            subject: emailTemplate.subject,
            text: emailTemplate.text,
            html: emailTemplate.html,
          },
          env
        );

        console.log(`Password reset email sent to: ${user.email}`);
      } catch (emailError) {
        console.error('Failed to send password reset email:', emailError);
        // Don't throw - return success to prevent email enumeration
      }
    }

    // Always return success message (security best practice)
    return new Response(
      JSON.stringify({
        success: true,
        message: 'If your email is registered, you will receive password reset instructions.',
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('Forgot password error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to process request',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
