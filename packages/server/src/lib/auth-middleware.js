/**
 * Authentication Middleware
 *
 * Provides JWT authentication for protected routes
 */

import { verifyToken, extractTokenFromHeader } from './jwt.js';
import { getUserById } from './users.js';

/**
 * Require authentication (returns user or throws error)
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Authenticated user object
 * @throws {Error} If authentication fails
 */
export async function requireAuth(request, env) {
  // Extract JWT token from Authorization header
  const token = extractTokenFromHeader(request);

  if (!token) {
    throw new AuthError('Authentication required', 401);
  }

  try {
    // Verify JWT token
    const decoded = verifyToken(token, env.JWT_SECRET);

    // Get user from database
    const user = await getUserById(decoded.userId, env);

    if (!user) {
      throw new AuthError('User not found', 401);
    }

    // Check if email is verified
    if (!user.email_verified) {
      throw new AuthError('Email not verified', 403);
    }

    // Check JWT version (for logout/token invalidation)
    if (user.jwt_version !== decoded.jwtVersion) {
      throw new AuthError('Token has been invalidated', 401);
    }

    // Return user object (without sensitive fields)
    return sanitizeUser(user);

  } catch (error) {
    if (error instanceof AuthError) {
      throw error;
    }

    // Handle JWT verification errors
    if (error.message === 'Token has expired') {
      throw new AuthError('Token has expired', 401);
    }

    if (error.message === 'Invalid token') {
      throw new AuthError('Invalid token', 401);
    }

    console.error('Authentication error:', error);
    throw new AuthError('Authentication failed', 401);
  }
}

/**
 * Optional authentication (returns user or null)
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Object|null>} User object or null
 */
export async function optionalAuth(request, env) {
  try {
    return await requireAuth(request, env);
  } catch (error) {
    // Return null if authentication fails (optional auth)
    return null;
  }
}

/**
 * Remove sensitive fields from user object
 *
 * @param {Object} user - User object from database
 * @returns {Object} Sanitized user object
 */
function sanitizeUser(user) {
  const {
    password_hash,
    email_verification_token,
    email_verification_expires,
    password_reset_token,
    password_reset_expires,
    ...safeUser
  } = user;

  return safeUser;
}

/**
 * Custom authentication error class
 */
export class AuthError extends Error {
  constructor(message, statusCode = 401) {
    super(message);
    this.name = 'AuthError';
    this.statusCode = statusCode;
  }
}

/**
 * Create JSON error response from AuthError
 *
 * @param {AuthError} error - Authentication error
 * @returns {Response} JSON error response
 */
export function createAuthErrorResponse(error) {
  return new Response(
    JSON.stringify({
      error: error.message,
    }),
    {
      status: error.statusCode || 401,
      headers: { 'Content-Type': 'application/json' },
    }
  );
}
