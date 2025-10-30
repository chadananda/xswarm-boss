/**
 * User Login Route
 *
 * POST /auth/login
 * Authenticates user with email and password
 */

import { getUserByEmail } from '../../lib/users.js';
import { verifyPassword } from '../../lib/password.js';
import { generateToken } from '../../lib/jwt.js';

/**
 * Handle user login
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} JSON response with JWT token
 */
export async function handleLogin(request, env) {
  try {
    // Parse request body
    const body = await request.json();
    const { email, password } = body;

    // Validate required fields
    if (!email || !password) {
      return new Response(
        JSON.stringify({
          error: 'Missing required fields: email, password',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Get user by email
    const user = await getUserByEmail(email, env);

    if (!user) {
      // Use generic error message to prevent email enumeration
      return new Response(
        JSON.stringify({
          error: 'Invalid email or password',
        }),
        {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Check if password hash exists
    if (!user.password_hash) {
      return new Response(
        JSON.stringify({
          error: 'Account not configured for password login',
        }),
        {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Verify password
    const passwordValid = await verifyPassword(password, user.password_hash);

    if (!passwordValid) {
      // Use generic error message to prevent user enumeration
      return new Response(
        JSON.stringify({
          error: 'Invalid email or password',
        }),
        {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Check if email is verified
    if (!user.email_verified) {
      return new Response(
        JSON.stringify({
          error: 'Email not verified. Please check your email for verification link.',
        }),
        {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Generate JWT token
    const jwtToken = generateToken(user, env.JWT_SECRET);

    console.log(`User login successful: ${user.email}`);

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Login successful',
        token: jwtToken,
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
          subscription_tier: user.subscription_tier,
          email_verified: user.email_verified,
        },
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('Login error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to login',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
