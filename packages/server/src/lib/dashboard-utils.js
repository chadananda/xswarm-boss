/**
 * Dashboard Utilities
 *
 * Aggregates data and formats it for dashboard display.
 * Provides analytics calculations and chart data formatting.
 */

import { getCurrentUsage, getUsageHistory } from './usage-tracker.js';
import { getUserById } from './users.js';
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
 * Get dashboard overview data
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 * @returns {Object} Overview data for dashboard
 */
export async function getDashboardOverview(userId, env) {
  try {
    const user = await getUserById(userId, env);
    const usage = await getCurrentUsage(userId, env);

    // Get plan details
    const planInfo = getPlanInfo(user.subscription_tier);

    // Calculate days remaining in billing period
    const periodEnd = new Date(usage.period_end);
    const now = new Date();
    const daysRemaining = Math.ceil((periodEnd - now) / (1000 * 60 * 60 * 24));

    // Get quick stats
    const stats = {
      voice_minutes_used: usage.voice_minutes,
      voice_minutes_limit: usage.limits.voice_minutes,
      voice_minutes_remaining: usage.limits.voice_minutes === -1 ? -1 : Math.max(0, usage.limits.voice_minutes - usage.voice_minutes),
      sms_used: usage.sms_messages,
      sms_limit: usage.limits.sms_messages,
      sms_remaining: usage.limits.sms_messages === -1 ? -1 : Math.max(0, usage.limits.sms_messages - usage.sms_messages),
      emails_sent: usage.email_count,
      total_overage_cost: usage.costs.total_overage,
    };

    return {
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        subscription_tier: user.subscription_tier,
        created_at: user.created_at,
      },
      plan: planInfo,
      billing_period: {
        start: usage.period_start,
        end: usage.period_end,
        days_remaining: daysRemaining,
      },
      stats,
      alerts: generateAlerts(usage),
    };
  } catch (error) {
    console.error('Error getting dashboard overview:', error);
    throw error;
  }
}

/**
 * Get detailed usage analytics with time series data
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 * @returns {Object} Usage analytics data
 */
export async function getUsageAnalytics(userId, env) {
  try {
    const currentUsage = await getCurrentUsage(userId, env);
    const history = await getUsageHistory(userId, 12, env);

    // Format data for charts
    const chartData = {
      voice: formatChartData(history, 'voice_minutes', 'Voice Minutes'),
      sms: formatChartData(history, 'sms_messages', 'SMS Messages'),
      email: formatChartData(history, 'email_count', 'Emails'),
    };

    // Calculate trends
    const trends = calculateTrends(history);

    return {
      current: currentUsage,
      history,
      charts: chartData,
      trends,
      comparative: getComparativeAnalytics(history),
    };
  } catch (error) {
    console.error('Error getting usage analytics:', error);
    throw error;
  }
}

/**
 * Get billing history and invoices
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 * @returns {Object} Billing history data
 */
export async function getBillingHistory(userId, env) {
  try {
    const db = getDbClient(env);
    const user = await getUserById(userId, env);

    // Get billing records
    const result = await db.execute({
      sql: `
        SELECT * FROM billing_history
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 12
      `,
      args: [userId],
    });

    const billingRecords = result.rows.map(formatBillingRecord);

    // Calculate upcoming charges
    const currentUsage = await getCurrentUsage(userId, env);
    const planPrice = getPlanPrice(user.subscription_tier);
    const upcomingCharge = {
      base_price: planPrice,
      overage_charges: currentUsage.costs.total_overage,
      total: planPrice + currentUsage.costs.total_overage,
      billing_date: currentUsage.period_end,
    };

    return {
      history: billingRecords,
      upcoming: upcomingCharge,
      payment_method: user.stripe_customer_id ? 'card' : 'none',
    };
  } catch (error) {
    console.error('Error getting billing history:', error);
    throw error;
  }
}

/**
 * Get subscription details
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 * @returns {Object} Subscription details
 */
export async function getSubscriptionDetails(userId, env) {
  try {
    const user = await getUserById(userId, env);
    const usage = await getCurrentUsage(userId, env);
    const planInfo = getPlanInfo(user.subscription_tier);

    return {
      current_plan: {
        tier: user.subscription_tier,
        name: planInfo.name,
        price: planInfo.price,
        features: planInfo.features,
        limits: usage.limits,
      },
      billing: {
        period_start: usage.period_start,
        period_end: usage.period_end,
        next_billing_date: usage.period_end,
      },
      stripe: {
        customer_id: user.stripe_customer_id,
        subscription_id: user.stripe_subscription_id,
      },
      upgrade_options: getUpgradeOptions(user.subscription_tier),
    };
  } catch (error) {
    console.error('Error getting subscription details:', error);
    throw error;
  }
}

/**
 * Format data for Chart.js
 */
function formatChartData(history, field, label) {
  const labels = history.map(h => {
    const date = new Date(h.period_start);
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }).reverse();

  const data = history.map(h => h[field] || 0).reverse();

  return {
    labels,
    datasets: [
      {
        label,
        data,
        borderColor: 'rgb(0, 217, 255)',
        backgroundColor: 'rgba(0, 217, 255, 0.1)',
        tension: 0.3,
      },
    ],
  };
}

/**
 * Calculate usage trends
 */
function calculateTrends(history) {
  if (history.length < 2) {
    return { voice: 0, sms: 0, email: 0 };
  }

  const current = history[0];
  const previous = history[1];

  return {
    voice: calculatePercentageChange(previous.voice_minutes, current.voice_minutes),
    sms: calculatePercentageChange(previous.sms_messages, current.sms_messages),
    email: calculatePercentageChange(previous.email_count, current.email_count),
  };
}

/**
 * Calculate percentage change
 */
function calculatePercentageChange(oldValue, newValue) {
  if (oldValue === 0) return newValue > 0 ? 100 : 0;
  return Math.round(((newValue - oldValue) / oldValue) * 100);
}

/**
 * Get comparative analytics (this month vs last month)
 */
function getComparativeAnalytics(history) {
  if (history.length < 2) {
    return null;
  }

  const current = history[0];
  const previous = history[1];

  return {
    current_period: {
      voice_minutes: current.voice_minutes,
      sms_messages: current.sms_messages,
      email_count: current.email_count,
      period: current.period_start,
    },
    previous_period: {
      voice_minutes: previous.voice_minutes,
      sms_messages: previous.sms_messages,
      email_count: previous.email_count,
      period: previous.period_start,
    },
    changes: {
      voice_minutes: current.voice_minutes - previous.voice_minutes,
      sms_messages: current.sms_messages - previous.sms_messages,
      email_count: current.email_count - previous.email_count,
      voice_percent: calculatePercentageChange(previous.voice_minutes, current.voice_minutes),
      sms_percent: calculatePercentageChange(previous.sms_messages, current.sms_messages),
      email_percent: calculatePercentageChange(previous.email_count, current.email_count),
    },
  };
}

/**
 * Generate usage alerts
 */
function generateAlerts(usage) {
  const alerts = [];

  // Voice usage alert
  if (usage.limits.voice_minutes > 0 && usage.usage_percentages.voice >= 80) {
    alerts.push({
      type: 'warning',
      category: 'voice',
      message: `You've used ${usage.usage_percentages.voice.toFixed(0)}% of your voice minutes`,
      severity: usage.usage_percentages.voice >= 100 ? 'high' : 'medium',
    });
  }

  // SMS usage alert
  if (usage.limits.sms_messages > 0 && usage.usage_percentages.sms >= 80) {
    alerts.push({
      type: 'warning',
      category: 'sms',
      message: `You've used ${usage.usage_percentages.sms.toFixed(0)}% of your SMS messages`,
      severity: usage.usage_percentages.sms >= 100 ? 'high' : 'medium',
    });
  }

  // Overage cost alert
  if (usage.costs.total_overage > 0) {
    alerts.push({
      type: 'info',
      category: 'billing',
      message: `You have $${usage.costs.total_overage.toFixed(2)} in overage charges this period`,
      severity: usage.costs.total_overage > 10 ? 'high' : 'low',
    });
  }

  return alerts;
}

/**
 * Get plan information
 */
function getPlanInfo(tier) {
  const plans = {
    ai_buddy: {
      name: 'AI Buddy',
      price: 0,
      features: ['Email only', '100 emails/day', 'Basic AI assistance'],
    },
    ai_secretary: {
      name: 'AI Secretary',
      price: 40,
      features: [
        'Unlimited emails',
        '100 voice minutes/month',
        '100 SMS messages/month',
        'Voice AI assistant',
        'SMS notifications',
      ],
    },
    ai_project_manager: {
      name: 'AI Project Manager',
      price: 280,
      features: [
        'Everything in AI Secretary',
        '500 voice minutes/month',
        '500 SMS messages/month',
        'Team management',
        'Buzz marketing platform',
        'Priority support',
      ],
    },
    ai_cto: {
      name: 'AI CTO',
      price: null, // Custom pricing
      features: [
        'Unlimited everything',
        'Dedicated infrastructure',
        'Custom integrations',
        'Enterprise support',
        '24/7 availability',
      ],
    },
    admin: {
      name: 'Admin',
      price: 0,
      features: ['Unlimited access to all features'],
    },
  };

  return plans[tier] || plans.ai_buddy;
}

/**
 * Get plan monthly price
 */
function getPlanPrice(tier) {
  const prices = {
    ai_buddy: 0,
    ai_secretary: 40,
    ai_project_manager: 280,
    ai_cto: 0, // Custom
    admin: 0,
  };

  return prices[tier] || 0;
}

/**
 * Get upgrade options for current tier
 */
function getUpgradeOptions(currentTier) {
  const tierHierarchy = ['ai_buddy', 'ai_secretary', 'ai_project_manager', 'ai_cto'];
  const currentIndex = tierHierarchy.indexOf(currentTier);

  if (currentIndex === -1 || currentTier === 'admin') {
    return [];
  }

  const options = [];
  for (let i = currentIndex + 1; i < tierHierarchy.length; i++) {
    const tier = tierHierarchy[i];
    const planInfo = getPlanInfo(tier);
    options.push({
      tier,
      name: planInfo.name,
      price: planInfo.price,
      features: planInfo.features,
    });
  }

  return options;
}

/**
 * Format billing record from database row
 */
function formatBillingRecord(row) {
  return {
    id: row.id,
    user_id: row.user_id,
    amount: row.amount,
    status: row.status,
    description: row.description,
    invoice_url: row.invoice_url,
    period_start: row.period_start,
    period_end: row.period_end,
    created_at: row.created_at,
  };
}
