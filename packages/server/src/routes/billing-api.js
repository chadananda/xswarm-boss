/**
 * Billing API Endpoints
 *
 * Provides billing information and cost estimates for users.
 */

import { getCurrentUsage, getUsageHistory } from '../lib/usage-tracker.js';
import { calculateOverages, calculateProration, getUpcomingInvoice } from '../lib/billing.js';
import { getUserById } from '../lib/users.js';
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
 * GET /api/billing/usage - Get current usage and limits
 */
export async function handleGetUsage(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const usage = await getCurrentUsage(user.id, env);
    const overages = await calculateOverages(user.id, env);

    return new Response(JSON.stringify({
      period: {
        start: usage.period_start,
        end: usage.period_end,
      },
      usage: {
        voice_minutes: usage.voice_minutes,
        sms_messages: usage.sms_messages,
        email_count: usage.email_count,
      },
      limits: usage.limits,
      overages: {
        voice_minutes: overages.voice.overage_units,
        sms_messages: overages.sms.overage_units,
      },
      costs: {
        voice_overage: (overages.voice.cost_cents / 100).toFixed(2),
        sms_overage: (overages.sms.cost_cents / 100).toFixed(2),
        phone_number: (overages.phone.cost_cents / 100).toFixed(2),
        total_overage: overages.total_dollars,
      },
      usage_percentages: usage.usage_percentages,
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error getting usage:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * GET /api/billing/history - Get billing history
 */
export async function handleGetBillingHistory(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const db = getDbClient(env);

    // Get billing history
    const historyResult = await db.execute({
      sql: `
        SELECT * FROM billing_history
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 12
      `,
      args: [user.id],
    });

    const history = historyResult.rows.map(row => ({
      id: row.id,
      amount: (row.amount / 100).toFixed(2),
      status: row.status,
      description: row.description,
      invoice_url: row.invoice_url,
      period_start: row.period_start,
      period_end: row.period_end,
      created_at: row.created_at,
    }));

    // Get billing events
    const eventsResult = await db.execute({
      sql: `
        SELECT * FROM billing_events
        WHERE user_id = ?
        ORDER BY processed_at DESC
        LIMIT 50
      `,
      args: [user.id],
    });

    const events = eventsResult.rows.map(row => ({
      event_type: row.event_type,
      amount: row.amount_cents ? (row.amount_cents / 100).toFixed(2) : null,
      description: row.description,
      processed_at: row.processed_at,
    }));

    return new Response(JSON.stringify({
      history,
      events,
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error getting billing history:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * POST /api/billing/estimate - Estimate costs for tier change
 */
export async function handleEstimateCosts(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = await request.json();
    const { target_tier } = body;

    if (!target_tier) {
      return new Response(JSON.stringify({ error: 'target_tier is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const usage = await getCurrentUsage(user.id, env);
    const periodStart = new Date(usage.period_start);
    const periodEnd = new Date(usage.period_end);

    const proration = await calculateProration(
      user.subscription_tier,
      target_tier,
      periodStart,
      periodEnd,
      env
    );

    // Calculate future limits with new tier
    const tierLimits = {
      ai_buddy: {
        voice_minutes: 0,
        sms_messages: 0,
      },
      ai_secretary: {
        voice_minutes: 100,
        sms_messages: 100,
      },
      ai_project_manager: {
        voice_minutes: 500,
        sms_messages: 500,
      },
      ai_cto: {
        voice_minutes: -1,
        sms_messages: -1,
      },
    };

    const newLimits = tierLimits[target_tier] || tierLimits.ai_buddy;

    return new Response(JSON.stringify({
      current_tier: proration.current_tier,
      new_tier: proration.new_tier,
      proration: {
        unused_credit: proration.unused_credit_cents / 100,
        prorated_charge: proration.prorated_charge_cents / 100,
        net_charge: proration.net_charge_dollars,
      },
      new_limits: newLimits,
      billing_date: usage.period_end,
      summary: {
        immediate_charge: proration.net_charge_dollars,
        monthly_price: (proration.new_price_cents / 100).toFixed(2),
      },
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error estimating costs:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * GET /api/billing/upcoming - Get upcoming invoice
 */
export async function handleGetUpcomingInvoice(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (!user.stripe_customer_id) {
      return new Response(JSON.stringify({ error: 'No Stripe customer found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const upcoming = await getUpcomingInvoice(user.stripe_customer_id, env);

    return new Response(JSON.stringify(upcoming), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error getting upcoming invoice:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
