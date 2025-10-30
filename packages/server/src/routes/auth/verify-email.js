/**
 * Email Verification Route
 *
 * POST /auth/verify-email
 * Verifies email with token and activates account
 */

import { getUserByVerificationToken, updateEmailVerified } from '../../lib/users.js';
import { generateToken } from '../../lib/jwt.js';
import { getWelcomeEmailTemplate } from '../../lib/email-templates.js';
import { sendEmail } from '../../lib/send-email.js';

/**
 * Handle email verification
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} JSON response with JWT token
 */
export async function handleVerifyEmail(request, env) {
  try {
    // Parse request body
    const body = await request.json();
    const { token } = body;

    // Validate required fields
    if (!token) {
      return new Response(
        JSON.stringify({
          error: 'Missing required field: token',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Get user by verification token
    const user = await getUserByVerificationToken(token, env);

    if (!user) {
      return new Response(
        JSON.stringify({
          error: 'Invalid or expired verification token',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Mark email as verified
    await updateEmailVerified(user.id, env);

    // Generate JWT token for authenticated session
    const jwtToken = generateToken(user, env.JWT_SECRET);

    // Send welcome email
    const userName = user.name ? user.name.split(' ')[0] : 'there';
    const emailTemplate = getWelcomeEmailTemplate(userName, user.subscription_tier);

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
    } catch (emailError) {
      // Log error but don't fail verification if welcome email fails
      console.error('Failed to send welcome email:', emailError);
    }

    console.log(`Email verified for user: ${user.email}`);

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Email verified successfully!',
        token: jwtToken,
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
          subscription_tier: user.subscription_tier,
          email_verified: true,
        },
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('Email verification error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to verify email',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
