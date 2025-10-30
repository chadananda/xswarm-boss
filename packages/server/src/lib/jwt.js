/**
 * JWT Token Generation and Verification
 *
 * Uses jsonwebtoken library for JWT operations
 */

import jwt from 'jsonwebtoken';

// Token expiration times
const AUTH_TOKEN_EXPIRY = '7d'; // 7 days for authentication
const VERIFICATION_TOKEN_EXPIRY = 24 * 60 * 60 * 1000; // 24 hours in milliseconds
const RESET_TOKEN_EXPIRY = 60 * 60 * 1000; // 1 hour in milliseconds

/**
 * Generate JWT authentication token
 *
 * @param {Object} user - User object
 * @param {string} jwtSecret - JWT secret from environment
 * @returns {string} JWT token
 */
export function generateToken(user, jwtSecret) {
  if (!jwtSecret) {
    throw new Error('JWT_SECRET not configured');
  }

  const payload = {
    userId: user.id,
    email: user.email,
    tier: user.subscription_tier || 'free',
    jwtVersion: user.jwt_version || 0,
  };

  return jwt.sign(payload, jwtSecret, {
    expiresIn: AUTH_TOKEN_EXPIRY,
    issuer: 'xswarm-api',
    audience: 'xswarm-users',
  });
}

/**
 * Verify and decode JWT token
 *
 * @param {string} token - JWT token to verify
 * @param {string} jwtSecret - JWT secret from environment
 * @returns {Object} Decoded token payload
 * @throws {Error} If token is invalid or expired
 */
export function verifyToken(token, jwtSecret) {
  if (!jwtSecret) {
    throw new Error('JWT_SECRET not configured');
  }

  try {
    return jwt.verify(token, jwtSecret, {
      issuer: 'xswarm-api',
      audience: 'xswarm-users',
    });
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      throw new Error('Token has expired');
    }
    if (error.name === 'JsonWebTokenError') {
      throw new Error('Invalid token');
    }
    throw error;
  }
}

/**
 * Generate random email verification token
 *
 * @returns {Object} { token: string, expires: string }
 */
export function generateEmailVerificationToken() {
  const token = generateSecureToken(32);
  const expires = new Date(Date.now() + VERIFICATION_TOKEN_EXPIRY).toISOString();

  return { token, expires };
}

/**
 * Generate random password reset token
 *
 * @returns {Object} { token: string, expires: string }
 */
export function generatePasswordResetToken() {
  const token = generateSecureToken(32);
  const expires = new Date(Date.now() + RESET_TOKEN_EXPIRY).toISOString();

  return { token, expires };
}

/**
 * Generate cryptographically secure random token
 *
 * @param {number} length - Length of token in bytes
 * @returns {string} URL-safe base64 token
 */
function generateSecureToken(length = 32) {
  const bytes = crypto.getRandomValues(new Uint8Array(length));
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

/**
 * Extract JWT token from Authorization header
 *
 * @param {Request} request - Fetch API request
 * @returns {string|null} JWT token or null if not present
 */
export function extractTokenFromHeader(request) {
  const authHeader = request.headers.get('Authorization');

  if (!authHeader) {
    return null;
  }

  // Support both "Bearer token" and "token" formats
  if (authHeader.startsWith('Bearer ')) {
    return authHeader.substring(7);
  }

  return authHeader;
}
