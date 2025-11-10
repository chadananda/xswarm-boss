/**
 * User Management (Database Users)
 *
 * IMPORTANT ARCHITECTURE:
 * - Admin user: Configured in config.toml [admin] section (single admin, full access)
 * - Regular users: Stored in Turso database (multiple users, limited permissions)
 *
 * This module handles REGULAR USERS from the database.
 * For admin user operations, load from ProjectConfig.admin
 */

import { createClient } from '@libsql/client';

/**
 * Create Turso client (singleton pattern)
 */
let dbClient = null;

function getDbClient(env) {
  if (!dbClient) {
    dbClient = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN,
    });
  }
  return dbClient;
}

/**
 * Get regular user by ID (database users only, NOT admin)
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 * @returns {Object|null} User record or null if not found
 */
export async function getUserById(userId, env) {
  try {
    const db = getDbClient(env);

    const result = await db.execute({
      sql: 'SELECT * FROM users WHERE id = ?',
      args: [userId],
    });

    if (result.rows.length === 0) {
      return null;
    }

    return formatUserRecord(result.rows[0]);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to query database');
  }
}

/**
 * Get regular user by email (database users only, NOT admin)
 *
 * @param {string} email - User email or xSwarm email
 * @param {Object} env - Environment variables
 * @returns {Object|null} User record or null if not found
 */
export async function getUserByEmail(email, env) {
  try {
    const db = getDbClient(env);

    const result = await db.execute({
      sql: 'SELECT * FROM users WHERE email = ? OR xswarm_email = ?',
      args: [email, email],
    });

    if (result.rows.length === 0) {
      return null;
    }

    return formatUserRecord(result.rows[0]);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to query database');
  }
}

/**
 * Get regular user by phone number (database users only, NOT admin)
 *
 * @param {string} phone - User phone or xSwarm phone (E.164 format)
 * @param {Object} env - Environment variables
 * @returns {Object|null} User record or null if not found
 */
export async function getUserByPhone(phone, env) {
  try {
    const db = getDbClient(env);

    const result = await db.execute({
      sql: 'SELECT * FROM users WHERE user_phone = ? OR xswarm_phone = ?',
      args: [phone, phone],
    });

    if (result.rows.length === 0) {
      return null;
    }

    return formatUserRecord(result.rows[0]);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to query database');
  }
}

/**
 * Get regular user by xSwarm phone number (database users only, NOT admin)
 *
 * @param {string} xswarmPhone - xSwarm phone number (E.164 format)
 * @param {Object} env - Environment variables
 * @returns {Object|null} User record or null if not found
 */
export async function getUserByXswarmPhone(xswarmPhone, env) {
  try {
    const db = getDbClient(env);

    const result = await db.execute({
      sql: 'SELECT * FROM users WHERE xswarm_phone = ?',
      args: [xswarmPhone],
    });

    if (result.rows.length === 0) {
      return null;
    }

    return formatUserRecord(result.rows[0]);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to query database');
  }
}

/**
 * Get regular user by Stripe customer ID (database users only, NOT admin)
 *
 * @param {string} customerId - Stripe customer ID
 * @param {Object} env - Environment variables
 * @returns {Object|null} User record or null if not found
 */
export async function getUserByStripeCustomerId(customerId, env) {
  try {
    const db = getDbClient(env);

    const result = await db.execute({
      sql: 'SELECT * FROM users WHERE stripe_customer_id = ?',
      args: [customerId],
    });

    if (result.rows.length === 0) {
      return null;
    }

    return formatUserRecord(result.rows[0]);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to query database');
  }
}

/**
 * Create a new regular user (database only, NOT for admin)
 *
 * @param {Object} userData - User data
 * @param {Object} env - Environment variables
 * @returns {Object} Created user record
 */
export async function createUser(userData, env) {
  try {
    const db = getDbClient(env);

    const now = new Date().toISOString();

    const result = await db.execute({
      sql: `
        INSERT INTO users (
          id, username, name, email, user_phone,
          xswarm_email, xswarm_phone, subscription_tier,
          persona, wake_word, stripe_customer_id,
          stripe_subscription_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING *
      `,
      args: [
        userData.id || crypto.randomUUID(),
        userData.username,
        userData.name || null,
        userData.email,
        userData.user_phone,
        userData.xswarm_email,
        userData.xswarm_phone || null,
        userData.subscription_tier || 'free',
        userData.persona || 'boss',
        userData.wake_word || null,
        userData.stripe_customer_id || null,
        userData.stripe_subscription_id || null,
        now,
        now,
      ],
    });

    return formatUserRecord(result.rows[0]);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to create user');
  }
}

/**
 * Update regular user subscription tier (database users only, NOT admin)
 *
 * @param {string} userId - User ID
 * @param {string} tier - Subscription tier (free, premium, enterprise)
 * @param {Object} env - Environment variables
 */
export async function updateUserTier(userId, tier, env) {
  try {
    const db = getDbClient(env);
    const now = new Date().toISOString();

    await db.execute({
      sql: 'UPDATE users SET subscription_tier = ?, updated_at = ? WHERE id = ?',
      args: [tier, now, userId],
    });

    console.log(`Updated user ${userId} to tier: ${tier}`);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to update user tier');
  }
}

/**
 * Update regular user phone number (database users only, NOT admin)
 *
 * @param {string} userId - User ID
 * @param {string} xswarmPhone - xSwarm phone number (E.164 format)
 * @param {Object} env - Environment variables
 */
export async function updateUserPhone(userId, xswarmPhone, env) {
  try {
    const db = getDbClient(env);
    const now = new Date().toISOString();

    await db.execute({
      sql: 'UPDATE users SET xswarm_phone = ?, updated_at = ? WHERE id = ?',
      args: [xswarmPhone, now, userId],
    });

    console.log(`Updated user ${userId} phone: ${xswarmPhone}`);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to update user phone');
  }
}

/**
 * Update regular user Stripe customer info (database users only, NOT admin)
 *
 * @param {string} userId - User ID
 * @param {string} customerId - Stripe customer ID
 * @param {string} subscriptionId - Stripe subscription ID (optional)
 * @param {Object} env - Environment variables
 */
export async function updateUserStripeInfo(userId, customerId, subscriptionId, env) {
  try {
    const db = getDbClient(env);
    const now = new Date().toISOString();

    await db.execute({
      sql: `
        UPDATE users
        SET stripe_customer_id = ?,
            stripe_subscription_id = ?,
            updated_at = ?
        WHERE id = ?
      `,
      args: [customerId, subscriptionId || null, now, userId],
    });

    console.log(`Updated user ${userId} Stripe info`);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to update user Stripe info');
  }
}

/**
 * List all regular users (admin operation only)
 *
 * @param {Object} env - Environment variables
 * @param {number} limit - Maximum number of users to return
 * @param {number} offset - Offset for pagination
 * @returns {Array} Array of user records
 */
export async function listUsers(env, limit = 100, offset = 0) {
  try {
    const db = getDbClient(env);

    const result = await db.execute({
      sql: 'SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?',
      args: [limit, offset],
    });

    return result.rows.map(formatUserRecord);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to list users');
  }
}

/**
 * Delete a regular user (admin operation only)
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 */
export async function deleteUser(userId, env) {
  try {
    const db = getDbClient(env);

    await db.execute({
      sql: 'DELETE FROM users WHERE id = ?',
      args: [userId],
    });

    console.log(`Deleted user ${userId}`);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to delete user');
  }
}

/**
 * Format database row into user object
 *
 * @param {Object} row - Database row
 * @returns {Object} Formatted user object
 */
function formatUserRecord(row) {
  return {
    id: row.id,
    username: row.username,
    name: row.name,
    email: row.email,
    user_phone: row.user_phone,
    xswarm_email: row.xswarm_email,
    xswarm_phone: row.xswarm_phone,
    subscription_tier: row.subscription_tier,
    persona: row.persona,
    wake_word: row.wake_word,
    stripe_customer_id: row.stripe_customer_id,
    stripe_subscription_id: row.stripe_subscription_id,
    email_verified: row.email_verified || false,
    email_verification_token: row.email_verification_token,
    email_verification_expires: row.email_verification_expires,
    password_hash: row.password_hash,
    password_reset_token: row.password_reset_token,
    password_reset_expires: row.password_reset_expires,
    jwt_version: row.jwt_version || 0,
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

/**
 * Check if user has permission for a feature based on subscription tier
 *
 * Enhanced version with comprehensive feature checking and usage limits.
 * Integrates with centralized feature definitions from features.js
 *
 * @param {Object} user - User object
 * @param {string} feature - Feature name (voice, sms, email, calendar, teams, buzz, etc.)
 * @param {Object} env - Environment variables (optional, for usage checking)
 * @returns {boolean|Promise<boolean|Object>} True if user has access, or detailed object with usage info
 */
export function userHasFeature(user, feature, env = null) {
  const tier = user.subscription_tier || 'free';

  // Admin tier has access to everything
  if (tier === 'admin') return true;

  // Map legacy feature names to new system
  const legacyMap = {
    voice: 'voice_minutes',
    sms: 'sms_messages',
    email: 'email_daily',
    phone: 'voice_minutes',
    teams: 'team_collaboration',
    buzz: 'buzz_workspace'
  };

  const mappedFeature = legacyMap[feature] || feature;

  // If env provided, do advanced async check with usage limits
  if (env) {
    return userHasFeatureAdvanced(user, mappedFeature, env);
  }

  // Synchronous basic check (backward compatible)
  try {
    // Try to import and use centralized features (sync path)
    const { hasFeature } = require('./features.js');
    return hasFeature(tier, mappedFeature);
  } catch (error) {
    // Fallback to legacy checking if features.js not available
    const tierFeatures = {
      free: ['email', 'email_daily'],
      personal: ['email', 'email_daily', 'voice', 'voice_minutes', 'sms', 'sms_messages', 'phone', 'calendar_access'],
      professional: ['email', 'email_daily', 'voice', 'voice_minutes', 'sms', 'sms_messages', 'phone', 'calendar_access', 'teams', 'team_collaboration', 'buzz', 'buzz_workspace'],
      enterprise: ['email', 'email_daily', 'voice', 'voice_minutes', 'sms', 'sms_messages', 'phone', 'calendar_access', 'teams', 'team_collaboration', 'buzz', 'buzz_workspace', 'enterprise'],
    };

    return tierFeatures[tier]?.includes(mappedFeature) ?? false;
  }
}

/**
 * Advanced feature check with usage limits (async)
 *
 * @param {Object} user - User object
 * @param {string} feature - Feature name
 * @param {Object} env - Environment variables
 * @returns {Promise<boolean|Object>} Access status with usage details
 */
async function userHasFeatureAdvanced(user, feature, env) {
  const tier = user.subscription_tier || 'free';

  try {
    const { hasFeature, checkLimit } = await import('./features.js');

    // Check if feature is available for tier
    const hasAccess = hasFeature(tier, feature);

    if (!hasAccess) {
      return {
        allowed: false,
        reason: 'feature_not_available',
        tier,
        feature
      };
    }

    // Check usage limits for metered features
    const meteredFeatures = ['voice_minutes', 'sms_messages', 'email_daily'];

    if (meteredFeatures.includes(feature)) {
      const { getCurrentUsage } = await import('./usage-tracker.js');
      const usage = await getCurrentUsage(user.id, env);

      const featureMap = {
        voice_minutes: usage.voice_minutes,
        sms_messages: usage.sms_messages,
        email_daily: usage.email_count
      };

      const currentUsage = featureMap[feature] || 0;
      const limitCheck = checkLimit(tier, feature, currentUsage);

      return {
        allowed: limitCheck.allowed,
        usage: currentUsage,
        limit: limitCheck.limit,
        remaining: limitCheck.remaining,
        overage: limitCheck.overage,
        overage_allowed: limitCheck.overage_allowed
      };
    }

    return true;
  } catch (error) {
    console.error('Error checking feature access:', error);
    // Fail open - allow access but log error
    return true;
  }
}

/**
 * Get user by email verification token
 *
 * @param {string} token - Email verification token
 * @param {Object} env - Environment variables
 * @returns {Object|null} User record or null if not found/expired
 */
export async function getUserByVerificationToken(token, env) {
  try {
    const db = getDbClient(env);
    const now = new Date().toISOString();

    const result = await db.execute({
      sql: `
        SELECT * FROM users
        WHERE email_verification_token = ?
        AND email_verification_expires > ?
      `,
      args: [token, now],
    });

    if (result.rows.length === 0) {
      return null;
    }

    return formatUserRecord(result.rows[0]);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to query database');
  }
}

/**
 * Get user by password reset token
 *
 * @param {string} token - Password reset token
 * @param {Object} env - Environment variables
 * @returns {Object|null} User record or null if not found/expired
 */
export async function getUserByResetToken(token, env) {
  try {
    const db = getDbClient(env);
    const now = new Date().toISOString();

    const result = await db.execute({
      sql: `
        SELECT * FROM users
        WHERE password_reset_token = ?
        AND password_reset_expires > ?
      `,
      args: [token, now],
    });

    if (result.rows.length === 0) {
      return null;
    }

    return formatUserRecord(result.rows[0]);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to query database');
  }
}

/**
 * Update user email verification status
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 */
export async function updateEmailVerified(userId, env) {
  try {
    const db = getDbClient(env);
    const now = new Date().toISOString();

    await db.execute({
      sql: `
        UPDATE users
        SET email_verified = TRUE,
            email_verification_token = NULL,
            email_verification_expires = NULL,
            updated_at = ?
        WHERE id = ?
      `,
      args: [now, userId],
    });

    console.log(`Email verified for user ${userId}`);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to update email verification status');
  }
}

/**
 * Update user password hash
 *
 * @param {string} userId - User ID
 * @param {string} passwordHash - New password hash
 * @param {Object} env - Environment variables
 */
export async function updatePasswordHash(userId, passwordHash, env) {
  try {
    const db = getDbClient(env);
    const now = new Date().toISOString();

    await db.execute({
      sql: `
        UPDATE users
        SET password_hash = ?,
            updated_at = ?
        WHERE id = ?
      `,
      args: [passwordHash, now, userId],
    });

    console.log(`Password updated for user ${userId}`);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to update password');
  }
}

/**
 * Set email verification token
 *
 * @param {string} userId - User ID
 * @param {string} token - Verification token
 * @param {string} expires - Expiration timestamp
 * @param {Object} env - Environment variables
 */
export async function setVerificationToken(userId, token, expires, env) {
  try {
    const db = getDbClient(env);
    const now = new Date().toISOString();

    await db.execute({
      sql: `
        UPDATE users
        SET email_verification_token = ?,
            email_verification_expires = ?,
            updated_at = ?
        WHERE id = ?
      `,
      args: [token, expires, now, userId],
    });

    console.log(`Verification token set for user ${userId}`);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to set verification token');
  }
}

/**
 * Set password reset token
 *
 * @param {string} userId - User ID
 * @param {string} token - Reset token
 * @param {string} expires - Expiration timestamp
 * @param {Object} env - Environment variables
 */
export async function setResetToken(userId, token, expires, env) {
  try {
    const db = getDbClient(env);
    const now = new Date().toISOString();

    await db.execute({
      sql: `
        UPDATE users
        SET password_reset_token = ?,
            password_reset_expires = ?,
            updated_at = ?
        WHERE id = ?
      `,
      args: [token, expires, now, userId],
    });

    console.log(`Password reset token set for user ${userId}`);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to set reset token');
  }
}

/**
 * Clear password reset token
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 */
export async function clearResetToken(userId, env) {
  try {
    const db = getDbClient(env);
    const now = new Date().toISOString();

    await db.execute({
      sql: `
        UPDATE users
        SET password_reset_token = NULL,
            password_reset_expires = NULL,
            updated_at = ?
        WHERE id = ?
      `,
      args: [now, userId],
    });

    console.log(`Password reset token cleared for user ${userId}`);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to clear reset token');
  }
}

/**
 * Increment JWT version (invalidates all existing tokens)
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 */
export async function incrementJwtVersion(userId, env) {
  try {
    const db = getDbClient(env);
    const now = new Date().toISOString();

    await db.execute({
      sql: `
        UPDATE users
        SET jwt_version = jwt_version + 1,
            updated_at = ?
        WHERE id = ?
      `,
      args: [now, userId],
    });

    console.log(`JWT version incremented for user ${userId}`);

  } catch (error) {
    console.error('Database error:', error);
    throw new Error('Failed to increment JWT version');
  }
}
