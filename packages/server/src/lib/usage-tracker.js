/**
 * Usage Tracking System
 *
 * Tracks voice minutes, SMS messages, and email volume for billing purposes.
 * Calculates overages and generates usage reports.
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
 * Get current billing period for a user
 */
export async function getCurrentBillingPeriod(userId, env) {
  try {
    const db = getDbClient(env);
    const now = new Date();

    // Billing periods run from 1st of month to last day of month
    const periodStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();
    const periodEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59).toISOString();

    return { periodStart, periodEnd };
  } catch (error) {
    console.error('Error calculating billing period:', error);
    throw error;
  }
}

/**
 * Get or create usage record for current billing period
 */
export async function getOrCreateUsageRecord(userId, env) {
  try {
    const db = getDbClient(env);
    const { periodStart, periodEnd } = await getCurrentBillingPeriod(userId, env);

    // Try to get existing record
    const result = await db.execute({
      sql: `
        SELECT * FROM usage_records
        WHERE user_id = ? AND period_start = ?
      `,
      args: [userId, periodStart],
    });

    if (result.rows.length > 0) {
      return formatUsageRecord(result.rows[0]);
    }

    // Create new record
    const id = crypto.randomUUID();
    await db.execute({
      sql: `
        INSERT INTO usage_records (
          id, user_id, period_start, period_end,
          voice_minutes, sms_messages, email_count,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, 0, 0, 0, ?, ?)
      `,
      args: [id, userId, periodStart, periodEnd, new Date().toISOString(), new Date().toISOString()],
    });

    return {
      id,
      user_id: userId,
      period_start: periodStart,
      period_end: periodEnd,
      voice_minutes: 0,
      sms_messages: 0,
      email_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  } catch (error) {
    console.error('Error getting/creating usage record:', error);
    throw error;
  }
}

/**
 * Track voice call usage
 *
 * @param {string} userId - User ID
 * @param {number} minutes - Number of minutes to add
 * @param {Object} env - Environment variables
 */
export async function trackVoiceUsage(userId, minutes, env) {
  try {
    const db = getDbClient(env);
    const { periodStart } = await getCurrentBillingPeriod(userId, env);
    const now = new Date().toISOString();

    await db.execute({
      sql: `
        UPDATE usage_records
        SET voice_minutes = voice_minutes + ?,
            updated_at = ?
        WHERE user_id = ? AND period_start = ?
      `,
      args: [minutes, now, userId, periodStart],
    });

    console.log(`Tracked ${minutes} voice minutes for user ${userId}`);
  } catch (error) {
    console.error('Error tracking voice usage:', error);
    throw error;
  }
}

/**
 * Track SMS usage
 *
 * @param {string} userId - User ID
 * @param {number} count - Number of messages to add (default 1)
 * @param {Object} env - Environment variables
 */
export async function trackSMSUsage(userId, count = 1, env) {
  try {
    const db = getDbClient(env);
    const { periodStart } = await getCurrentBillingPeriod(userId, env);
    const now = new Date().toISOString();

    await db.execute({
      sql: `
        UPDATE usage_records
        SET sms_messages = sms_messages + ?,
            updated_at = ?
        WHERE user_id = ? AND period_start = ?
      `,
      args: [count, now, userId, periodStart],
    });

    console.log(`Tracked ${count} SMS messages for user ${userId}`);
  } catch (error) {
    console.error('Error tracking SMS usage:', error);
    throw error;
  }
}

/**
 * Track email usage
 *
 * @param {string} userId - User ID
 * @param {number} count - Number of emails to add (default 1)
 * @param {Object} env - Environment variables
 */
export async function trackEmailUsage(userId, count = 1, env) {
  try {
    const db = getDbClient(env);
    const { periodStart } = await getCurrentBillingPeriod(userId, env);
    const now = new Date().toISOString();

    await db.execute({
      sql: `
        UPDATE usage_records
        SET email_count = email_count + ?,
            updated_at = ?
        WHERE user_id = ? AND period_start = ?
      `,
      args: [count, now, userId, periodStart],
    });

    console.log(`Tracked ${count} emails for user ${userId}`);
  } catch (error) {
    console.error('Error tracking email usage:', error);
    throw error;
  }
}

/**
 * Get usage for current billing period
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 * @returns {Object} Usage record with calculated overages
 */
export async function getCurrentUsage(userId, env) {
  try {
    const record = await getOrCreateUsageRecord(userId, env);
    const user = await getUserById(userId, env);

    const tier = user.subscription_tier;
    const limits = getSubscriptionLimits(tier);

    // Calculate overages
    const voiceOverage = Math.max(0, record.voice_minutes - limits.voice_minutes);
    const smsOverage = Math.max(0, record.sms_messages - limits.sms_messages);

    // Calculate costs
    const voiceOverageCost = voiceOverage * 0.013; // $0.013 per minute
    const smsOverageCost = smsOverage * 0.0075; // $0.0075 per message
    const totalOverageCost = voiceOverageCost + smsOverageCost;

    return {
      ...record,
      limits,
      overages: {
        voice_minutes: voiceOverage,
        sms_messages: smsOverage,
      },
      costs: {
        voice_overage: voiceOverageCost,
        sms_overage: smsOverageCost,
        total_overage: totalOverageCost,
      },
      usage_percentages: {
        voice: limits.voice_minutes > 0 ? (record.voice_minutes / limits.voice_minutes) * 100 : 0,
        sms: limits.sms_messages > 0 ? (record.sms_messages / limits.sms_messages) * 100 : 0,
      },
    };
  } catch (error) {
    console.error('Error getting current usage:', error);
    throw error;
  }
}

/**
 * Get usage history for a user
 *
 * @param {string} userId - User ID
 * @param {number} months - Number of months to retrieve (default 6)
 * @param {Object} env - Environment variables
 * @returns {Array} Array of usage records
 */
export async function getUsageHistory(userId, months = 6, env) {
  try {
    const db = getDbClient(env);

    const result = await db.execute({
      sql: `
        SELECT * FROM usage_records
        WHERE user_id = ?
        ORDER BY period_start DESC
        LIMIT ?
      `,
      args: [userId, months],
    });

    return result.rows.map(formatUsageRecord);
  } catch (error) {
    console.error('Error getting usage history:', error);
    throw error;
  }
}

/**
 * Get subscription tier limits
 */
function getSubscriptionLimits(tier) {
  const limits = {
    ai_buddy: {
      voice_minutes: 0,
      sms_messages: 0,
      email_limit: 100, // per day
      has_voice: false,
      has_sms: false,
    },
    ai_secretary: {
      voice_minutes: 100,
      sms_messages: 100,
      email_limit: -1, // unlimited
      has_voice: true,
      has_sms: true,
    },
    ai_project_manager: {
      voice_minutes: 500,
      sms_messages: 500,
      email_limit: -1, // unlimited
      has_voice: true,
      has_sms: true,
      has_teams: true,
      has_buzz: true,
    },
    ai_cto: {
      voice_minutes: -1, // unlimited
      sms_messages: -1, // unlimited
      email_limit: -1, // unlimited
      has_voice: true,
      has_sms: true,
      has_teams: true,
      has_buzz: true,
      has_enterprise: true,
    },
    admin: {
      voice_minutes: -1,
      sms_messages: -1,
      email_limit: -1,
      has_voice: true,
      has_sms: true,
      has_teams: true,
      has_buzz: true,
      has_enterprise: true,
    },
  };

  return limits[tier] || limits.ai_buddy;
}

/**
 * Check if user can perform action based on usage limits
 *
 * @param {string} userId - User ID
 * @param {string} action - Action type (voice, sms, email)
 * @param {Object} env - Environment variables
 * @returns {Object} { allowed: boolean, reason?: string }
 */
export async function checkUsageLimit(userId, action, env) {
  try {
    const usage = await getCurrentUsage(userId, env);
    const limits = usage.limits;

    switch (action) {
      case 'voice':
        if (!limits.has_voice) {
          return { allowed: false, reason: 'Voice features not available on your plan' };
        }
        if (limits.voice_minutes === -1) {
          return { allowed: true }; // unlimited
        }
        // Allow overages, they will be charged
        return { allowed: true };

      case 'sms':
        if (!limits.has_sms) {
          return { allowed: false, reason: 'SMS features not available on your plan' };
        }
        if (limits.sms_messages === -1) {
          return { allowed: true }; // unlimited
        }
        // Allow overages, they will be charged
        return { allowed: true };

      case 'email':
        if (limits.email_limit === -1) {
          return { allowed: true }; // unlimited
        }
        if (usage.email_count >= limits.email_limit) {
          return { allowed: false, reason: 'Daily email limit reached' };
        }
        return { allowed: true };

      default:
        return { allowed: false, reason: 'Unknown action type' };
    }
  } catch (error) {
    console.error('Error checking usage limit:', error);
    return { allowed: false, reason: 'Error checking usage limit' };
  }
}

/**
 * Format usage record from database row
 */
function formatUsageRecord(row) {
  return {
    id: row.id,
    user_id: row.user_id,
    period_start: row.period_start,
    period_end: row.period_end,
    voice_minutes: row.voice_minutes || 0,
    sms_messages: row.sms_messages || 0,
    email_count: row.email_count || 0,
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

/**
 * Helper to get user by ID (imported from users.js)
 */
async function getUserById(userId, env) {
  const { getUserById: getUser } = await import('./users.js');
  return await getUser(userId, env);
}

/**
 * Reset usage for new billing period (called by cron job)
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 */
export async function resetUsageForNewPeriod(userId, env) {
  try {
    // This will create a new record for the current period
    await getOrCreateUsageRecord(userId, env);
    console.log(`Reset usage for user ${userId} for new billing period`);
  } catch (error) {
    console.error('Error resetting usage:', error);
    throw error;
  }
}
