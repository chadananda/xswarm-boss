/**
 * Identity API - User Identity & Authentication for Rust Client
 *
 * The Rust client connects to these endpoints to:
 * 1. Get current user identity
 * 2. Validate authentication tokens
 * 3. Fetch user permissions and limits
 *
 * Architecture:
 * - Server owns all user data (libsql → Turso)
 * - Client is stateless regarding user identity
 * - Client caches identity during session
 */

import { loadConfig } from '../config/loader.js';

/**
 * GET /api/identity
 * Returns the current user's identity and permissions
 *
 * For now, returns the admin user from config.toml
 * TODO: Support multiple users via database query based on auth token
 */
export async function handleGetIdentity(request, env) {
  try {
    // Get auth token from Authorization header
    const authHeader = request.headers.get('Authorization');
    let authToken = null;

    if (authHeader && authHeader.startsWith('Bearer ')) {
      authToken = authHeader.substring(7);
    }

    // Load configuration
    const config = await loadConfig(env);

    // For now, we only support the admin user from config.toml
    // TODO: Query database for user based on auth token
    const adminUser = config.admin;

    if (!adminUser) {
      return new Response(JSON.stringify({
        error: 'No user configuration found',
        message: 'Admin user not configured in config.toml',
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Map admin user to identity format
    const identity = {
      id: 'admin-' + adminUser.username,
      username: adminUser.username,
      name: adminUser.name,
      email: adminUser.email,
      user_phone: adminUser.phone,
      xswarm_email: adminUser.xswarm_email,
      xswarm_phone: adminUser.xswarm_phone,
      subscription_tier: adminUser.subscription_tier || 'admin',
      persona: adminUser.persona || 'boss',
      wake_word: adminUser.wake_word || 'hey boss',

      // Admin permissions (full access)
      can_use_voice: true,
      can_use_sms: true,
      can_use_email: true,
      can_provision_numbers: adminUser.can_provision_numbers !== false,

      // Admin has unlimited usage
      voice_minutes_remaining: null, // null = unlimited
      sms_messages_remaining: null,  // null = unlimited

      created_at: new Date().toISOString(),
      updated_at: null,
    };

    console.log('Identity request:', {
      user_id: identity.id,
      username: identity.username,
      tier: identity.subscription_tier,
      has_auth: !!authToken,
    });

    return new Response(JSON.stringify(identity), {
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'private, max-age=300', // Cache for 5 minutes
      },
    });

  } catch (error) {
    console.error('Error handling identity request:', error);

    return new Response(JSON.stringify({
      error: 'Internal Server Error',
      message: error.message,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * POST /api/auth/validate
 * Validates an authentication token
 *
 * For now, accepts any token (development mode)
 * TODO: Validate against database or JWT signing
 */
export async function handleAuthValidate(request, env) {
  try {
    // Get auth token from Authorization header
    const authHeader = request.headers.get('Authorization');

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return new Response(JSON.stringify({
        error: 'Unauthorized',
        message: 'Missing or invalid Authorization header',
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const authToken = authHeader.substring(7);

    // For development, accept any non-empty token
    // TODO: Validate against database or verify JWT signature
    if (!authToken || authToken.length < 8) {
      return new Response(JSON.stringify({
        error: 'Unauthorized',
        message: 'Invalid authentication token',
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    console.log('Auth validation:', {
      token_length: authToken.length,
      valid: true,
    });

    return new Response(JSON.stringify({
      valid: true,
      message: 'Authentication token is valid',
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error validating auth token:', error);

    return new Response(JSON.stringify({
      error: 'Internal Server Error',
      message: error.message,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
