/**
 * Email Management System
 *
 * Unified interface for email operations with Gmail OAuth,
 * AI summarization, and natural language queries
 */

import { GmailClient } from './gmail-client.js';
import { EmailSummarization } from './summarization.js';
import { EmailQueries } from './queries.js';
import { getUserById } from '../users.js';
import { createClient } from '@libsql/client';

export class EmailSystem {
  constructor(env) {
    this.env = env;
    this.gmail = new GmailClient(env);
    this.summarization = new EmailSummarization(env);
    this.queries = new EmailQueries(env);

    this.db = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN,
    });
  }

  /**
   * Get Gmail OAuth authorization URL
   *
   * @param {string} userId - User ID
   * @param {string} tier - Subscription tier
   * @returns {Object} Auth URL and permissions
   */
  async getGmailAuthUrl(userId, tier) {
    // Determine permissions based on tier
    const permissions = this.getPermissionsForTier(tier);

    const authUrl = this.gmail.getAuthUrl(userId, permissions);

    return {
      authUrl,
      permissions,
      tier
    };
  }

  /**
   * Handle Gmail OAuth callback
   *
   * @param {string} code - Authorization code
   * @param {string} state - State parameter (contains userId and permissions)
   * @returns {Object} Connection result
   */
  async handleGmailCallback(code, state) {
    const stateData = JSON.parse(state);
    const { userId, permissions } = stateData;

    // Exchange code for tokens
    const tokens = await this.gmail.exchangeCodeForTokens(code);

    // Get user's Gmail profile
    const profile = await this.gmail.getUserProfile(tokens.access_token);

    // Store tokens
    await this.gmail.storeTokens(userId, tokens, permissions, profile.emailAddress);

    return {
      success: true,
      message: 'Gmail connected successfully',
      email: profile.emailAddress,
      permissions
    };
  }

  /**
   * Query emails with natural language
   *
   * @param {string} userId - User ID
   * @param {string} query - Natural language query
   * @param {Object} options - Query options
   * @returns {Object} Query results
   */
  async queryEmails(userId, query, options = {}) {
    return await this.queries.processQuery(userId, query, options);
  }

  /**
   * Get email briefing
   *
   * @param {string} userId - User ID
   * @param {string} timeframe - Timeframe (24h, 7d, etc.)
   * @returns {Object} Email briefing
   */
  async getEmailBriefing(userId, timeframe = '24h') {
    // Convert timeframe to Gmail query
    const hoursMap = {
      '24h': 1,
      '48h': 2,
      '7d': 7,
      '30d': 30
    };

    const days = hoursMap[timeframe] || 1;
    const date = new Date();
    date.setDate(date.getDate() - days);
    const dateStr = date.toISOString().split('T')[0];

    // Get unread emails from timeframe
    const unreadEmails = await this.gmail.getMessages(userId, {
      query: `is:unread after:${dateStr}`,
      maxResults: 50
    });

    // Get important emails from timeframe
    const importantEmails = await this.gmail.getMessages(userId, {
      query: `is:important after:${dateStr}`,
      maxResults: 20
    });

    // Summarize top emails
    const topEmails = unreadEmails
      .sort((a, b) => {
        // Sort by importance score (would be calculated)
        const scoreA = a.isImportant ? 1 : 0.5;
        const scoreB = b.isImportant ? 1 : 0.5;
        return scoreB - scoreA;
      })
      .slice(0, 10);

    const summaries = await this.summarization.summarizeMultiple(topEmails);

    // Combine emails with their summaries
    const briefingEmails = topEmails.map((email, index) => ({
      ...email,
      summary: summaries[index]
    }));

    return {
      timeframe,
      stats: {
        totalUnread: unreadEmails.length,
        totalImportant: importantEmails.length,
        needsResponse: briefingEmails.filter(e =>
          e.summary.actionItems.length > 0
        ).length
      },
      topEmails: briefingEmails,
      actionItems: briefingEmails.flatMap(e =>
        e.summary.actionItems.map(item => ({
          email: { subject: e.subject, from: e.from },
          action: item
        }))
      ).slice(0, 10)
    };
  }

  /**
   * Compose and send email (Personal tier+)
   *
   * @param {string} userId - User ID
   * @param {Object} emailData - Email data
   * @returns {Object} Send result
   */
  async composeEmail(userId, emailData) {
    // Check user tier
    const user = await getUserById(userId, this.env);
    const tier = user.subscription_tier || 'free';

    if (!['personal', 'professional', 'enterprise', 'admin'].includes(tier)) {
      throw new Error('Email composition requires Personal tier or higher');
    }

    // Send email via Gmail
    const result = await this.gmail.sendEmail(userId, emailData);

    return {
      success: true,
      messageId: result.id,
      threadId: result.threadId
    };
  }

  /**
   * Summarize specific email
   *
   * @param {string} userId - User ID
   * @param {string} emailId - Gmail message ID
   * @returns {Object} Email summary
   */
  async summarizeEmail(userId, emailId) {
    // Get email
    const email = await this.gmail.getMessage(userId, emailId);

    // Summarize
    const summary = await this.summarization.summarizeEmail(email);

    // Store summary in database
    await this.storeSummary(userId, emailId, summary);

    return {
      email: {
        id: email.id,
        subject: email.subject,
        from: email.from,
        date: email.date
      },
      ...summary
    };
  }

  /**
   * Store email summary in database
   */
  async storeSummary(userId, emailId, summary) {
    try {
      // First get the cache ID for this email
      const cacheResult = await this.db.execute({
        sql: `SELECT id FROM email_cache WHERE user_id = ? AND provider_message_id = ? AND provider = 'gmail'`,
        args: [userId, emailId]
      });

      if (cacheResult.rows.length === 0) {
        console.warn('Email not in cache, skipping summary storage');
        return;
      }

      const cacheId = cacheResult.rows[0].id;

      await this.db.execute({
        sql: `
          INSERT INTO email_summaries (
            user_id, email_id, summary, importance_score,
            action_items, key_points, sentiment, reading_time_minutes
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
          ON CONFLICT (user_id, email_id) DO UPDATE SET
            summary = EXCLUDED.summary,
            importance_score = EXCLUDED.importance_score,
            action_items = EXCLUDED.action_items,
            key_points = EXCLUDED.key_points,
            sentiment = EXCLUDED.sentiment,
            reading_time_minutes = EXCLUDED.reading_time_minutes
        `,
        args: [
          userId,
          cacheId,
          summary.summary,
          summary.importance,
          JSON.stringify(summary.actionItems),
          JSON.stringify(summary.keyPoints),
          summary.sentiment,
          summary.readingTime
        ]
      });
    } catch (error) {
      console.error('Failed to store summary:', error);
      // Don't throw - summary storage failure shouldn't break the operation
    }
  }

  /**
   * Get permissions for user tier
   */
  getPermissionsForTier(tier) {
    const tierPermissions = {
      free: ['readonly'],
      personal: ['readonly', 'compose', 'send'],
      professional: ['readonly', 'compose', 'send', 'modify'],
      enterprise: ['readonly', 'compose', 'send', 'modify'],
      admin: ['readonly', 'compose', 'send', 'modify']
    };

    return tierPermissions[tier] || ['readonly'];
  }

  /**
   * Check if user has Gmail connected
   *
   * @param {string} userId - User ID
   * @returns {Object|null} Integration info or null
   */
  async getIntegrationStatus(userId) {
    const integration = await this.gmail.getStoredTokens(userId);

    if (!integration) {
      return null;
    }

    return {
      connected: true,
      email: integration.email_address,
      permissions: JSON.parse(integration.permissions),
      lastSync: integration.last_sync,
      syncEnabled: integration.sync_enabled
    };
  }

  /**
   * Disconnect Gmail integration
   *
   * @param {string} userId - User ID
   */
  async disconnectGmail(userId) {
    await this.db.execute({
      sql: `DELETE FROM email_integrations WHERE user_id = ? AND provider = 'gmail'`,
      args: [userId]
    });

    // Also delete cached emails for privacy
    await this.db.execute({
      sql: `DELETE FROM email_cache WHERE user_id = ? AND provider = 'gmail'`,
      args: [userId]
    });

    return { success: true, message: 'Gmail disconnected successfully' };
  }
}
