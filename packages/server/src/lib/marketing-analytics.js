/**
 * Marketing Analytics
 *
 * Provides comprehensive analytics and reporting for email marketing campaigns.
 * Tracks conversions, engagement, A/B test results, and ROI.
 */

import { createClient } from '@libsql/client';

/**
 * Get overview dashboard stats
 *
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Dashboard statistics
 */
export async function getDashboardStats(env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    // Get overall campaign stats
    const campaigns = await db.execute(`
      SELECT
        COUNT(DISTINCT campaign_id) as total_campaigns,
        COUNT(DISTINCT CASE WHEN active = TRUE THEN campaign_id END) as active_campaigns
      FROM email_campaigns
    `);

    // Get subscriber stats
    const subscribers = await db.execute(`
      SELECT
        COUNT(*) as total_subscriptions,
        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_subscriptions,
        COUNT(CASE WHEN status = 'converted' THEN 1 END) as total_conversions,
        COUNT(CASE WHEN status = 'unsubscribed' THEN 1 END) as total_unsubscribes
      FROM user_email_subscriptions
    `);

    // Get email send stats
    const sends = await db.execute(`
      SELECT
        COUNT(*) as total_sends,
        COUNT(CASE WHEN opened_at IS NOT NULL THEN 1 END) as total_opens,
        COUNT(CASE WHEN clicked_at IS NOT NULL THEN 1 END) as total_clicks,
        COUNT(CASE WHEN bounced_at IS NOT NULL THEN 1 END) as total_bounces,
        COUNT(CASE WHEN complained_at IS NOT NULL THEN 1 END) as total_complaints,
        ROUND(
          CAST(COUNT(CASE WHEN opened_at IS NOT NULL THEN 1 END) AS FLOAT) /
          NULLIF(COUNT(*), 0) * 100,
          2
        ) as overall_open_rate,
        ROUND(
          CAST(COUNT(CASE WHEN clicked_at IS NOT NULL THEN 1 END) AS FLOAT) /
          NULLIF(COUNT(*), 0) * 100,
          2
        ) as overall_click_rate
      FROM email_sends
    `);

    // Get recent performance (last 30 days)
    const recent = await db.execute(`
      SELECT
        COUNT(*) as sends_last_30_days,
        COUNT(CASE WHEN opened_at IS NOT NULL THEN 1 END) as opens_last_30_days,
        COUNT(CASE WHEN clicked_at IS NOT NULL THEN 1 END) as clicks_last_30_days
      FROM email_sends
      WHERE sent_at >= datetime('now', '-30 days')
    `);

    return {
      campaigns: campaigns.rows[0],
      subscribers: subscribers.rows[0],
      sends: sends.rows[0],
      recent: recent.rows[0],
    };
  } finally {
    db.close();
  }
}

/**
 * Get detailed campaign performance
 *
 * @param {string} campaignId - Campaign ID (optional)
 * @param {Object} env - Environment variables
 * @returns {Promise<Array>} Campaign performance data
 */
export async function getCampaignPerformance(campaignId, env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    let query = 'SELECT * FROM campaign_analytics';
    let args = [];

    if (campaignId) {
      query += ' WHERE campaign_id = ?';
      args = [campaignId];
    } else {
      query += ' ORDER BY conversion_rate DESC';
    }

    const result = await db.execute({ sql: query, args });

    return result.rows;
  } finally {
    db.close();
  }
}

/**
 * Get email sequence performance
 *
 * Shows which emails in a sequence perform best.
 *
 * @param {string} campaignId - Campaign ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Array>} Sequence performance data
 */
export async function getSequencePerformance(campaignId, env) {
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
 * Get A/B test results for subject lines
 *
 * @param {string} campaignId - Campaign ID (optional)
 * @param {Object} env - Environment variables
 * @returns {Promise<Array>} A/B test results
 */
export async function getABTestResults(campaignId, env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    let query = `
      SELECT
        seq.campaign_id,
        c.name as campaign_name,
        seq.sequence_number,
        seq.email_type,
        seq.subject_line as variant_a,
        seq.subject_line_variant as variant_b,
        COUNT(CASE WHEN es.subject_line_used = seq.subject_line THEN 1 END) as variant_a_sends,
        COUNT(CASE WHEN es.subject_line_used = seq.subject_line_variant THEN 1 END) as variant_b_sends,
        COUNT(CASE WHEN es.subject_line_used = seq.subject_line AND es.opened_at IS NOT NULL THEN 1 END) as variant_a_opens,
        COUNT(CASE WHEN es.subject_line_used = seq.subject_line_variant AND es.opened_at IS NOT NULL THEN 1 END) as variant_b_opens,
        ROUND(
          CAST(COUNT(CASE WHEN es.subject_line_used = seq.subject_line AND es.opened_at IS NOT NULL THEN 1 END) AS FLOAT) /
          NULLIF(COUNT(CASE WHEN es.subject_line_used = seq.subject_line THEN 1 END), 0) * 100,
          2
        ) as variant_a_open_rate,
        ROUND(
          CAST(COUNT(CASE WHEN es.subject_line_used = seq.subject_line_variant AND es.opened_at IS NOT NULL THEN 1 END) AS FLOAT) /
          NULLIF(COUNT(CASE WHEN es.subject_line_used = seq.subject_line_variant THEN 1 END), 0) * 100,
          2
        ) as variant_b_open_rate
      FROM email_sequences seq
      JOIN email_campaigns c ON seq.campaign_id = c.id
      LEFT JOIN email_sends es ON seq.id = es.sequence_id
      WHERE seq.subject_line_variant IS NOT NULL
    `;

    let args = [];

    if (campaignId) {
      query += ' AND seq.campaign_id = ?';
      args = [campaignId];
    }

    query += `
      GROUP BY seq.campaign_id, c.name, seq.sequence_number, seq.email_type, seq.subject_line, seq.subject_line_variant
      ORDER BY seq.campaign_id, seq.sequence_number
    `;

    const result = await db.execute({ sql: query, args });

    return result.rows;
  } finally {
    db.close();
  }
}

/**
 * Get conversion funnel data
 *
 * Shows the progression of users through email sequences.
 *
 * @param {string} campaignId - Campaign ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Funnel data
 */
export async function getConversionFunnel(campaignId, env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    // Get funnel stages
    const funnel = await db.execute({
      sql: `
        SELECT
          seq.sequence_number,
          seq.email_type,
          seq.subject_line,
          COUNT(DISTINCT es.user_id) as users_reached,
          COUNT(DISTINCT CASE WHEN es.opened_at IS NOT NULL THEN es.user_id END) as users_opened,
          COUNT(DISTINCT CASE WHEN es.clicked_at IS NOT NULL THEN es.user_id END) as users_clicked,
          ROUND(
            CAST(COUNT(DISTINCT CASE WHEN es.opened_at IS NOT NULL THEN es.user_id END) AS FLOAT) /
            NULLIF(COUNT(DISTINCT es.user_id), 0) * 100,
            2
          ) as open_rate,
          ROUND(
            CAST(COUNT(DISTINCT CASE WHEN es.clicked_at IS NOT NULL THEN es.user_id END) AS FLOAT) /
            NULLIF(COUNT(DISTINCT es.user_id), 0) * 100,
            2
          ) as click_rate
        FROM email_sequences seq
        LEFT JOIN email_sends es ON seq.id = es.sequence_id
        WHERE seq.campaign_id = ?
        GROUP BY seq.sequence_number, seq.email_type, seq.subject_line
        ORDER BY seq.sequence_number ASC
      `,
      args: [campaignId],
    });

    // Get total enrolled and converted
    const summary = await db.execute({
      sql: `
        SELECT
          COUNT(*) as total_enrolled,
          COUNT(CASE WHEN status = 'converted' THEN 1 END) as total_converted,
          ROUND(
            CAST(COUNT(CASE WHEN status = 'converted' THEN 1 END) AS FLOAT) /
            NULLIF(COUNT(*), 0) * 100,
            2
          ) as conversion_rate
        FROM user_email_subscriptions
        WHERE campaign_id = ?
      `,
      args: [campaignId],
    });

    return {
      campaign_id: campaignId,
      summary: summary.rows[0],
      funnel: funnel.rows,
    };
  } finally {
    db.close();
  }
}

/**
 * Get revenue attribution
 *
 * Estimates revenue generated from marketing campaigns.
 *
 * @param {string} campaignId - Campaign ID (optional)
 * @param {Object} env - Environment variables
 * @returns {Promise<Array>} Revenue data
 */
export async function getRevenueAttribution(campaignId, env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    // Tier pricing (monthly)
    const tierPricing = {
      ai_secretary: 49,
      ai_project_manager: 149,
      ai_cto: 499,
    };

    let query = `
      SELECT
        c.id as campaign_id,
        c.name as campaign_name,
        c.from_tier,
        c.to_tier,
        COUNT(CASE WHEN sub.status = 'converted' THEN 1 END) as conversions,
        sub.converted_to_tier
      FROM email_campaigns c
      LEFT JOIN user_email_subscriptions sub ON c.id = sub.campaign_id
    `;

    let args = [];

    if (campaignId) {
      query += ' WHERE c.id = ?';
      args = [campaignId];
    }

    query += `
      GROUP BY c.id, c.name, c.from_tier, c.to_tier, sub.converted_to_tier
    `;

    const result = await db.execute({ sql: query, args });

    // Calculate revenue for each campaign
    const revenueData = result.rows.map(row => {
      const conversions = row.conversions || 0;
      const toTierPrice = tierPricing[row.to_tier] || 0;
      const fromTierPrice = tierPricing[row.from_tier] || 0;

      // Revenue = (new tier price - old tier price) × conversions
      const monthlyRevenue = (toTierPrice - fromTierPrice) * conversions;

      // Assume 12-month average customer lifetime
      const estimatedLTV = monthlyRevenue * 12;

      return {
        campaign_id: row.campaign_id,
        campaign_name: row.campaign_name,
        from_tier: row.from_tier,
        to_tier: row.to_tier,
        conversions,
        monthly_revenue: monthlyRevenue,
        estimated_annual_revenue: estimatedLTV,
      };
    });

    return revenueData;
  } finally {
    db.close();
  }
}

/**
 * Get engagement timeline
 *
 * Shows email engagement over time.
 *
 * @param {string} campaignId - Campaign ID (optional)
 * @param {number} days - Number of days to look back (default: 30)
 * @param {Object} env - Environment variables
 * @returns {Promise<Array>} Timeline data
 */
export async function getEngagementTimeline(campaignId, days, env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    const lookbackDays = days || 30;

    let query = `
      SELECT
        date(sent_at) as date,
        COUNT(*) as sends,
        COUNT(CASE WHEN opened_at IS NOT NULL THEN 1 END) as opens,
        COUNT(CASE WHEN clicked_at IS NOT NULL THEN 1 END) as clicks,
        ROUND(
          CAST(COUNT(CASE WHEN opened_at IS NOT NULL THEN 1 END) AS FLOAT) /
          NULLIF(COUNT(*), 0) * 100,
          2
        ) as open_rate,
        ROUND(
          CAST(COUNT(CASE WHEN clicked_at IS NOT NULL THEN 1 END) AS FLOAT) /
          NULLIF(COUNT(*), 0) * 100,
          2
        ) as click_rate
      FROM email_sends es
    `;

    let args = [];

    if (campaignId) {
      query += `
        JOIN user_email_subscriptions sub ON es.subscription_id = sub.id
        WHERE sub.campaign_id = ? AND es.sent_at >= datetime('now', '-${lookbackDays} days')
      `;
      args = [campaignId];
    } else {
      query += ` WHERE es.sent_at >= datetime('now', '-${lookbackDays} days')`;
    }

    query += `
      GROUP BY date(sent_at)
      ORDER BY date(sent_at) DESC
    `;

    const result = await db.execute({ sql: query, args });

    return result.rows;
  } finally {
    db.close();
  }
}

/**
 * Get top performing emails
 *
 * @param {number} limit - Number of results to return (default: 10)
 * @param {Object} env - Environment variables
 * @returns {Promise<Array>} Top performing emails
 */
export async function getTopPerformingEmails(limit, env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    const resultLimit = limit || 10;

    const result = await db.execute({
      sql: `
        SELECT * FROM sequence_analytics
        WHERE sends > 0
        ORDER BY click_rate DESC, open_rate DESC
        LIMIT ?
      `,
      args: [resultLimit],
    });

    return result.rows;
  } finally {
    db.close();
  }
}

/**
 * Get underperforming emails
 *
 * Identifies emails that need optimization.
 *
 * @param {number} limit - Number of results to return (default: 10)
 * @param {Object} env - Environment variables
 * @returns {Promise<Array>} Underperforming emails
 */
export async function getUnderperformingEmails(limit, env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    const resultLimit = limit || 10;

    const result = await db.execute({
      sql: `
        SELECT * FROM sequence_analytics
        WHERE sends >= 10
        ORDER BY click_rate ASC, open_rate ASC
        LIMIT ?
      `,
      args: [resultLimit],
    });

    return result.rows;
  } finally {
    db.close();
  }
}

/**
 * Get user engagement profile
 *
 * Shows how engaged a specific user is with marketing emails.
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} User engagement data
 */
export async function getUserEngagement(userId, env) {
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN,
  });

  try {
    // Get user's subscriptions
    const subscriptions = await db.execute({
      sql: `
        SELECT
          sub.id,
          sub.campaign_id,
          c.name as campaign_name,
          sub.enrolled_at,
          sub.status,
          sub.converted_at,
          sub.converted_to_tier
        FROM user_email_subscriptions sub
        JOIN email_campaigns c ON sub.campaign_id = c.id
        WHERE sub.user_id = ?
        ORDER BY sub.enrolled_at DESC
      `,
      args: [userId],
    });

    // Get user's email engagement
    const engagement = await db.execute({
      sql: `
        SELECT
          COUNT(*) as total_received,
          COUNT(CASE WHEN opened_at IS NOT NULL THEN 1 END) as total_opened,
          COUNT(CASE WHEN clicked_at IS NOT NULL THEN 1 END) as total_clicked,
          ROUND(
            CAST(COUNT(CASE WHEN opened_at IS NOT NULL THEN 1 END) AS FLOAT) /
            NULLIF(COUNT(*), 0) * 100,
            2
          ) as open_rate,
          ROUND(
            CAST(COUNT(CASE WHEN clicked_at IS NOT NULL THEN 1 END) AS FLOAT) /
            NULLIF(COUNT(*), 0) * 100,
            2
          ) as click_rate,
          MAX(sent_at) as last_email_sent,
          MAX(opened_at) as last_email_opened,
          MAX(clicked_at) as last_email_clicked
        FROM email_sends
        WHERE user_id = ?
      `,
      args: [userId],
    });

    // Get recent emails
    const recentEmails = await db.execute({
      sql: `
        SELECT
          es.id,
          es.sent_at,
          es.subject_line_used,
          es.opened_at,
          es.clicked_at,
          seq.email_type,
          c.name as campaign_name
        FROM email_sends es
        JOIN email_sequences seq ON es.sequence_id = seq.id
        JOIN email_campaigns c ON seq.campaign_id = c.id
        WHERE es.user_id = ?
        ORDER BY es.sent_at DESC
        LIMIT 20
      `,
      args: [userId],
    });

    return {
      user_id: userId,
      subscriptions: subscriptions.rows,
      engagement: engagement.rows[0],
      recent_emails: recentEmails.rows,
    };
  } finally {
    db.close();
  }
}

/**
 * Export analytics report
 *
 * Generates a comprehensive analytics report for a campaign.
 *
 * @param {string} campaignId - Campaign ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Complete analytics report
 */
export async function exportAnalyticsReport(campaignId, env) {
  const [
    performance,
    sequences,
    abTests,
    funnel,
    revenue,
    timeline,
  ] = await Promise.all([
    getCampaignPerformance(campaignId, env),
    getSequencePerformance(campaignId, env),
    getABTestResults(campaignId, env),
    getConversionFunnel(campaignId, env),
    getRevenueAttribution(campaignId, env),
    getEngagementTimeline(campaignId, 30, env),
  ]);

  return {
    campaign_id: campaignId,
    generated_at: new Date().toISOString(),
    performance: performance[0],
    sequences,
    ab_tests: abTests,
    funnel,
    revenue: revenue[0],
    timeline,
  };
}
