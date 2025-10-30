/**
 * Email Marketing Scheduler
 *
 * Handles automated sending of marketing email sequences based on user enrollment
 * and campaign schedules. Respects unsubscribe requests and tracks engagement.
 */

import { sendEmail } from './send-email.js';
import { getEmailTemplate } from './marketing-emails.js';
import { createClient } from '@libsql/client';

/**
 * Process pending marketing emails
 *
 * This should be called periodically (e.g., every hour via cron job)
 * to send scheduled marketing emails to enrolled users.
 *
 * @param {Object} env - Environment variables (DB config, SendGrid key)
 * @returns {Promise<Object>} { sent: number, failed: number, errors: Array }
 */
export async function processPendingEmails(env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  const results = {
    sent: 0,
    failed: 0,
    errors: [],
  };

  try {
    // Get pending emails that need to be sent
    const pendingEmails = await db.execute(`
      SELECT * FROM pending_marketing_emails
      ORDER BY scheduled_send_time ASC
      LIMIT 100
    `);

    console.log(`[Email Scheduler] Found ${pendingEmails.rows.length} pending emails`);

    // Send each email
    for (const email of pendingEmails.rows) {
      try {
        await sendMarketingEmail(email, env, db);
        results.sent++;
        console.log(`[Email Scheduler] Sent ${email.email_type} to ${email.email}`);
      } catch (error) {
        results.failed++;
        results.errors.push({
          user_id: email.user_id,
          email: email.email,
          error: error.message,
        });
        console.error(`[Email Scheduler] Failed to send to ${email.email}:`, error);
      }

      // Rate limiting: small delay between sends
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    return results;
  } finally {
    // Close database connection
    db.close();
  }
}

/**
 * Send a single marketing email
 */
async function sendMarketingEmail(emailData, env, db) {
  const {
    subscription_id,
    user_id,
    email,
    name,
    campaign_id,
    campaign_name,
    sequence_id,
    sequence_number,
    email_type,
    subject_line,
    subject_line_variant,
    template_id,
    cta_text,
    cta_url,
    unsubscribe_token,
  } = emailData;

  // Determine which subject line to use (A/B testing)
  const shouldUseVariant = Math.random() < 0.5;
  const subjectLineToUse = (shouldUseVariant && subject_line_variant)
    ? subject_line_variant
    : subject_line;

  // Generate unsubscribe URL
  const unsubscribe_url = `${env.BASE_URL || 'https://xswarm.ai'}/marketing/unsubscribe/${unsubscribe_token}`;

  // Get email template
  const { html, text } = getEmailTemplate(template_id, {
    name,
    email,
    cta_text,
    cta_url,
    unsubscribe_token,
    unsubscribe_url,
    campaign_name,
    email_type,
  });

  // Send email via SendGrid
  const result = await sendEmail(
    {
      to: email,
      from: env.FROM_EMAIL || 'boss@xswarm.ai',
      subject: subjectLineToUse,
      text,
      html,
    },
    env
  );

  // Record the send in database
  const sendId = `send_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  await db.execute({
    sql: `
      INSERT INTO email_sends (
        id,
        subscription_id,
        sequence_id,
        user_id,
        sendgrid_message_id,
        subject_line_used,
        send_status
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
    `,
    args: [
      sendId,
      subscription_id,
      sequence_id,
      user_id,
      result.messageId || null,
      subjectLineToUse,
      'sent',
    ],
  });

  return result;
}

/**
 * Enroll user in appropriate marketing campaign
 *
 * Automatically enrolls user in the right campaign based on their current tier.
 * Should be called when user signs up or changes tier.
 *
 * @param {string} userId - User ID
 * @param {string} currentTier - User's current subscription tier
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} { enrolled: boolean, campaign_id: string }
 */
export async function enrollUserInCampaign(userId, currentTier, env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    // Determine target campaign based on current tier
    const campaignMap = {
      free: 'camp_free_to_secretary',
      ai_secretary: 'camp_secretary_to_pm',
      ai_project_manager: 'camp_pm_to_cto',
    };

    const campaignId = campaignMap[currentTier];

    if (!campaignId) {
      console.log(`[Enrollment] No campaign for tier: ${currentTier}`);
      return { enrolled: false, campaign_id: null };
    }

    // Check if user is already enrolled in this campaign
    const existing = await db.execute({
      sql: 'SELECT id, status FROM user_email_subscriptions WHERE user_id = ? AND campaign_id = ?',
      args: [userId, campaignId],
    });

    if (existing.rows.length > 0) {
      const status = existing.rows[0].status;
      console.log(`[Enrollment] User already enrolled in ${campaignId} with status: ${status}`);

      // Reactivate if they were unsubscribed or paused
      if (status !== 'active') {
        await db.execute({
          sql: 'UPDATE user_email_subscriptions SET status = ? WHERE id = ?',
          args: ['active', existing.rows[0].id],
        });
        console.log(`[Enrollment] Reactivated subscription for user ${userId}`);
      }

      return { enrolled: true, campaign_id: campaignId };
    }

    // Create new subscription
    const subscriptionId = `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const unsubscribeToken = `unsub_${Date.now()}_${Math.random().toString(36).substr(2, 16)}`;

    await db.execute({
      sql: `
        INSERT INTO user_email_subscriptions (
          id,
          user_id,
          campaign_id,
          status,
          unsubscribe_token
        ) VALUES (?, ?, ?, ?, ?)
      `,
      args: [subscriptionId, userId, campaignId, 'active', unsubscribeToken],
    });

    console.log(`[Enrollment] Enrolled user ${userId} in campaign ${campaignId}`);

    return { enrolled: true, campaign_id: campaignId };
  } finally {
    db.close();
  }
}

/**
 * Unsubscribe user from marketing emails
 *
 * @param {string} unsubscribeToken - Unique unsubscribe token
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} { success: boolean, message: string }
 */
export async function unsubscribeUser(unsubscribeToken, env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    // Find subscription by token
    const result = await db.execute({
      sql: 'SELECT id, user_id, campaign_id, status FROM user_email_subscriptions WHERE unsubscribe_token = ?',
      args: [unsubscribeToken],
    });

    if (result.rows.length === 0) {
      return { success: false, message: 'Invalid unsubscribe token' };
    }

    const subscription = result.rows[0];

    if (subscription.status === 'unsubscribed') {
      return { success: true, message: 'Already unsubscribed' };
    }

    // Update subscription status
    await db.execute({
      sql: 'UPDATE user_email_subscriptions SET status = ? WHERE id = ?',
      args: ['unsubscribed', subscription.id],
    });

    console.log(`[Unsubscribe] User ${subscription.user_id} unsubscribed from campaign ${subscription.campaign_id}`);

    return { success: true, message: 'Successfully unsubscribed' };
  } finally {
    db.close();
  }
}

/**
 * Mark subscription as converted (user upgraded)
 *
 * @param {string} userId - User ID
 * @param {string} newTier - New subscription tier they upgraded to
 * @param {Object} env - Environment variables
 * @returns {Promise<void>}
 */
export async function markSubscriptionConverted(userId, newTier, env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    // Mark all active subscriptions for this user as converted
    await db.execute({
      sql: `
        UPDATE user_email_subscriptions
        SET status = ?, converted_at = datetime('now'), converted_to_tier = ?
        WHERE user_id = ? AND status = ?
      `,
      args: ['converted', newTier, userId, 'active'],
    });

    console.log(`[Conversion] Marked user ${userId} as converted to ${newTier}`);

    // Enroll in next tier's campaign
    await enrollUserInCampaign(userId, newTier, env);
  } finally {
    db.close();
  }
}

/**
 * Track email engagement (opens, clicks, bounces)
 *
 * Should be called from SendGrid webhook handlers.
 *
 * @param {string} sendgridMessageId - SendGrid message ID
 * @param {string} eventType - Event type (open, click, bounce, complaint)
 * @param {Object} env - Environment variables
 * @returns {Promise<void>}
 */
export async function trackEmailEngagement(sendgridMessageId, eventType, env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    // Map event types to column names
    const columnMap = {
      open: 'opened_at',
      click: 'clicked_at',
      bounce: 'bounced_at',
      spamreport: 'complained_at',
      unsubscribe: 'unsubscribed_at',
    };

    const column = columnMap[eventType];

    if (!column) {
      console.log(`[Engagement] Unknown event type: ${eventType}`);
      return;
    }

    // Update email_sends record
    await db.execute({
      sql: `
        UPDATE email_sends
        SET ${column} = datetime('now')
        WHERE sendgrid_message_id = ? AND ${column} IS NULL
      `,
      args: [sendgridMessageId],
    });

    console.log(`[Engagement] Tracked ${eventType} for message ${sendgridMessageId}`);

    // If it's an unsubscribe event, also update the subscription
    if (eventType === 'unsubscribe' || eventType === 'spamreport') {
      await db.execute({
        sql: `
          UPDATE user_email_subscriptions
          SET status = 'unsubscribed'
          WHERE id IN (
            SELECT subscription_id FROM email_sends
            WHERE sendgrid_message_id = ?
          )
        `,
        args: [sendgridMessageId],
      });
    }
  } finally {
    db.close();
  }
}

/**
 * Get campaign analytics
 *
 * @param {string} campaignId - Campaign ID (optional, null for all campaigns)
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Campaign performance data
 */
export async function getCampaignAnalytics(campaignId, env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    let query;
    let args = [];

    if (campaignId) {
      query = 'SELECT * FROM campaign_analytics WHERE campaign_id = ?';
      args = [campaignId];
    } else {
      query = 'SELECT * FROM campaign_analytics ORDER BY conversion_rate DESC';
    }

    const result = await db.execute({ sql: query, args });

    return result.rows;
  } finally {
    db.close();
  }
}

/**
 * Get sequence performance analytics
 *
 * @param {string} campaignId - Campaign ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Array>} Sequence performance data
 */
export async function getSequenceAnalytics(campaignId, env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    const result = await db.execute({
      sql: 'SELECT * FROM sequence_analytics WHERE campaign_id = ? ORDER BY sequence_number ASC',
      args: [campaignId],
    });

    return result.rows;
  } finally {
    db.close();
  }
}

/**
 * Batch enroll all eligible users
 *
 * Enrolls all users who are ready for tier upgrade campaigns.
 * Should be run as an admin operation.
 *
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} { enrolled: number, skipped: number }
 */
export async function batchEnrollUsers(env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  const results = {
    enrolled: 0,
    skipped: 0,
  };

  try {
    // Get all users ready for upgrade
    const readyUsers = await db.execute('SELECT * FROM upgrade_ready_users');

    console.log(`[Batch Enrollment] Found ${readyUsers.rows.length} users ready for enrollment`);

    for (const user of readyUsers.rows) {
      try {
        const result = await enrollUserInCampaign(user.user_id, user.current_tier, env);
        if (result.enrolled) {
          results.enrolled++;
        } else {
          results.skipped++;
        }
      } catch (error) {
        console.error(`[Batch Enrollment] Failed to enroll user ${user.user_id}:`, error);
        results.skipped++;
      }
    }

    return results;
  } finally {
    db.close();
  }
}
